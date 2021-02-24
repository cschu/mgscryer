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
PROJECT_QUERY = "search?query=host_tax_id=9606%20AND%20(instrument_platform=%22ILLUMINA%22%20AND%20(%20instrument_model!=%22Illumina%20Genome%20Analyzer%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20II%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20IIx%22%20)%20AND%20(%20(%20library_strategy=%22WGS%22%20AND%20library_source=%22METAGENOMIC%22%20)%20OR%20(%20library_strategy=%22RNA-Seq%22%20AND%20library_source=%22METATRANSCRIPTOMIC%22%20)%20))&result=read_study"

DEBUG = False

class Entity:
    @staticmethod
    def get_tag_value_pairs(xml):
        for child in xml.children:
            yield child.find("TAG").text.lower(), child.find("VALUE").text.lower()
    @staticmethod
    def parse_xlink_ids(ids):
        start, end = ids.split("-")
        prefix = "".join(map(lambda c:(c if c.isalpha() else " "), start)).strip().split(" ")[0]
        suffix = "{{id:0{n}d}}".format(n=len(start) - len(prefix))
        start, end = map(lambda x:int(x[len(prefix):]), (start, end))
        return ["{prefix}{suffix}".format(prefix=prefix, suffix=suffix.format(id=_id)) for _id in range(start, end + 1)]
    @staticmethod
    def parse_xlinks(xml):
        d = dict()
        for plink in xml.children:
            xlink = plink.find("XREF_LINK")
            db, val = map(lambda x:x.text, xlink.children)
            db = db.lower()
            if db in {"pubmed", "ena-sample", "ena-experiment", "ena-run"}:
                d[db] = db_ids = list()
                for ids in val.split(","):
                    if "-" in ids:
                        db_ids.extend(Entity.parse_xlink_ids(ids))
                    else:
                        db_ids.append(ids)
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
            caller_attribs = dict(Entity.get_tag_value_pairs(
                xml.find("{cls}_ATTRIBUTES".format(cls=caller.__name__.upper()))))

            attribs["ena_first_public"] = caller_attribs.get("ena-first-public")
            attribs["ena_last_update"] = caller_attribs.get("ena-last-update")
            attribs["read_count"] = caller_attribs.get("ena-spot-count")

        return attribs
    def get_linked_entities(self, entity):
        for _id in self.xlinks.get("ena-{}".format(entity.__name__.lower()), list()):
            xml = rest_query(_id)
            if DEBUG:
                print(xml)
            try:
                entity_obj = entity.from_xml(getattr(xml, "{entity}_SET".format(entity=entity.__name__.upper())))
                if DEBUG:
                    entity_obj.show()
            except:
                print("WARNING: {entity_type} {id} does not yield result.".format(
                    entity_type="ENA-{}".format(entity.__name__.upper()), id=_id),
                    file=sys.stderr)
                entity_obj = None
                raise
            yield _id, entity_obj

    def __init__(self, **args):
        self.children = dict()
        self.primary_id = None
        for k, v in args.items():
            setattr(self, k, v)
    def show(self):
        print(*self.__dict__.items(), sep="\n")
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
            print("existing record", table, self.primary_id)
        for child_id, child in self.children.items():
            has_updates |= child.process_updates(cursor)
            update_links(cursor, self, child)
        return has_updates
    def insert_into_db(self, cursor):
        table = self.__class__.__name__.lower()
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
        attribs["read_count"] = run_attribs["ena-spot-count"]
        attribs["ena_first_public"] = run_attribs["ena-first-public"]
        attribs["ena_last_update"] = run_attribs["ena-last-update"]

        return Run(**attribs)
    def as_tuple(self):
        return (self.primary_id, self.title, self.read_count, self.ena_first_public, self.ena_last_update)

class Experiment(Entity):
    def __init__(self, **args):
        super().__init__(**args)
        try:
            self.children = dict(self.get_linked_entities(Run))
        except:
            self.children = dict()
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
            attribs["spot_length"] = design.find("SPOT_LENGTH").text

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
        try:
            self.children = dict(self.get_linked_entities(Experiment))
        except:
            self.children = dict()
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
        attribs["ena_first_public"] = sample_attribs["ena-first-public"]
        attribs["ena_last_update"] = sample_attribs["ena-last-update"]
        return Sample(**attribs)

    def as_tuple(self):
        return (self.primary_id, self.biosample, self.title, self.taxon_id, self.scientific_name,
                self.ena_first_public, self.ena_last_update)

class Project(Entity):
    def __init__(self, **args):
        super().__init__(**args)
        try:
            self.children = dict(self.get_linked_entities(Sample))
        except:
            self.children = dict()
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
        attribs["ena_first_public"] = proj_attribs["ena-first-public"]
        attribs["ena_last_update"] = proj_attribs["ena-last-update"]
        print(*attribs.items(), sep="\n")
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
    return None

def insert_record(cursor, table, values):
    cmd = "INSERT INTO {table} VALUES ({dummy})".format(
        table=table, dummy=",".join("?" for f in values))
    res = cursor.execute(cmd, values)
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
        print("new link: {} <- {}".format(entity1.primary_id, entity2.primary_id))
        insert_record(cursor, link_table, (entity1.primary_id, entity2.primary_id))

def update_record(cursor, table, _id, updates):
    update_ops = ", ".join(["{col} = ?".format(col=col) for col, _ in updates])
    cmd = "UPDATE {table} SET {update_ops} WHERE id = ?;".format(table=table, update_ops=update_ops)
    print(cmd)
    res = cursor.execute(cmd, [val for _, val in updates] + [_id])
    for row in res:
        print(row) 

def rest_query(query_str, base_url=BASE_API_URL):
    if DEBUG:
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
            if i > 10:
                break
            project = Project.from_xml(project)
            has_updates = project.process_updates(cursor)
            print("*************************************************")


if __name__ == "__main__":
    main()
