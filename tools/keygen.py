#!/usr/bin/env python3
"""
keygen.py -- turn a declaration into semantic keys.

A key is a user-friendly, globally unique string that names an INTENT. Every
entry gets one canonical key plus aliases spread across several modalities, so
the same function is reachable whether the user thinks in verbs ("sort a
vector"), in objects ("vector, sorted"), in plain speech ("put it in order"),
in questions ("how do I sort"), or in API spelling ("std::sort").

Uniqueness is absolute: no two entries may share a key. When two entries want
the same string, the more "primary" one keeps it (see primacy_rank) and the
other is pushed to a longer, more specific form. That mirrors the atom-number
registry rule -- the registered owner keeps the short name.
"""
from __future__ import annotations

import re
from collections import defaultdict

from lexicon import (CONCEPT_MAP, DECLARED_TERMS, GENERIC_OBJECT,
                     ENUM_ACTIONS, KNOWN_NAMESPACES, MASS_NOUNS,
                     QUALIFIER_TERMS, ENUM_FRAMES, HEADER_DOMAIN, MODIFIERS,
                     NAMESPACE_OBJECT, OBJECT_NOUNS, PARAM_NAME_ROLES,
                     PARAM_TYPE_ROLES, PHRASE_FRAMES, ROLE_DISAMBIG,
                     TYPEDEF_ALIASES, VERB_SYNONYMS, VERBS, home_header)

# How many generated paraphrase keys one entry may claim. Generous on purpose:
# the whole point is that a user's phrasing lands on a key rather than falling
# through to fuzzy matching. Capped only so a 10k-entry lexicon stays sane.
MAX_PARAPHRASES = 130

WORD_RE = re.compile(r"[a-z0-9]+")
STD_ORDER = {"C++98": 0, "C++11": 1, "C++14": 2, "C++17": 3,
             "C++20": 4, "C++23": 5, "C++26": 6, None: 7}


def slug(s: str) -> str:
    """Anything -> a friendly key segment: lowercase words joined by '-'."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s or "")
    parts = WORD_RE.findall(s.lower())
    return "-".join(p for p in parts if p)


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[_\s]+", name.lower()) if t]


# ------------------------------------------------------ parameter roles -----

def infer_param(p: dict) -> tuple[str | None, str | None]:
    """(role, semantic) for one parameter, from its name then its type."""
    nm = (p.get("name") or "").lower().strip("_")
    for names, role, sem in PARAM_NAME_ROLES:
        if nm in names:
            return role, sem
    ty = p.get("type") or ""
    for needle, role, sem in PARAM_TYPE_ROLES:
        if needle in ty:
            return role, sem
    if p.get("is_pack"):
        return "callable", "args.pack"
    if "&" in ty and "const" not in ty:
        return "inout", None
    return "input", None


def annotate_params(rec: dict) -> list[dict]:
    out = []
    for p in rec.get("params", []):
        role, sem = infer_param(p)
        q = dict(p)
        q["role"] = role
        q["semantic"] = sem
        q["optional"] = bool(p.get("default_value"))
        out.append(q)
    return out


# ------------------------------------------------------- name analysis ------

def analyse_name(name: str):
    """Split a C++ identifier into its intent parts.

    -> (action, phrase templates, modifier segments, noun segments, summary tmpl)

    Modifiers qualify the action ('_if' -> matching-predicate, '_back' ->
    at-end). Nouns are tokens we do not recognise as either verb or modifier,
    and they almost always name the thing being acted on: copy_FILE,
    create_DIRECTORY, is_regular_FILE.
    """
    # A name that hides its meaning is overridden outright: 'malloc' is not an
    # intent, "allocate memory for" is. This is what keeps intents portable
    # across languages that spell the same operation differently.
    concept = CONCEPT_MAP.get(name)
    if concept:
        return concept["a"], concept["say"], [], [], concept["sum"]

    toks = tokens(name)
    action, say, summ, mods, nouns = None, [], None, [], []
    for t in toks:
        if action is None and t in VERBS:
            v = VERBS[t]
            action, say, summ = v["a"], v["say"], v["sum"]
            continue
        if t in MODIFIERS:
            m = MODIFIERS[t]
            if m:
                mods.append(m)
            continue
        if t in VERBS:
            continue          # a second verb ('stable_SORT') is not a noun
        nouns.append(slug(t))
    if action is None:
        # No known verb -- the whole name IS the action (e.g. 'gcd', 'lerp').
        action = slug(name)
        nouns = []
    return action, say, [m for m in mods if m], [n for n in nouns if n], summ


def primary_header(rec: dict) -> str | None:
    h = rec.get("_home")
    if h is None:
        h = home_header(rec.get("file"), rec.get("headers") or [])
        rec["_home"] = h
    return h


def domain_of(rec: dict) -> str:
    h = primary_header(rec)
    if h and h in HEADER_DOMAIN:
        return HEADER_DOMAIN[h]
    for h in rec.get("headers") or []:
        if h in HEADER_DOMAIN:
            return HEADER_DOMAIN[h]
    ns = rec.get("namespace") or ""
    if "ranges" in ns:
        return "range"
    if "filesystem" in ns:
        return "filesystem"
    if "chrono" in ns:
        return "time"
    return "core"


MEMBER_KINDS = ("member_function", "constructor", "destructor", "conversion")


def is_member(rec: dict) -> bool:
    """True for anything called ON an object.

    clang reports a templated member function as FUNCTION_TEMPLATE, so kind
    alone is not enough: std::basic_string::append would otherwise look like a
    free function and have its object inferred from its iterator parameters.
    """
    if rec.get("kind") in MEMBER_KINDS:
        return True
    ns = rec.get("namespace")
    if ns is None:
        return False
    return ns not in KNOWN_NAMESPACES


def object_of(rec: dict, aparams: list[dict]) -> tuple[str, list[str]]:
    """-> (canonical object segment, alternate nouns)"""
    # A concept may declare what it acts on when the signature cannot say it:
    # malloc(size_t) looks like it takes a count, but it acts on MEMORY.
    concept = CONCEPT_MAP.get(rec.get("name", ""))
    if concept and concept.get("obj"):
        return concept["obj"], list(concept.get("alts") or [])

    parent = rec.get("qualified_name", "").split("::")
    if is_member(rec) and len(parent) >= 2:
        cls = parent[-2]
        nouns = OBJECT_NOUNS.get(cls)
        if nouns:
            return slug(nouns[0]), [slug(n) for n in nouns[1:]]
        return slug(cls), []
    # Free function: the object is whatever it operates on.
    roles = {p["role"] for p in aparams}
    if "range" in roles or "sentinel" in roles:
        # Nobody says "sort a range of iterators" -- they say "sort a vector".
        # The concrete containers are alternates so the paraphrase fan-out
        # produces sort-a-vector / order-an-array / arrange-a-list as real keys.
        return "range", ["vector", "array", "list", "sequence", "collection",
                         "string", "deque", "set", "map", "container"]
    if "path" in roles:
        return "path", ["file", "filename"]
    if "stream" in roles:
        return "stream", ["io"]
    ns = rec.get("namespace") or ""
    if ns in NAMESPACE_OBJECT:
        o, alts = NAMESPACE_OBJECT[ns]
        return o, alts
    if aparams:
        return "value", ["thing"]
    return "self", []


def disambiguator(aparams: list[dict]) -> list[str]:
    """Distinguish overloads by what their EXTRA parameters mean."""
    segs = []
    for p in aparams:
        d = ROLE_DISAMBIG.get(p["role"] or "")
        if d and d not in segs:
            segs.append(d)
    # Range/exec are the two that most often distinguish an overload family.
    order = ["parallel", "with-comparator", "matching-predicate",
             "with-projection", "with-allocator", "n-elements",
             "into-destination", "with-deleter", "with-flags"]
    segs.sort(key=lambda s: order.index(s) if s in order else 99)
    return segs


def refine_hints(rec: dict) -> list[str]:
    """Meaningful ways to tell two same-named entries apart, best first.

    Overloads usually differ by value category, constness, or one distinctive
    parameter type -- all of which a user can guess. The namespace is not a
    useful refinement (every entry shares it), so it is never used.
    """
    hints = []
    aps = rec.get("_params", [])
    # For members, const-ness is usually the whole difference between overloads.
    if rec.get("is_const"):
        hints.append("const")
    if rec.get("is_static"):
        hints.append("static")
    # A distinctive non-plumbing parameter type often names the variant:
    # copy_file(from, to, copy_options) -> '.copy-options'
    for p in reversed(aps):
        if p.get("role") in (None, "input", "inout") and p.get("type"):
            t = slug(re.sub(r"\b(const|volatile|std|basic|filesystem)\b", "",
                            p["type"]).replace("&", "").replace("*", ""))
            if t and t not in hints and 2 < len(t) < 28:
                hints.append(t)
            break
    if any("&&" in (p.get("type") or "") for p in aps):
        hints.append("move")
    elif any("const" in (p.get("type") or "") and "&" in (p.get("type") or "")
             for p in aps):
        hints.append("copy")
    if rec.get("std_since"):
        hints.append(slug(rec["std_since"]))
    return hints


# Who wins a contested key. Callables first: a phrase like
# "wait-for-the-thread-to-finish" describes an ACTION, so std::thread::join
# must outrank the class std::ranges::join_view no matter how the namespaces
# compare.
KIND_PRIMACY = {
    "function": 0, "function_template": 0, "member_function": 0,
    "operator": 0, "keyword": 0, "statement": 0, "preprocessor": 0,
    "attribute": 1, "punctuator": 1, "macro": 1,
    "constructor": 2, "conversion": 3, "destructor": 3,
    "concept": 4,
    "class": 5, "class_template": 5, "struct": 5, "union": 5, "enum": 5,
    "alias": 6, "variable": 6, "variable_template": 6, "literal_suffix": 6,
}


# When several containers offer the same member, which one does an unqualified
# phrase like "add to the end" most likely mean? Order reflects real-world use.
CONTAINER_PRIMACY = ["vector", "basic_string", "string", "unordered_map",
                     "map", "set", "unordered_set", "array", "deque", "list",
                     "span", "queue", "stack", "forward_list", "multimap",
                     "multiset", "unordered_multimap", "unordered_multiset"]


def container_rank(qname: str, member: bool = False) -> int:
    """Tiebreaker AMONG members of different containers. A free function is not
    a container member and must not be penalised by it -- std::sort is the
    canonical way to sort a sequence, ahead of std::list::sort."""
    if not member:
        return -1
    parts = qname.split("::")
    if len(parts) >= 2 and parts[-2] in CONTAINER_PRIMACY:
        return CONTAINER_PRIMACY.index(parts[-2])
    return len(CONTAINER_PRIMACY)


def namespace_rank(qname: str) -> int:
    """Plain std beats the specialised sub-namespaces for the short key."""
    if qname.startswith("std::experimental"):
        return 4
    if qname.startswith(("std::pmr::", "std::execution::")):
        return 3
    if qname.startswith(("std::ranges::", "std::views::")):
        return 2
    if qname.startswith("std::"):
        return 0
    return 1


def primacy_rank(rec: dict, aparams: list[dict]) -> tuple:
    """Lower sorts first == wins the short, bare key."""
    qname = rec.get("qualified_name", "")
    return (
        1 if rec.get("is_deprecated") else 0,
        KIND_PRIMACY.get(rec["kind"], 7),
        namespace_rank(qname),
        container_rank(qname, is_member(rec)),
        len(aparams),
        STD_ORDER.get(rec.get("std_since"), 7),
        len(qname),
        qname,
    )


# ------------------------------------------------------------ key build -----

def paraphrases(action: str, objs: list[str],
                mods: list[str]) -> list[tuple[str, str, float]]:
    """Every plausible way to ASK for this operation.

    Cross of (interchangeable verbs) x (names for the object) x (sentence
    shapes). "list all X" and "show me all X" are different keys pointing at
    the same entry -- that is the design, not a collision.
    """
    verbs = VERB_SYNONYMS.get(action)
    if not verbs:
        verbs = [action]
    # Deliberately NO modifier suffix here. "append to a vector" is what a
    # person types; "append-to-a-vector-at-end" is not. When two entries want
    # the same natural phrase, assign_keys() refines the loser -- that is the
    # right place to disambiguate, not the phrase generator.

    out: list[tuple[str, str, float]] = []
    for oi, obj in enumerate(objs[:9]):
        o = articled(obj)
        for vi, v in enumerate(verbs[:6]):
            # "allocate-memory-for" + object "memory" would read
            # "allocate-memory-for-memory"; when the verb already names the
            # object, the verb alone is the phrase.
            head = obj.split("-")[-1]
            redundant = head in v.split("-")
            for fi, (kind, frame) in enumerate(PHRASE_FRAMES):
                w = 5.0 - 0.02 * (vi * 2 + oi + fi * 3)
                phrase = (frame.replace("-{o}", "").replace("{o}", "")
                          if redundant else frame).format(v=v, o=o)
                out.append((kind, phrase.strip("-"), w))
        if action in ENUM_ACTIONS:
            for frame in ENUM_FRAMES:
                out.append(("colloquial", frame.format(o=obj + "s"
                                                       if not obj.endswith("s")
                                                       else obj), 4.0))
    out.sort(key=lambda t: -t[2])
    return out[:MAX_PARAPHRASES]


NEUTRAL_MODALITIES = {"canonical", "colloquial", "question", "problem",
                      "verb_object", "object_verb", "abbrev"}


def intent_key_of(rec: dict) -> tuple[str, str, str, list[str]]:
    """The language-neutral identity of what this entry DOES.

    -> (intent_key, generic_object, action, qualifiers)

    Built from the GENERIC object so std::vector::push_back and (later)
    Python's list.append land on the same row: 'sequence.append'.
    """
    action, _say, mods, nouns, _sum = analyse_name(rec["name"])
    obj, _alts = object_of(rec, rec.get("_params", []))
    generic = GENERIC_OBJECT.get(obj, obj)
    quals = disambiguator(rec.get("_params", []))
    act = ".".join([action] + nouns + mods)
    key = f"{generic}.{act}" if generic else act
    if quals:
        key += "." + ".".join(quals)
    return key, generic, act, quals


def canonical_term(rec: dict) -> tuple[str, str]:
    """The one precise phrase this intent is SAID BACK as. -> (term, source)

    Never taken from the alias pool. Aliases are deliberately loose so input
    can be broad; using the highest-weighted one as output produced things like
    "stick something on the end of a vector" -- an alias doing a canonical
    term's job. Declared terms win; otherwise the term is derived from the
    curated summary template, which was already written to be precise.
    """
    ikey, generic, act, quals = intent_key_of(rec)
    base_key = f"{generic}.{act}" if generic else act

    if base_key in DECLARED_TERMS:
        term, source = DECLARED_TERMS[base_key], "declared"
    else:
        action, _say, mods, nouns, summ = analyse_name(rec["name"])
        concept = CONCEPT_MAP.get(rec.get("name", ""))
        explicit = (concept or {}).get("term")
        if explicit:
            term, source = explicit, "declared"
        elif summ:
            # the summary template is already an imperative sentence
            t = summ.replace("{o}", articled(generic).replace("-", " "))
            t = re.sub(r"\s*Returns .*$", "", t).strip().rstrip(".")
            term = t[:1].lower() + t[1:] if t else act.replace(".", " ")
            source = "derived"
        else:
            thing = " ".join(nouns) if nouns else generic.replace("-", " ")
            term = f"{action.replace('-', ' ')} {thing}".strip()
            source = "derived"

    # A qualifier clause earns its place only if it ADDS information. A term
    # that already says "to the end" must not gain ", at the end", and a lone
    # size argument is inherent to the operation, not a distinguishing variant.
    nparams = len(rec.get("_params", []))
    stop = {"a", "an", "the", "of", "to", "in", "at", "for", "with", "by",
            "its", "that", "every", "each", "caller", "supplied", "specified"}

    def adds_information(clause: str) -> bool:
        words = {w for w in re.findall(r"[a-z]+", clause.lower())
                 if w not in stop}
        have = set(re.findall(r"[a-z]+", term.lower()))
        return not words <= have

    ordered = list(quals)
    _a, _s, mods, _n, _sm = analyse_name(rec["name"])
    ordered += [m for m in mods if m not in ordered]

    clauses = []
    for q in ordered:
        if q not in QUALIFIER_TERMS:
            continue
        if q == "n-elements" and nparams <= 1:
            continue        # the size IS the operation, not a variant of it
        c = QUALIFIER_TERMS[q]
        if c not in clauses and adds_information(c):
            clauses.append(c)
    if clauses:
        term = term + ", " + ", ".join(clauses)
    return term, source


def articled(obj: str) -> str:
    """'vector' -> 'a-vector'; 'output-stream' -> 'an-output-stream'.

    Mass nouns get no article ('memory', not 'a memory'), and an object that
    already carries one is left alone ('a-buffer').
    """
    if obj in ("self", "value"):
        return "it"
    if obj in MASS_NOUNS:
        return obj
    if obj.startswith(("a-", "an-", "the-")):
        return obj
    return ("an-" if obj[:1] in "aeiou" else "a-") + obj


def curated_keys(rec: dict) -> list[tuple[str, str, float]]:
    """Keys written by hand in curated/*.yaml, which always outrank generated
    ones. Shape: {canonical: str, colloquial: [...], question: [...], ...}."""
    spec = rec.get("keys") or {}
    out = []
    if isinstance(spec, dict):
        for kt, val in spec.items():
            vals = [val] if isinstance(val, str) else list(val or [])
            for i, v in enumerate(vals):
                w = 10.0 if kt == "canonical" else max(9.0 - i * 0.1, 5.0)
                out.append((kt, str(v), w))
    out.sort(key=lambda t: (t[0] != "canonical", -t[2]))
    return out


def intent_candidate_keys(rec: dict, aparams: list[dict]) -> list:
    """Language-NEUTRAL keys, which attach to the intent rather than the entry.

    The canonical key uses the generic object ('sequence.append'); the aliases
    span the concrete words people actually type ('append-to-a-vector',
    'add-to-a-list'). Because these hang off the intent, binding Python's
    list.append to the same intent later reuses every one of them -- no
    regeneration, and therefore no collision with C++'s copies.
    """
    ikey, generic, act, quals = intent_key_of(rec)
    obj, alt_objs = object_of(rec, aparams)
    action, say, mods, nouns, _ = analyse_name(rec["name"])

    out: list[tuple[str, str, float]] = [("canonical", ikey, 10.0)]
    objs = [generic] + [o for o in [obj] + alt_objs if o != generic]
    for o in objs[:5]:
        out.append(("verb_object", f"{act}.{o}", 6.0))
        out.append(("object_verb", f"{o}.{act}", 6.0))
    o0 = articled(obj)
    for i, tmpl in enumerate(say[:4]):
        phrase = tmpl.format(o=o0) if "{o}" in tmpl else tmpl
        out.append(("colloquial", phrase, 6.0 - i * 0.1))
        if i == 0:
            out.append(("question", f"how-do-i.{phrase}", 5.5))
    out.extend(paraphrases(action, objs, mods))

    seen, uniq = set(), []
    for kt, k, w in out:
        k = k.strip(".-")
        if not k or k in seen or ".." in k or "--" in k:
            continue
        if not re.match(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$", k):
            continue
        seen.add(k)
        uniq.append((kt, k, w))
    return uniq


def entry_symbolic_keys(rec: dict, aparams: list[dict]) -> list:
    """Language-SPECIFIC spellings. These stay on the entry: 'std::sort' means
    nothing in Python, so it must never be inherited through an intent."""
    q = rec["qualified_name"]
    out = [("symbolic", q, 8.0)]
    if rec.get("overload_index"):
        out.append(("symbolic", f"{q}/{len(aparams)}", 7.0))
    short = q.replace("std::", "")
    if short != q:
        out.append(("symbolic", short, 5.0))
    parts = q.split("::")
    if len(parts) >= 2 and parts[-2] in TYPEDEF_ALIASES:
        for friendly in TYPEDEF_ALIASES[parts[-2]]:
            alias = "::".join(parts[:-2] + [friendly, parts[-1]])
            out.append(("symbolic", alias, 7.5))
            out.append(("symbolic", alias.replace("std::", ""), 4.5))
    seen, uniq = set(), []
    for kt, k, w in out:
        if k and k not in seen:
            seen.add(k)
            uniq.append((kt, k, w))
    return uniq


def candidate_keys(rec: dict, aparams: list[dict]) -> list[tuple[str, str, float]]:
    """-> [(key_type, key, weight)] in preference order, before uniquing."""
    if rec.get("_curated") and rec.get("keys"):
        hand = curated_keys(rec)
        auto = [] if any(kt == "canonical" for kt, _, _ in hand) else None
        if auto is not None:
            seen = {k.lower() for _, k, _ in hand}
            return hand + [(kt, k, w) for kt, k, w in _generated_keys(rec, aparams)
                           if k.lower() not in seen and kt != "canonical"]
    return _generated_keys(rec, aparams)


def _generated_keys(rec: dict, aparams: list[dict]) -> list[tuple[str, str, float]]:
    dom = domain_of(rec)
    obj, alt_objs = object_of(rec, aparams)
    action, say, mods, nouns, _ = analyse_name(rec["name"])
    disamb = disambiguator(aparams)
    qname = rec["qualified_name"]

    act_full = ".".join([action] + nouns + mods)
    # '_if' already says "matching-predicate"; do not say it twice.
    disamb = [d for d in disamb if d not in mods]
    base = f"{dom}.{obj}.{act_full}"
    canonical = ".".join([base] + disamb) if disamb else base

    out: list[tuple[str, str, float]] = [("canonical", canonical, 10.0)]

    # verb-first and object-first views of the same idea
    out.append(("verb_object", f"{act_full}.{obj}", 6.0))
    out.append(("object_verb", f"{obj}.{act_full}", 6.0))
    for a in alt_objs[:2]:
        out.append(("object_verb", f"{a}.{act_full}", 4.0))
        out.append(("verb_object", f"{act_full}.{a}", 4.0))

    # plain speech, hand-written first: these are the best phrasings we have
    o = articled(obj)
    for i, tmpl in enumerate(say[:4]):
        phrase = tmpl.format(o=o) if "{o}" in tmpl else tmpl
        out.append(("colloquial", phrase, 6.0 - i * 0.1))
        if i == 0:
            out.append(("question", f"how-do-i.{phrase}", 5.5))

    # ...then the generated paraphrase fan-out, so a user's wording lands on a
    # real key instead of falling through to fuzzy matching.
    out.extend(paraphrases(action, [obj] + alt_objs, mods))

    # literal API spelling -- power users type this
    out.append(("symbolic", qname, 8.0))
    if rec.get("overload_index"):
        out.append(("symbolic", f"{qname}/{len(aparams)}", 7.0))
    short = qname.replace("std::", "")
    if short != qname:
        out.append(("symbolic", short, 5.0))
    parts = qname.split("::")
    if len(parts) >= 2 and parts[-2] in TYPEDEF_ALIASES:
        for friendly in TYPEDEF_ALIASES[parts[-2]]:
            alias = "::".join(parts[:-2] + [friendly, parts[-1]])
            out.append(("symbolic", alias, 7.5))
            out.append(("symbolic", alias.replace("std::", ""), 4.5))

    seen, uniq = set(), []
    for kt, k, w in out:
        k = k.strip(".-")
        # An empty path segment ('.-it', 'sort..range') means some part of the
        # name analysis produced nothing; drop rather than emit a broken key.
        if not k or k in seen or ".." in k or "--" in k or ".-" in k or "-." in k:
            continue
        if kt != "symbolic" and not re.match(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$", k):
            continue
        seen.add(k)
        uniq.append((kt, k, w))
    return uniq


def assign_keys(entries: list[dict], pinned: dict | None = None
                ) -> dict[int, list[tuple[str, str, float]]]:
    """
    Global assignment pass. Entries are ranked by primacy; the winner of a
    contested key keeps it and losers fall back to a longer specific form.
    Deterministic: same input always yields the same keys.
    """
    ranked = sorted(entries, key=lambda e: e["_primacy"])
    taken: dict[str, int] = {}
    result: dict[int, list] = defaultdict(list)
    collisions = 0

    for e in ranked:
        idx = e["_idx"]
        got_canonical = False
        # Suffixes tried, in order, when a wanted key is already owned. They
        # read as natural refinements, so a contested key still ends up
        # guessable: 'sort.range' taken -> 'sort.range.with-comparator'.
        refine = [*e.get("_disamb", []), *refine_hints(e),
                  f"arity-{len(e['_params'])}"]

        for kt, key, w in e["_cands"]:
            k = key
            if k.lower() in taken:
                collisions += 1
                sep = "-" if kt in ("colloquial", "question") else "."
                for suffix in refine:
                    if not suffix:
                        continue
                    trial = f"{k}{sep}{slug(suffix)}"
                    if trial.lower() not in taken:
                        k = trial
                        break
                else:
                    if kt != "canonical":
                        continue          # alias yields to the primary owner
                    n = 2
                    while f"{k}.v{n}".lower() in taken:
                        n += 1
                    k = f"{k}.v{n}"
            taken[k.lower()] = idx
            result[idx].append((kt, k, w))
            if kt == "canonical":
                got_canonical = True
        # R2 applies to INTENTS. An entry carries only language-specific
        # spellings; its canonical name lives on the intent it binds to, so a
        # missing canonical here is correct, not a defect to paper over.
        if not got_canonical and e.get("_needs_canonical", True):
            fallback = slug(str(e.get("qualified_name") or idx))
            n = 1
            while f"{fallback}-{n}" in taken:
                n += 1
            fallback = f"{fallback}-{n}"
            taken[fallback] = idx
            result[idx].insert(0, ("canonical", fallback, 10.0))
    result["_collisions"] = collisions
    return result


def prepare(recs: list[dict]) -> list[dict]:
    """Annotate records with params/keys ready for DB insert."""
    # group overloads
    by_q = defaultdict(list)
    for r in recs:
        by_q[r["qualified_name"]].append(r)

    out = []
    for i, r in enumerate(recs):
        ap = annotate_params(r)
        r["_params"] = ap
        r["_idx"] = i
        r["_primacy"] = primacy_rank(r, ap)
        r["_disamb"] = disambiguator(ap)
        r["_shape"] = "-".join(p["role"] or "input" for p in ap) or None
        siblings = by_q[r["qualified_name"]]
        r["overload_count"] = len(siblings)
        out.append(r)

    for q, sibs in by_q.items():
        for n, s in enumerate(sorted(sibs, key=lambda x: x["_primacy"])):
            s["overload_index"] = n

    for r in out:
        r["_cands"] = candidate_keys(r, r["_params"])
    return out
