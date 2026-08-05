# Branching, review and promotion

Most projects review contributions by taste. Here, most of them are
**measurable** — a phrasing either improves retrieval or it does not, and
`tools/eval.py` says which. That makes "approved" mostly objective, and this
document says exactly what the bar is.

## Two tracks

Choose by **size and lifetime**, not by importance.

### Track 1 — pull request to `main`

For anything that lands in one sitting: phrasings, canonical terms, advisory
edges, scanner fixes, a missed-coverage bug.

```
fork → branch → PR → automated gates → review → merge
```

Branch naming, so the intent is visible before the diff is read:

| prefix | for | example |
|---|---|---|
| `phrase/` | semantic phrasings | `phrase/filesystem-verbs` |
| `term/` | canonical terms | `term/container-operations` |
| `advice/` | advisory edges | `advice/cpp-iterator-invalidation` |
| `scan/` | scanner and extraction fixes | `scan/posix-aio-headers` |
| `fix/` | anything else | `fix/bm25-ranking` |

### Track 2 — long-lived branch

For work measured in weeks that should not block `main` and should not be
merged half-finished:

| prefix | for |
|---|---|
| `pack/<locale>` | a human-language pack — `pack/cs`, `pack/ja` |
| `lang/<name>` | a new programming surface — `lang/rust`, `lang/go` |

These get a branch because they are **additive and isolated**: a pack writes
only `packs/<locale>/`, a language writes only `langs/<name>/` plus its
scanner. Neither can break an existing surface, so they can develop in the open
and merge when they clear the bar.

Rebase on `main` rather than merging it back and forth. The shared scan
(`base.db`) moves underneath you; your surface should not carry merge commits
from it.

## Promotion gates

### Everything must pass

| gate | requirement |
|---|---|
| **lint** | `tools/lint.py` reports **0 errors** |
| **retrieval** | `tools/eval.py` top-1 **does not regress** |
| **build** | `make` completes from a clean checkout |
| **artifacts** | no `out/` or `data/` in the diff |

CI runs all four on every PR. A red build is not a matter of opinion.

### Additionally, by kind

**Phrasings** — if the phrasing is worth protecting, add it to `CASES` in
`tools/eval.py`. A contribution that only helps a case nobody measures will
be silently undone by the next change.

**Canonical terms** — must be imperative, specific, and distinguish the concept
from its neighbours. This is the one place a confident wrong answer does real
damage, because the term is shown to someone who does not already know the
answer. Reviewed by a maintainer, always.

**Advisory edges** — the rationale must be **true**, and the severity honest.
`unsafe` is a real hazard; `prefer` is a better idiom. Inflating `prefer` to
`unsafe` makes the whole advisory layer ignorable.

**Language packs** — promoted in three stages, so partial work is usable
without pretending to be finished:

| stage | bar | what it means |
|---|---|---|
| **experimental** | builds, lint clean | lives on `pack/<locale>`, not advertised |
| **reviewed** | ≥1 native speaker has signed off; `reviewed: 1` on every term | merges to `main`, listed as partial |
| **promoted** | ≥80% of concepts have terms; connectives complete | listed as a supported language |

A pack that is machine-translated from another pack is declined at every stage.
Native fluency is the requirement — see
[`packs/PACK_CONTRACT.md`](packs/PACK_CONTRACT.md).

**New programming surfaces** — must ship a scanner that extracts mechanically
(no hand-typed declarations), a `langs/<name>/structure.py`, and evidence that
the existing surfaces did not regress. Expect the concept model to need work:
every language added so far has broken something, and that is the point of
adding it early.

## Releases

`main` is always buildable. Versions are **tags**, not branches:

```
v0.2.0    tag on main
          release carries out/base.db and out/pack_*.db as assets
```

Standard version and implementation are already columns
(`std_since`, `impl`), so one database answers every targeting question — there
is no reason to branch per C++ version or per stdlib. See the README.

## Who decides

- **Automated** — lint, retrieval, build, artifacts. Not negotiable, not
  overridden by a maintainer being persuaded.
- **Maintainer** — canonical terms, advisory severity, concept partitioning.
  These encode judgement about what *is the same operation* and what is
  *actually hazardous*.
- **Native speakers** — everything inside a language pack. A maintainer who
  does not speak the language does not review its wording.

## When you disagree

Open an issue before the PR. "That is deliberate, and here is why" costs less
than a reverted merge, and several things that look like bugs are load-bearing
decisions — the concept partition and the aliases/canonical-term asymmetry
especially.
