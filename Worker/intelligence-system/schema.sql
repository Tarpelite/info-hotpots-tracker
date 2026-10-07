CREATE TABLE IF NOT EXISTS paper (
    id TEXT PRIMARY KEY,
    abstract TEXT,
    abstract_zh TEXT,
    authors TEXT,
    doi TEXT,
    issn TEXT,
    issue TEXT,
    keywords TEXT,
    keywords_zh TEXT,
    title TEXT,
    title_zh TEXT,
    venue TEXT,
    volume TEXT,
    year INTEGER
);