# Language pack contract

A pack is a **complete bidirectional lexicon for one human language**:

    C++ declaration  <-->  semantics in that language

Packs are independent. A pack is never a translation of another pack, and no
pack may read another pack's rows. Czech is authored from the declarations, not
from the English sentences about them -- otherwise the Czech layer inherits how
English happened to carve up the concept space, which is the failure this
structure exists to prevent.

## What is shared

Exactly one thing: `data/raw_decls.jsonl`, the compiler scan.

    signature · parameters · parameter roles · ports · return type
    effects · std_since · headers

That artifact is produced by clang, not by any human language, so building it
per-pack would run the same compiler for identical output. **Everything above
it is pack-local**, including the concept partition.

## What a pack must provide

`packs/<locale>/lexicon.py` exporting:

| name | purpose |
|---|---|
| `CONCEPT_MAP` | identifier -> meaning, for names that hide it (`malloc`) |
| `VERBS` | identifier token -> action, phrasings, summary template |
| `MODIFIERS` | tokens that qualify an action (`_if`, `_back`) |
| `OBJECT_NOUNS` | class -> the words this language uses for it |
| `GENERIC_OBJECT` | concrete noun -> generic concept (`vector` -> sequence) |
| `DECLARED_TERMS` | concept key -> the precise canonical term |
| `QUALIFIER_TERMS` | qualifier -> the clause that distinguishes it |
| `VERB_SYNONYMS` | action -> interchangeable verbs, for broad input |
| `PHRASE_FRAMES` | sentence shapes (`{v}-{o}`, `how-do-i-{v}-{o}`) |
| `FILLER` / `NAME_STOPWORDS` | words carrying no lookup signal |
| `MASS_NOUNS` | nouns taking no article |
| `HEADER_DOMAIN` | header -> domain segment |

`packs/<locale>/pack.yaml` declaring `locale`, `name`, `version`.

## Consequences worth stating plainly

- **The concept partition is pack-local.** English splits `sort_heap` into
  `sequence.sort` + `on-heap` because the English tables say `heap` qualifies an
  action. Another language may carve it differently, and that is allowed.
- **Reading English code in Czech needs no English rows.** The join key is the
  declaration (`std::sort`), which every pack maps independently.
- **Cross-PROGRAMMING-language work is a different axis.** Deriving Photon asks
  "which operations exist in C++ and Python and Rust" -- that lives in one
  designated pack and does not require two human languages to agree.

## Building

    build_db.py --pack en     ->  out/pack_en.db
    build_db.py --pack cs     ->  out/pack_cs.db

Each database is single-locale: there is no `locale` column, because the pack
IS the locale.
