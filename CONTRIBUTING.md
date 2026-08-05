# Contributing

Almost every contribution here is **data, not code**. You are teaching the
lexicon words it does not know, or telling it something it got wrong.

Three rules apply to all of them:

1. **Nothing mechanical is written by hand.** Signatures, parameters and types
   come from libclang, `inspect` and `--help`. If a declaration is missing,
   that is a scanner bug — file it, do not type the declaration in.
2. **Every change is measured.** `tools/eval.py` reports retrieval accuracy
   before and after. Include both numbers in the PR.
3. **The build stays clean.** `tools/lint.py` must report **0 errors**. It
   enforces the invariants the database depends on, listed at the bottom.

**Adding words needs no toolchain.** Phrasings and canonical terms feed only
the semantic layer, which builds against a prebuilt `base.db`:

```bash
python3 -m venv .venv
./.venv/bin/pip install sqlite-vec model2vec pyyaml
# download base.db from Releases into out/
make words                    # ~30 seconds: rebuild, embed, lint, measure
```

Only changing a **scanner** needs clang, GCC 14 headers and `make scan`.

---

## 1 · Semantic phrasings — the highest-value contribution

The way someone actually asks for something. Generated aliases come from
templates; real phrasings beat them.

**Where:** `packs/en/lexicon.py` → `VERB_SYNONYMS`

```python
"clear": ["clear", "empty", "wipe", "reset", "blank", "purge",
          "remove-everything-from", "delete-everything-in"],
```

Add the words you would actually type. Do not invent ones nobody says.

**Sentence shapes** live next to it in `PHRASE_FRAMES`, and filler words the
matcher should ignore in `FILLER`.

**Check it worked**

```bash
make && ./.venv/bin/python tools/eval.py
./.venv/bin/python tools/query.py "your new phrasing"
```

If the phrasing you added is a case worth protecting, add it to `CASES` in
`tools/eval.py` so a later change cannot silently break it.

---

## 2 · Canonical terms — precision work

The **one precise phrase** the system says back. Currently 263 of 15,101 are
hand-declared; the rest are derived and get thin in the tail.

**Where:** `packs/en/lexicon.py` → `DECLARED_TERMS`

```python
"sequence.reserve-capacity": "reserve capacity without changing the number of elements",
"memory.allocate-memory":    "allocate a block of uninitialised memory",
```

A good canonical term is:

- **imperative** — "sort a sequence into ascending order", not "sorting"
- **specific** — it names what distinguishes this from its neighbours
- **not an alias** — aliases are deliberately loose; this is the opposite job

Find the concept key with:

```bash
./.venv/bin/python tools/query.py --json "..." | grep intent
```

> **This is the one place a wrong answer does real damage.** The canonical term
> is what gets shown to someone who does not already know the answer. A
> plausible-but-wrong term teaches a false fact to exactly the person least able
> to catch it. If you are not sure, open an issue instead of a PR.

---

## 3 · Missed coverage — bug reports welcome

If something you expect is absent, that is a scanner bug.

```bash
./.venv/bin/python -c "
import sqlite3; con = sqlite3.connect('out/base.db')
print(con.execute('SELECT lang, header, std_since FROM entry WHERE qualified_name=?',
                  ('std::flat_map',)).fetchall())"
```

Open an issue with the symbol, the language, and the header you expected. Known
gaps: `<flat_map>` needs GCC 15 / libc++ 19; `sort`, `cat`, `head` and `ps` are
missing from the Unix surface because the safety denylist in
`tools/scan_unix.py` is over-broad.

---

## 4 · Language packs — a whole human language

Read [`packs/PACK_CONTRACT.md`](packs/PACK_CONTRACT.md) first. The essential
rule:

> A pack is **never a translation of another pack.** It is authored against the
> declarations. Translating English would make the new language inherit how
> English happened to carve up the concept space, which is the failure the
> structure exists to prevent.

```
packs/<locale>/
  pack.yaml      locale · name · connectives (grammar fragments)
  lexicon.py     the tables listed in PACK_CONTRACT.md
```

```bash
./.venv/bin/python tools/build_pack.py <locale>     # -> out/pack_<locale>.db
```

Machine translation of an existing pack will be declined. Native fluency is the
requirement, and unreviewed terms must carry `reviewed: 0`.

---

## 5 · Advisory edges — "this works, here is a safer way"

**Where:** `advice/<dialect>.yaml` for the edge, `packs/en/advice.yaml` for the
words.

```yaml
# advice/cpp.yaml
- {from: "std::map::operator[]", to: "std::map::at", severity: unsafe, key: subscript_inserts}
```

```yaml
# packs/en/advice.yaml
subscript_inserts:
  headline: "This works, but reading a missing key silently INSERTS it."
  rationale: >-
    operator[] default-constructs a value when the key is absent, so a lookup
    meant only to read quietly grows the map...
```

Advice is **per programming language**. `strcpy → std::string` is right in C++
and meaningless in C, where the honest answer is `snprintf`. Put C advice in
`advice/c.yaml`.

Three severities, and the distinction matters:

| | meaning |
|---|---|
| `unsafe` | a real correctness or security hazard is easy to hit |
| `obsolete` | superseded or removed by the standard |
| `prefer` | works correctly; a better idiom exists |

`malloc` is `prefer`, not `unsafe` — sometimes it is the right call, and a tool
that cries wolf gets ignored.

**Every rationale must be true.** An invented precondition is worse than none.

---

## Invariants (enforced by `tools/lint.py`)

| | |
|---|---|
| **R1** | every semantic key is unique within its locale |
| **R2** | every concept has exactly one canonical key |
| **R2b** | every entry is reachable |
| **R2c** | exactly one primary binding per (concept, language) |
| **R3** | keys are lowercase words joined by `-` and `.` — any script |
| **R4** | every concept is reachable from ≥2 modalities |
| **R7** | every concept declares a canonical term |

---

## Pull requests

- One kind of change per PR. Phrasings and advisory edges do not belong together.
- Include `eval.py` before/after and confirm `lint.py` reports 0 errors.
- Do not commit `out/` or `data/` — they are build artifacts and gitignored.
- Say what you verified, and say what you did not.

Uncertain whether something is a bug or a design choice? Open an issue. Being
told "that is deliberate, here is why" costs less than a reverted PR.
