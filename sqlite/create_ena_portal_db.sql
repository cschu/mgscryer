DROP TABLE IF EXISTS study;
CREATE TABLE IF NOT EXISTS study(
    study_accession TEXT PRIMARY KEY,
    study_title TEXT,
    first_public TEXT,
    last_updated TEXT,
    status INTEGER DEFAULT 1
);

DROP TABLE IF EXISTS sample;
CREATE TABLE IF NOT EXISTS sample(
    sample_accession TEXT PRIMARY KEY,
    host TEXT,
    host_body_site TEXT,
    host_tax_id TEXT,
    environment_biome TEXT,
    study_accession TEXT NOT NULL,
    last_updated TEXT,
    FOREIGN KEY ([study_accession]) REFERENCES 'study' ([study_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS run;
CREATE TABLE IF NOT EXISTS run(
    run_accession TEXT PRIMARY KEY,
    experiment_title TEXT,
    description TEXT,
    instrument_model TEXT,
    instrument_platform TEXT,
    library_source TEXT,
    library_layout TEXT,
    library_strategy TEXT,
    nominal_length INTEGER,
    read_count INTEGER,
    sample_accession TEXT NOT NULL,
    last_updated TEXT,
    FOREIGN KEY ([sample_accession]) REFERENCES 'sample' ([sample_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS study_sample;
CREATE TABLE IF NOT EXISTS study_sample(
    study_accession TEXT,
    sample_accession TEXT,
    PRIMARY KEY (study_accession, sample_accession),
    FOREIGN KEY ([study_accession]) REFERENCES 'study' ([study_accession])    
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([sample_accession]) REFERENCES 'sample' ([sample_accession])    
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS sample_run;
CREATE TABLE IF NOT EXISTS sample_run(
    sample_accession TEXT,
    run_accession TEXT,
    PRIMARY KEY (sample_accession, run_accession),
    FOREIGN KEY ([sample_accession]) REFERENCES 'sample' ([sample_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([run_accession]) REFERENCES 'run' ([run_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS study_pubmed;
CREATE TABLE IF NOT EXISTS study_pubmed(
    study_accession TEXT,
    pubmed_id TEXT,
    PRIMARY KEY (study_accession, pubmed_id),
    FOREIGN KEY ([study_accession]) REFERENCES 'study' ([study_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS timepoints;
CREATE TABLE IF NOT EXISTS timepoints(
    action TEXT PRIMARY KEY,
    date_time TEXT NOT NULL
);

INSERT INTO timepoints VALUES("last_update", "2021-01-01T00:00:00");

DROP TABLE IF EXISTS tax_trees;
CREATE TABLE IF NOT EXISTS tax_trees(
    taxid INTEGER PRIMARY KEY,
    name TEXT
);

INSERT INTO tax_trees VALUES
    (9606, "human"),
    (256318, "metagenomics"),
    (33208, "animal"),
    (33090, "green plants");

DROP TABLE IF EXISTS study_taxtree;
CREATE TABLE IF NOT EXISTS study_taxtree(
    study_accession TEXT NOT NULL,
    tax_tree TEXT NOT NULL,
    PRIMARY KEY (study_accession, tax_tree),
    FOREIGN KEY ([study_accession]) REFERENCES 'study' ([study_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([tax_tree]) REFERENCES 'tax_trees' ([taxid])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

