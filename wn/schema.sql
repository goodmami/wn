
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
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    definition TEXT,
    metadata META
);
CREATE INDEX proposed_ili_synset_index ON proposed_ilis(synset_rowid);

-- Lexical Entries

/* The 'lemma' entity of a lexical entry is just a form, but it should
   be the only form with rank = 0. After that, rank can be used to
   indicate preference for a form. */


CREATE TABLE entries (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    pos_rowid INTEGER NOT NULL REFERENCES parts_of_speech (rowid),
    metadata META,
    UNIQUE (id, lexicon_rowid)
);
CREATE INDEX entry_id_index ON entries (id);

CREATE TABLE forms (
    rowid INTEGER PRIMARY KEY,
    entry_rowid INTEGER NOT NULL REFERENCES entries(rowid) ON DELETE CASCADE,
    form TEXT NOT NULL,
    script TEXT,
    rank INTEGER DEFAULT 1,  -- rank 0 is the preferred lemma
    UNIQUE (entry_rowid, form, script)
);
CREATE INDEX form_entry_index ON forms (entry_rowid);
CREATE INDEX form_index ON forms (form);


CREATE TABLE tags (
    form_rowid INTEGER NOT NULL REFERENCES forms (rowid) ON DELETE CASCADE,
    tag TEXT,
    category TEXT
);

CREATE TABLE syntactic_behaviours (
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    frame TEXT,
    PRIMARY KEY (id, lexicon_rowid)
);

CREATE TABLE syntactic_behaviour_senses (
    syntactic_behaviour_id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL,
    sense_rowid INTEGER NOT NULL REFERENCES senses (rowid) ON DELETE CASCADE,
    FOREIGN KEY (syntactic_behaviour_id, lexicon_rowid) REFERENCES syntactic_behaviours (id, lexicon_rowid)
);
CREATE INDEX syntactic_behavior_sense_index ON syntactic_behaviour_senses (sense_rowid);

-- Synsets

CREATE TABLE synsets (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid),
    ili TEXT,
    pos_rowid INTEGER NOT NULL REFERENCES parts_of_speech (rowid),
    -- lexfile_id INTEGER REFERENCES lexicographer_files (id),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META
);
CREATE INDEX synset_id_index ON synsets (id);
CREATE INDEX synset_ili_index ON synsets (ili);

CREATE TABLE synset_relations (
    source_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    type INTEGER NOT NULL,
    metadata META
);
CREATE INDEX synset_relation_source_index ON synset_relations (source_rowid);
CREATE INDEX synset_relation_target_index ON synset_relations (target_rowid);

CREATE TABLE definitions (
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    definition TEXT,
    language TEXT,  -- bcp-47 language tag
    -- sense_rowid INTEGER NOT NULL REFERENCES senses(rowid),
    metadata META
);
CREATE INDEX definition_rowid_index ON definitions (synset_rowid);

CREATE TABLE synset_examples (
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META
);
CREATE INDEX synset_example_rowid_index ON synset_examples(synset_rowid);

-- Senses

CREATE TABLE senses (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid),
    entry_rowid INTEGER NOT NULL REFERENCES entries(rowid) ON DELETE CASCADE,
    entry_rank INTEGER DEFAULT 1,
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    -- sense_key TEXT,  -- not actually UNIQUE ?
    -- adjposition_rowid INTEGER REFERENCES adjpositions (rowid),
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META
    -- FOREIGN KEY (synset_id, lexicon_rowid) REFERENCES synsets (id, lexicon_rowid),
    -- UNIQUE (id, lexicon_rowid)
);
CREATE INDEX sense_id_index ON senses(id);
CREATE INDEX sense_entry_rowid_index ON senses (entry_rowid);
CREATE INDEX sense_synset_rowid_index ON senses (synset_rowid);

CREATE TABLE sense_relations (
    source_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    type INTEGER NOT NULL,
    metadata META
);
CREATE INDEX sense_relation_source_index ON sense_relations (source_rowid);
CREATE INDEX sense_relation_target_index ON sense_relations (target_rowid);

CREATE TABLE sense_synset_relations (
    source_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    type INTEGER NOT NULL,
    metadata META
);
CREATE INDEX sense_synset_relation_source_index ON sense_synset_relations (source_rowid);
CREATE INDEX sense_synset_relation_target_index ON sense_synset_relations (target_rowid);

CREATE TABLE sense_examples (
    sense_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META
);
CREATE INDEX sense_example_index ON sense_examples (sense_rowid);

CREATE TABLE counts (
    sense_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    count INTEGER NOT NULL,
    metadata META
);
CREATE INDEX count_index ON counts(sense_rowid);

-- Lookup tables

CREATE TABLE parts_of_speech (
    rowid INTEGER PRIMARY KEY,
    pos TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX pos_index ON parts_of_speech (pos);

CREATE TABLE adjpositions (
    rowid INTEGER PRIMARY KEY,
    position TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX adposition_index ON adjpositions (position);

CREATE TABLE lexicographer_files (
    id INTEGER PRIMARY KEY,  -- this is actually an ID, not just a rowid
    name TEXT NOT NULL UNIQUE
);
CREATE UNIQUE INDEX lexicographer_file_index ON lexicographer_files (name);
