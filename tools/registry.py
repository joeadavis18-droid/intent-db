#!/usr/bin/env python3
"""
registry.py -- once an alias points at a concept, it keeps pointing at it.

Alias uniqueness is enforced by lint (R1). Alias *ownership* was not: contested
aliases are awarded by ranking, so a newly added language could outrank an
incumbent and take one. Measured on adding Python: 1.1% of existing alias ->
concept relationships moved.

That is fine for search and fatal for anything joining to the lexicon from
outside, because a moved alias silently repoints an external link rather than
breaking it visibly.

So the first assignment wins, permanently. A newcomer that wants a taken alias
gets a refined variant instead -- exactly what already happens when two
concepts collide within one build. The registry is committed, so the guarantee
holds across machines and rebuilds, not just within one.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def path_for(locale: str) -> Path:
    return ROOT / "packs" / locale / "alias_registry.json"


def load(locale: str) -> dict:
    """alias -> concept_key, for every alias ever published in this pack."""
    p = path_for(locale)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh).get("aliases", {})
    except (OSError, json.JSONDecodeError):
        return {}


def save(locale: str, aliases: dict) -> None:
    """Write the live map, PRESERVING the retirement list.

    An earlier version rebuilt the file from the alias map alone, which
    silently erased every retirement on the next build -- the withdrawal
    mechanism quietly undid itself. Retirements are read back and carried
    forward explicitly.
    """
    p = path_for(locale)
    p.parent.mkdir(parents=True, exist_ok=True)
    retired = sorted(load_retired(locale))
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({
            "schema": "intent-db/alias-registry/1",
            "note": "First assignment wins. An alias here may never point at a "
                    "different concept; a later claimant is refined instead. "
                    "Entries are added, never rewritten. `retired` names are "
                    "withdrawn permanently and never reissued.",
            "count": len(aliases),
            "retired": retired,
            "aliases": dict(sorted(aliases.items())),
        }, fh, indent=0, sort_keys=True)
    tmp.replace(p)


def load_retired(locale: str) -> set:
    """Aliases withdrawn from service. Never reissued, never resolved.

    The registry is append-only so a published alias cannot silently repoint.
    Retirement is the deliberate exception: an alias that should never have
    existed is withdrawn rather than left to mean something wrong forever.
    Retired names are remembered precisely so they are not handed out again.
    """
    p = path_for(locale)
    if not p.exists():
        return set()
    try:
        with open(p, encoding="utf-8") as fh:
            return set(json.load(fh).get("retired", []))
    except (OSError, json.JSONDecodeError):
        return set()


def retire(locale: str, aliases, reason: str = "") -> int:
    """Withdraw aliases. Returns how many were newly retired."""
    p = path_for(locale)
    doc = {"schema": "intent-db/alias-registry/1", "aliases": {}, "retired": []}
    if p.exists():
        try:
            with open(p, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            pass
    live = doc.get("aliases", {})
    retired = set(doc.get("retired", []))
    n = 0
    for a in aliases:
        if a in live:
            del live[a]
            n += 1
        retired.add(a)
    doc["aliases"] = live
    doc["retired"] = sorted(retired)
    doc["count"] = len(live)
    doc.setdefault("retirement_notes", []).append(
        {"count": n, "reason": reason}) if reason else None
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=0, sort_keys=True)
    tmp.replace(p)
    return n


def reconcile(locale: str, assigned: dict) -> tuple[dict, list]:
    """Check a fresh assignment against the registry.

    -> (aliases to add, violations). A violation is an alias the build wanted
    to move; the caller must not honour it.
    """
    known = load(locale)
    additions, violations = {}, []
    for alias, concept in assigned.items():
        prior = known.get(alias)
        if prior is None:
            additions[alias] = concept
        elif prior != concept:
            violations.append((alias, prior, concept))
    return additions, violations
