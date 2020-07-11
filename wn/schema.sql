
CREATE TABLE lexicons (
    rowid INTEGER PRIMARY KEY,  -- name it for later reference
    id TEXT NOT NULL,
    label TEXT NOT NULL,
    language TEXT NOT NULL,  -- bcp-47 language tag
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
    synset_id TEXT REFERENCES synsets (id),
    definition TEXT,
    metadata META
);

-- Lexical Entries

/* The 'lemma' entity of a lexical entry is just a form, but it should
   be the only form with rank = 0. After that, rank can be used to
   indicate preference for a form. */


CREATE TABLE entries (
    id TEXT PRIMARY KEY NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    pos_id INTEGER NOT NULL REFERENCES parts_of_speech (id),
    metadata META
);

CREATE TABLE forms (
    id INTEGER PRIMARY KEY,
    entry_id TEXT NOT NULL REFERENCES entries (id),
    form TEXT NOT NULL,
    script TEXT,
    rank INTEGER DEFAULT 1,  -- rank 0 is the preferred lemma
    UNIQUE (entry_id, form, script)
);

CREATE TABLE tags (
    form_id INTEGER NOT NULL REFERENCES forms (id),
    tag TEXT,
    category TEXT
);

CREATE TABLE syntactic_behaviours (
    id INTEGER PRIMARY KEY,
    entry_id TEXT NOT NULL REFERENCES entries (id),
    frame TEXT
);

CREATE TABLE syntactic_behaviour_senses (
    syntactic_behaviour_id INTEGER NOT NULL REFERENCES syntactic_behaviours (id),
    sense_id TEXT NOT NULL REFERENCES senses (id)
);

-- Synsets

CREATE TABLE synsets (
    id TEXT PRIMARY KEY NOT NULL,
    ili TEXT UNIQUE,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    lexname_id INTEGER REFERENCES lexicographer_files (id),
    pos_id INTEGER REFERENCES parts_of_speech (id),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META
);
CREATE INDEX synset_ili_index ON synsets (ili);

CREATE TABLE synset_relations (
    source_id TEXT NOT NULL REFERENCES synsets (id),
    target_id TEXT NOT NULL REFERENCES synsets (id),
    type_id INTEGER NOT NULL REFERENCES synset_relation_types (id),
    metadata META
);
CREATE INDEX synset_relations_source_index ON synset_relations (source_id);

CREATE TABLE definitions (
    synset_id TEXT NOT NULL REFERENCES synsets (id),
    definition TEXT,
    language TEXT,  -- bcp-47 language tag
    sense_id TEXT REFERENCES senses (id),
    metadata META
);
CREATE INDEX definitions_id_index ON definitions (synset_id);

CREATE TABLE synset_examples (
    synset_id TEXT NOT NULL REFERENCES synsets (id),
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META
);
CREATE INDEX synset_example_id_index ON synset_examples(synset_id);

-- Senses

CREATE TABLE senses (
    id TEXT PRIMARY KEY NOT NULL,
    entry_id TEXT REFERENCES entries (id),
    entry_rank INTEGER DEFAULT 1,
    synset_id TEXT REFERENCES synsets (id),
    sense_key TEXT,  -- not actually UNIQUE ?
    adjposition_id INTEGER REFERENCES adjpositions (id),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META
);
CREATE INDEX senses_entry_id_index ON senses (entry_id);
CREATE INDEX senses_synset_id_index ON senses (synset_id);

CREATE TABLE sense_sense_relations (
    source_id TEXT NOT NULL REFERENCES senses (id),
    target_id TEXT NOT NULL REFERENCES senses (id),
    type_id TEXT NOT NULL REFERENCES sense_relation_types (id),
    metadata META
);
CREATE INDEX sense_sense_relations_id_index ON sense_sense_relations (source_id);

CREATE TABLE sense_synset_relations (
    source_id TEXT NOT NULL REFERENCES senses (id),
    target_id TEXT NOT NULL REFERENCES synsets (id),
    -- limit the type to ('domain_topic', 'domain_region', 'exemplifies') ?
    type_id TEXT NOT NULL REFERENCES sense_relation_types (id),
    metadata META
);
CREATE INDEX sense_synset_relations_id_index ON sense_synset_relations (source_id);

CREATE TABLE sense_examples (
    sense_id TEXT NOT NULL REFERENCES senses (id),
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META
);
CREATE INDEX sense_examples_index ON sense_examples (sense_id);

CREATE TABLE counts (
    sense_id TEXT NOT NULL REFERENCES senses (id),
    count INTEGER NOT NULL,
    metadata META
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
