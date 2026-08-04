#!/usr/bin/env python3
"""
prose.py -- English descriptive text for a declaration.

This is what the full-text and vector stages search. It is deliberately packed
with the words a user would type rather than the words the standard uses:
someone looking for std::sort types "vector", never "RandomAccessIterator".

English prose, so it lives in the English pack. Another language generates its
own from the same declarations and never translates this.
"""
from __future__ import annotations

import re

import keygen
from lexicon import MOD_SYNONYMS, RANGE_LIKE


def make_summary(rec: dict) -> str:
    action, say, mods, nouns, tmpl = keygen.analyse_name(rec["name"])
    obj, _ = keygen.object_of(rec, rec.get("_params", []))
    o = keygen.articled(obj).replace("-", " ")

    if rec["kind"] in ("class", "class_template", "struct", "union"):
        return f"{rec['qualified_name']}: a {rec['name'].replace('_', ' ')} type."
    if rec["kind"] == "concept":
        return (f"{rec['qualified_name']}: satisfied when a type models "
                f"{rec['name'].replace('_', ' ')}.")
    if rec["kind"] == "alias":
        return f"{rec['qualified_name']}: a type alias."
    if rec["kind"] == "enum":
        return f"{rec['qualified_name']}: an enumeration."
    if rec["kind"] == "constructor":
        return f"Construct {o}."
    if rec["kind"] == "destructor":
        return f"Destroy {o} and release whatever it owns."

    if nouns:
        thing = keygen.articled("-".join(nouns)).replace("-", " ")
        base = f"{action.replace('-', ' ').capitalize()} {thing}."
    elif tmpl and (obj in RANGE_LIKE or "{o}" not in tmpl):
        base = tmpl.format(o=o) if "{o}" in tmpl else tmpl
    else:
        base = f"{action.replace('-', ' ').capitalize()} ({obj.replace('-', ' ')})."

    extra = []
    for p in rec.get("_params", []):
        if p.get("role") == "predicate" and "matching-predicate" in mods:
            continue
        if p.get("role") == "comparator":
            extra.append("using a custom comparator")
        elif p.get("role") == "predicate":
            extra.append("selecting elements with a predicate")
        elif p.get("role") == "policy":
            extra.append("under an execution policy (may run in parallel)")
        elif p.get("role") == "projection":
            extra.append("comparing a projection of each element")
    if extra:
        base = base.rstrip(".") + ", " + ", ".join(dict.fromkeys(extra)) + "."
    ret = rec.get("return_type") or "void"
    if ret not in ("void", "", None):
        base += f" Returns {ret}."
    return base


def make_intent_text(rec: dict) -> str:
    action, say, mods, nouns, _t = keygen.analyse_name(rec["name"])
    obj, alts = keygen.object_of(rec, rec.get("_params", []))
    dom = keygen.domain_of(rec)
    o = keygen.articled(obj)

    bits = [rec["qualified_name"], rec["name"].replace("_", " "),
            action.replace("-", " ")]
    bits += [t.format(o=o).replace("-", " ") if "{o}" in t else t.replace("-", " ")
             for t in say]
    bits += [obj.replace("-", " ")] + [a.replace("-", " ") for a in alts]
    for m in mods + nouns:
        bits.append(m.replace("-", " "))
        if m in MOD_SYNONYMS:
            bits.append(MOD_SYNONYMS[m])
    bits.append(f"{dom} operations in C++")
    if obj in RANGE_LIKE:
        bits.append("container collection")
    if obj in ("range", "sequence", "collection"):
        # Users say "sort a vector", never "sort a range of iterators".
        bits.append("works on a vector array deque list forward_list set map "
                    "unordered_map string span or any container or range")
    if rec.get("header"):
        bits.append("header " + rec["header"])
    for p in rec.get("_params", []):
        if p.get("semantic"):
            bits.append(f"{p.get('name') or p.get('role')} is the "
                        f"{p['semantic'].replace('.', ' ')}")
        elif p.get("name"):
            bits.append(f"parameter {p['name']} of type {p['type']}")
    if rec.get("return_type") and rec["return_type"] != "void":
        bits.append(f"returns {rec['return_type']}")
    if rec.get("std_since"):
        bits.append(f"available since {rec['std_since']}")
    return ". ".join(b for b in bits if b)
