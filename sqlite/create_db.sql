DROP TABLE IF EXISTS study;

CREATE TABLE study(
    id TEXT PRIMARY KEY,
    bioproject TEXT,
    accession TEXT,
    samples_count INTEGER,
    secondary_accession TEXT,
    centre_name TEXT,
    is_public INTEGER,
    public_release_date TEXT,
    abstract TEXT,
    name TEXT,
    data_origination TEXT,
    last_update TEXT,
    status INTEGER DEFAULT 0
);

DROP TABLE IF EXISTS sample;

CREATE TABLE sample(
    id TEXT PRIMARY KEY,
    biosample TEXT,
    accession TEXT,
    description TEXT,
    sample_name TEXT,
    sample_alias TEXT,
    last_update TEXT,
    status INTEGER DEFAULT 0
);
 
DROP TABLE IF EXISTS run;

CREATE TABLE run(
    id TEXT PRIMARY KEY,
    experiment_type TEXT,
    accession TEXT,
    secondary_accession TEXT,
    status INTEGER DEFAULT 0
);
