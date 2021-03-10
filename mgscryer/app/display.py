import sqlite3

def get_studies(cursor):
    query = """
    SELECT study.*, study_pubmed.pubmed_id, study_taxtree.tax_tree
    FROM study
    LEFT JOIN study_pubmed 
    ON study.study_accession = study_pubmed.study_accession
    LEFT JOIN study_taxtree
    ON study.study_accession = study_taxtree.study_accession;
    """.strip()
    cursor.execute(query)
    rows = cursor.fetchall()
    for row in rows:
        yield row

def get_study_samples(cursor, study_accession):
    #query = """
    #SELECT sample.* 
    #FROM study_sample
    #LEFT JOIN sample ON study_sample.sample_accession = sample.sample_accession
    #WHERE study_sample.study_accession = '{}'
    query = """
    SELECT *
    FROM sample
    WHERE study_accession = '{}';
    """.strip().format(study_accession)
    cursor.execute(query)
    rows = cursor.fetchall()
    samples = dict()
    for sample_data in rows:
        sample_accession, sample_data = sample_data[0], sample_data[1:]
        samples.setdefault(tuple(sample_data[:-2]), list()).append(sample_accession)
    return samples

def get_sample_runs(cursor, sample_accession):
    #query = """
    #SELECT run.*
    #FROM sample_run
    #LEFT JOIN run ON sample_run.run_accession = run.run_accession
    #WHERE sample_run.sample_accession = '{}'
    query = """
    SELECT *
    FROM run
    WHERE sample_accession = '{}';
    """.strip().format(sample_accession)
    cursor.execute(query)
    rows = cursor.fetchall()
    runs = dict()
    for run_data in rows:
        run_accession, run_data = run_data[0], run_data[1:]
        runs.setdefault(tuple(run_data[3:-3]), list()).append(run_accession)
    return runs


def display_data(cursor):
    output = list()
    for study_data in get_studies(cursor):
        study_accession, study_data = study_data[0], study_data[1:]
        output.append("<div>")
        output.append("<h3>{}</h3>".format(study_accession))
        sample_data = get_study_samples(cursor, study_accession)
        n_samples = sum(map(len, sample_data.values()))
        #print(study_accession, *study_data, n_samples, "samples")
        output.append("<p>{} {} samples</p>".format(study_data, n_samples))
        for sample_type, samples in sample_data.items():
            #n_runs = sum(map(len, run_data.values()))
            run_data = dict()
            n_runs = 0
            for sample_accession in samples:
                for run_type, runs in get_sample_runs(cursor, sample_accession).items():
                    run_data.setdefault(run_type, list()).extend(runs)
                #run_data.append(get_sample_runs(conn.cursor(), sample_accession))
            n_runs = sum(map(len, run_data.values()))
            output.append("<ul><li>{} {} samples {} runs<ul>".format(sample_type, len(samples), n_runs))


            #print(*sample_type, len(samples), "samples", n_runs, "runs")
            for run_type, runs in run_data.items():
                output.append("<li>{} {} runs</li>".format(run_type, len(runs)))
                output.append("</ul></li>")
                pass
                #print(*run_type, len(runs))
            output.append("</ul>")

        output.append("</div>")
    return "".join(output)
    
if __name__ == "__main__":
    conn = sqlite3.connect("/home/schudoma/mgscryer/sqlite/ena_portal_db_3.sqlite")
    string = display_data(conn.cursor())
    print(string)
    

"""
-- select study.*, study_pubmed.pubmed_id, sample.*, run.* from study
-- left join study_sample on study.study_accession = study_sample.study_accession
-- left join sample on study_sample.sample_accession = sample.sample_accession
-- left join sample_run on sample.sample_accession = sample_run.sample_accession
-- left join run on sample_run.run_accession = run.run_accession
-- left join study_pubmed on study.study_accession = study_pubmed.study_accession
-- group by sample.sample_accession
-- limit 10;
"""
