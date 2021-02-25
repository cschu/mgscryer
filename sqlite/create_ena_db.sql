DROP TABLE IF EXISTS project;
CREATE TABLE IF NOT EXISTS project(
    id TEXT PRIMARY KEY,
    secondary_id TEXT,
    name TEXT,
    title TEXT,
    description TEXT, 
    ena_first_public TEXT,
    ena_last_update TEXT,
    status INTEGER DEFAULT 0
);

DROP TABLE IF EXISTS project_sample;
CREATE TABLE IF NOT EXISTS project_sample(
    project_id TEXT NOT NULL,
    sample_id TEXT NOT NULL,
    FOREIGN KEY ([project_id]) REFERENCES 'projects' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([sample_id]) REFERENCES 'samples' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS project_pubmed;
CREATE TABLE IF NOT EXISTS project_pubmed(
    project_id TEXT NOT NULL,
    pubmed_id TEXT NOT NULL,
    FOREIGN KEY ([project_id]) REFERENCES 'projects' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS sample;
CREATE TABLE IF NOT EXISTS sample(
    id TEXT PRIMARY KEY,
    biosample TEXT,
    title TEXT,
    taxon_id INTEGER,
    scientific_name TEXT,
    ena_first_public TEXT,
    ena_last_update TEXT     
);

DROP TABLE IF EXISTS sample_experiment;
CREATE TABLE IF NOT EXISTS sample_experiment(
    sample_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    FOREIGN KEY ([sample_id]) REFERENCES 'samples' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([experiment_id]) REFERENCES 'experiments' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS experiment;
CREATE TABLE IF NOT EXISTS experiment(
    id TEXT PRIMARY KEY,
    title TEXT,
    library_strategy TEXT,
    library_source TEXT,
    library_selection TEXT,
    library_layout TEXT,
    spot_length INTEGER,
    instrument TEXT
);

DROP TABLE IF EXISTS experiment_run;
CREATE TABLE IF NOT EXISTS experiment_run(
    experiment_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    FOREIGN KEY ([experiment_id]) REFERENCES 'experiments' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    FOREIGN KEY ([run_id]) REFERENCES 'runs' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

DROP TABLE IF EXISTS run;
CREATE TABLE IF NOT EXISTS run(
    id TEXT PRIMARY KEY,
    title TEXT,
    read_count INTEGER,
    ena_first_public TEXT,
    ena_last_update TEXT
);
