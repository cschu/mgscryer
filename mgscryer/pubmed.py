import re

from bs4 import BeautifulSoup
import requests

class PubmedQuery:
    @staticmethod
    def get_ids(studies):
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
                                    db, pubmed_id = xref_link.DB.text, xref_link.ID.text
                                except:
                                    continue
                                if db == "PUBMED":
                                    yield study_accession, pubmed_id
