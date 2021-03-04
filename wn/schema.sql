
-- ILI : Interlingual Index

CREATE TABLE ilis (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    status_rowid INTEGER NOT NULL REFERENCES ili_statuses (rowid),
    definition TEXT,
    metadata META,
    UNIQUE (id)
);
CREATE INDEX ili_id_index ON ilis (id);

CREATE TABLE proposed_ilis (
    rowid INTEGER PRIMARY KEY,
    synset_rowid INTEGER REFERENCES synsets (rowid) ON DELETE CASCADE,
    definition TEXT,
    metadata META,
    UNIQUE (synset_rowid)
);
CREATE INDEX proposed_ili_synset_rowid_index ON proposed_ilis (synset_rowid);


-- Wordnet lexicons

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
    logo TEXT,
    metadata META,
    modified BOOLEAN CHECK( modified IN (0, 1) ) DEFAULT 0 NOT NULL,
    UNIQUE (id, version)
);

CREATE TABLE lexicon_dependencies (
    dependent_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    provider_id TEXT NOT NULL,
    provider_version TEXT NOT NULL,
    provider_url TEXT,
    provider_rowid INTEGER REFERENCES lexicons (rowid) ON DELETE SET NULL
);
CREATE INDEX lexicon_dependent_index ON lexicon_dependencies(dependent_rowid);

CREATE TABLE lexicon_extensions (
    extension_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    base_id TEXT NOT NULL,
    base_version TEXT NOT NULL,
    base_url TEXT,
    base_rowid INTEGER REFERENCES lexicons (rowid),
    UNIQUE (extension_rowid, base_rowid)
);
CREATE INDEX lexicon_extension_index ON lexicon_extensions(extension_rowid);


-- Lexical Entries

/* The 'lemma' entity of a lexical entry is just a form, but it should
   be the only form with rank = 0. After that, rank can be used to
   indicate preference for a form. */


CREATE TABLE entries (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    pos TEXT NOT NULL,
    metadata META,
    UNIQUE (id, lexicon_rowid)
);
CREATE INDEX entry_id_index ON entries (id);

CREATE TABLE forms (
    rowid INTEGER PRIMARY KEY,
    id TEXT,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
    entry_rowid INTEGER NOT NULL REFERENCES entries(rowid) ON DELETE CASCADE,
    form TEXT NOT NULL,
    normalized_form TEXT,
    script TEXT,
    rank INTEGER DEFAULT 1,  -- rank 0 is the preferred lemma
    UNIQUE (entry_rowid, form, script)
);
CREATE INDEX form_entry_index ON forms (entry_rowid);
CREATE INDEX form_index ON forms (form);
CREATE INDEX form_norm_index ON forms (normalized_form);

CREATE TABLE pronunciations (
    form_rowid INTEGER NOT NULL REFERENCES forms (rowid) ON DELETE CASCADE,
    value TEXT,
    variety TEXT,
    notation TEXT,
    phonemic BOOLEAN CHECK( phonemic IN (0, 1) ) DEFAULT 1 NOT NULL,
    audio TEXT
);
CREATE INDEX pronunciation_form_index ON pronunciations (form_rowid);

CREATE TABLE tags (
    form_rowid INTEGER NOT NULL REFERENCES forms (rowid) ON DELETE CASCADE,
    tag TEXT,
    category TEXT
);
CREATE INDEX tag_form_index ON tags (form_rowid);


-- Synsets

CREATE TABLE synsets (
    rowid INTEGER PRIMARY KEY,
    id TEXT NOT NULL,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    ili_rowid INTEGER REFERENCES ilis (rowid),
    pos TEXT,
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    lexfile_rowid INTEGER REFERENCES lexfiles (rowid),
    metadata META
);
CREATE INDEX synset_id_index ON synsets (id);
CREATE INDEX synset_ili_rowid_index ON synsets (ili_rowid);

CREATE TABLE synset_relations (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    source_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    type_rowid INTEGER NOT NULL REFERENCES relation_types(rowid),
    metadata META
);
CREATE INDEX synset_relation_source_index ON synset_relations (source_rowid);
CREATE INDEX synset_relation_target_index ON synset_relations (target_rowid);

CREATE TABLE definitions (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    definition TEXT,
    language TEXT,  -- bcp-47 language tag
    sense_rowid INTEGER REFERENCES senses(rowid) ON DELETE SET NULL,
    metadata META
);
CREATE INDEX definition_rowid_index ON definitions (synset_rowid);
CREATE INDEX definition_sense_index ON definitions (sense_rowid);

CREATE TABLE synset_examples (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
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
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
    entry_rowid INTEGER NOT NULL REFERENCES entries(rowid) ON DELETE CASCADE,
    entry_rank INTEGER DEFAULT 1,
    synset_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    synset_rank INTEGER DEFAULT 1,
    lexicalized BOOLEAN CHECK( lexicalized IN (0, 1) ) DEFAULT 1 NOT NULL,
    metadata META
);
CREATE INDEX sense_id_index ON senses(id);
CREATE INDEX sense_entry_rowid_index ON senses (entry_rowid);
CREATE INDEX sense_synset_rowid_index ON senses (synset_rowid);

CREATE TABLE sense_relations (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    source_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    type_rowid INTEGER NOT NULL REFERENCES relation_types(rowid),
    metadata META
);
CREATE INDEX sense_relation_source_index ON sense_relations (source_rowid);
CREATE INDEX sense_relation_target_index ON sense_relations (target_rowid);

CREATE TABLE sense_synset_relations (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    source_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    target_rowid INTEGER NOT NULL REFERENCES synsets(rowid) ON DELETE CASCADE,
    type_rowid INTEGER NOT NULL REFERENCES relation_types(rowid),
    metadata META
);
CREATE INDEX sense_synset_relation_source_index ON sense_synset_relations (source_rowid);
CREATE INDEX sense_synset_relation_target_index ON sense_synset_relations (target_rowid);

CREATE TABLE adjpositions (
    sense_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    adjposition TEXT NOT NULL
);
CREATE INDEX adjposition_sense_index ON adjpositions (sense_rowid);

CREATE TABLE sense_examples (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
    sense_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    example TEXT,
    language TEXT,  -- bcp-47 language tag
    metadata META
);
CREATE INDEX sense_example_index ON sense_examples (sense_rowid);

CREATE TABLE counts (
    rowid INTEGER PRIMARY KEY,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons(rowid) ON DELETE CASCADE,
    sense_rowid INTEGER NOT NULL REFERENCES senses(rowid) ON DELETE CASCADE,
    count INTEGER NOT NULL,
    metadata META
);
CREATE INDEX count_index ON counts(sense_rowid);


-- Syntactic Behaviours

CREATE TABLE syntactic_behaviours (
    rowid INTEGER PRIMARY KEY,
    id TEXT,
    lexicon_rowid INTEGER NOT NULL REFERENCES lexicons (rowid) ON DELETE CASCADE,
    frame TEXT NOT NULL,
    UNIQUE (lexicon_rowid, id),
    UNIQUE (lexicon_rowid, frame)
);
CREATE INDEX syntactic_behaviour_id_index ON syntactic_behaviours (id);

CREATE TABLE syntactic_behaviour_senses (
    syntactic_behaviour_rowid INTEGER NOT NULL REFERENCES syntactic_behaviours (rowid) ON DELETE CASCADE,
    sense_rowid INTEGER NOT NULL REFERENCES senses (rowid) ON DELETE CASCADE
);
CREATE INDEX syntactic_behaviour_sense_sb_index
    ON syntactic_behaviour_senses (syntactic_behaviour_rowid);
CREATE INDEX syntactic_behaviour_sense_sense_index
    ON syntactic_behaviour_senses (sense_rowid);


-- Lookup Tables

CREATE TABLE relation_types (
    rowid INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    UNIQUE (type)
);
CREATE INDEX relation_type_index ON relation_types (type);

CREATE TABLE ili_statuses (
    rowid INTEGER PRIMARY KEY,
    status TEXT NOT NULL,
    UNIQUE (status)
);
CREATE INDEX ili_status_index ON ili_statuses (status);

CREATE TABLE lexfiles (
    rowid INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    UNIQUE (name)
);
CREATE INDEX lexfile_index ON lexfiles (name);
