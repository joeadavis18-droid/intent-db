#!/usr/bin/env python3
"""
build_base.py -- the syntax layer. Built once, shared by every language pack.

Everything here comes from clang: declarations, parameters and the roles they
play, canvas ports, emit templates. No human language is involved, so this is
built once and ATTACHed rather than copied into each pack.

    build_base.py   ->  out/base.db
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"


def load_constructs(con):
    """Constructs are written, not called, so their slots are declared rather
    than derived from a parameter list. Everything else -- ports, emit
    template, prompts -- flows through the same tables as a function."""
    import yaml
    f = ROOT / "constructs" / "cpp.yaml"
    if not f.exists():
        return
    n = 0
    for c in yaml.safe_load(f.read_text()) or []:
        uid = f"cpp:construct.{c['name']}"
        con.execute("""INSERT OR IGNORE INTO entry(
                uid, lang, kind, name, qualified_name, header, signature,
                std_since, source, confidence, emit_form, emit_template,
                emit_include, emit_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (uid, "cpp", c.get("kind", "statement"), c["name"],
                     c["name"], c.get("header"), c.get("emit"),
                     c.get("since"), "curated", 1.0, "construct",
                     c.get("emit"), None, 1.0))
        eid = con.execute("SELECT id FROM entry WHERE uid=?", (uid,)).fetchone()[0]
        for i, sl in enumerate(c.get("slots") or []):
            con.execute("""INSERT OR IGNORE INTO port(
                    entry_id, direction, ordinal, label, port_kind, type,
                    required, variadic, param_ids, slot, doc,
                    input_kind, constraint_rule, seed_value)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (eid, "in", i, sl["slot"], sl.get("port_kind", "value"),
                         None, int(sl.get("required", 1)), 0, "[]", sl["slot"],
                         None, sl.get("input_kind"), sl.get("constraint"),
                         sl.get("seed")))
        n += 1
    print(f"constructs {n} (declared slots, not derived)")


def _overload_key(rec):
    """Identity of an overload, independent of which stdlib declared it.

    USRs encode the declaring implementation, so they never match across
    libstdc++ and libc++ and every shared function looked unique. Parameter
    NAMES are standardised by the standard itself -- both spell them
    first/last/comp -- so the name tuple identifies the overload. Types fall
    back for unnamed parameters, arity for the rest.
    """
    params = rec.get("params") or []
    names = tuple((p.get("name") or "") for p in params)
    if all(names):
        shape = names
    else:
        shape = tuple((p.get("type") or "?") for p in params) or (len(params),)
    return (rec.get("lang", "cpp"), rec["qualified_name"], shape)


def load_language(con):
    """Keywords, operators, preprocessor directives, attributes.

    No compiler scan produces these -- clang reports what a keyword MEANS by
    obeying it, never by declaring it -- so the set is authored. Structural
    only; the English wording lives in the pack.
    """
    import yaml
    n = 0
    for f in sorted((ROOT / "language").glob("*.yaml")):
        lang = f.stem                     # language/c.yaml -> lang 'c'
        n = _load_language_file(con, f, lang, n)
    print(f"language   {n} constructs (keywords, operators, preprocessor)")


def _load_language_file(con, f, lang, n):
    import yaml
    for c in yaml.safe_load(f.read_text()) or []:
        con.execute("""INSERT OR IGNORE INTO entry(
                uid, lang, kind, name, qualified_name, signature, std_since,
                is_deprecated, source, confidence, emit_form, emit_template,
                emit_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (c["uid"], lang, c["kind"], c["name"], c["name"],
                     c.get("syntax"), c.get("since"),
                     int(bool(c.get("deprecated"))), "curated", 1.0,
                     c["kind"], c.get("syntax"), 1.0))
        n += 1
    return n


def load_advice(con):
    """Advisory edges: this declaration works, that one is safer."""
    import yaml
    n = miss = 0
    for f in sorted((ROOT / "advice").glob("*.yaml")):
        applies = f.stem              # advice/c.yaml -> applies_to = 'c'
        n, miss = _load_advice_file(con, f, applies, n, miss)
    print(f"advice     {n} edges ({miss} unresolved sources)")


def _load_advice_file(con, f, applies, n, miss):
    import yaml
    for a in yaml.safe_load(f.read_text()) or []:
        src = con.execute(
            "SELECT id FROM entry WHERE qualified_name=? ORDER BY overload_index",
            (a["from"],)).fetchall()
        if not src:
            miss += 1
            continue
        tgt = con.execute("SELECT id FROM entry WHERE qualified_name=? LIMIT 1",
                          (a["to"],)).fetchone()
        for (eid,) in src:
            con.execute("""INSERT OR IGNORE INTO advice(
                    entry_id, applies_to, prefer_name, prefer_entry,
                    severity, advice_key)
                    VALUES (?,?,?,?,?,?)""",
                        (eid, applies, a["to"], tgt[0] if tgt else None,
                         a["severity"], a["key"]))
            n += 1
    return n, miss


def main(lang="cpp"):
    # Structural analysis comes from the PROGRAMMING language's module, never
    # from a human-language pack: which parameter is the range and which
    # header to include are the same facts whatever the reader speaks.
    sys.path.insert(0, str(ROOT / "langs" / lang))
    sys.path.insert(0, str(ROOT / "packs" / "en"))   # codegen/keygen helpers
    import structure, codegen, keygen, lexicon, lexicon

    BASE.parent.mkdir(exist_ok=True)
    if BASE.exists():
        BASE.unlink()
    con = sqlite3.connect(BASE)
    for f in sorted((ROOT / "schema" / "base").glob("*.sql")):
        con.executescript(f.read_text())

    # every scanned language lands in the SAME base. A concept can then bind
    # to C and C++ at once, which is the axis Photon is derived from.
    # No single standard-library implementation ships all of C++23: libstdc++
    # has <generator>, libc++ has <mdspan>, and neither has <flat_map>. The
    # primary scan defines the surface; a supplementary implementation may only
    # ADD declarations the primary lacks, and each entry records its provenance.
    recs, seen = [], {}
    for f, lang, role in (("raw_decls.jsonl", "cpp", "primary"),
                          ("raw_decls_c.jsonl", "c", "primary"),
                          ("raw_decls_libcxx.jsonl", "cpp", "supplementary")):
        path = ROOT / "data" / f
        if not path.exists():
            continue
        got = [json.loads(l) for l in open(path)]
        added = shared = 0
        for r in got:
            r.setdefault("lang", lang)
            key = _overload_key(r)
            if role == "supplementary":
                if key in seen:
                    # present in both implementations: note it and move on
                    seen[key]["impl"] = "both"
                    shared += 1
                    continue
                r["impl"] = r.get("impl") or "libc++"
                added += 1
            else:
                r.setdefault("impl", "libstdc++" if lang == "cpp" else "glibc")
            seen[key] = r
            recs.append(r)
        if role == "supplementary":
            print(f"  {lang}/libc++: +{added} unique, {shared} already covered")
        else:
            print(f"  {lang}: {len(got)} declarations")
    n_raw = len(recs)
    recs = [r for r in recs
            if "(" not in r["name"] and "anonymous" not in r["name"]
            and "unnamed" not in r["name"] and "<" not in r["name"]
            and "deduction guide" not in r["name"]]
    print(f"loaded {len(recs)} declarations ({n_raw - len(recs)} artefacts dropped)")

    # roles + home header: structural, from langs/<lang>/structure.py
    for r in recs:
        r["_params"] = structure.annotate_params(r)
        r["_home"] = structure.home_header(r.get("file"), r.get("headers") or [])
    recs = keygen.prepare(recs)
    for r in recs:
        lang = r.get("lang", "cpp")
        uid = f"{lang}:{r['qualified_name']}#{r.get('overload_index', 0)}"
        con.execute("""
            INSERT OR IGNORE INTO entry(
                uid, lang, kind, name, qualified_name, namespace, parent,
                header, signature, return_type, template_params,
                overload_index, overload_count, is_template, is_constexpr,
                is_consteval, is_noexcept, is_static, is_const, is_explicit,
                is_variadic, is_deprecated, std_since, complexity,
                summary, intent_text, example, source, confidence,
                is_standard, impl)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            uid, lang, r["kind"], r["name"], r["qualified_name"],
            r.get("namespace"),
            r["qualified_name"].rsplit("::", 1)[0]
            if keygen.is_member(r) else None,
            r["_home"], r.get("signature"), r.get("return_type"),
            json.dumps(r.get("template_params") or []),
            r.get("overload_index", 0), r.get("overload_count", 1),
            *[int(bool(r.get(k))) for k in
              ("is_template", "is_constexpr", "is_consteval", "is_noexcept",
               "is_static", "is_const", "is_explicit", "is_variadic",
               "is_deprecated")],
            r.get("std_since"), r.get("complexity"),
            None, None, None, "libstdcxx-scan", 0.75,
            int(r["qualified_name"].startswith("std::")
                or r["name"] in lexicon.C_STANDARD),
            r.get("impl")))
        eid = con.execute("SELECT id FROM entry WHERE uid=?", (uid,)).fetchone()[0]
        r["_eid"] = eid

        for h in (r.get("headers") or []):
            con.execute("INSERT OR IGNORE INTO entry_header VALUES (?,?,?)",
                        (eid, h, 1 if h == r["_home"] else 0))
        for p in r.get("_params", []):
            con.execute("""INSERT OR IGNORE INTO param(
                    entry_id, ordinal, name, type, canonical_type,
                    default_value, is_pack, optional, role, semantic)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (eid, p.get("ordinal", 0), p.get("name"),
                         p.get("type", "?"), p.get("canonical_type"),
                         p.get("default_value"), int(bool(p.get("is_pack"))),
                         int(bool(p.get("optional"))), p.get("role"),
                         p.get("semantic")))

        ports = codegen.derive_ports(r, r.get("_params", []))
        form, tmpl, inc, conf = codegen.derive_emit(
            r, r.get("_params", []), r["_home"])
        con.execute("""UPDATE entry SET emit_form=?, emit_template=?,
                       emit_include=?, emit_confidence=? WHERE id=?""",
                    (form, tmpl, inc, conf, eid))
        for pt in ports:
            con.execute("""INSERT OR IGNORE INTO port(
                    entry_id, direction, ordinal, label, port_kind, type,
                    required, variadic, param_ids, slot, doc,
                    input_kind, constraint_rule, seed_value)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (eid, pt["direction"], pt["ordinal"], pt["label"],
                         pt["port_kind"], pt["type"], pt["required"],
                         pt["variadic"], json.dumps(pt["param_ids"]),
                         pt["slot"], pt["doc"], pt.get("input_kind"),
                         pt.get("constraint"), pt.get("example")))

    load_constructs(con)
    load_language(con)
    load_advice(con)
    con.commit()
    n = lambda q: con.execute(q).fetchone()[0]
    print(f"\nentries    {n('SELECT count(*) FROM entry')}")
    print(f"parameters {n('SELECT count(*) FROM param')}")
    print(f"ports      {n('SELECT count(*) FROM port')}")
    print(f"emittable  {n('SELECT count(*) FROM entry WHERE emit_confidence>=0.6')}")
    con.close()
    print(f"\n-> {BASE}   (shared by every pack)")


if __name__ == "__main__":
    main(*sys.argv[1:])
