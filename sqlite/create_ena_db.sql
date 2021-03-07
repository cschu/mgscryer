DROP TABLE IF EXISTS project;
CREATE TABLE IF NOT EXISTS project(
    id TEXT PRIMARY KEY,
    secondary_id TEXT,
    name TEXT,
    title TEXT,
    description TEXT, 
    ena_first_public TEXT,
    ena_last_update TEXT,
    status INTEGER DEFAULT 1
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

DROP TABLE IF EXISTS project_status;
CREATE TABLE IF NOT EXISTS project_status(
    id INTEGER DEFAULT 1,
    label TEXT NOT NULL
);

--                               _________ IGNORED(4)
--                             /             /
-- poll -> NEW(1)|IMPORTANT(2) -- ASSIGNED(8) <-------
--                                           \        \     
--                                         IN_PROGRESS(16) -> DONE(32)


INSERT INTO project_status VALUES(1, 'NEW'); -- obtained from latest poll
INSERT INTO project_status VALUES(2, 'IMPORTANT'); -- obtained from latest poll and ticks some boxes
INSERT INTO project_status VALUES(4, 'IGNORED'); -- study was ignored (negative outcome of ASSIGNED|NEW|IMPORTANT) 
INSERT INTO project_status VALUES(8, 'ASSIGNED'); -- study was assigned to someone
INSERT INTO project_status VALUES(16, 'IN_PROGRESS'); -- study was submitted to be processed (positive outcome of ASSIGNED)
INSERT INTO project_status VALUES(32, 'DONE'); -- study was processed successfully (positive outcome of IN_PROGRESS)

DROP TABLE IF EXISTS scryer_users;
CREATE TABLE IF NOT EXISTS scryer_users(
    id TEXT PRIMARY KEY,
    full_name TEXT,
    admin INTEGER DEFAULT 0
);

INSERT INTO scryer_users VALUES('karcher', 'Nic Karcher', 0)
INSERT INTO scryer_users VALUES('milanese', 'Alessio Milanese', 0)
INSERT INTO scryer_users VALUES('schudoma', 'Christian Schudoma', 1)
INSERT INTO scryer_users VALUES('wirbel', 'Jakob Wirbel', 0)
INSERT INTO scryer_users VALUES('zeller', 'Georg Zeller', 1)


DROP TABLE IF EXISTS project_user;
CREATE TABLE IF NOT EXISTS project_user(
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    FOREIGN KEY ([project_id]) REFERENCES 'projects' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION,               
    FOREIGN KEY ([user_id]) REFERENCES 'scryer_users' ([id])
        ON DELETE NO ACTION ON UPDATE NO ACTION,
);








