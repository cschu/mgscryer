import time
import re
import sys
from datetime import datetime
import urllib.parse
import argparse
import sqlite3
import json

from bs4 import BeautifulSoup
import requests

from db_helpers import check_record_exists, insert_record, update_record, check_link_exists
from pubmed import PubmedQuery

DEBUG = False

BASE_API_URL = "https://www.ebi.ac.uk/ena/portal/api/"
FIELDS = ["study_accession", "study_title", "experiment_title", "description",
          "host", "host_body_site", "host_tax_id", "instrument_model", "instrument_platform",
          "library_source", "library_layout", "library_strategy", "nominal_length",
          "read_count", "environment_biome", "first_public", "last_updated"]
BASE_QUERY = "instrument_platform=%22ILLUMINA%22" \
             "%20AND((library_strategy=%22WGS%22%20AND%20library_source=%22METAGENOMIC%22)%20" \
             "OR%20(library_strategy=%22RNA-Seq%22%20AND%20library_source=%22METATRANSCRIPTOMIC%22))" \
             "{sub_query}&limit={limit}&offset={{offset}}"

MAIN_QUERY = f"search?result=read_run&includeMetagenomes=1&format=json&fields={','.join(FIELDS)}&query={BASE_QUERY}"

def get_tax_trees(cursor):
    cursor.execute("SELECT * FROM clades;")
    rows = cursor.fetchall()
    return [row[0:2] for row in rows]
def get_last_update(cursor):
    cursor.execute("SELECT date_time FROM timepoints WHERE action = 'last_update';")
    rows = cursor.fetchall()
    return rows[0][0].split("T")[0]
def set_timestamp(cursor):
    now = datetime.isoformat(datetime.now())
    cursor.execute(f"UPDATE timepoints SET date_time = '{now}' WHERE action = 'last_update';")
    rows = cursor.fetchall()
    return rows
	
class Entity:
    FIELDS = []
    def __init__(self, **kwargs):
        for field in self.FIELDS:
            setattr(self, field, kwargs.get(field))
    def to_tuple(self):
        return tuple(getattr(self, field) for field in self.FIELDS)    
    def update_db(self, cursor):
        whatami = self.__class__.__name__.lower()
        try:
            new_record, updated_record = process_updates(cursor, whatami, self.to_tuple())
        except Exception as e:
            print(e)
            print(f"Couldn't update {whatami}:", self.to_tuple(), file=sys.stderr, flush=True)
            new_record, updated_record = False, False
        return new_record, updated_record

class Study(Entity):
    FIELDS = ["study_accession", "study_title", "first_public", "last_updated"]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def to_tuple(self):
        return super().to_tuple() + (0,)

class Sample(Entity):
    FIELDS = ["sample_accession", "host", "host_body_site", "host_tax_id", "environment_biome", "last_updated"]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
class Run(Entity):
    FIELDS = ["run_accession", "experiment_title", 
              "description", "instrument_model", "instrument_platform",
              "library_source", "library_layout", "library_strategy",
              "nominal_length", "read_count", "last_updated"]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Record:
    FIELDS = ["study", "sample", "run"]
    def __init__(self, **kwargs):
        self.study = Study(**kwargs)
        self.sample = Sample(**kwargs)
        self.run = Run(**kwargs)

    def update_db(self, cursor):
        record_states = list()
        for i, field in enumerate(Record.FIELDS):
            entity = getattr(self, field)
            new_record, updated_record = entity.update_db(cursor)
            record_states.append((new_record, updated_record))
            if field != "run":
                entity2 = getattr(self, Record.FIELDS[i + 1])
                table = "_".join(Record.FIELDS[i:i + 2])
                id1, id2 = getattr(entity, entity.FIELDS[0]), getattr(entity2, entity2.FIELDS[0])
                if not check_link_exists(cursor, *table.split("_"), id1, id2):
                    try:
                        insert_record(cursor, table, (id1, id2))
                    except Exception as e:
                        print(e)
                        print(f"Couldn't update {table}: {id1} {id2}")
        return record_states

class EnaPortalScryer:
    def __init__(self, db, base_url=BASE_API_URL, query=MAIN_QUERY, sub_query="", limit=1000, sleep_interval=0.1):
        self.base_url = base_url
        self.query = query
        self.offset = 0
        self.limit = limit
        self.conn = sqlite3.connect(db, isolation_level=None)
        self._get_last_update()
        self.sleep_interval = sleep_interval
    def _get_last_update(self):
        self.last_update = get_last_update(self.conn.cursor())
    def run(self):
        studies = set()
        limit = self.limit
        for tax_tree, tax_label in get_tax_trees(self.conn.cursor()):
            print(f"{tax_label} ({tax_tree}): ", end="", flush=True)
            record_states = dict()
            sub_query = f"%20AND%20tax_tree({tax_tree})%20AND%20last_updated%3E={self.last_update}"
            query_string = self.base_url + self.query.format(**locals())
            response = self._get_records(query_string)
            for i, record in enumerate(response):
                entity_states = record.update_db(self.conn.cursor())
                study_d = record_states.setdefault(record.study.study_accession, dict())
                if not study_d:
                    study_d["state"] = entity_states[0]
                    study_d["samples"] = dict()
                sample_d = study_d["samples"].setdefault(record.sample.sample_accession, dict())
                if not sample_d:
                    sample_d["state"] = entity_states[1]
                    sample_d["runs"] = dict()
                run_d = sample_d["runs"].setdefault(record.run.run_accession, entity_states[2])
                studies.add(record.study.study_accession)
            try:
                i = i
            except:
                print(f"Nothing to see here")
            else:
                self._summarise_updates(record_states)
        self._add_pubmed_information(self.conn.cursor(), studies)
        set_timestamp(self.conn.cursor())
    def _summarise_updates(self, record_states):
        new_studies, updated_studies, new_samples, updated_samples, new_runs, updated_runs = 0, 0, 0, 0, 0, 0
        for study, study_data in record_states.items():
            if study_data["state"][0]:
                new_studies += 1
            elif study_data["state"][1]:
                updated_studies += 1
            for sample, sample_data in study_data["samples"].items():
                if sample_data["state"][0]:
                    new_samples += 1
                elif sample_data["state"][1]:
                    updated_samples += 1
                for run, run_state in sample_data["runs"].items():
                    if run_state[0]:
                        new_runs += 1
                    elif run_state[1]:
                        updated_runs += 1
        print(f"studies {new_studies}|{updated_studies}, samples {new_samples}|{updated_samples}, runs {new_runs}|{updated_runs}")
        
    def _add_pubmed_information(self, cursor, studies):
        def add_pubmed_links(cursor, studies):
            for study_accession, pubmed_id in PubmedQuery.get_ids(studies):
                try:
                    insert_record(cursor, "study_pubmed", (study_accession, pubmed_id))
                except:
                    print("Couldn't update study_pubmed:", study_accession, pubmed_id, file=sys.stderr, flush=True)

        projects = {_id for _id in studies if _id.startswith("P")}
        add_pubmed_links(cursor, studies.difference(projects))
        add_pubmed_links(cursor, projects) # !@£$% SRA!

    def _get_records(self, query_string):
        offset = self.offset
        while True:
            time.sleep(self.sleep_interval)
            query = query_string.format(offset=offset)
            #print(query)
            try:
                data = json.loads(requests.get(query).content.decode())
            except json.decoder.JSONDecodeError:
                break
            for record in data:
                yield Record(**record)
            if len(data) < self.limit:
                break
            offset += self.limit

def exists_in_db(cursor, table, record):
    updates, existing_record = list(), list(check_record_exists(cursor, table, record[0]))
    if existing_record:
        updates = [(header, new_col) 
                   for (header, cur_col), new_col in zip(existing_record, record)
                   if new_col != cur_col]
    return existing_record, updates

def process_updates(cursor, table, record):
    existing_record, updates = exists_in_db(cursor, table, record)
    has_updates = not existing_record or updates
    if not existing_record:
        insert_record(cursor, table, record)
    elif updates:
        update_record(cursor, table, record[0], updates)
    return not existing_record, bool(updates)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    args = ap.parse_args()

    scryer = EnaPortalScryer(args.db)
    print(*scryer.__dict__.items(), sep="\n")
    scryer.run()

if __name__ == "__main__":
    main()
