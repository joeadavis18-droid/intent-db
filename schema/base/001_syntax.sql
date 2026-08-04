-- BASE :: the syntax layer. Language-NEUTRAL and shared by every pack.
--
-- This is what clang produced: declarations, parameters, the roles those
-- parameters play, canvas ports, and the emit templates. None of it depends on
-- a human language, so it is built once and ATTACHed by each pack rather than
-- duplicated into all of them.
--
-- It must cover the whole programming language. Semantic coverage may be
-- partial -- you only need words for what someone actually asks for -- but a
-- declaration that is missing here is invisible to every pack at once.

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS entry (
    id              INTEGER PRIMARY KEY,
    uid             TEXT NOT NULL UNIQUE,   -- 'cpp:std::sort(2)' / 'cpp:lang.kw.constexpr'
    lang            TEXT NOT NULL,          -- 'cpp'
    kind            TEXT NOT NULL,          -- see CHECK below
    name            TEXT NOT NULL,          -- 'sort'
    qualified_name  TEXT NOT NULL,          -- 'std::ranges::sort'
    namespace       TEXT,                   -- 'std::ranges'
    parent          TEXT,                   -- owning class for members: 'std::vector'
    header          TEXT,                   -- '<algorithm>'
    signature       TEXT,                   -- normalized one-line declaration
    return_type     TEXT,
    template_params TEXT,                   -- JSON array of template parameter decls
    overload_index  INTEGER DEFAULT 0,      -- disambiguates same-name overloads
    overload_count  INTEGER DEFAULT 1,

    is_template     INTEGER DEFAULT 0,
    is_constexpr    INTEGER DEFAULT 0,
    is_consteval    INTEGER DEFAULT 0,
    is_noexcept     INTEGER DEFAULT 0,
    is_static       INTEGER DEFAULT 0,
    is_const        INTEGER DEFAULT 0,
    is_explicit     INTEGER DEFAULT 0,
    is_variadic     INTEGER DEFAULT 0,
    is_deprecated   INTEGER DEFAULT 0,
    mutates_input   INTEGER,                -- NULL = unknown
    allocates       INTEGER,
    may_throw       INTEGER,

    std_since       TEXT,                   -- 'C++98' | 'C++11' | ... | 'C++26'
    std_deprecated  TEXT,
    std_removed     TEXT,
    complexity      TEXT,                   -- 'O(N log N)'

    summary         TEXT,                   -- one line: what it does, plain English
    intent_text     TEXT,                   -- rich paragraph; THIS is what gets embedded
    example         TEXT,                   -- minimal runnable snippet

    impl            TEXT,                   -- which stdlib provided it:
                                            -- libstdc++ | libc++ | both
    is_standard     INTEGER DEFAULT 1,      -- 0 = POSIX/vendor, not ISO
    source          TEXT NOT NULL,          -- 'libstdcxx-scan' | 'curated' | 'cppreference'
    confidence      REAL DEFAULT 1.0,       -- 1.0 curated, lower for auto-derived prose
    created_at      TEXT DEFAULT (datetime('now')),

    CHECK (kind IN (
        'function','function_template','member_function','constructor','destructor',
        'operator','conversion','class','class_template','struct','union','enum',
        'alias','concept','variable','variable_template','macro','keyword',
        'statement','preprocessor','attribute','literal_suffix','punctuator'
    ))
);

CREATE INDEX IF NOT EXISTS idx_entry_qname   ON entry(qualified_name);
CREATE INDEX IF NOT EXISTS idx_entry_name    ON entry(name);
CREATE INDEX IF NOT EXISTS idx_entry_header  ON entry(header);
CREATE INDEX IF NOT EXISTS idx_entry_kind    ON entry(lang, kind);

CREATE TABLE IF NOT EXISTS param (
    id              INTEGER PRIMARY KEY,
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL,
    name            TEXT,                   -- may be empty in a declaration
    type            TEXT NOT NULL,
    canonical_type  TEXT,                   -- clang-canonicalized
    default_value   TEXT,
    is_template_param INTEGER DEFAULT 0,
    is_pack         INTEGER DEFAULT 0,      -- Args&&...
    optional        INTEGER DEFAULT 0,      -- has a default / trailing-optional

    -- The semantic layer: what this parameter MEANS, not just its type.
    role            TEXT,                   -- input|output|inout|predicate|comparator|
                                            -- projection|allocator|policy|count|index|
                                            -- capacity|position|value|range|sentinel|
                                            -- callable|deleter|stream|path|flags
    semantic        TEXT,                   -- 'range.first' | 'range.last' | 'needle' |
                                            -- 'haystack' | 'exec.policy'
    units           TEXT,                   -- 'bytes' | 'elements' | 'seconds'
    constraints     TEXT,                   -- 'first <= last', 'n >= 0'
    doc             TEXT,

    UNIQUE (entry_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_param_entry ON param(entry_id);
CREATE INDEX IF NOT EXISTS idx_param_role  ON param(role);

-- Which public headers provide a given entry. A decl usually lives in a
-- bits/*.h detail file that several public headers pull in; we record every
-- public header that provides it and mark the most specific one as primary.

CREATE TABLE IF NOT EXISTS entry_header (
    entry_id   INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    header     TEXT NOT NULL,        -- '<algorithm>'
    is_primary INTEGER DEFAULT 0,
    PRIMARY KEY (entry_id, header)
);

CREATE INDEX IF NOT EXISTS idx_eh_header ON entry_header(header);

-- Raw scanner staging, kept so re-curation never needs a re-parse.
CREATE TABLE IF NOT EXISTS raw_decl (
    usr         TEXT PRIMARY KEY,
    payload     TEXT NOT NULL        -- JSON blob straight from the scanner
);

-- Codegen + canvas layer.
--
-- Two consumers drive this schema:
--   1. intent -> syntax compilation. An intent must resolve to ONE entry and
--      emit compilable text, so `emit_template` carries slots and `emit_form`
--      says how the call is spelled (free / method / static / ctor / operator).
--   2. visual canvas. A node needs PORTS, not parameters. std::sort takes two
--      iterator parameters but has ONE logical input: a sequence. `port`
--      groups the underlying params so the canvas draws one socket.

ALTER TABLE entry ADD COLUMN emit_form TEXT;       -- free|method|static|ctor|operator|construct
ALTER TABLE entry ADD COLUMN emit_template TEXT;   -- 'std::sort(${first}, ${last})'
ALTER TABLE entry ADD COLUMN emit_include TEXT;    -- '#include <algorithm>'
ALTER TABLE entry ADD COLUMN emit_confidence REAL DEFAULT 0.0;

-- One row per logical socket on the canvas node.
CREATE TABLE IF NOT EXISTS port (
    id          INTEGER PRIMARY KEY,
    entry_id    INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    direction   TEXT NOT NULL,      -- in | out | inout
    ordinal     INTEGER NOT NULL,
    label       TEXT NOT NULL,      -- 'sequence', 'comparator', 'result'
    port_kind   TEXT NOT NULL,      -- see CHECK below: drives socket shape/colour
    type        TEXT,               -- C++ type, or the element/iterator type
    required    INTEGER DEFAULT 1,
    variadic    INTEGER DEFAULT 0,
    param_ids   TEXT,               -- JSON [param.ordinal, ...] this port covers
    slot        TEXT,               -- name of the emit_template slot it fills
    doc         TEXT,

    -- What the IDE needs to RENDER a prompt for this socket. Structural and
    -- language-neutral: the widget to show, the rule to validate against, a
    -- seed value. The WORDS live in the pack (port_prompt), because they are
    -- language-specific; these three are not.
    input_kind      TEXT,           -- number|expression|lambda|identifier|
                                    -- path|type|enum|text|inferred|produced
    constraint_rule TEXT,           -- machine-checkable rule, or a stated
                                    -- precondition the caller must guarantee
                                    -- ('constraint' is reserved in SQLite)
    seed_value      TEXT,

    UNIQUE (entry_id, direction, ordinal),
    CHECK (direction IN ('in', 'out', 'inout')),
    CHECK (port_kind IN (
        'sequence','value','callable','predicate','comparator','projection',
        'policy','allocator','count','position','path','stream','flags',
        'object','result','error','pack'
    ))
);

CREATE INDEX IF NOT EXISTS idx_port_entry ON port(entry_id, direction);
CREATE INDEX IF NOT EXISTS idx_port_kind  ON port(port_kind);

-- Which port kinds may legally be wired together on the canvas. Deliberately a
-- table rather than code so the IDE can query it and grey out bad drops.
CREATE TABLE IF NOT EXISTS port_compat (
    out_kind    TEXT NOT NULL,
    in_kind     TEXT NOT NULL,
    note        TEXT,
    PRIMARY KEY (out_kind, in_kind)
);

INSERT OR IGNORE INTO port_compat (out_kind, in_kind, note) VALUES
    ('sequence','sequence','a range feeds any range-taking node'),
    ('sequence','value',   'a range can be reduced to a value downstream'),
    ('result',  'value',   'a returned value feeds a value socket'),
    ('result',  'sequence','a returned container feeds a range socket'),
    ('result',  'count',   'a returned size feeds a count socket'),
    ('result',  'position','a returned iterator feeds a position socket'),
    ('result',  'object',  'a returned object feeds a method receiver'),
    ('result',  'path',    'a returned path feeds a path socket'),
    ('value',   'value',   NULL),
    ('value',   'count',   NULL),
    ('count',   'count',   NULL),
    ('position','position',NULL),
    ('object',  'object',  NULL),
    ('path',    'path',    NULL),
    ('stream',  'stream',  NULL),
    ('callable','callable',NULL),
    ('callable','predicate','a callable returning bool is a predicate'),
    ('callable','comparator','a binary callable is a comparator'),
    ('predicate','predicate',NULL),
    ('comparator','comparator',NULL),
    ('error',   'error',   NULL);


-- "This works, and here is a safer way." The EDGE is structural: which
-- declaration supersedes which, and how strongly. Keyed by declaration
-- because concept partitions are pack-local and an edge stated in concepts
-- would not survive into another language pack. The WORDS live in the pack.
-- Advice is per PROGRAMMING language and does not transfer between them.
-- "use std::string instead of strcpy" is right in C++ and meaningless in C,
-- where the honest advice is strncpy or snprintf. Same hazard, different
-- remedy, so the row is scoped by the dialect it applies to.
CREATE TABLE IF NOT EXISTS advice (
    entry_id     INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    applies_to   TEXT NOT NULL DEFAULT 'cpp',  -- the dialect being written
    prefer_name  TEXT NOT NULL,        -- 'std::make_unique'
    prefer_entry INTEGER,              -- resolved where the target is indexed
    severity     TEXT NOT NULL,        -- prefer | unsafe | obsolete
    advice_key   TEXT NOT NULL,        -- -> pack advice_text
    PRIMARY KEY (entry_id, applies_to, prefer_name)
);
CREATE INDEX IF NOT EXISTS idx_advice_entry ON advice(entry_id);
