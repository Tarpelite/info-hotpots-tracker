PRAGMA foreign_keys = ON;

-- Source: AMiner/data_cleaned/paper_detail_cleaned.csv
CREATE TABLE IF NOT EXISTS paper (
    id          TEXT    NOT NULL PRIMARY KEY,
    doi         TEXT,
    title       TEXT,
    title_zh    TEXT,
    abstract    TEXT,
    abstract_zh TEXT,
    authors     TEXT,
    keywords    TEXT,
    keywords_zh TEXT,
    venue       TEXT,
    issn        TEXT,
    volume      TEXT,
    issue       TEXT,
    year        INTEGER,
    n_citation  INTEGER
);

-- Source: AMiner/data_cleaned/organization_detail_cleaned.csv
CREATE TABLE IF NOT EXISTS organization (
    id       TEXT NOT NULL PRIMARY KEY,
    name     TEXT NOT NULL,
    name_en  TEXT,
    name_zh  TEXT,
    type     TEXT,
    acronyms TEXT,
    aliases  TEXT,
    details  TEXT,
    location TEXT,
    url      TEXT,
    image    TEXT
);

-- Source: AMiner/data_cleaned/paper_author_cleaned.csv
CREATE TABLE IF NOT EXISTS paper_author (
    paperid TEXT NOT NULL,
    name    TEXT,
    name_zh TEXT,
    org     TEXT,
    org_zh  TEXT,
    PRIMARY KEY (paperid, name, name_zh, org, org_zh),
    FOREIGN KEY (paperid) REFERENCES paper (id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_paper_doi
    ON paper (doi);
CREATE INDEX IF NOT EXISTS idx_paper_year
    ON paper (year);
CREATE INDEX IF NOT EXISTS idx_paper_issn
    ON paper (issn);

CREATE INDEX IF NOT EXISTS idx_organization_name_zh
    ON organization (name_zh);
CREATE INDEX IF NOT EXISTS idx_organization_type
    ON organization (type);

CREATE INDEX IF NOT EXISTS idx_paper_author_paperid
    ON paper_author (paperid);

