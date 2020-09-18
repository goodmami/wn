
CREATE TABLE lexicons (
    rowid INTEGER PRIMARY KEY,  -- unique database-internal id
    id TEXT NOT NULL,           -- user-facing id
    label TEXT NOT NULL,
    language TEXT NOT NULL,     -- bcp-47 language tag
    email TEXT NOT NULL,
    license TEXT NOT NULL,
    version TEXT NOT NULL,
    url TEXT,
    citation TEXT,
    metadata META,
    UNIQUE (id, version)
);

-- ILI : Interlingual Index

CREATE TABLE ilis (
    ili TEXT PRIMARY KEY,
    definition TEXT,
    metadata META
);

CREATE TABLE proposed_ilis (
    synset_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    definition TEXT,
    metadata META,
    FOREIGN KEY (synset_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid)
);

-- Lexical Entries

/* The 'lemma' entity of a lexical entry is just a form, but it should
   be the only form with rank = 0. After that, rank can be used to
   indicate preference for a form. */


CREATE TABLE entries (
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    pos_id INTEGER NOT NULL REFERENCES parts_of_speech (id),
    metadata META,
    PRIMARY KEY (id, lexicon_rowid)
);
CREATE INDEX entry_id_index ON entries (id);

CREATE TABLE forms (
    rowid INTEGER PRIMARY KEY,
    entry_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    form TEXT NOT NULL,
    script TEXT,
    rank INTEGER DEFAULT 1,  -- rank 0 is the preferred lemma
    FOREIGN KEY (entry_id, lexicon_rowid) REFERENCES entries (id, lexicon_rowid),
    UNIQUE (entry_id, lexicon_rowid, form, script)
);
CREATE INDEX form_index ON forms (form);


CREATE TABLE tags (
    form_rowid INTEGER NOT NULL REFERENCES forms (rowid),
    tag TEXT,
    category TEXT
);

CREATE TABLE syntactic_behaviours (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    frame TEXT
);

CREATE TABLE syntactic_behaviour_senses (
    syntactic_behaviour_rowid INTEGER NOT NULL REFERENCES syntactic_behaviours (rowid),
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    sense_id TEXT NOT NULL REFERENCES senses (id)
);

-- Synsets

CREATE TABLE synsets (
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    ili TEXT,
    lexname_id INTEGER REFERENCES lexicographer_files (id),
    pos_id INTEGER REFERENCES parts_of_speech (id),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META,
    PRIMARY KEY (id, lexicon_rowid)
);
CREATE INDEX synset_ili_index ON synsets (ili);

CREATE TABLE synset_relations (
    lexicon_rowid INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type_id INTEGER NOT NULL REFERENCES synset_relation_types (id),
    metadata META,
    FOREIGN KEY (source_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid),
    FOREIGN KEY (target_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid)
);
CREATE INDEX synset_relation_source_index ON synset_relations (source_id);

CREATE TABLE definitions (
    synset_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    definition TEXT,
    language TEXT,  -- bcp-47 language tag
    sense_id TEXT,
    metadata META,
    FOREIGN KEY (synset_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid),
    FOREIGN KEY (sense_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid)
);
CREATE INDEX definition_id_index ON definitions (synset_id);

CREATE TABLE synset_examples (
    synset_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META,
    FOREIGN KEY (synset_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid)
);
CREATE INDEX synset_example_id_index ON synset_examples(synset_id);

-- Senses

CREATE TABLE senses (
    id TEXT NOT NULL,
    entry_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    entry_rank INTEGER DEFAULT 1,
    synset_id TEXT NOT NULL,
    sense_key TEXT,  -- not actually UNIQUE ?
    adjposition_id INTEGER REFERENCES adjpositions (id),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META,
    PRIMARY KEY (id, lexicon_rowid),
    FOREIGN KEY (entry_id, lexicon_rowid) REFERENCES entries (id, lexicon_rowid),
    FOREIGN KEY (synset_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid),
    UNIQUE (id, lexicon_rowid)
);
CREATE INDEX sense_id_index ON senses (id);
CREATE INDEX sense_entry_id_index ON senses (entry_id);
CREATE INDEX sense_synset_id_index ON senses (synset_id);

CREATE TABLE sense_relations (
    lexicon_rowid INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type_id TEXT NOT NULL REFERENCES sense_relation_types (id),
    metadata META,
    FOREIGN KEY (source_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid),
    FOREIGN KEY (target_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid)
);
CREATE INDEX sense_relations_id_index ON sense_relations (source_id);

CREATE TABLE sense_synset_relations (
    lexicon_rowid INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    -- limit the type to ('domain_topic', 'domain_region', 'exemplifies') ?
    type_id TEXT NOT NULL REFERENCES sense_relation_types (id),
    metadata META,
    FOREIGN KEY (source_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid),
    FOREIGN KEY (target_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid)
);
CREATE INDEX sense_synset_relation_id_index ON sense_synset_relations (source_id);

CREATE TABLE sense_examples (
    sense_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META,
    FOREIGN KEY (sense_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid)
);
CREATE INDEX sense_example_index ON sense_examples (sense_id);

CREATE TABLE counts (
    sense_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    count INTEGER NOT NULL,
    metadata META,
    FOREIGN KEY (sense_id, lexicon_rowid) REFERENCES senses (id, lexicon_rowid)
);

-- Lookup tables

CREATE TABLE parts_of_speech (
    id INTEGER PRIMARY KEY,
    pos TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX pos_index ON parts_of_speech (pos);

CREATE TABLE adjpositions (
    id INTEGER PRIMARY KEY,
    position TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX adposition_index ON adjpositions (position);

CREATE TABLE synset_relation_types (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX synset_relation_type_index ON synset_relation_types (type);

CREATE TABLE sense_relation_types (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX sense_relation_type_index ON sense_relation_types (type);

CREATE TABLE lexicographer_files (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX lexicographer_file_index ON lexicographer_files (name);
