# intent_db — specification

**Status:** 2026-08-04. §0 is the goal and §1–§2 the definition. §3 is
measured, never recalled. §4 records implementation decisions so they stay
visible and reversible. §5 is open and is never closed by inference.

This document covers **the database only**. Anything built to consume it is a
separate, private concern and is deliberately absent — not the code, and not
descriptions of it.

---

## 0. Goal

**Build a comprehensive database that captures all of the syntax, maps it to
semantic intents, and gets updated as both evolve.**

There is **no completion criterion**, because language does not stop moving —
syntactically or semantically. New standards land, libraries appear, functions
are deprecated and removed; and separately the words people use to describe an
operation shift, and better canonical statements get chosen for ones already
recorded.

So the measure is not *how much is done* but **how current and comprehensive it
is**:

- is every language covered scanned against its present state?
- is anything in the source absent from the database?
- when the source changes, does the database follow — including removals?
- does adding new material leave what is already published intact?

A percentage against a denominator the project chose for itself measures
nothing. Currency against an external source measures something real.

## 1. What this is

A **database lexicon of all known coding languages**.

Every function, tool and argument for every language should be represented. All
flags, arguments and parameters should be clearly documented.

Each function is mapped to:

1. a **canonical semantic key** — the one statement that best describes what it
   does, and
2. a **list of semantic aliases** — the many other ways people state the same
   thing.

So a request phrased loosely resolves to the right function, and the correct
syntax can be produced from the record.

It works in reverse as well: **given code, syntax lookup returns the canonical
semantic key describing what that code does.**

The database is **standalone**. It is a reference anyone can query, and it does
not assume any particular consumer.

## 2. Definitions

### 2.1 Canonical semantic key

The canonical semantic key is the **most descriptive semantic term** for a
function, chosen per language pack.

`malloc` could be stated as *reserve memory for*, *allocate memory for*, *grab
some memory*, *dedicate x amount of memory*. Several statements describe the
same action. **We choose the single statement that is most universal and
descriptive at the same time.** Because that statement may serve C, C++, Rust
and others, it is not simply `malloc`: it is the most technically correct but
semantically natural statement that fits.

Consequences:

- It is a **statement**, not an identifier. It reads as language.
- It is **chosen**, not generated. Choosing is the work.
- It is **free of any one language's spelling** — it serves C, C++ and Rust
  alike.
- It is **per language pack**. English first.
- There is exactly **one** per function.

### 2.2 Semantic aliases

Every other way the same action is stated: *reserve memory for*, *grab some
memory*, *dedicate x amount of memory*. Input is matched against these; the
canonical key is what comes back.

Aliases are deliberately broad. The canonical key is deliberately precise.

### 2.3 Parameter documentation

Every argument, flag and parameter carries **a definition of how to use it**:
what kind of value it takes, what makes a value valid, and why it matters.

A rule alone is not enough. *"Must be a valid identifier"* validates; it does
not teach. Both are recorded — the rule and the explanation.

Documentation must be **true**. An invented precondition is worse than none,
because it is read by whoever is least able to catch the error.

### 2.4 Reverse lookup

Given code, return the canonical semantic key for what it does. Whether a
consumer shows the key alone or alongside the code is the consumer's choice;
the database supplies both.

### 2.5 Scope

**All libraries and ecosystems**, in priority order: **standard, then expanded,
then obscure.**

### 2.6 Versioning

Version is **metadata on a row** — never a separate database, file or branch.
One database answers every targeting question by query. A package version is
another column, not another artifact.

### 2.7 Composition

A request may state several operations on several objects. This is served two
ways: single lookups that a consumer composes, **and** named composites in the
database for cases where the individual pieces give the wrong answer.

### 2.8 Evolution — derived from §0, not stated by the owner

Marked as derived: these follow from "gets updated as both evolve", but they
are my reading of it rather than the owner's words.

- **Syntax evolves.** A re-scan must be able to say what changed: what is new,
  what is gone, what altered its signature. Removals must be recorded as
  removed, not silently dropped, or the database cannot answer "can I still use
  this?"
- **Semantics evolve.** Canonical keys are rewritten as better statements are
  chosen, and new aliases appear as usage shifts. That must not disturb what is
  already published.
- **Provenance is required.** Every record should carry what it was scanned
  from and when, or currency cannot be assessed — only asserted.

## 3. Measured state — 2026-08-04

| | |
|---|---|
| declarations | 27,153 — C++ 14,249 · C 5,774 (ISO + POSIX) · Python 5,513 · Unix 1,617 |
| parameters | 44,622, with names, types and defaults; 23,219 shell flags |
| aliases | 339,797 |
| parameter documentation | 59,160 entries: kind, validation rule, example |
| logical inputs | 70,681 |
| reverse lookup | statement-by-statement; 7/7 round-trip on the test file |
| lint | 0 errors |

Extraction is mechanical throughout — libclang at each `-std=` level, Python
`inspect`, shell `--help`. Nothing is hand-typed.

### 3.1 The principal gap

A canonical semantic key is **chosen** (§2.1). By that standard:

```
declared      263    chosen by a person
vendor-doc  2,959    borrowed from a docstring or --help summary
derived    11,879    template output
```

**263 of 15,101 — 1.7% — have a canonical semantic key.** The rest hold
generated placeholders in the field where the key belongs: *"ETIMEDOUT: a
standard macro"*, *"param exponential distribution"*, *"expand default value"*.

Extraction is nearly complete. **Choosing has barely started**, and it is the
larger body of work.

### 3.2 Evolution is not built

Against §0, which is the goal rather than a detail:

- **Every rebuild destroys and recreates.** `build_base.py` calls
  `BASE.unlink()`. There is no history, so no rebuild can report what changed.
- **Removals are not tracked.** The `std_removed` column exists and is
  populated **0** times. A function withdrawn from a standard would simply
  vanish from the database, indistinguishable from one never scanned.
- **No provenance.** No `scanned_at`, no toolchain version, no source version.
  Currency cannot be measured, only claimed.
- **One piece does exist**: alias ownership is pinned and retirement is
  possible, so new material can be added without moving what is already
  published. That is evolution infrastructure and it serves §0 directly.

### 3.3 Other gaps

- **Scope assumes bounded.** §2.5 requires all libraries and ecosystems; the
  schema has no package or package-version column.
- **Composition does not exist.** Neither single-lookup composition support nor
  named composites are built.
- **Some internal identifiers carry C++ vocabulary** —
  `memory.allocate-memory.n-elements` — conflicting with §2.1's
  language-neutrality rule.
- **Reverse lookup uses regex, not a parser**; it will misresolve real files
  using `auto`, templates or member fields.
- **Unix retrieval is weak**: `rgrep` outranks `grep`. No prominence signal
  exists in `--help` output.
- **`<flat_map>`** needs GCC 15 / libc++ 19. `sort`, `cat`, `head`, `ps` are
  missing from the Unix surface — the safety denylist in `scan_unix.py` is
  over-broad.

## 4. Implementation decisions

Not part of the definition. Recorded so they are visible and reversible; if one
conflicts with §1–§2, §1–§2 wins.

### 4.1 An internal identifier alongside the key

Each concept carries a dotted identifier (`sequence.sort`) as well as its
canonical key. It exists to:

- **group declarations across programming languages** — the row binding
  `std::sort`, `qsort` and `sorted` together, and
- **stay stable when the key is reworded**, since keys will be rewritten as
  better statements are chosen.

It is never presented as the key, and must be free of any one language's
vocabulary, same rule as §2.1.

### 4.2 Package and version are columns

Following §2.6.

### 4.3 Logical inputs

Parameters are grouped into logical inputs. `std::sort` takes two iterators but
has one logical input, a sequence. The grouping is a property of the function,
recorded once, rather than something every consumer re-derives.

## 5. Open

1. **Licence shape.** The repository is Apache-2.0, a software licence, for a
   deliverable that is data.
2. **Publishing built databases** distributes signatures extracted from
   libstdc++ and libc++.

## 6. How this document is used

| section | rule |
|---|---|
| §0 | the goal; there is no completion criterion by design |
| §1–§2 | the definition; changed deliberately, not in passing |
| §3 | measured; re-measured, never recalled |
| §4 | implementation; reversible, loses to §1–§2 on conflict |
| §5 | open; never closed by inference |

A question answered in §2 is not asked again.
