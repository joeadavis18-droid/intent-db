# intent_db — a lexicon of programming intent

**Compiling all known code into a database with semantic keys.**

Not a library and not a tool: a *lexicon*. The deliverable is the data. Look up
a function by **what you are trying to do**, and read existing code back as
**what it means**.

```
$ intentq "grab some memory"
malloc  <cstdlib>  [C++98]
  PREFER  This works, but modern C++ can manage this memory for you.  -> std::make_unique
  means   allocate a block of uninitialised memory

$ intentq --lang c "grab some memory"
malloc  <stdlib.h>  [C89]
  PREFER  This is correct C. Two things are easy to get wrong.  -> calloc
  means   allocate a block of uninitialised memory
```

…and the same lexicon in reverse:

```
$ explain --semantic main.cpp
   5  sequence.push.at-end     append an element to the end of `v` (3)
   7  sequence.sort            sort `v` into ascending order
  10  memory.allocate-memory   allocate a block of uninitialised memory for 64 bytes
```

## Why

Most references are organised by **spelling**. You have to already know the
thing is called `std::lower_bound` before you can look it up. That is backwards
for the person who most needs the answer.

This is organised by **intent**. Say it any way you like — `"grab some memory"`,
`"reserve storage"`, `"set aside memory for"` — and get one precise answer back.
Broad on the way in, exact on the way out.

## What is in it

| surface | declarations | source |
|---|---:|---|
| **C++** | 14,249 | libstdc++ 14 + libc++ 18, merged |
| **C** | 5,774 | glibc — ISO C **and POSIX** (`open`, `mmap`, `socket`, `fork`) |
| **Python** | 5,513 | CPython 3.12 by runtime introspection |
| **Unix** | 1,617 | shell commands, 23,219 flags, from `--help` |
| | **27,153** | |

| | |
|---|---|
| concepts | **15,101** language-neutral operations |
| semantic keys | **339,797** ways to ask for them |
| canvas ports | **70,681** typed sockets |
| parameter prompts | **59,160** |
| advisory edges | 79, scoped per dialect |

Everything mechanical is derived from the source of truth rather than
hand-typed: C and C++ from libclang at each `-std=` level, Python from
`inspect`, shell tools from `--help`. No one enumerated these by hand, and no
contribution should need to.

Shell commands and the POSIX C API are **different layers, not duplicates**: a
command is argv and flags, a syscall is a C function with a header. `stat` is
both, and they are separate entries.

## Design

Three axes, deliberately independent:

| axis | example | answers |
|---|---|---|
| **concept** | `sequence.sort` | *what is being done* |
| **programming language** | `cpp`, `c` | *what implements it* |
| **human language** | `en`, … | *what it is called* |

One `concept` row, many bindings. `memory.allocate-memory` binds to `malloc` in
`<stdlib.h>` for C and `<cstdlib>` for C++, with different advice for each —
because `malloc` is simply correct in C and usually a smell in modern C++.

```
data/raw_decls*.jsonl      the compiler scan — language-neutral
      │
      ├── out/base.db      declarations · parameters · roles · ports · emit templates
      │
      └── out/pack_en.db   concepts · canonical terms · 222k aliases · prompts
```

`base.db` is built once and shared. A **language pack** is a complete
bidirectional lexicon for one human language, authored against the declarations
— never translated from another pack, so it does not inherit how English
happened to carve up the concept space. See
[`packs/PACK_CONTRACT.md`](packs/PACK_CONTRACT.md).

### Versions are columns, not branches

Standard version and implementation are recorded per declaration, so one
database answers every targeting question by query:

```sql
-- what can I use if I target C++17?
SELECT * FROM entry WHERE std_since IN ('C++98','C++11','C++14','C++17');

-- what exists only in libc++?
SELECT qualified_name FROM entry WHERE impl = 'libc++';
```

No parallel trees to keep in sync.

### Aliases are loose; the canonical term is not

Aliases exist so input can be broad. The canonical term is the opposite
obligation: exactly one precise phrase per concept, stored separately, and it is
what the system says back. `std::vector::push_back` has 141 aliases and one
term — *"append an element to the end of a sequence"*.

## Using it

```bash
python3 -m venv .venv
./.venv/bin/pip install sqlite-vec model2vec pyyaml
# download base.db + pack_en.db from Releases, into out/
./.venv/bin/python tools/query.py "sort a vector"
```

**Adding words needs nothing more than that.** Edit a data file, then:

```bash
make words        # ~30 seconds: rebuild, embed, lint, measure
```

### Rebuilding the declarations themselves

Only needed if you are changing a *scanner*. This is the part that wants a
toolchain — clang 18, GCC 14 headers, optionally libc++ 18 for `<mdspan>`:

```bash
./.venv/bin/pip install libclang
make scan         # re-parse the standard libraries (~5 min)
make
```

## Where it needs help

This is the part that does not parallelise inside one head:

- **Semantic phrasings.** 340k aliases sounds like a lot; it is ~22 per concept
  and generated from templates. Phrasings real people actually type beat
  anything a template produces.
- **Canonical terms.** Only **263 of 15,101** are hand-declared. The rest are
  derived, and they get thin in the tail.
- **Missed coverage.** `<flat_map>` needs GCC 15 / libc++ 19. Beyond that, if
  something you expect is absent, that is a bug worth filing.
- **Language packs.** Czech, Japanese, anything. Someone who thinks in their own
  language should not have to think in English first.
- **Advisory edges.** 76 is a start. The valuable ones are the C++-on-C++ cases
  that bite people who believe they are already writing safe code.

## Status

Honest about what is unfinished:

- Reverse lookup uses regex, not a parser — fine for the examples above, will
  misresolve on real files with `auto` and templates.
- No composition: `find` followed by `if (it != end())` is one intent reported
  as two.
- Rust is planned, not started.
- Unix retrieval is weak: `rgrep` outranks `grep`. There is no prominence
  signal in `--help` output, so this needs package provenance, not tuning.
- Retrieval (C++): top-1 65%, top-5 80%, phrasing agreement 82%
  (`tools/eval.py`).

## Contributing

Almost everything here is **data, not code** — words the lexicon does not know
yet, or something it got wrong.

- [`SPEC.md`](SPEC.md) — **what this project is**, the decisions already
  settled and why, and what "done" means. Read this first.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — the five ways in, the file each lives
  in, and how to check your change helped
- [`GOVERNANCE.md`](GOVERNANCE.md) — branching, review, and how work gets
  promoted to `main`
- [`packs/PACK_CONTRACT.md`](packs/PACK_CONTRACT.md) — adding a human language

Contributions here are unusually **measurable**: a phrasing either improves
retrieval or it does not, and `tools/eval.py` says which. CI enforces that on
every PR, so approval mostly is not a matter of opinion.

Small changes go straight to a PR. A language pack or a new programming
surface gets a long-lived branch (`pack/ja`, `lang/rust`) because it is
additive and isolated — it writes only its own directory and cannot break an
existing surface.

Licensed Apache-2.0.
