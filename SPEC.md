# intent_db — project specification

**Status:** draft · 2026-08-04 · supersedes decisions held only in conversation

This document exists because the project was being built from active context
rather than from a written definition, and that produced circling — the same
framing questions reopened several times, and documentation that described the
project as something it is not.

Anything decided here should not be re-litigated without changing this file.

---

## 1. What this is

**Compiling all known code into a database with semantic keys.**

A lexicon: the deliverable is *data*, not software. The tools in `tools/` exist
only to build and query it, and are a means to the artifact.

It maps **intent ↔ syntax**, in both directions, across programming languages
and (eventually) human languages.

```
"grab some memory"  ─┐                        ┌─→  "allocate a block of
"reserve storage"   ─┼→  memory.allocate-memory  ─┤    uninitialised memory"
malloc(64)          ─┘                        └─→  malloc(${size});
```

Input may be broad. Output must be precise. That asymmetry is the core design
commitment, not an implementation detail.

## 2. What it is not

- **Not a documentation site.** Documentation is organised by spelling; you
  must already know the answer is called `std::lower_bound`. This is organised
  by intent.
- **Not a code-generation model.** It answers from a database. Given the same
  input it returns the same output, and it does not invent.
- **Not an IDE.** Two IDEs are intended to consume it (§3). They are separate,
  private products. This repository is the lexicon they read.
- **Not a translation of English into other languages.** Each human-language
  pack is authored against the declarations (§5.4).

## 3. Who consumes it

Two products, both private, both reading this database:

1. **Intent → syntax IDE.** The developer writes intent; the lexicon returns
   emittable syntax with slots, the include line, and prompts for every
   parameter the user must supply.
2. **Visual canvas IDE.** Functions as nodes with typed ports, wired together.
   Ports, not parameters: `std::sort` takes two iterators but has one logical
   input, a sequence.

A third use is served by the same data: **reading code you did not write.**
`explain` renders real source back into the intent layer.

### The purpose behind all three

Developer agency. Someone should be able to generate their own code alongside
AI rather than depending on it for syntax they do not understand — and be able
to read what AI produced well enough to argue with it.

## 4. Settled decisions

These cost real work to learn. Each states the failure that motivated it, so
the reason survives the decision.

### 4.1 Three independent axes

| axis | column | example |
|---|---|---|
| concept | `concept.concept_key` | `sequence.sort` |
| programming language | `binding.lang` | `cpp`, `c`, `python`, `unix` |
| human language | the pack file itself | `pack_en.db` |

Conflating any two of these caused a bug. Human language is the *pack*, not a
column, so a stray row cannot land in the wrong language.

### 4.2 Aliases are loose; canonical terms are precise

Aliases exist so input can be broad — 340k of them, ~22 per concept. The
canonical term is exactly one per concept, stored in a **separate table**, and
is what the system says back.

> **Failure that motivated it:** picking the highest-weighted alias as output
> returned *"stick something on the end of a vector"* where the correct answer
> was *"append an element to the end of a sequence"*. An alias doing a
> canonical term's job destroys the precision the whole design rests on.

### 4.3 The declaration is the join key

Human-language packs pivot on the *declaration*, not on a shared concept
partition. A Czech pack maps `std::sort → "seřadit posloupnost vzestupně"`
directly; reading an English codebase in Czech consults no English row.

> **Failure that motivated it:** the initial design routed Czech through an
> English-derived concept partition, so Czech inherited how English happened to
> carve up the space.

### 4.4 Nothing mechanical is hand-typed

Signatures, parameters, roles and versions come from libclang, `inspect` and
`--help`. A missing declaration is a scanner bug, never something to type in.

### 4.5 Versions are columns, not branches

`std_since` and `impl` are per-declaration, so one database answers every
targeting question by query. No parallel trees.

### 4.6 Concept partitioning is per-surface

Library functions share concepts because they are interchangeable
implementations — `vector::push_back` and `deque::push_back` are one operation.
**Shell commands are not.**

> **Failure that motivated it:** `ls`, `lsblk`, `lsns`, `lslocks`, `dir` and
> `vdir` collapsed into one concept, so "list directory contents" answered
> `lslocks`. Each command is now its own concept.

### 4.7 Advice is per programming language

`strcpy → std::string` is right in C++ and meaningless in C, where the honest
answer is `snprintf`. Severity is three-valued and honest: `unsafe` is a real
hazard, `prefer` is a better idiom. **Every rationale must be true** — an
invented precondition is taught as fact to the person least able to catch it.

### 4.8 The contributor loop needs no toolchain

Phrasings and canonical terms feed only `build_pack`, which reads a prebuilt
`base.db`. `make words` takes ~30 seconds and requires no clang. Only changing
a *scanner* needs the toolchain.

## 5. Current state — measured, 2026-08-04

```
declarations   27,153     cpp 14,249 · c 5,774 · python 5,513 · unix 1,617
concepts       15,101
semantic keys 339,797
canvas ports   70,681
param prompts  59,160
advisory edges     79     across 2 dialects
lint                0 errors
retrieval (C++)   top-1 65%  ·  top-5 80%  ·  phrasing agreement 82%
round-trip        7/7 statements
```

| surface | state |
|---|---|
| **C++** | complete for this toolchain. `<flat_map>` needs GCC 15 / libc++ 19 |
| **C** | ISO C and POSIX both present |
| **Python** | usable; carried by docstrings |
| **Unix** | **weak** — `rgrep` outranks `grep`; needs a prominence signal |

## 6. Open decisions — needed from the owner

These block or shape work and are **not** mine to settle.

1. **Licence shape.** The repository is Apache-2.0, a *software* licence. The
   deliverable is data. Should the data carry CC-BY-4.0 or CC-BY-SA-4.0 while
   the tools stay Apache-2.0?
2. **Publishing built databases.** Releasing `base.db` means distributing
   signatures extracted from libstdc++ (GPL-3 + runtime exception) and libc++
   (Apache-2.0 + LLVM exception). API declarations are generally facts, and
   *Google v. Oracle* is favourable, but this warrants a decision before assets
   are attached to a release.
3. **Scope of "all known code."** Standard libraries only, or third-party
   ecosystems too (PyPI, crates.io, Boost)? This changes the architecture: the
   current design assumes a bounded, versioned surface.
4. **Unix — keep, or park?** Weakest surface, not on the original roadmap,
   needs its own modeling.
5. **Photon's relationship to this repository.** Public lexicon, private
   language? The capability surface that Photon is derived from lives here.

## 7. Roadmap — checkable criteria only

No item may be phrased so that completion is a judgement call. "Robust" is not
a criterion.

| # | item | done when |
|---|---|---|
| 1 | **Rust surface** | `rustdoc --output-format json` extraction produces `raw_decls_rust.jsonl`; `langs/rust/structure.py` exists; `lang=rust` returns correct answers for 10 named intents; existing surfaces do not regress |
| 2 | **Canonical terms** | ≥2,000 of 15,101 declared (currently 263) |
| 3 | **Reverse parsing** | `explain` uses libclang; correctly resolves a file using `auto`, templates and member fields |
| 4 | **Unix prominence** | `grep`, `ls`, `tar`, `df`, `find` each rank first for one named intent |
| 5 | **Missing Unix tools** | `sort`, `cat`, `head`, `ps` present |
| 6 | **First non-English pack** | one pack at *reviewed* stage per `GOVERNANCE.md` |
| 7 | **Composition** | `find` + `it != end()` reported as one intent, not two |

Ordering is the owner's call. Items 1–5 are independent.

## 8. Non-goals

- Executing or compiling user code.
- Replacing a compiler, a language server, or documentation.
- Guessing when it does not know. A missing answer is correct behaviour; a
  confident wrong answer is a defect.
- Any bundled model. Retrieval is deterministic where a key matches.

## 9. How this document is used

Work is done **against this file**, not against conversation. If work in flight
does not correspond to something here, either it is out of scope or this file
is out of date — and the second is fixed by editing it first.

Changing a settled decision (§4) means editing §4 in the same commit, with the
reason. The failures recorded there are the expensive part; losing them means
relearning them.
