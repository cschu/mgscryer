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
    environment_biome TEXT
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
    read_count INTEGER    
);

DROP TABLE IF EXISTS study_sample;
CREATE TABLE IF NOT EXISTS study_sample(
    study_accession TEXT,
    sample_accession TEXT,
    FOREIGN KEY ([study_accession]) REFERENCES 'study' ([study_accession])    
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([sample_accession]) REFERENCES 'sample' ([sample_accession])    
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS sample_run;
CREATE TABLE IF NOT EXISTS sample_run(
    sample_accession TEXT,
    run_accession TEXT,
    FOREIGN KEY ([sample_accession]) REFERENCES 'sample' ([sample_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([run_accession]) REFERENCES 'run' ([run_accession])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);
