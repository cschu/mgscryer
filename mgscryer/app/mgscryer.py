#!/usr/bin/env python

#/congo/DB/MGSCRYER/mgscryer_env/bin/python3

import sys
import os
import sqlite3

#sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_env/lib/python3.6/site-packages")
#sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_py27_env/lib/python2.7/site-packages")
sys.path.insert(0, "/congo/DB/MGSCRYER/mgscryer_env/lib/python2.7/site-packages")
sys.stderr.write(sys.version)

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hiya():
    return "BLARGH"

@app.route("/dbtest")
def dbtest():
    from display import display_data
    db = "/congo/DB/MGSCRYER/mgscryer_db.sqlite"
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    #cursor.execute("SELECT COUNT(*) FROM study;")
    #cursor.execute(query)
    #rows = cursor.fetchall()
    content = display_data(cursor)
    conn.close()
    return content
    


    #return "I have {} studies.".format(rows[0][0])
    #return str(rows)
    return "xxx"


if __name__ == "__main__":
    app.run()


query = """
select distinct
    study_sample.study_accession,
    -- study_sample.sample_accession,
    run.instrument_model, run.instrument_platform, run.library_source, run.library_layout, run.library_strategy, run.nominal_length,
    count(*)
from
    study_sample
    left join sample_run on study_sample.sample_accession = sample_run.sample_accession
    left join run on sample_run.run_accession = run.run_accession
group by
    study_sample.sample_accession,
    study_sample.study_accession;
"""
