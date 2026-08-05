#!/usr/bin/env python3
"""
build_pack.py -- the semantic layer for ONE human language.

Reads the SHARED syntax base and this pack's own lexicon tables. It never reads
another pack: Czech concepts are derived from the declarations, not from the
English sentences about them, so Czech does not inherit how English happened to
carve up the concept space.

    build_pack.py en   ->  out/pack_en.db
    build_pack.py cs   ->  out/pack_cs.db
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"


def load_pack(name: str):
    d = ROOT / "packs" / name
    if not (d / "lexicon.py").exists():
        sys.exit(f"no pack at {d}")
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(d))
    import lexicon, keygen, codegen, prose
    import yaml
    meta = yaml.safe_load((d / "pack.yaml").read_text())
    return lexicon, keygen, codegen, prose, meta


def main(name="en"):
    lexicon, keygen, codegen, prose, meta = load_pack(name)
    out = ROOT / "out" / f"pack_{meta['locale']}.db"
    if out.exists():
        out.unlink()
    con = sqlite3.connect(out)
    for f in sorted((ROOT / "schema" / "pack").glob("*.sql")):
        con.executescript(f.read_text())
    con.execute("ATTACH DATABASE ? AS base", (str(BASE),))
    for k, v in meta.items():
        con.execute("INSERT OR REPLACE INTO pack_meta VALUES (?,?)", (k, str(v)))
    for k, v in (meta.get("connectives") or {}).items():
        con.execute("INSERT OR REPLACE INTO connective VALUES (?,?)",
                    (str(k), str(v)))

    # Rebuild the analysis records from the SHARED base, so the pack sees
    # declarations and roles -- never another language's prose.
    con.row_factory = sqlite3.Row
    recs = []
    for e in con.execute("SELECT * FROM base.entry").fetchall():
        r = dict(e)
        r["headers"] = [h[0] for h in con.execute(
            "SELECT header FROM base.entry_header WHERE entry_id=? "
            "ORDER BY is_primary DESC", (r["id"],))]
        r["_params"] = [dict(p) for p in con.execute(
            "SELECT ordinal,name,type,canonical_type,default_value,is_pack,"
            "optional,role,semantic FROM base.param WHERE entry_id=? "
            "ORDER BY ordinal", (r["id"],))]
        r["params"] = r["_params"]
        r["_eid"] = r["id"]
        r["doc"] = r.get("doc")
        r["_home"] = r["header"]
        r["_primacy"] = keygen.primary_rank_of(r) if hasattr(
            keygen, "primary_rank_of") else keygen.primacy_rank(r, r["_params"])
        r["_disamb"] = keygen.disambiguator(r["_params"])
        recs.append(r)
    print(f"pack '{meta['name']}' [{meta['locale']}]: "
          f"{len(recs)} declarations from base")

    # ---- concept partition: THIS pack's own carving -------------------------
    made, primary = {}, {}
    for r in recs:
        key, generic, act, quals = keygen.intent_key_of(r)
        r["_concept_key"] = key
        if key not in made:
            term, tsource = keygen.canonical_term(r)
            con.execute("""INSERT OR IGNORE INTO concept(
                    concept_key, domain, object, action, qualifiers,
                    canonical_term, term_source, summary)
                    VALUES (?,?,?,?,?,?,?,?)""",
                        (key, keygen.domain_of(r), generic, act,
                         json.dumps(quals), term, tsource, None))
            made[key] = con.execute(
                "SELECT id FROM concept WHERE concept_key=?", (key,)).fetchone()[0]
        cid = made[key]
        con.execute("""INSERT OR IGNORE INTO binding(
                concept_id, entry_id, lang, quality, is_primary)
                VALUES (?,?,?,?,0)""",
                    (cid, r["_eid"], r.get("lang", "cpp"), "exact"))
        # one primary per (concept, LANGUAGE): asking for "allocate memory"
        # in C must reach malloc, and in C++ whatever C++ prefers.
        lang = r.get("lang", "cpp")
        best = primary.get((key, lang))
        if best is None or r["_primacy"] < best[0]:
            primary[(key, lang)] = (r["_primacy"], r["_eid"])
    for (key, lang), (_p, eid) in primary.items():
        con.execute("UPDATE binding SET is_primary=1 WHERE concept_id=? "
                    "AND entry_id=? AND lang=?", (made[key], eid, lang))
    con.execute("""UPDATE concept SET n_bindings =
        (SELECT count(*) FROM binding b WHERE b.concept_id = concept.id)""")
    print(f"  concepts: {len(made)}   bindings: {len(recs)}")

    # ---- keys ---------------------------------------------------------------
    items, best = [], {}
    for r in recs:
        k = r["_concept_key"]
        if k not in best or r["_primacy"] < best[k]["_primacy"]:
            best[k] = r
    # what each concept-scoped item may claim, for the registry check
    import registry as _reg
    pinned = {a.lower(): c for a, c in _reg.load(meta["locale"]).items()}
    # withdrawn aliases are never reissued: the name is remembered so it
    # cannot be handed to a different concept later
    retired = {a.lower() for a in _reg.load_retired(meta["locale"])}

    for k, rep in best.items():
        _a, _s, mods, nouns, _sm = keygen.analyse_name(rep["name"])
        quals = keygen.disambiguator(rep["_params"])
        # Rank by how specialised the qualifiers are, not merely how many:
        # push_back(at-end) and push_heap(on-heap) each have one, but only one
        # of them is what "append to a vector" ordinarily means.
        spec = sum(getattr(lexicon, "MOD_RANK", {}).get(
                       m, getattr(lexicon, "DEFAULT_MOD_RANK", 3))
                   for m in mods)
        items.append({
            "_idx": ("concept", k), "_needs_canonical": True,
            "_cands": keygen.intent_candidate_keys(rep, rep["_params"]),
            "_primacy": (len(quals) + len(nouns), spec, len(mods))
                        + tuple(rep["_primacy"]),
            "_params": rep["_params"], "_disamb": mods + nouns + quals,
            "qualified_name": k, "namespace": None, "_owner_key": k})
    for r in recs:
        items.append({
            "_idx": ("entry", r["_eid"]), "_needs_canonical": False,
            "_cands": keygen.entry_symbolic_keys(r, r["_params"]),
            "_primacy": (99,) + tuple(r["_primacy"]),
            "_params": r["_params"], "_disamb": r["_disamb"],
            "qualified_name": r["qualified_name"],
            "namespace": r.get("namespace")})

    # Every canonical term must be typeable back in. The system says "the null
    # pointer constant"; typing that must return the same concept, or the two
    # directions disagree about their own vocabulary.
    for k, cid in made.items():
        term = con.execute("SELECT canonical_term FROM concept WHERE id=?",
                           (cid,)).fetchone()[0]
        if not term:
            continue
        as_key = re.sub(r"[^a-z0-9]+", "-", term.lower()).strip("-")
        if as_key:
            items.append({
                "_idx": ("concept", k), "_needs_canonical": False,
                "_cands": [("colloquial", as_key, 9.5)],
                "_primacy": (-1,) + tuple(best[k]["_primacy"]),
                "_params": [], "_disamb": [],
                "qualified_name": k, "namespace": None, "_owner_key": k})

    assigned = keygen.assign_keys(items, pinned, retired)
    collisions = assigned.pop("_collisions", 0)
    nkeys = 0
    for idx, keys in assigned.items():
        scope, ref = idx
        for kt, key, w in keys:
            if key.lower() in retired:
                continue
            col = "concept_id" if scope == "concept" else "entry_id"
            val = made.get(ref) if scope == "concept" else ref
            con.execute(f"""INSERT OR IGNORE INTO semantic_key(
                    key, {col}, key_type, weight, source, skeleton)
                    VALUES (?,?,?,?,?,?)""",
                        (key, val, kt, w, "generated",
                         skeleton(lexicon, key) if kt != "symbolic" else None))
            nkeys += 1
    print(f"  keys: {nkeys} ({collisions} collisions resolved)")

    # descriptive prose: what the text and vector stages actually search
    for r in recs:
        con.execute("INSERT OR REPLACE INTO entry_text VALUES (?,?,?)",
                    (r["_eid"], prose.make_summary(r), prose.make_intent_text(r)))
    print(f"  prose: {len(recs)} summaries")

    # teaching help + enumerated choices for declared construct slots
    nhelp = nchoice = 0
    for e in con.execute("SELECT id, name FROM base.entry "
                         "WHERE emit_form='construct'").fetchall():
        for pt in con.execute("SELECT slot FROM base.port WHERE entry_id=?",
                              (e["id"],)).fetchall():
            key = (e["name"], pt["slot"])
            help_text = getattr(lexicon, "SLOT_HELP", {}).get(key)
            if help_text:
                con.execute("""INSERT OR REPLACE INTO port_prompt(
                        entry_id, slot, prompt, help) VALUES (?,?,?,?)""",
                            (e["id"], pt["slot"],
                             pt["slot"].replace("_", " ").capitalize() + "?",
                             help_text))
                nhelp += 1
            for i, (val, label, hlp) in enumerate(
                    getattr(lexicon, "SLOT_CHOICES", {}).get(key, [])):
                con.execute("""INSERT OR REPLACE INTO port_choice(
                        entry_id, slot, ordinal, value, label, help)
                        VALUES (?,?,?,?,?,?)""",
                            (e["id"], pt["slot"], i, val, label, hlp))
                nchoice += 1
    print(f"  construct help: {nhelp} slots, {nchoice} choices")

    # the WORDS of each prompt, in this pack's language
    nprompt = 0
    for r in recs:
        for pt in codegen.derive_ports(r, r["_params"]):
            if not pt.get("prompt"):
                continue
            con.execute("""INSERT OR IGNORE INTO port_prompt(
                    entry_id, slot, prompt, help) VALUES (?,?,?,?)""",
                        (r["_eid"], pt["slot"], pt["prompt"], pt.get("help")))
            nprompt += 1
    print(f"  prompts: {nprompt}")

    # English wording for the authored language constructs. These carry
    # hand-written keys, which always outrank generated ones.
    import yaml as _y
    nlang = 0
    for lf in sorted((ROOT / "packs" / name).glob("language*.yaml")):
        for uid, w in (_y.safe_load(lf.read_text()) or {}).items():
            row = con.execute(
                "SELECT id, name, kind, lang FROM base.entry WHERE uid=?",
                (uid,)).fetchone()
            if not row:
                continue
            # a C keyword and its C++ namesake are different concepts: they
            # have different standard versions and can diverge in meaning
            ckey = f"{row['lang']}.language.{row['kind']}.{row['name']}".lower()
            con.execute("""INSERT OR IGNORE INTO concept(
                    concept_key, domain, object, action, qualifiers,
                    canonical_term, term_source, summary)
                    VALUES (?,?,?,?,?,?,?,?)""",
                        (ckey, "language", row["kind"], row["name"], "[]",
                         w.get("term") or row["name"], "declared",
                         w.get("intent")))
            cid = con.execute("SELECT id FROM concept WHERE concept_key=?",
                              (ckey,)).fetchone()[0]
            con.execute("""INSERT OR IGNORE INTO binding(
                    concept_id, entry_id, lang, quality, is_primary)
                    VALUES (?,?,?,?,1)""", (cid, row["id"], "cpp", "exact"))
            for kt, val in (w.get("keys") or {}).items():
                vals = [val] if isinstance(val, str) else list(val or [])
                for i, v in enumerate(vals):
                    con.execute("""INSERT OR IGNORE INTO semantic_key(
                            key, concept_id, key_type, weight, source, skeleton)
                            VALUES (?,?,?,?,?,?)""",
                                (str(v), cid, kt,
                                 10.0 if kt == "canonical" else 9.0 - i * 0.1,
                                 "curated",
                                 skeleton(lexicon, str(v))
                                 if kt != "symbolic" else None))
            nlang += 1
    print(f"  language: {nlang} constructs with authored keys")

    af = ROOT / "packs" / name / "advice.yaml"
    if af.exists():
        for k, v in (_y.safe_load(af.read_text()) or {}).items():
            con.execute("INSERT OR REPLACE INTO advice_text VALUES (?,?,?)",
                        (k, v["headline"], v["rationale"]))
        print(f"  advice text: {len(_y.safe_load(af.read_text()))} rationales")

    # register every concept alias, so the next build cannot move it
    fresh = {}
    for idx, keys in assigned.items():
        scope, ref = idx
        if scope == "concept":
            for kt, key, _w in keys:
                fresh[key] = ref
    additions, violations = _reg.reconcile(meta["locale"], fresh)
    if violations:
        print(f"  !! {len(violations)} alias(es) tried to move; refused")
        for a, was, now in violations[:3]:
            print(f"       '{a}': {was} -> {now}")
    merged = {**_reg.load(meta["locale"]), **additions}
    _reg.save(meta["locale"], merged)
    print(f"  registry: {len(merged)} pinned (+{len(additions)} new)")

    build_fts(con)
    con.commit()
    con.close()
    print(f"\n-> {out}   (ATTACHes base.db for syntax)")


def skeleton(lexicon, key: str) -> str:
    parts = re.split(r"[.\-]+", key.lower())
    kept = [p for p in parts if p and p not in lexicon.FILLER]
    return "-".join(kept or parts)


def build_fts(con):
    con.execute("DELETE FROM entry_fts")
    con.execute("DELETE FROM key_fts")
    rows = con.execute("""
        SELECT e.id, e.name, e.qualified_name, COALESCE(e.header,''),
               (SELECT group_concat(k.key, ' ') FROM semantic_key k
                 WHERE k.entry_id = e.id OR k.concept_id IN
                   (SELECT b.concept_id FROM binding b WHERE b.entry_id = e.id)),
               COALESCE((SELECT group_concat(c.canonical_term, ' ') FROM binding b
                 JOIN concept c ON c.id = b.concept_id WHERE b.entry_id = e.id), ''),
               COALESCE((SELECT t.intent_text FROM entry_text t
                 WHERE t.entry_id = e.id), '')
        FROM base.entry e""").fetchall()
    con.executemany(
        "INSERT INTO entry_fts(rowid, keys, name, qualified_name, summary,"
        " intent_text, header, tags) VALUES (?,?,?,?,?,?,?,?)",
        [(r[0], r[4] or "", r[1], r[2], r[5] or "", r[6] or "", r[3], "")
         for r in rows])
    con.executemany("INSERT INTO key_fts(rowid, key) VALUES (?,?)",
                    con.execute("SELECT id, key FROM semantic_key").fetchall())


if __name__ == "__main__":
    main(*sys.argv[1:])
