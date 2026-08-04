-- PACK :: the semantic layer for ONE human language.
--
-- ATTACHes base.db for the syntax. There is deliberately no `locale` column
-- anywhere: this whole database is one locale, so a stray row cannot end up in
-- the wrong language, and a pack can be shipped or dropped as a single file.
--
-- The concept partition lives HERE, not in base. English splits sort_heap into
-- (sort, on-heap) because the English tables say so; another language may
-- carve it differently and is entitled to.

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS pack_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS concept (
    id             INTEGER PRIMARY KEY,
    concept_key    TEXT NOT NULL UNIQUE,   -- 'sequence.sort' -- pack-local
    domain         TEXT,
    object         TEXT,
    action         TEXT,
    qualifiers     TEXT,
    canonical_term TEXT NOT NULL,          -- the precise phrase said BACK
    term_source    TEXT,                   -- 'declared' | 'derived'
    reviewed       INTEGER DEFAULT 0,
    summary        TEXT,
    port_shape     TEXT,
    n_bindings     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_concept_obj ON concept(object, action);

-- concept -> declaration in base.db. The declaration is the join key, which is
-- why reading English code in Czech never consults an English row.
CREATE TABLE IF NOT EXISTS binding (
    concept_id INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
    entry_id   INTEGER NOT NULL,           -- -> base.entry(id)
    lang       TEXT NOT NULL DEFAULT 'cpp',-- PROGRAMMING language
    quality    TEXT NOT NULL DEFAULT 'exact',
    is_primary INTEGER DEFAULT 0,
    note       TEXT,
    PRIMARY KEY (concept_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_binding_entry ON binding(entry_id);
CREATE INDEX IF NOT EXISTS idx_binding_lang  ON binding(lang, concept_id);

CREATE TABLE IF NOT EXISTS semantic_key (
    id         INTEGER PRIMARY KEY,
    key        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    concept_id INTEGER REFERENCES concept(id) ON DELETE CASCADE,
    entry_id   INTEGER,                    -- language-specific spellings
    key_type   TEXT NOT NULL,
    weight     REAL DEFAULT 1.0,
    source     TEXT NOT NULL DEFAULT 'generated',
    skeleton   TEXT,
    CHECK (key_type IN ('canonical','verb_object','object_verb','colloquial',
                        'question','problem','symbolic','abbrev'))
);

CREATE INDEX IF NOT EXISTS idx_key_concept  ON semantic_key(concept_id);
CREATE INDEX IF NOT EXISTS idx_key_entry    ON semantic_key(entry_id);
CREATE INDEX IF NOT EXISTS idx_key_skeleton ON semantic_key(skeleton);

-- Grammar fragments this language needs to bind arguments into a sentence.
CREATE TABLE IF NOT EXISTS connective (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- The WORDS of a parameter prompt, in this pack's language. Separate from the
-- structural half in base.port so a language pack can rewrite every question
-- without touching validation, and so validation cannot drift per language.
CREATE TABLE IF NOT EXISTS port_prompt (
    entry_id INTEGER NOT NULL,      -- -> base.entry(id)
    slot     TEXT NOT NULL,
    prompt   TEXT NOT NULL,         -- "How many bytes?"
    help     TEXT,                  -- why, and what counts as valid
    PRIMARY KEY (entry_id, slot)
);

-- Enumerated options for a slot, each carrying its own explanation, so the
-- popup can offer a dropdown where every choice teaches what it is. Lives in
-- the pack because the explanations are the substance and they are language-
-- specific; the values themselves are C++ tokens and travel with them.
CREATE TABLE IF NOT EXISTS port_choice (
    entry_id INTEGER NOT NULL,
    slot     TEXT NOT NULL,
    ordinal  INTEGER NOT NULL,
    value    TEXT NOT NULL,     -- the token emitted: 'int'
    label    TEXT,              -- what to show: 'whole number'
    help     TEXT,              -- what it MEANS, for someone who does not know
    PRIMARY KEY (entry_id, slot, ordinal)
);

-- Descriptive prose per declaration, in this pack's language. Feeds the
-- full-text and vector stages. Generated from the declaration, never
-- translated from another pack.
CREATE TABLE IF NOT EXISTS entry_text (
    entry_id    INTEGER PRIMARY KEY,
    summary     TEXT,
    intent_text TEXT
);

CREATE TABLE IF NOT EXISTS advice_text (
    advice_key TEXT PRIMARY KEY,
    headline   TEXT NOT NULL,   -- "This works, but ..."
    rationale  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tag (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, facet TEXT);
CREATE TABLE IF NOT EXISTS entry_tag (
    entry_id INTEGER NOT NULL, tag_id INTEGER NOT NULL,
    PRIMARY KEY (entry_id, tag_id));

CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(
    keys, name, qualified_name, summary, intent_text, header, tags,
    content='', tokenize="porter unicode61 remove_diacritics 2 tokenchars '_:.-'");
CREATE VIRTUAL TABLE IF NOT EXISTS key_fts USING fts5(key, tokenize="trigram");

-- ---------------------------------------------------------------- Photon ----
-- Photon is the UNION, not the intersection.
--
-- The goal is a language that can address every function from every language,
-- so a concept present in only ONE language is not noise to be discarded -- it
-- is a capability Photon must be able to express. The intersection would give
-- the smallest language that runs everywhere; the union gives the only one
-- that can do everything. These are opposite designs and it is worth being
-- explicit about which this is.
--
-- Photon does not exist until every language is exposed here and every
-- function defined. Until then this view measures how far short we are.
CREATE VIEW IF NOT EXISTS capability_surface AS
SELECT c.id,
       c.concept_key,
       c.canonical_term,
       c.domain,
       c.object,
       count(DISTINCT b.lang)          AS langs,
       group_concat(DISTINCT b.lang)   AS lang_list,
       count(b.entry_id)               AS implementations
FROM concept c LEFT JOIN binding b ON b.concept_id = c.id
GROUP BY c.id;

-- What Photon must cover that a given language cannot express at all.
CREATE VIEW IF NOT EXISTS capability_gaps AS
SELECT concept_key, canonical_term, domain, lang_list, langs
FROM capability_surface
ORDER BY langs ASC, domain, concept_key;
