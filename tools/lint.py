#!/usr/bin/env python3
"""
lint.py -- enforce the invariants the database depends on.

Run after every build. Exits non-zero on any ERROR; warnings are advisory and
name the entries worth curating next.

  R1  every semantic key is globally unique (case-insensitively)
  R2  every (intent, locale) has exactly one canonical key
  R3  keys are user-friendly: lowercase words (any script) joined by - and .
      (symbolic exempt, since those are the literal API spelling)
  R4  every entry is reachable from at least two distinct modalities
  R5  every callable declares its parameters
  R6  uids are unique and namespaced by language
  R7  every intent declares a canonical term (the precise phrase said back)
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"

# Unicode-aware on purpose. The rule is "lowercase words joined by - and .",
# not "ASCII": a Czech key like 'seřadit-vektor' is well formed, and demanding
# ASCII would make every non-English pack fail its own lexicon.
KEY_GRAMMAR = re.compile(r"^[^\W_]+(?:[-.][^\W_]+)*$", re.UNICODE)
MAX_KEY_LEN = 90
MIN_MODALITIES = 2
CALLABLE = ("function", "function_template", "member_function", "operator")

errors: list[str] = []
warnings: list[str] = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def main(locale="en"):
    con = sqlite3.connect(ROOT / "out" / f"pack_{locale}.db")
    con.row_factory = sqlite3.Row
    con.execute("ATTACH DATABASE ? AS base", (str(BASE),))
    print(f"pack: {locale}\n")

    # R1 -- uniqueness
    dupes = con.execute("""
        SELECT lower(key) k, count(*) n FROM semantic_key
        GROUP BY lower(key) HAVING n > 1 LIMIT 20""").fetchall()
    for d in dupes:
        err(f"R1 duplicate key '{d['k']}' used {d['n']} times")
    print(f"R1 uniqueness      : {len(dupes)} duplicates")

    # R2 -- exactly one canonical per INTENT (keys moved to the intent layer)
    # Per (intent, locale): each language names the intent once. Counting
    # globally would flag every intent the moment a second language pack lands.
    counts = con.execute("""
        SELECT c.concept_key, count(*) n
        FROM concept c JOIN semantic_key k
          ON k.concept_id = c.id AND k.key_type = 'canonical'
        GROUP BY c.id""").fetchall()
    bad = [c for c in counts if c["n"] != 1]
    for c in bad[:20]:
        err(f"R2 concept {c['concept_key']} has {c['n']} canonical keys")
    print(f"R2 canonical keys  : {len(counts) - len(bad)}/{len(counts)} concepts ok")

    # R2b -- every entry is reachable: bound to an intent, or has its own keys
    orphan = con.execute("""
        SELECT count(*) FROM base.entry e
        WHERE NOT EXISTS (SELECT 1 FROM binding b WHERE b.entry_id = e.id)
          AND NOT EXISTS (SELECT 1 FROM semantic_key k WHERE k.entry_id = e.id)
    """).fetchone()[0]
    if orphan:
        err(f"R2b {orphan} entries are unreachable (no binding and no keys)")
    print(f"R2b reachability   : {orphan} unreachable entries")

    # R2c -- exactly one primary binding per (intent, lang), or resolution is
    # ambiguous and ranking degenerates
    multi = con.execute("""
        SELECT count(*) FROM (SELECT concept_id, lang, count(*) n FROM binding
        WHERE is_primary=1 GROUP BY concept_id, lang HAVING n > 1)""").fetchone()[0]
    if multi:
        err(f"R2c {multi} intents have more than one primary binding")
    print(f"R2c primary binding: {multi} intents with multiple primaries")

    # R7 -- every intent declares a canonical term. Aliases may be loose; the
    # phrase the system says BACK may not be missing or empty.
    noterm = con.execute(
        "SELECT count(*) FROM concept WHERE canonical_term IS NULL "
        "OR trim(canonical_term) = ''").fetchone()[0]
    if noterm:
        err(f"R7 {noterm} intents have no canonical term")
    declared = con.execute(
        "SELECT count(*) FROM concept WHERE term_source='declared'").fetchone()[0]
    tot_i = con.execute("SELECT count(*) FROM concept").fetchone()[0]
    print(f"R7 canonical terms : {tot_i - noterm}/{tot_i} present "
          f"({declared} declared, {tot_i - declared} derived)")

    # R3 -- grammar
    ungrammatical = []
    toolong = []
    for k in con.execute(
            "SELECT key, key_type FROM semantic_key WHERE key_type != 'symbolic'"):
        if not KEY_GRAMMAR.match(k["key"]) or k["key"] != k["key"].lower():
            ungrammatical.append(k["key"])
        elif len(k["key"]) > MAX_KEY_LEN:
            toolong.append(k["key"])
    for k in ungrammatical[:15]:
        err(f"R3 key is not user-friendly: '{k}'")
    for k in toolong[:10]:
        warn(f"R3 key is {len(k)} chars, over {MAX_KEY_LEN}: '{k}'")
    print(f"R3 grammar         : {len(ungrammatical)} malformed, "
          f"{len(toolong)} overlong")

    # R4 -- modality coverage, measured on intents
    mod = {r["concept_id"]: r["m"] for r in con.execute("""
        SELECT concept_id, count(DISTINCT key_type) m FROM semantic_key
        WHERE concept_id IS NOT NULL GROUP BY concept_id""")}
    total = con.execute("SELECT count(*) FROM concept").fetchone()[0]
    thin = [i for i in con.execute("SELECT id, concept_key FROM concept")
            if mod.get(i["id"], 0) < MIN_MODALITIES]
    for i in thin[:10]:
        warn(f"R4 concept {i['concept_key']} reachable from "
             f"{mod.get(i['id'], 0)} modality only")
    print(f"R4 modalities      : {total - len(thin)}/{total} intents have "
          f">={MIN_MODALITIES} modalities")

    # R5 -- callables declare parameters (a zero-arg callable is legitimate,
    # so only flag ones whose signature clearly shows arguments)
    missing = con.execute(f"""
        SELECT uid, signature FROM base.entry e
        WHERE e.kind IN {CALLABLE!r}
          AND (SELECT count(*) FROM param p WHERE p.entry_id = e.id) = 0
          AND e.signature LIKE '%(%'
          AND e.signature NOT LIKE '%()%'
        LIMIT 2000""").fetchall()
    for m in missing[:5]:
        warn(f"R5 {m['uid']} takes arguments but declares no parameters")
    print(f"R5 parameters      : {len(missing)} callables missing parameter rows")

    # R6 -- uids
    d = con.execute("""SELECT uid, count(*) n FROM base.entry GROUP BY uid
                       HAVING n > 1 LIMIT 10""").fetchall()
    for x in d:
        err(f"R6 duplicate uid {x['uid']}")
    nolang = con.execute(
        "SELECT count(*) FROM base.entry WHERE uid NOT LIKE '%:%'").fetchone()[0]
    if nolang:
        err(f"R6 {nolang} uids are not namespaced 'lang:...'")
    print(f"R6 uids            : {len(d)} duplicates, {nolang} unnamespaced")

    # ---------------------------------------------------------- statistics --
    print("\n-- coverage " + "-" * 50)
    for row in con.execute("""SELECT kind, count(*) n FROM base.entry
                              GROUP BY kind ORDER BY n DESC"""):
        print(f"  {row['kind']:20} {row['n']:6}")
    print("\n-- keys by modality " + "-" * 42)
    for row in con.execute("""SELECT key_type, count(*) n FROM semantic_key
                              GROUP BY key_type ORDER BY n DESC"""):
        print(f"  {row['key_type']:20} {row['n']:6}")
    print("\n-- aliases per intent " + "-" * 40)
    dist = Counter(r["n"] for r in con.execute(
        "SELECT concept_id, count(*) n FROM semantic_key "
        "WHERE concept_id IS NOT NULL GROUP BY concept_id"))
    avg = sum(k * v for k, v in dist.items()) / max(sum(dist.values()), 1)
    print(f"  mean {avg:.1f}   min {min(dist)}   max {max(dist)}")
    print("\n-- capability surface (what Photon must cover) " + "-" * 15)
    for row in con.execute("""SELECT langs, count(*) n FROM capability_surface
                              GROUP BY langs ORDER BY langs"""):
        print(f"  concepts reachable in {row['langs']} language(s): {row['n']}")
    print(f"  emittable entries: " + str(con.execute(
        "SELECT count(*) FROM base.entry WHERE emit_confidence>=0.6").fetchone()[0]))
    print(f"  canvas ports:      " + str(con.execute(
        "SELECT count(*) FROM base.port").fetchone()[0]))

    print("\n-- by standard " + "-" * 47)
    for row in con.execute("""SELECT COALESCE(std_since,'unknown') s, count(*) n
                              FROM base.entry GROUP BY s ORDER BY s"""):
        print(f"  {row['s']:20} {row['n']:6}")

    print("\n" + "=" * 62)
    for w in warnings[:25]:
        print(f"WARN  {w}")
    if len(warnings) > 25:
        print(f"      ... and {len(warnings) - 25} more warnings")
    for e in errors:
        print(f"ERROR {e}")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
