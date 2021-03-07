import time
import re
import sys
from datetime import datetime
import urllib.parse
import argparse
import sqlite3

from bs4 import BeautifulSoup
import urllib3
import requests

BASE_API_URL = "https://www.ebi.ac.uk/ena/browser/api/xml/"
PROJECT_QUERY = "search?query=host_tax_id=9606%20AND%20(instrument_platform=%22ILLUMINA%22%20AND%20(%20instrument_model!=%22Illumina%20Genome%20Analyzer%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20II%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20IIx%22%20)%20AND%20(%20(%20library_strategy=%22WGS%22%20AND%20library_source=%22METAGENOMIC%22%20)%20OR%20(%20library_strategy=%22RNA-Seq%22%20AND%20library_source=%22METATRANSCRIPTOMIC%22%20)%20))&result=read_study&sortFields=accession" #last_updated" <- this doesn't work >:(

DEBUG = False

class EntityParseError(Exception):
    ...

class Entity:
    @staticmethod
    def get_tag_value_pairs(xml):
        for child in xml.children:
            tag = child.find("TAG")
            if tag:
                tag = tag.text.lower()
            value = child.find("VALUE")
            if value:
                value = value.text.lower()
            if tag and value:
                yield tag, value
    @staticmethod
    def parse_xlink_ids(ids):
        individual_ids = list()
        ids = ids.split(",")
        for item in ids:
            item = item.split("-")
            if len(item) == 1:
                individual_ids.extend(item)
            else:
                start, end = item
                prefix = "".join(map(lambda c:(c if c.isalpha() else " "), start)).strip().split(" ")[0]
                suffix = "{{id:0{n}d}}".format(n=len(start) - len(prefix))
                start, end = map(lambda x:int(x[len(prefix):]), (start, end))
                individual_ids.extend("{prefix}{suffix}".format(prefix=prefix, suffix=suffix.format(id=_id)) for _id in range(start, end + 1))
        return individual_ids
    @staticmethod
    def parse_xlinks(xml):
        d = dict()
        for link in xml.children:
            xlink = link.find("XREF_LINK")
            db, val = map(lambda x:x.text, xlink.children)
            db = db.lower()
            if db == "pubmed":
                d[db] = val.split(",")
            elif db in {"ena-sample", "ena-experiment", "ena-run"}:
                d[db] = val
        return d
    @staticmethod
    def parse_common_fields(xml, caller=None):
        attribs = dict()
        identifiers = xml.find("IDENTIFIERS")
        for field in ("primary_id", "secondary_id", "name", "title", "description"):
            try:
                attribs[field] = identifiers.find(field.upper()).text
            except:
                attribs[field] = None

        if caller:
            caller_attribs = xml.find("{cls}_ATTRIBUTES".format(cls=caller.__name__.upper()))
            if caller_attribs:
                caller_attribs = dict(Entity.get_tag_value_pairs(caller_attribs))

                attribs["ena_first_public"] = caller_attribs.get("ena-first-public")
                attribs["ena_last_update"] = caller_attribs.get("ena-last-update")
                attribs["read_count"] = caller_attribs.get("ena-spot-count")

        return attribs
    def get_linked_entities(self, entity_type):
        entity_name = entity_type.__name__
        entities = dict()
        ids = self.xlinks.get("ena-{}".format(entity_name.lower()))
        if ids:
            for idrange in ids.split(","):
                xml = rest_query(idrange)
                if DEBUG:
                    print(entity_name)
                    print(xml)
                for entity_xml in xml.find_all(entity_name.upper()):
                    try:
                        entity_obj = entity_type.from_xml(entity_xml)
                        if DEBUG:
                            entity_obj.show()
                    except:
                        raise EntityParseError("{entity_type} could not be parsed.\n{xml}".format(entity_type=entity_name.lower(), xml=entity_xml))
                    entities[entity_obj.primary_id] = entity_obj

        return entities

    def __init__(self, **args):
        self.children = dict()
        self.primary_id = None
        for k, v in args.items():
            setattr(self, k, v)
    def show(self):
        print(self.primary_id, self.ena_last_update, len(self.children), sep="\n")
        #print(*self.__dict__.items(), sep="\n")
    def as_tuple(self):
        return tuple()
    def exists_in_db(self, cursor):
        requires_update = False
        exists = list(check_record_exists(cursor, self.__class__.__name__.lower(), self.primary_id))
        if exists and not isinstance(self, Experiment):
            # we assume that experiments are never updated? they don't have a timestamp
            new_ts, cur_ts = map(datetime.fromisoformat,
                (self.ena_last_update, exists[-2 if isinstance(self, Project) else -1][1]))
            requires_update = new_ts > cur_ts
        return exists, requires_update
    def process_updates(self, cursor):
        has_updates = False
        table = self.__class__.__name__.lower()
        existing_record, requires_update = self.exists_in_db(cursor)
        if not existing_record:
            has_updates = True
            self.insert_into_db(cursor)
        elif requires_update:
            has_updates = True
            self.update_db_record(cursor, existing_record)
        else:
            if DEBUG:
                print("existing record", table, self.primary_id)
        for child_id, child in self.children.items():
            has_updates |= child.process_updates(cursor)
            update_links(cursor, self, child)
        return has_updates
    def insert_into_db(self, cursor):
        table = self.__class__.__name__.lower()
        if DEBUG:
            print("new {table} record: {id}".format(table=table, id=self.primary_id))
        insert_record(cursor, table, self.as_tuple())
    def update_db_record(self, cursor, current_record):
        updates = [(header, new_col)
                   for (header, cur_col), new_col in zip(current_record, self.as_tuple())
                   if new_col != cur_col]
        update_record(cursor, self.__class__.__name__.lower(), self.primary_id, updates)
        print("record updated:", self.__class__.__name__.lower(), self.primary_id, updates)

class Run(Entity):
    def __init__(self, **args):
        super().__init__(**args)
    @classmethod
    def from_xml(cls, xml):
        attribs = Entity.parse_common_fields(xml, caller=cls)

        run_attribs = dict(Entity.get_tag_value_pairs(xml.find("RUN_ATTRIBUTES")))
        attribs["read_count"] = run_attribs.get("ena-spot-count")
        attribs["ena_first_public"] = run_attribs.get("ena-first-public")
        attribs["ena_last_update"] = run_attribs.get("ena-last-update")

        attribs["xlinks"] = Entity.parse_xlinks(xml.find("RUN_LINKS"))

        return Run(**attribs)
    def as_tuple(self):
        return (self.primary_id, self.title, self.read_count, self.ena_first_public, self.ena_last_update)

class Experiment(Entity):
    def __init__(self, **args):
        super().__init__(**args)
    @classmethod
    def from_xml(cls, xml):
        attribs = Entity.parse_common_fields(xml, caller=cls)

        design = xml.find("DESIGN")
        if design:
            lib_desc = design.find("LIBRARY_DESCRIPTOR")
            if lib_desc:
                for child in lib_desc.children:
                    tag = child.name.lower()
                    if tag in ("library_strategy", "library_source", "library_selection"):
                        attribs[tag] = child.text
                    elif tag == "library_layout":
                        attribs["library_layout"] = next(child.children).name
            try:
                attribs["spot_length"] = design.find("SPOT_LENGTH").text
            except:
                attribs["spot_length"] = None

        platform = xml.find("PLATFORM")
        attribs["instrument"] = platform.find("INSTRUMENT_MODEL").text

        attribs["xlinks"] = Entity.parse_xlinks(xml.find("EXPERIMENT_LINKS"))

        return Experiment(**attribs)

    def as_tuple(self):
        return (self.primary_id, self.title, self.library_strategy, self.library_source,
                self.library_selection, self.library_layout, self.spot_length, self.instrument)


class Sample(Entity):
    def __init__(self, **args):
        super().__init__(**args)
    @classmethod
    def from_xml(cls, xml):
        attribs = Entity.parse_common_fields(xml, caller=cls)

        biosample = xml.find("IDENTIFIERS").find(namespace="BioSample")
        attribs["biosample"] = biosample.text if biosample else None
        tax_attribs = xml.find("SAMPLE_NAME")
        try:
            taxon_id, scientific_name = map(lambda x:x.text, tax_attribs.children)
        except:
            taxon_id, scientific_name = None, None
        attribs.update({"taxon_id": taxon_id, "scientific_name": scientific_name})

        attribs["xlinks"] = Entity.parse_xlinks(xml.find("SAMPLE_LINKS"))

        sample_attribs = dict(Entity.get_tag_value_pairs(xml.find("SAMPLE_ATTRIBUTES")))
        attribs["ena_first_public"] = sample_attribs.get("ena-first-public")
        attribs["ena_last_update"] = sample_attribs.get("ena-last-update")
        return Sample(**attribs)

    def as_tuple(self):
        return (self.primary_id, self.biosample, self.title, self.taxon_id, self.scientific_name,
                self.ena_first_public, self.ena_last_update)

class Project(Entity):
    def __init__(self, **args):
        super().__init__(**args)
        self._process_children()
    def _process_children(self):
        self.children = samples = self.get_linked_entities(Sample)
        experiments = self.get_linked_entities(Experiment)
        runs = self.get_linked_entities(Run)

        for sample_id, sample in samples.items():
            experiment_ids = sample.xlinks.get("ena-experiment")
            if not experiment_ids:
                raise ValueError("cannot find experiment ids for sample {}".format(sample.primary_id))
            for experiment_id in Entity.parse_xlink_ids(experiment_ids):
                experiment = experiments.get(experiment_id)
                if not experiment:
                    print(*experiments.items(), sep="\n")
                    raise ValueError("didn't parse experiment {} for project {}".format(experiment_id, self.primary_id))
                sample.children[experiment_id] = experiment
                run_ids = experiment.xlinks.get("ena-run")
                if not run_ids:
                    raise ValueError("cannot find run ids for experiment {}".format(experiment.primary_id))
                for run_id in Entity.parse_xlink_ids(run_ids):
                    run = runs.get(run_id)
                    if not run:
                        raise ValueError("didn't parse run {} for project {}".format(run_id, self.primary_id))
                    experiment.children[run_id] = run
    @classmethod
    def from_xml(cls, xml):
        attribs = Entity.parse_common_fields(xml, caller=cls)

        tax_attribs = xml.find("SUBMISSION_PROJECT").find("ORGANISM")
        try:
            taxon_id, scientific_name = map(lambda x:x.text, tax_attribs.children)
        except:
            taxon_id, scientific_name = None, None
        attribs.update({"taxon_id": taxon_id, "scientific_name": scientific_name})

        attribs["xlinks"] = Entity.parse_xlinks(xml.find("PROJECT_LINKS"))

        proj_attribs = dict(Entity.get_tag_value_pairs(xml.find("PROJECT_ATTRIBUTES")))
        attribs["ena_first_public"] = proj_attribs.get("ena-first-public")
        attribs["ena_last_update"] = proj_attribs.get("ena-last-update")

        return Project(**attribs)

    def as_tuple(self):
        return (self.primary_id, self.secondary_id, self.name, self.title,
                self.description, self.ena_first_public, self.ena_last_update, None)


def check_link_exists(cursor, table, entity1, entity2, id1, id2):
    cmd = "SELECT * FROM {table} WHERE {entity1}_id = ? AND {entity2}_id = ?;".format(
        table=table, entity1=entity1, entity2=entity2)
    cursor.execute(cmd, (id1, id2))
    rows = cursor.fetchall()
    return rows

def check_record_exists(cursor, table, id_):
    cmd = "SELECT * FROM {table} WHERE id = ?;".format(table=table)
    cursor.execute(cmd, (id_,))
    rows = cursor.fetchall()
    if rows:
        return zip([d[0] for d in cursor.description], rows[0])
    return list()

def insert_record(cursor, table, values):
    cmd = "INSERT INTO {table} VALUES ({dummy})".format(
        table=table, dummy=",".join("?" for f in values))
    res = cursor.execute(cmd, values)
    if DEBUG:
        for row in res:
            print(row)

def get_latest_timestamp(cursor):
    try:
        cursor.execute("SELECT MAX(ena_last_update) FROM study;")
        rows = cursor.fetchall()
        return datetime.fromisoformat(rows[0][0])
    except:
        return datetime(1970, 1, 1)

def update_links(cursor, entity1, entity2):
    table1, table2 = map(lambda x:x.__class__.__name__, (entity1, entity2))
    link_table = "_".join((table1, table2))
    link_exists = check_link_exists(cursor, link_table, table1, table2,
                                    entity1.primary_id, entity2.primary_id)
    if not link_exists:
        if DEBUG:
            print("new link: {} <- {}".format(entity1.primary_id, entity2.primary_id))
        insert_record(cursor, link_table, (entity1.primary_id, entity2.primary_id))

def update_record(cursor, table, _id, updates):
    update_ops = ", ".join(["{col} = ?".format(col=col) for col, _ in updates])
    cmd = "UPDATE {table} SET {update_ops} WHERE id = ?;".format(table=table, update_ops=update_ops)
    if DEBUG:
        print(cmd)
    res = cursor.execute(cmd, [val for _, val in updates] + [_id])
    if DEBUG:
        for row in res:
            print(row)

def rest_query(query_str, base_url=BASE_API_URL, verbose=False):
    time.sleep(0.1)
    if verbose:
        print(base_url + query_str)
    xml = requests.get(base_url + query_str).content.decode()
    xml = xml.replace("\n", "")
    xml = re.sub(">\s+<", "><", xml)
    # https://stackoverflow.com/questions/14822188/dont-put-html-head-and-body-tags-automatically-beautifulsoup
    # THIS SHOULD BE IN THE MAIN DOCS...
    soup = BeautifulSoup(xml, "lxml-xml")
    return soup

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    with conn:
        cursor = conn.cursor()
        latest_timestamp = get_latest_timestamp(cursor)

        soup = rest_query(PROJECT_QUERY)
        projects = soup.PROJECT_SET

        for i, project in enumerate(projects.find_all("PROJECT")):
            #if i > 10:
            #    break
                
            try:
                project = Project.from_xml(project)
            except:
                print(project)
                raise

            for pmid in project.xlinks.get("pubmed", list()):
                try:
                    insert_record(cursor, "project_pubmed", (project.primary_id, pmid))
                except:
                    pass

            has_updates = project.process_updates(cursor)
            if has_updates:
                print("UPDATES available:")
                project.show()
            else:
                print("Project {}: no updates".format(project.primary_id))
            print("*************************************************")


if __name__ == "__main__":
    main()
