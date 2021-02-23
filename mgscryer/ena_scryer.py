import re
import sys
import urllib.parse

from bs4 import BeautifulSoup
import urllib3

BASE_API_URL = "https://www.ebi.ac.uk/ena/browser/api/xml/"
PROJECT_QUERY = "search?query=host_tax_id=9606%20AND%20(instrument_platform=%22ILLUMINA%22%20AND%20(%20instrument_model!=%22Illumina%20Genome%20Analyzer%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20II%22%20AND%20instrument_model!=%22Illumina%20Genome%20Analyzer%20IIx%22%20)%20AND%20(%20(%20library_strategy=%22WGS%22%20AND%20library_source=%22METAGENOMIC%22%20)%20OR%20(%20library_strategy=%22RNA-Seq%22%20AND%20library_source=%22METATRANSCRIPTOMIC%22%20)%20))&result=read_study"


class Entity:
    @staticmethod
    def get_tag_value_pairs(xml):
        for child in xml.children:
            yield child.find("tag").text.lower(), child.find("value").text.lower()
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
            xlink = plink.find("xref_link")
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


    def __init__(self, **args):
        for k, v in args.items():        
            setattr(self, k, v)
    def show(self):
        print(*self.__dict__.items(), sep="\n")
    
class Sample(Entity):
    def __init__(self, **args):
        super().__init__(**args)
        
        
    @classmethod
    def from_xml(cls, xml):
        attribs = dict()


        print("SAMPLE_XML")
        print(xml)

        identifiers = xml.find("identifiers")
        try:
            attribs["primary_id"] = identifiers.find("primary_id").text
        except:
            attribs["primary_id"] = None
        print(identifiers, file=sys.stderr)
        biosample = identifiers.find(namespace="BioSample")
        attribs["biosample"] = biosample.text if biosample else None
        try: 
            attribs["title"] = xml.find("title").text
        except:
            attribs["title"] = None
        tax_attribs = xml.find("sample_name")
        try:
            taxon_id, scientific_name = map(lambda x:x.text, tax_attribs.children)
        except:
            taxon_id, scientific_name = None, None
        attribs.update({"taxon_id": taxon_id, "scientific_name": scientific_name})

        sample_attribs = dict(Entity.get_tag_value_pairs(xml.find("sample_attributes"))) 
        attribs["ena-first-public"] = sample_attribs["ena-first-public"]
        attribs["ena-last-update"] = sample_attribs["ena-last-update"]
        
        return Sample(**attribs)

        

class Project(Entity):
    def __init__(self, **args):
        super().__init__(**args)
        self._samples = dict(self._get_samples())
    @staticmethod
    def parse_project_links(xml):
        d = dict()
        for plink in xml.children:
            xlink = plink.find("xref_link")
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
    def _get_samples(self):
        for sample_id in self.xlinks.get("ena-sample", list()):
            sample_xml = rest_query(sample_id)
            try:
                sample = Sample.from_xml(sample_xml.sample_set)
            except:
                print("WARNING: sample {sample_id} does not yield result.".format(sample_id=sample_id), file=sys.stderr)
                sample = None
            yield sample_id, sample
    @classmethod
    def from_xml(cls, xml):
        attribs = dict()

        identifiers = xml.find("identifiers")
        try:
            attribs["primary_id"] = identifiers.find("primary_id").text
        except:
            attribs["primary_id"] = None
        try:
            attribs["secondary_id"] = identifiers.find("secondary_id").text
        except:
            attribs["secondary_id"] = None
        try:        
            attribs["name"] = xml.find("name").text
        except:
            attribs["name"] = None
        try:
            attribs["title"] = xml.find("title").text
        except:
            attribs["title"] = None
        try:
            attribs["description"] = xml.find("description").text
        except:
            attribs["description"] = None

        tax_attribs = xml.find("submission_project").find("organism")
        try:
            taxon_id, scientific_name = map(lambda x:x.text, tax_attribs.children)
        except:
            taxon_id, scientific_name = None, None
        attribs.update({"taxon_id": taxon_id, "scientific_name": scientific_name})
        print("PRIMARY", attribs.get("primary_id"))

        #plinks = Project.parse_project_links(xml.find("project_links"))
        plinks = Entity.parse_xlinks(xml.find("project_links"))
        print(*plinks.items(), sep="\n")
        attribs["xlinks"] = plinks

        proj_attribs = dict(Entity.get_tag_value_pairs(xml.find("project_attributes")))
        attribs["ena-first-public"] = proj_attribs["ena-first-public"]
        attribs["ena-last-update"] = proj_attribs["ena-last-update"]
            
        return Project(**attribs)

def get_mgnify_studies(db):
    http = urllib3.PoolManager()
    conn = sqlite3.connect(db)

    with conn:
        cursor = conn.cursor()
        try:
            latest_timestamp = get_latest_timestamp(cursor)
        except:
            latest_timestamp = datetime(1900,1,1)

        for lineage in BIOME_LINEAGES:
            request_str = "{apibase}/studies?lineage={lineage}&page={page}&page_size=100".format(apibase=APIBASE, lineage=lineage, page="{page}")
            request = http.request("GET", request_str.format(page=1))
            page_data = json.loads(request.data)
            npages = page_data["meta"]["pagination"]["pages"]

            data = page_data
            for page in range(1, npages + 1):
                if page > 1:
                    data = json.loads(http.request("GET", request_str.format(page=page)).data)
                has_unknown_records = process_data_block(page, data["data"], cursor, latest_timestamp)
                if not has_unknown_records:
                    break

def query_projects():
    http = urllib3.PoolManager()
    projects_xml = http.request("GET", PROJECT_QUERY).data.decode()
    projects_xml.replace("\n", "")
    projects_xml =  re.sub(">\s+<", "><", projects_xml)
    return projects_xml
    
def rest_query(query_str, base_url=BASE_API_URL):
    http = urllib3.PoolManager()
    print(base_url + query_str)
    xml = http.request("GET", base_url + query_str).data.decode()
    xml = xml.replace("\n", "")
    xml = re.sub(">\s+<", "><", xml)
    soup = BeautifulSoup(xml, "lxml")
    return soup
 
    

def main():
    #raw_project_xml = open(sys.argv[1]).read()
    #raw_project_xml = raw_project_xml.replace("\n", "")
    #raw_project_xml = re.sub(">\s+<", "><", raw_project_xml)
    
    #print(raw_project_xml)
    #sys.exit(0)

    #raw_project_xml = rest_query(PROJECT_QUERY)
    # print(raw_project_xml)[:1000]
    #print(raw_project_xml) 
    #soup = BeautifulSoup(raw_project_xml, "lxml")
    
    soup = rest_query(PROJECT_QUERY)
    projects = soup.project_set
    
    for i, project in enumerate(projects.find_all("project")):
        if i > 10:
            break
        Project.from_xml(project).show()
        print("*************************************************")
    #
    #project = projects.find("project")
    #while project:
    #    print(type(project))
    #    print(project["accession"])
    #    project = project.next_sibling
    #    print(project)
    #
    #


if __name__ == "__main__":
    main()
