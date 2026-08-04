#!/usr/bin/env python3
"""
langs/unix/structure.py -- structural analysis of command-line tools.

A flag is a parameter. The only distinction that matters structurally is
whether it takes a value, which the --help scan already recorded.
"""
from __future__ import annotations

# Flags whose meaning is near-universal across GNU tools.
COMMON_FLAGS = {
    "recursive": ("flags", "opt.recursive"), "verbose": ("flags", "opt.verbose"),
    "quiet": ("flags", "opt.quiet"), "silent": ("flags", "opt.quiet"),
    "force": ("flags", "opt.force"), "output": ("path", "fs.output"),
    "file": ("path", "fs.path"), "directory": ("path", "fs.path"),
    "help": ("flags", "opt.help"), "version": ("flags", "opt.version"),
    "all": ("flags", "opt.all"), "interactive": ("flags", "opt.interactive"),
    "dry-run": ("flags", "opt.dry-run"), "exclude": ("value", "filter.exclude"),
    "include": ("value", "filter.include"), "color": ("flags", "opt.colour"),
}


def infer_param(p: dict):
    name = (p.get("name") or "").lower()
    if name in COMMON_FLAGS:
        return COMMON_FLAGS[name]
    if p.get("param_kind") == "option-with-value":
        return "value", "opt.value"
    return "flags", "opt.flags"


def annotate_params(rec: dict) -> list[dict]:
    out = []
    for p in rec.get("params", []):
        role, sem = infer_param(p)
        q = dict(p)
        q["role"], q["semantic"] = role, sem
        q["optional"] = 1          # flags are optional by definition
        out.append(q)
    return out


def home_header(defining_file, providers):
    return None                    # a shell command has nothing to include
