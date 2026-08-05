#!/usr/bin/env python3
"""
codegen.py -- emittable syntax, and parameters grouped into logical inputs.

Two derived facts about every declaration:

  emit template   the call, with named slots and the include line, so the
                  syntax can be reconstructed:
                      #include <algorithm>
                      std::sort(v.begin(), v.end());

  ports           a parameter LIST is not the same as a function's logical
                  inputs. std::sort takes two iterators but has one logical
                  input: a sequence. A port records which parameters belong
                  together and what each group means.
"""
from __future__ import annotations

import json
import re

# Parameter semantics that collapse into one logical socket.
SEQUENCE_SEMANTICS = {"range.first", "range.last", "range.iterator", "the.range"}
DEST_SEMANTICS = {"range.destination"}

ROLE_TO_PORT = {
    "range": "sequence", "sentinel": "sequence",
    "predicate": "predicate", "comparator": "comparator",
    "projection": "projection", "policy": "policy",
    "allocator": "allocator", "count": "count", "position": "position",
    "value": "value", "callable": "callable", "deleter": "callable",
    "stream": "stream", "path": "path", "flags": "flags",
    "output": "sequence", "input": "value", "inout": "value",
}

# Types that are really an error channel rather than a value.
ERROR_TYPES = ("error_code", "errc")


def _is_member(rec: dict) -> bool:
    import keygen
    return keygen.is_member(rec) and rec.get("kind") != "constructor"


def slot_name(p: dict) -> str:
    return (p.get("name") or p.get("role") or f"arg{p['ordinal']}").lstrip("_")


# ------------------------------------------------------------------ ports ---

def derive_ports(rec: dict, params: list[dict]) -> list[dict]:
    """Group parameters into logical inputs, in declaration order."""
    ports: list[dict] = []
    used: set[int] = set()

    # 1. the receiver, for member calls -- the object the call acts on
    if _is_member(rec):
        parent = rec["qualified_name"].rsplit("::", 1)[0]
        ports.append({
            "direction": "inout" if not rec.get("is_const") else "in",
            "label": "object", "port_kind": "object", "type": parent,
            "required": 1, "variadic": 0, "param_ids": [], "slot": "object",
            "doc": f"the {parent.rsplit('::', 1)[-1]} the call acts on",
        })

    # 2. an iterator pair is ONE logical input, not two
    seq = [p for p in params if (p.get("semantic") in SEQUENCE_SEMANTICS)]
    if seq:
        ports.append({
            "direction": "in", "label": "sequence", "port_kind": "sequence",
            "type": seq[0].get("type"), "required": 1, "variadic": 0,
            "param_ids": [p["ordinal"] for p in seq],
            "slot": "sequence",
            "doc": "the range operated on; expands to begin/end at emit time",
        })
        used.update(p["ordinal"] for p in seq)

    dest = [p for p in params if p.get("semantic") in DEST_SEMANTICS]
    if dest:
        ports.append({
            "direction": "out", "label": "destination", "port_kind": "sequence",
            "type": dest[0].get("type"), "required": 1, "variadic": 0,
            "param_ids": [p["ordinal"] for p in dest],
            "slot": slot_name(dest[0]),
            "doc": "where results are written",
        })
        used.update(p["ordinal"] for p in dest)

    # 3. everything else is its own input
    for p in params:
        if p["ordinal"] in used:
            continue
        kind = ROLE_TO_PORT.get(p.get("role") or "input", "value")
        ty = p.get("type") or ""
        if any(e in ty for e in ERROR_TYPES):
            kind, direction = "error", "out"
        elif p.get("is_pack"):
            kind, direction = "pack", "in"
        elif "&" in ty and "const" not in ty and kind == "value":
            direction = "inout"
        else:
            direction = "in"
        ports.append({
            "direction": direction,
            "label": slot_name(p), "port_kind": kind, "type": p.get("type"),
            "required": 0 if p.get("optional") else 1,
            "variadic": 1 if p.get("is_pack") else 0,
            "param_ids": [p["ordinal"]], "slot": slot_name(p),
            "doc": p.get("semantic"),
        })

    # 4. the return value
    ret = rec.get("return_type")
    if ret and ret not in ("void", ""):
        kind = "result"
        if any(e in ret for e in ERROR_TYPES):
            kind = "error"
        ports.append({
            "direction": "out", "label": "result", "port_kind": kind,
            "type": ret, "required": 1, "variadic": 0, "param_ids": [],
            "slot": "result", "doc": f"returns {ret}",
        })

    for d in ("in", "out", "inout"):
        for i, p in enumerate([q for q in ports if q["direction"] == d]):
            p["ordinal"] = i
    return ports


# ------------------------------------------------------------------ emit ----

def derive_emit(rec: dict, params: list[dict], header: str | None):
    """-> (form, template, include, confidence)

    Slots are ${name}. The sequence slot is emitted as two arguments because
    that is what the call actually takes: the grouping is a property of the
    port, not of the emitted syntax.
    """
    q = rec["qualified_name"]
    kind = rec["kind"]

    args = []
    for p in params:
        if p.get("semantic") == "range.first":
            args.append("${sequence}.begin()")
        elif p.get("semantic") == "range.last":
            args.append("${sequence}.end()")
        elif p.get("optional"):
            args.append(f"${{{slot_name(p)}}}")
        else:
            args.append(f"${{{slot_name(p)}}}")
    arglist = ", ".join(args)
    include = f"#include {header}" if header else None

    if kind in ("function", "function_template") and not _is_member(rec):
        return "free", f"{q}({arglist});", include, 0.9
    if kind == "member_function" or _is_member(rec):
        method = q.rsplit("::", 1)[-1]
        if rec.get("is_static"):
            return "static", f"{q}({arglist});", include, 0.85
        return "method", f"${{object}}.{method}({arglist});", include, 0.85
    if kind == "constructor":
        cls = q.rsplit("::", 1)[0]
        return "ctor", f"{cls} ${{name}}{{{arglist}}};", include, 0.7
    if kind in ("class", "class_template", "struct", "alias"):
        return "construct", f"{q} ${{name}}{{}};", include, 0.6
    if kind == "operator":
        return "operator", rec.get("signature") or q, include, 0.4
    if kind in ("keyword", "statement", "preprocessor", "attribute",
                "punctuator", "macro"):
        # curated entries may supply their own `syntax:` in YAML
        return kind, rec.get("syntax") or rec["name"], None, \
            1.0 if rec.get("syntax") else 0.3
    return kind, None, include, 0.0


def render(template: str, bindings: dict[str, str]) -> str:
    """Fill ${slots}. Unbound slots stay visible as <name> placeholders, so
    what is still required is explicit rather than silently omitted."""
    def sub(m):
        k = m.group(1)
        return bindings.get(k, f"<{k}>")
    return re.sub(r"\$\{(\w+)\}", sub, template or "")
