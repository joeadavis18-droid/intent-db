#!/usr/bin/env python3
"""
langs/python/structure.py -- structural analysis of Python declarations.

Python's calling convention is part of its API in a way C++'s is not: an
argument that is keyword-only cannot be passed positionally, and that has to be
recorded. `inspect` already told us, so this mostly translates it into the
shared role vocabulary.
"""
from __future__ import annotations

# Argument names that carry a consistent meaning across the standard library.
NAME_ROLES = {
    "iterable": ("range", "the.range"), "seq": ("range", "the.range"),
    "sequence": ("range", "the.range"), "it": ("range", "the.range"),
    "key": ("projection", "access.projection"),
    "cmp": ("comparator", "order.compare"),
    "reverse": ("flags", "opt.flags"),
    "func": ("callable", "do.callable"), "function": ("callable", "do.callable"),
    "fn": ("callable", "do.callable"), "callback": ("callable", "do.callable"),
    "predicate": ("predicate", "test.predicate"),
    "path": ("path", "fs.path"), "filename": ("path", "fs.path"),
    "file": ("stream", "io.stream"), "fp": ("stream", "io.stream"),
    "obj": ("value", "the.value"), "o": ("value", "the.value"),
    "value": ("value", "the.value"), "val": ("value", "the.value"),
    "s": ("value", "the.text"), "string": ("value", "the.text"),
    "text": ("value", "the.text"), "pattern": ("value", "the.pattern"),
    "n": ("count", "amount.count"), "count": ("count", "amount.count"),
    "size": ("count", "amount.count"), "maxsplit": ("count", "amount.count"),
    "index": ("position", "at.index"), "i": ("position", "at.index"),
    "start": ("position", "range.first"), "stop": ("position", "range.last"),
    "encoding": ("flags", "opt.encoding"), "errors": ("flags", "opt.errors"),
    "mode": ("flags", "opt.mode"), "flags": ("flags", "opt.flags"),
    "default": ("value", "fallback.value"),
    "timeout": ("value", "time.duration"),
}

ANNOTATION_ROLES = [
    ("Callable", ("callable", "do.callable")),
    ("Iterable", ("range", "the.range")),
    ("Iterator", ("range", "the.range")),
    ("Sequence", ("range", "the.range")),
    ("Path", ("path", "fs.path")),
    ("IO", ("stream", "io.stream")),
    ("bool", ("flags", "opt.flags")),
    ("int", ("count", "amount.count")),
    ("str", ("value", "the.text")),
]


def infer_param(p: dict):
    kind = p.get("param_kind") or "positional-or-keyword"
    # A **kwargs bag is options, not a value.
    if kind == "var-keyword":
        return "flags", "opt.flags"
    if kind == "var-positional":
        return "callable", "args.pack"
    name = (p.get("name") or "").lower()
    if name in NAME_ROLES:
        return NAME_ROLES[name]
    ann = p.get("type") or ""
    for needle, role in ANNOTATION_ROLES:
        if needle in ann:
            return role
    # Keyword-only arguments with a default are how Python spells a flag.
    if kind == "keyword-only":
        return "flags", "opt.flags"
    return "input", None


def annotate_params(rec: dict) -> list[dict]:
    out = []
    for p in rec.get("params", []):
        role, sem = infer_param(p)
        q = dict(p)
        q["role"], q["semantic"] = role, sem
        q["optional"] = bool(p.get("default_value")) or p.get("optional", 0)
        out.append(q)
    return out


def home_header(defining_file, providers):
    """Python's include line is the import statement."""
    return providers[0] if providers else None
