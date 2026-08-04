#!/usr/bin/env python3
"""
query.py -- resolve an intent to a function.

Resolution is a cascade, strongest evidence first:

  1. exact semantic key      -- deterministic, weight-ordered
  2. normalised key          -- spaces/underscores folded to the key form
  3. key prefix / substring  -- trigram index, tolerant of partial recall
  4. full text               -- BM25 over keys + summary + intent text
  5. vector similarity       -- catches phrasings nobody wrote down

Stages 1-2 short-circuit: if a user typed a real key they get exactly that
entry. Everything below is ranked and merged.

  intentq "sort a vector"
  intentq --json "how do I read a whole file into a string"
  intentq --explain "put it in order"
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"          # shared syntax, every pack
DEFAULT_PACK = "en"


def pack_db(locale: str) -> Path:
    return ROOT / "out" / f"pack_{locale}.db"
sys.path.insert(0, str(Path(__file__).resolve().parent))

STAGE_WEIGHT = {"exact": 100.0, "normalised": 80.0, "skeleton": 60.0,
                "prefix": 40.0, "fts": 18.0, "pairs": 11.0, "vector": 15.0,
                "name": 8.0}

# "sort a vector" wants std::sort, not the std::vector class. Callables are
# what an intent lookup is for; types are supporting cast. Applied only to
# fuzzy stages -- an exact key hit is never re-ranked.
KIND_PRIOR = {
    "function": 1.0, "function_template": 1.0, "member_function": 0.95,
    "operator": 0.9, "constructor": 0.7, "conversion": 0.6, "destructor": 0.5,
    "keyword": 1.0, "statement": 1.0, "preprocessor": 1.0, "attribute": 0.9,
    "macro": 0.9, "literal_suffix": 0.9, "punctuator": 0.8,
    "concept": 0.55, "class": 0.5, "class_template": 0.5, "struct": 0.5,
    "union": 0.45, "enum": 0.45, "alias": 0.3, "variable": 0.35,
    "variable_template": 0.35,
}


def strip_frames(q: str) -> str:
    """Remove request wrappers so the intent underneath is what we match.

    "show me all the variables" and "list all variables" both reduce to
    "variables", which is why they resolve to the same entry without either
    phrasing needing its own key.
    """
    from lexicon import QUERY_FRAMES
    t = " " + re.sub(r"[^a-z0-9 ]+", " ", q.lower()).strip() + " "
    t = re.sub(r"\s+", " ", t)
    changed = True
    while changed:
        changed = False
        for f in sorted(QUERY_FRAMES, key=len, reverse=True):
            if t.startswith(" " + f + " "):
                t = " " + t[len(f) + 2:]
                changed = True
                break
    return t.strip()


def normalise(q: str) -> str:
    q = q.strip().lower()
    q = re.sub(r"[\s_]+", "-", q)
    q = re.sub(r"[^a-z0-9:.\-<>]", "", q)
    return q.strip("-.")


class Conn(sqlite3.Connection):
    """sqlite3.Connection forbids attribute assignment; subclass to allow it."""
    _vec = False


def open_db(locale: str = DEFAULT_PACK, base=BASE):
    """Open a language pack and ATTACH the shared syntax base.

    The pack holds the concepts and every phrasing; base holds the
    declarations. Selecting a language is choosing which pack file to open --
    there is no locale column to filter on.
    """
    con = sqlite3.connect(pack_db(locale), factory=Conn)
    con.row_factory = sqlite3.Row
    con.execute("ATTACH DATABASE ? AS base", (str(base),))
    try:
        import sqlite_vec
        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        con.execute("SELECT count(*) FROM vec_entry").fetchone()
        con._vec = True
    except Exception:
        con._vec = False
    return con


_model = None


def embed(text: str):
    global _model
    if _model is None:
        from model2vec import StaticModel
        cache = ROOT / "data" / "model"
        _model = StaticModel.from_pretrained(
            str(cache) if cache.exists() else "minishlab/potion-base-8M")
    import numpy as np
    v = np.asarray(_model.encode([text]), dtype=np.float32)[0]
    v /= (np.linalg.norm(v) + 1e-9)
    return v


SQL_KEY_TO_ENTRY = """
    SELECT COALESCE(k.entry_id, b.entry_id) AS entry_id,
           k.key, k.key_type, k.weight,
           CASE WHEN k.concept_id IS NULL THEN 1.0
                WHEN b.is_primary = 1      THEN 1.0
                ELSE 0.55 END AS binding_w
    FROM semantic_key k
    LEFT JOIN binding b
           ON b.concept_id = k.concept_id AND b.lang = ?
    WHERE {where}
      AND COALESCE(k.entry_id, b.entry_id) IS NOT NULL
"""


def search(con, query: str, limit=10, want_all=False, lang="cpp",
           locale="en"):
    """Resolve an intent to entries.

    A key may hang off an ENTRY (a C++ spelling) or off an INTENT (a neutral
    alias). Intent keys are followed through `binding` into the requested
    language, which is what lets one alias serve every language that
    implements the same operation.
    """
    hits: dict[int, dict] = {}

    def add(eid, stage, score, why):
        h = hits.setdefault(eid, {"score": 0.0, "why": []})
        h["score"] += STAGE_WEIGHT[stage] * score
        h["why"].append(why)

    nq = normalise(query)
    stripped = strip_frames(query)
    n_stripped = normalise(stripped)

    # 1/2. exact key: raw, normalised, then with request wrappers removed
    cands = [(query.strip(), "exact"), (nq, "normalised")]
    if n_stripped and n_stripped != nq:
        cands.append((n_stripped, "normalised"))
    for cand, stage in cands:
        for r in con.execute(
                SQL_KEY_TO_ENTRY.format(where="k.key = ? COLLATE NOCASE"),
                (lang, cand)):
            add(r["entry_id"], stage,
                r["weight"] / 10.0 * r["binding_w"],
                f"{stage} key '{r['key']}' ({r['key_type']})")
    # 2b. filler-stripped match: "wait for A thread to finish" reaches the key
    # "wait-for-THE-thread-to-finish".
    sys.path.insert(0, str(ROOT / "packs" / locale))
    from lexicon import FILLER, NAME_STOPWORDS
    for src in dict.fromkeys((query.lower(), stripped)):
        skel = "-".join(w for w in re.split(r"[^a-z0-9]+", src)
                        if w and w not in FILLER)
        if not skel:
            continue
        for r in con.execute(
                SQL_KEY_TO_ENTRY.format(where="k.skeleton = ?"), (lang, skel)):
            add(r["entry_id"], "skeleton", r["weight"] / 10.0 * r["binding_w"],
                f"filler-stripped match on '{r['key']}'")

    if hits and not want_all:
        return rank(con, hits, limit, locale, lang)

    # 3. key prefix / substring
    for r in con.execute(
            SQL_KEY_TO_ENTRY.format(
                where="k.id IN (SELECT rowid FROM key_fts WHERE key MATCH ?)")
            + " LIMIT 80", (lang, f'"{nq}"')):
        frac = len(nq) / max(len(r["key"]), 1)
        add(r["entry_id"], "prefix", r["weight"] / 10.0 * frac * r["binding_w"],
            f"key contains '{nq}': {r['key']}")

    words = [w for w in re.split(r"[^A-Za-z0-9_:]+", stripped or query)
             if len(w) > 1]
    # "a container" should reach vector/map/list entries, which never use the
    # word "container" in their own identifier.
    SYN = {"container": ["vector", "list", "map", "collection"],
           "list": ["vector", "container"], "array": ["vector", "container"],
           "dictionary": ["map", "unordered_map"], "hash": ["unordered_map"],
           "text": ["string"], "file": ["filesystem", "fstream"],
           "lambda": ["function", "callable"], "thread": ["thread", "async"]}
    expanded = list(words)
    for w in words:
        expanded += SYN.get(w.lower(), [])

    # 3b. a query word that IS the function name is strong evidence:
    # "sort a vector" should reach std::sort before std::stable_sort.
    # 4. full text
    if words:
        expr = " OR ".join(f'"{w}"' for w in dict.fromkeys(expanded))
        try:
            # The language restriction must be part of the query. Ranking
            # globally and filtering afterwards squeezed minority languages out
            # entirely -- a Unix query returned the top 40 C++ rows, then
            # discarded all of them.
            for r in con.execute("""
                    SELECT f.rowid AS entry_id,
                           bm25(entry_fts, 6,4,4,2,1,1,1) AS s
                    FROM entry_fts f
                    JOIN base.entry e ON e.id = f.rowid AND e.lang = ?
                    WHERE entry_fts MATCH ?
                    ORDER BY s LIMIT 40""", (lang, expr)):
                # SQLite bm25() returns MORE NEGATIVE for a better match, so
                # relevance is abs(s). Dividing by it inverted the ranking:
                # the worst text match scored highest.
                add(r["entry_id"], "fts", min(abs(r["s"]) / 8.0, 2.0),
                    f"text match (bm25 {r['s']:.1f})")
        except sqlite3.OperationalError:
            pass

    # 4b. coverage: entries matching MORE of the query should win. BM25 with an
    # OR rewards rare terms, so a single unusual word can carry an otherwise
    # irrelevant entry. Scoring adjacent word PAIRS accumulates naturally in
    # favour of entries that match the phrase rather than one lucky token.
    content = [w for w in words if w.lower() not in FILLER]
    for a, b in zip(content, content[1:]):
        try:
            for r in con.execute("""
                    SELECT rowid AS entry_id, bm25(entry_fts, 6,4,4,2,1,1,1) AS s
                    FROM entry_fts WHERE entry_fts MATCH ?
                    ORDER BY s LIMIT 12""", (f'"{a}" AND "{b}"',)):
                add(r["entry_id"], "pairs", min(abs(r["s"]) / 8.0, 2.0),
                    f"matched '{a} {b}' together")
        except sqlite3.OperationalError:
            pass

    # 5. vectors
    if getattr(con, "_vec", False):
        try:
            v = embed(query)
            for r in con.execute("""
                    SELECT v.entry_id, v.distance FROM vec_entry v
                    JOIN base.entry e ON e.id = v.entry_id AND e.lang = ?
                    WHERE v.embedding MATCH ? AND v.k = 400
                    ORDER BY v.distance LIMIT 40""", (lang, v.tobytes())):
                add(r["entry_id"], "vector", max(0.0, 1.0 - r["distance"] / 2.0),
                    f"semantic similarity {1 - r['distance']/2:.2f}")
        except Exception as e:
            print(f"[vector stage unavailable: {e}]", file=sys.stderr)

    # 6. A query word that IS a function name. Deliberately LAST and mostly
    # multiplicative: "equal" and "fill" and "empty" are ordinary English as
    # well as function names, so a bare name match must not outrank an entry
    # that actually matched the whole phrase. It amplifies existing evidence
    # rather than manufacturing its own.
    for w in words:
        if w.lower() in FILLER or w.lower() in NAME_STOPWORDS:
            continue
        rows = con.execute(
            "SELECT id, name FROM base.entry WHERE name = ? COLLATE NOCASE "
            "AND lang = ? "
            "AND kind IN ('function','function_template','member_function',"
            "'keyword','statement','operator','preprocessor','macro') "
            "LIMIT 60", (w, lang)).fetchall()
        share = 1.0 / (len(rows) ** 0.5) if rows else 0.0
        for r in rows:
            if r["id"] in hits:
                hits[r["id"]]["score"] *= 1.0 + 0.9 * share
                hits[r["id"]]["why"].append(f"name is '{r['name']}'")
            else:
                add(r["id"], "name", share, f"name is '{r['name']}'")

    return rank(con, hits, limit, locale, lang)


def rank(con, hits, limit, locale="en", lang="cpp"):
    # The language filter has to apply to EVERY stage. Keys resolve through
    # bindings, which are language-scoped, but full-text and vector matches are
    # not -- without this, asking in Python returns C++ answers.
    if lang:
        keep = {}
        for eid, h in hits.items():
            row = con.execute("SELECT lang FROM base.entry WHERE id=?",
                              (eid,)).fetchone()
            if row and row[0] == lang:
                keep[eid] = h
        hits = keep

    exact = any(w.startswith(("exact", "normalised"))
                for h in hits.values() for w in h["why"])
    if not exact:
        for eid, h in hits.items():
            k = con.execute(
                "SELECT kind, is_standard FROM base.entry WHERE id=?",
                (eid,)).fetchone()
            if k:
                h["score"] *= KIND_PRIOR.get(k[0], 0.7)
                if not k[1]:
                    # POSIX/vendor leakage: reachable by exact name, but it
                    # must not beat real API on an English phrase.
                    h["score"] *= 0.25
    out = []
    for eid, h in sorted(hits.items(), key=lambda kv: -kv[1]["score"])[:limit]:
        e = con.execute("SELECT * FROM base.entry WHERE id = ?", (eid,)).fetchone()
        if e is None:
            continue
        rec = dict(e)
        # prose lives in the pack, not in the shared syntax base
        t = con.execute("SELECT summary FROM entry_text WHERE entry_id=?",
                        (eid,)).fetchone()
        if t:
            rec["summary"] = t[0]
        rec["score"] = round(h["score"], 2)
        rec["why"] = h["why"][:3]
        # The CANONICAL way to say what the user asked for. Input may be loose
        # ("grab some memory"); what we hand back must be specific and clear
        # ("allocate memory"). Showing both is what teaches the reader.
        rec["semantic"] = None
        rec["intent"] = (con.execute(
            "SELECT c.concept_key FROM binding b JOIN concept c "
            "ON c.id=b.concept_id WHERE b.entry_id=?", (eid,)).fetchone()
            or [None])[0]
        rec["canonical_key"] = rec["intent"]
        if rec["intent"]:
            row = con.execute(
                "SELECT canonical_term FROM concept WHERE concept_key = ?",
                (rec["intent"],)).fetchone()
            if row:
                rec["semantic"] = row[0]
        rec["keys"] = [dict(r) for r in con.execute(
            """SELECT key, key_type FROM semantic_key
               WHERE entry_id=? OR concept_id IN
                     (SELECT concept_id FROM binding WHERE entry_id=?)
               ORDER BY weight DESC LIMIT 16""", (eid, eid))]
        rec["params"] = [dict(r) for r in con.execute(
            "SELECT ordinal,name,type,role,semantic,optional,default_value "
            "FROM base.param WHERE entry_id=? ORDER BY ordinal", (eid,))]
        rec["headers"] = [r[0] for r in con.execute(
            "SELECT header FROM base.entry_header WHERE entry_id=? "
            "ORDER BY is_primary DESC", (eid,))]
        # "this works, and here is a safer way" -- shown ABOVE the details,
        # because someone who asked for malloc most needs to hear it first.
        rec["advice"] = [dict(r) for r in con.execute("""
            SELECT a.prefer_name, a.severity, t.headline, t.rationale
            FROM advice a LEFT JOIN advice_text t ON t.advice_key = a.advice_key
            WHERE a.entry_id = ? AND a.applies_to = ?""", (eid, lang))]
        rec["alternatives"] = [dict(r) for r in con.execute("""
            SELECT e2.qualified_name, c.canonical_term AS summary,
                   'same_concept' AS kind
            FROM binding b
            JOIN concept c  ON c.id = b.concept_id
            JOIN binding b2 ON b2.concept_id = c.id AND b2.entry_id <> b.entry_id
            JOIN base.entry e2 ON e2.id = b2.entry_id
            WHERE b.entry_id = ? LIMIT 6""", (eid,))]
        out.append(rec)
    return out


# ------------------------------------------------------------- rendering ----

C = {"dim": "\033[2m", "b": "\033[1m", "g": "\033[32m", "y": "\033[33m",
     "c": "\033[36m", "r": "\033[0m", "m": "\033[35m"}


def render(recs, explain=False, color=True):
    c = C if color and sys.stdout.isatty() else {k: "" for k in C}
    if not recs:
        return "no match"
    lines = []
    for i, r in enumerate(recs, 1):
        std = f" {c['dim']}[{r['std_since']}]{c['r']}" if r["std_since"] else ""
        lines.append(f"{c['b']}{i}. {r['qualified_name']}{c['r']}"
                     f"  {c['c']}{r['header'] or ''}{c['r']}{std}"
                     f"  {c['dim']}score {r['score']}{c['r']}")
        for adv in r.get("advice", [])[:1]:
            mark = adv["severity"].upper()
            lines.append(f"   {c['m']}{mark}{c['r']} {adv['headline']}"
                         f"  {c['dim']}-> {adv['prefer_name']}{c['r']}")
        if r.get("semantic"):
            lines.append(f"   {c['m']}means{c['r']} {r['semantic']}")
        if r["summary"]:
            lines.append(f"   {r['summary']}")
        if r["signature"]:
            lines.append(f"   {c['g']}{r['signature']}{c['r']}")
        if r["canonical_key"]:
            lines.append(f"   {c['m']}key{c['r']} {r['canonical_key']}")
        if r["params"]:
            lines.append(f"   {c['dim']}parameters:{c['r']}")
            for p in r["params"]:
                opt = " (optional)" if p["optional"] else ""
                sem = f"  {c['dim']}<- {p['semantic']}{c['r']}" if p["semantic"] else ""
                lines.append(f"     {p['ordinal']}. {c['y']}{p['name'] or '_'}{c['r']}"
                             f": {p['type']}{opt}  {c['dim']}[{p['role']}]{c['r']}{sem}")
        alts = [a for a in r["alternatives"]][:3]
        if alts:
            lines.append(f"   {c['dim']}see also: "
                         + ", ".join(a["qualified_name"] for a in alts) + c["r"])
        if explain:
            for w in r["why"]:
                lines.append(f"   {c['dim']}. {w}{c['r']}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="resolve an intent to a C++ function")
    ap.add_argument("query", nargs="+")
    ap.add_argument("-n", "--limit", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="do not short-circuit on an exact key hit")

    ap.add_argument("--locale", default="en",
                    help="language pack to open (out/pack_<locale>.db)")
    ap.add_argument("--lang", default="cpp",
                    help="resolve intents into this language's bindings")
    ap.add_argument("--emit", action="store_true",
                    help="intent -> syntax: print the emittable call")
    ap.add_argument("--ports", action="store_true",
                    help="canvas: print the node's sockets")
    ap.add_argument("--strict", action="store_true",
                    help="one answer or none; refuse to guess when ambiguous")
    a = ap.parse_args()

    con = open_db(a.locale)
    recs = search(con, " ".join(a.query), max(a.limit, 2), a.all,
                  a.lang, a.locale)

    if a.strict:
        # Intent -> syntax compilation must not guess. Emit only when the top
        # hit is clearly ahead of the runner-up; otherwise report ambiguity so
        # the IDE can ask rather than silently produce the wrong call.
        if not recs:
            print("no match", file=sys.stderr)
            return 1
        top = recs[0]
        rival = recs[1]["score"] if len(recs) > 1 else 0.0
        if rival > top["score"] * 0.75:
            print(f"ambiguous: {top['qualified_name']} ({top['score']}) vs "
                  f"{recs[1]['qualified_name']} ({rival})", file=sys.stderr)
            return 2
        recs = [top]

    if a.emit:
        for r in recs[:a.limit]:
            if r.get("emit_include"):
                print(r["emit_include"])
            print(r.get("emit_template") or f"/* no template for {r['qualified_name']} */")
        return 0

    if a.ports:
        for r in recs[:a.limit]:
            print(f"{r['qualified_name']}   [{r.get('intent')}]")
            for p in con.execute(
                    "SELECT direction,ordinal,label,port_kind,type,required "
                    "FROM base.port WHERE entry_id=? ORDER BY direction, ordinal",
                    (r["id"],)):
                req = "" if p["required"] else "?"
                print(f"   {p['direction']:5} {p['label']}{req}: "
                      f"{p['port_kind']}  ({p['type']})")
        return 0

    recs = recs[:a.limit]
    if a.json:
        print(json.dumps(recs, indent=2, default=str))
    else:
        print(render(recs, a.explain))


if __name__ == "__main__":
    main()
