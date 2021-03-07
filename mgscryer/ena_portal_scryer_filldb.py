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

from db_helpers import check_record_exists, insert_record, update_record

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

TAX_TREES = {
    256318: "metagenomics",
    9606: "human",
    33208: "animal",
    33090: "green plants"
}


class EnaPortalScryer:
    def __init__(self, base_url, query, sub_query="", limit=1000):
        self.query_string = base_url + query.format(**locals())
        self.offset = 0
        self.limit = limit
    def get_records(self):
        while True:
            time.sleep(0.1)
            query = self.query_string.format(offset=self.offset)
            #print(query)
            data = json.loads(requests.get(query).content.decode())
            for record in data:
                yield record
            if len(data) < self.limit:
                break
            self.offset += self.limit




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    args = ap.parse_args()


    studies = set()
    for tax_tree in TAX_TREES:
        #sub_query="%20AND%20tax_tree(256318)%20AND%20last_updated%3E=2021-02-01"
        sub_query = f"%20AND%20tax_tree({tax_tree})"
        scryer = EnaPortalScryer(BASE_API_URL, MAIN_QUERY, sub_query=sub_query, limit=100000)

        conn = sqlite3.connect(args.db)
        with conn:
            cursor = conn.cursor()

            if True:
	            for record in scryer.get_records():
	                #print(record)
	                studies.add(record["study_accession"])
	
	                study = (record["study_accession"], record["study_title"], 
	                         record["first_public"], record["last_updated"], 1)
	                sample = (record["sample_accession"], record["host"],
	                          record["host_body_site"], record["host_tax_id"],
	                          record["environment_biome"])
	                run = (record["run_accession"], record["experiment_title"],
	                       record["description"], record["instrument_model"], record["instrument_platform"],
	                       record["library_source"], record["library_layout"], record["library_strategy"],
	                       record["nominal_length"], record["read_count"])
	
	                try:
	                    process_updates(cursor, "study", study)     
	                except:
	                    print("Couldn't update study:", study, file=sys.stderr, flush=True)
	                   
	                try:
	                    process_updates(cursor, "sample", sample)
	                except:
	                    print("Couldn't update sample:", sample, file=sys.stderr, flush=True)
	
	                try:
	                    process_updates(cursor, "run", run)
	                except:
	                    print("Couldn't update run:", run, file=sys.stderr, flush=True)
	
	                try:
	                    insert_record(cursor, "study_sample", (record["study_accession"], record["sample_accession"]))
	                except:
	                    print("Couldn't update study_sample:", study[0], sample[0], file=sys.stderr, flush=True)
	                    pass
	                try:
	                    insert_record(cursor, "sample_run", (record["sample_accession"], record["run_accession"]))
	                except:
	                    print("Couldn't update sample_run:", sample, run, file=sys.stderr, flush=True)
	                    pass

            # studies = set(line.strip() for line in open("studies.txt"))
            projects = {_id for _id in studies if _id.startswith("P")}
            studies.difference_update(projects)
            add_pubmed_information(cursor, studies)
            add_pubmed_information(cursor, projects) # !@£$% SRA!

def add_pubmed_information(cursor, studies):
    study_queries = [("accessions", study_id) for study_id in studies]
    xml = requests.post("https://www.ebi.ac.uk/ena/browser/api/xml", data=study_queries).content.decode()
    xml = xml.replace("\n", "")
    xml = re.sub(">\s+<", "><", xml)
    soup = BeautifulSoup(xml, "lxml-xml")
 
    if soup:
        studies = soup.find_all("PROJECT")
        if studies:
            for study in studies:
                study_accession = study.PRIMARY_ID.text
                project_links = study.find("PROJECT_LINKS")
                if project_links:
                    xref_links = project_links.find_all("XREF_LINK")
                    if xref_links:
                        for xref_link in xref_links:
                            try:
                                db, _id = xref_link.DB.text, xref_link.ID.text
                            except:
                                continue
                            if db == "PUBMED":
                                #print(xref_link)
                                #print("******************")
                                try:
                                    insert_record(cursor, "study_pubmed", (study_accession, _id))
                                except:
                                    print("Couldn't update study_pubmed:", study_accession, _id, file=sys.stderr, flush=True)


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


#def check_link_exists(cursor, table, field1, field2, id1, id2):
#def check_record_exists(cursor, table, id_):
#def insert_record(cursor, table, values):
#def get_latest_timestamp(cursor):
#def update_links(cursor, entity1, entity2):
#def update_record(cursor, table, _id, updates):
#def rest_query(query_str, base_url=BASE_API_URL, verbose=False):

#"study_accession":"PRJEB42399"
#"study_title":"Shared signatures and divergence in skin microbiomes of children with atopic dermatitis and their adult caregivers"
#    "sample_accession":"SAMEA7992856"
#    "host":"","host_body_site":"","host_tax_id":""
#    "environment_biome":""
#        "experiment_title":"Illumina HiSeq 4000 paired end sequencing"
#            "run_accession":"ERR5242652"
#            "description":"Illumina HiSeq 4000 paired end sequencing"
#            "instrument_model":"Illumina HiSeq 4000" "instrument_platform":"ILLUMINA"
#            "library_source":"METAGENOMIC","library_layout":"PAIRED","library_strategy":"WGS","nominal_length":"200","read_count":"17596"
#            "first_public":"2021-02-07","last_updated":"2021-02-04"

if __name__ == "__main__":
    main()













