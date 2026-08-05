#!/usr/bin/env python3
"""
explain.py -- syntax -> semantics. The inverse direction of query.py.

query.py serves the developer who knows what they want and not how to spell it.
This serves the developer holding code they did not write: it renders real C++
back into the intent layer, so the reader can see what each statement MEANS
without already knowing the syntax.

The lexicon is meant to work both ways, so the round-trip is the test:

    syntax  --explain-->  intent  --emit-->  syntax

`--roundtrip` runs exactly that and reports how many statements survive it.

  explain --file main.cpp                 # per-call detail
  explain --semantic --file main.cpp      # the program, as intent
  explain --roundtrip --file main.cpp     # does it come back?
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codegen

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "out" / "base.db"

# --- lightweight local type knowledge ---------------------------------------
# Not a parser. Just enough to know that `v` is a vector, because resolving
# v.push_back() to std::basic_string::push_back is worse than useless -- it
# teaches the reader something false.
DECL_RE = re.compile(r"""
    \b(?P<type>(?:std\s*::\s*)?[A-Za-z_]\w*)      # std::vector / string
    \s*(?:<(?P<targs>[^;{}()]*?)>)?               # <int>
    \s+(?P<var>[A-Za-z_]\w*)\s*(?=[;={(\[])       # v
""", re.X)

CALL_RE = re.compile(r"""
    (?:(?P<qual>[A-Za-z_]\w*(?:\s*::\s*[A-Za-z_]\w*)+)   # std::filesystem::exists
     | (?P<recv>[A-Za-z_]\w*)\s*(?:\.|->)\s*(?P<meth>[A-Za-z_]\w*)   # v.push_back
     | (?P<bare>[A-Za-z_]\w*))                           # malloc
    \s*\(
""", re.X)

KEYWORD_RE = re.compile(
    r"\b(constexpr|consteval|constinit|noexcept|decltype|static_assert|"
    r"thread_local|dynamic_cast|static_cast|reinterpret_cast|const_cast|"
    r"co_await|co_return|co_yield|requires|concept|typename|"
    r"override|final|explicit|mutable|volatile|alignas|alignof)\b")

SKIP = {"if", "for", "while", "switch", "return", "sizeof", "catch", "and",
        "or", "not", "main", "int", "void", "auto", "const", "static",
        "else", "do", "try", "new", "delete", "throw"}

# std::string is std::basic_string, and so on -- the reader's spelling is not
# the library's spelling.
TYPEDEF_CLASS = {
    "string": "basic_string", "wstring": "basic_string",
    "string_view": "basic_string_view", "ostream": "basic_ostream",
    "istream": "basic_istream", "ifstream": "basic_ifstream",
    "ofstream": "basic_ofstream", "fstream": "basic_fstream",
    "stringstream": "basic_stringstream", "regex": "basic_regex",
    "ostringstream": "basic_ostringstream",
    "istringstream": "basic_istringstream",
}


def open_db(locale: str = "en"):
    con = sqlite3.connect(ROOT / "out" / f"pack_{locale}.db")
    con.row_factory = sqlite3.Row
    con.execute("ATTACH DATABASE ? AS base", (str(BASE),))
    return con


def scan_decls(text: str) -> dict[str, str]:
    """var -> class name, from obvious declarations. Best effort by design."""
    env = {}
    for m in DECL_RE.finditer(text):
        ty = re.sub(r"\s|std::", "", m.group("type"))
        var = m.group("var")
        if ty in SKIP or var in SKIP:
            continue
        env[var] = TYPEDEF_CLASS.get(ty, ty)
    return env


# --------------------------------------------------------------- resolution --

def _pick(con, rows, nargs: int):
    """Choose the overload the call actually made.

    Specificity is the whole point of the reverse direction: sort(a,b,cmp) must
    report 'sort with a custom comparator', not bare 'sort'. Iterator pairs
    count as one logical argument, so a 3-arg call matches a 3-param entry.
    """
    if not rows:
        return None
    best, best_score = None, None
    for r in rows:
        n = con.execute("SELECT count(*) FROM param WHERE entry_id=?",
                        (r["id"],)).fetchone()[0]
        score = (abs(n - nargs), r["overload_index"])
        if best_score is None or score < best_score:
            best, best_score = r, score
    return best


def lookup_member(con, cls: str, meth: str, nargs: int = -1):
    rows = con.execute("""
        SELECT * FROM base.entry WHERE name = ? AND (parent = ? OR parent = ?)
        ORDER BY overload_index""", (meth, f"std::{cls}", cls)).fetchall()
    if not rows:
        rows = con.execute("""
            SELECT * FROM base.entry WHERE name = ? AND qualified_name LIKE ?
            ORDER BY overload_index""", (meth, f"%{cls}::{meth}")).fetchall()
    return _pick(con, rows, nargs)


def lookup_symbol(con, name: str, nargs: int = -1):
    for cand in ([name] if "::" in name else [f"std::{name}", name]):
        rows = con.execute("""
            SELECT e.* FROM semantic_key k JOIN base.entry e ON e.id = k.entry_id
            WHERE k.key = ? COLLATE NOCASE AND k.key_type = 'symbolic'""",
                           (cand,)).fetchall()
        if rows:
            qn = rows[0]["qualified_name"]
            allrows = con.execute(
                "SELECT * FROM base.entry WHERE qualified_name=? ORDER BY overload_index",
                (qn,)).fetchall()
            return _pick(con, allrows, nargs)
    rows = con.execute("""
        SELECT * FROM base.entry WHERE name = ? COLLATE NOCASE
          AND kind IN ('member_function','function','function_template')
        ORDER BY overload_index""", (name,)).fetchall()
    return _pick(con, rows, nargs)


def split_args(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "(<[":
            depth += 1
        elif ch in ")>]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def balanced_args(text: str, open_idx: int) -> tuple[str, int]:
    """Return the argument text inside the parens starting at open_idx."""
    depth, i = 0, open_idx
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i + 1
        i += 1
    return "", len(text)


def summary_of(con, eid):
    """Prose lives in the pack, not in the shared syntax base."""
    r = con.execute("SELECT summary FROM entry_text WHERE entry_id=?",
                    (eid,)).fetchone()
    return r[0] if r else None


# Not every hazard is spelled as a call. counts["k"] is a subscript, std::endl
# is a bare symbol, and both are advised against -- a review that only sees
# parentheses misses the cases people actually write.
SUBSCRIPT_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\[")
BARE_SYMBOL_RE = re.compile(r"\bstd\s*::\s*(endl|ends)\b")


def scan_nonvcall(con, text: str, env: dict, seen_lines: set):
    """Advised constructs that are not function calls."""
    out = []
    for m in SUBSCRIPT_RE.finditer(text):
        var = m.group(1)
        cls = env.get(var)
        if not cls:
            continue
        e = con.execute("""SELECT * FROM base.entry
                WHERE name='operator[]' AND (parent=? OR parent=?)
                ORDER BY overload_index LIMIT 1""",
                        (f"std::{cls}", cls)).fetchone()
        if e is None:
            continue
        out.append({"entry": e, "intent": None, "_alias": None,
                    "_summary": summary_of(con, e["id"]),
                    "call": text[m.start():m.end()] + "...]",
                    "args": [], "bindings": {"object": var}, "notes": [],
                    "receiver": var,
                    "line": text[:m.start()].count("\n") + 1})
    for m in BARE_SYMBOL_RE.finditer(text):
        e = con.execute("SELECT * FROM base.entry WHERE qualified_name=? LIMIT 1",
                        (f"std::{m.group(1)}",)).fetchone()
        if e is None:
            continue
        out.append({"entry": e, "intent": None, "_alias": None,
                    "_summary": summary_of(con, e["id"]),
                    "call": m.group(0), "args": [], "bindings": {},
                    "notes": [], "receiver": None,
                    "line": text[:m.start()].count("\n") + 1})
    return out


ITER_PAIR = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\.|->)\s*c?begin\s*\(\s*\)\s*$")
ITER_END = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\.|->)\s*c?end\s*\(\s*\)\s*$")


def bind_arguments(entry, con, args: list[str], receiver: str | None):
    """Map textual arguments onto the entry's ports.

    `v.begin(), v.end()` is ONE sequence argument, not two calls -- collapsing
    it is what makes the semantic rendering read like intent instead of like
    iterator plumbing.
    """
    params = con.execute(
        "SELECT ordinal,name,type,role,semantic,optional FROM base.param "
        "WHERE entry_id=? ORDER BY ordinal", (entry["id"],)).fetchall()
    bindings, notes = {}, []
    if receiver:
        bindings["object"] = receiver

    ai = 0
    pair_consumed = False
    for p in params:
        if ai >= len(args):
            break
        sem = p["semantic"] or ""
        if sem == "range.first":
            m = ITER_PAIR.match(args[ai])
            nxt = ITER_END.match(args[ai + 1]) if ai + 1 < len(args) else None
            if m and nxt and m.group(1) == nxt.group(1):
                # begin()/end() collapse to ONE logical argument; both textual
                # arguments are consumed here, so the matching range.last
                # parameter must not advance the index a second time.
                bindings["sequence"] = m.group(1)
                ai += 2
                pair_consumed = True
                continue
            bindings["sequence"] = args[ai].split(".")[0]
            ai += 1
            continue
        if sem == "range.last":
            if not pair_consumed:
                ai += 1
            pair_consumed = False
            continue
        slot = codegen.slot_name(dict(p))
        bindings[slot] = args[ai]
        notes.append((slot, args[ai], (p["semantic"] or p["role"] or "value")))
        ai += 1
    return bindings, notes


def analyse(con, text: str, limit=60, locale="en"):
    env = scan_decls(text)
    seen_kw, results = set(), []
    pos = 0
    while True:
        m = CALL_RE.search(text, pos)
        if m is None:
            break
        open_idx = text.index("(", m.end() - 1)
        argtext, after = balanced_args(text, open_idx)
        pos = m.end()

        name = m.group("qual") or m.group("meth") or m.group("bare")
        recv = m.group("recv")
        if not name or name in SKIP:
            continue
        # begin/end are absorbed into the enclosing call's sequence argument
        if name in ("begin", "end", "cbegin", "cend", "rbegin", "rend") and recv:
            continue
        name = re.sub(r"\s+", "", name)

        args = split_args(argtext)
        nargs = len(args)
        entry = None
        if recv and recv in env:
            entry = lookup_member(con, env[recv], name, nargs)
        if entry is None:
            entry = lookup_symbol(con, name, nargs)
        if entry is None:
            continue
        bindings, notes = bind_arguments(entry, con, args, recv)
        intent = con.execute(
            "SELECT c.concept_key FROM binding b JOIN concept c "
            "ON c.id=b.concept_id WHERE b.entry_id=?", (entry["id"],)).fetchone()
        ikey = intent["concept_key"] if intent else None
        results.append({
            "entry": entry, "intent": ikey, "_alias": best_alias(con, ikey, locale),
            "call": text[m.start():after].strip(),
            "args": args, "bindings": bindings, "notes": notes,
            "receiver": recv, "line": text[:m.start()].count("\n") + 1,
        })
        if len(results) >= limit:
            break

    for m in KEYWORD_RE.finditer(text):
        kw = m.group(1)
        if kw in seen_kw:
            continue
        r = con.execute(
            "SELECT * FROM base.entry WHERE name=? AND kind IN "
            "('keyword','attribute','preprocessor','punctuator') LIMIT 1",
            (kw,)).fetchone()
        if r:
            seen_kw.add(kw)
            results.append({"entry": r, "intent": None, "call": kw, "args": [],
                            "bindings": {}, "notes": [], "receiver": None,
                            "line": text[:m.start()].count("\n") + 1})
    results += scan_nonvcall(con, text, env, set())
    results.sort(key=lambda d: d["line"])
    return results


# ---------------------------------------------------------------- rendering --

C = {"dim": "\033[2m", "b": "\033[1m", "g": "\033[32m", "y": "\033[33m",
     "c": "\033[36m", "r": "\033[0m", "m": "\033[35m"}


def best_alias(con, intent_key: str | None, locale: str = "en") -> str | None:
    """The highest-ranked CLEAR phrasing for an intent.

    Input may be loose; output must not be. Among the dozens of aliases an
    intent carries, this returns the one meant to be read -- the highest
    weighted colloquial form, which is the phrasing chosen as primary when the
    keys were generated.
    """
    if not intent_key:
        return None
    r = con.execute("SELECT canonical_term FROM concept WHERE concept_key = ?",
                    (intent_key,)).fetchone()
    return r[0] if r else None


EN_CONNECTIVES = {"on": "on", "with": "with", "using": "using",
                  "where": "where", "count": "count", "bytes": "bytes",
                  "for": "for"}


def connectives(con, locale: str = "en") -> dict:
    """Grammar fragments for this locale, falling back to English."""
    out = dict(EN_CONNECTIVES)
    for k, v in con.execute("SELECT key, value FROM connective"):
        out[k] = v
    return out


def phrase(d, cx=EN_CONNECTIVES) -> str:
    """The statement said in English, with the real variable names in it."""
    e, b = d["entry"], d["bindings"]
    s = d.get("_alias") or (d.get("_summary") or e["qualified_name"])
    s = re.sub(r"\s*Returns .*$", "", s).rstrip(".")
    subject = b.get("sequence") or b.get("object")
    if subject:
        # Put the caller's variable INTO the sentence rather than trailing it,
        # so the line reads as a statement about this code.
        s2 = re.sub(r"\b(?:a|the) (?:range|vector|string|sequence|container|"
                    r"collection|mapping|block of[a-z ]*memory)\b",
                    f"`{subject}`", s, count=1)
        if s2 == s:
            s2 = re.sub(r"\bthe (elements|number of elements|contents)\b",
                        lambda m: f"the {m.group(1)} of `{subject}`", s, count=1)
        s = s2 if s2 != s else f"{s} {cx['on']} `{subject}`"
    # Read the arguments into the sentence, so the result is a statement about
    # THIS code rather than a generic description with values bolted on.
    already = {b.get("object"), b.get("sequence")}
    for slot, val, sem in d["notes"]:
        if slot == "object" or val in already:
            continue
        sem = (sem or "").split(".")[-1]
        if sem in ("count", "size"):
            s += (f" {cx['for']} {val} {cx['bytes']}"
                  if ("memory" in s or "paměti" in s or "pamet" in s)
                  else f", {cx['count']}: {val}")
        elif sem in ("compare",):
            s += f" {cx['using']} `{val}`"
        elif sem in ("predicate",):
            s += f" {cx['where']} `{val}`"
        elif sem in ("value", "text", "key"):
            s += f" {cx['with']} `{val}`"
        else:
            s += f" ({val})"
    return s


def render_detail(items, color=True):
    c = C if color and sys.stdout.isatty() else {k: "" for k in C}
    out = []
    for d in items:
        e = d["entry"]
        std = f" {c['dim']}[{e['std_since']}]{c['r']}" if e["std_since"] else ""
        out.append(f"{c['dim']}line {d['line']}{c['r']}  "
                   f"{c['b']}{e['qualified_name']}{c['r']}"
                   f"  {c['c']}{e['header'] or ''}{c['r']}{std}")
        if d.get("_summary"):
            out.append(f"   {d['_summary']}")
        if d["intent"]:
            out.append(f"   {c['m']}intent{c['r']} {d['intent']}")
        for slot, val, sem in d["notes"]:
            out.append(f"     {c['y']}{val}{c['r']}"
                       f"   {c['dim']}-- {sem.replace('.', ' ')}{c['r']}")
        out.append("")
    return "\n".join(out)


def render_semantic(items, color=True, cx=EN_CONNECTIVES):
    c = C if color and sys.stdout.isatty() else {k: "" for k in C}
    out = []
    for d in items:
        key = d["intent"] or d["entry"]["qualified_name"]
        out.append(f"{c['dim']}{d['line']:>4}{c['r']}  "
                   f"{c['m']}{key:<38}{c['r']} {phrase(d, cx)}")
    return "\n".join(out)


SEVERITY_MARK = {"unsafe": "UNSAFE", "obsolete": "OBSOLETE", "prefer": "prefer"}


def advisories(con, items, dialect="cpp"):
    """Design review, driven by the lexicon rather than a separate rule engine.

    Every finding is an edge someone declared in advice/cpp.yaml, so the review
    can never drift from what the documentation says -- one row produces both.
    """
    out = []
    for d in items:
        rows = con.execute("""
            SELECT a.prefer_name, a.severity, t.headline, t.rationale
            FROM advice a LEFT JOIN advice_text t ON t.advice_key = a.advice_key
            WHERE a.entry_id = ? AND a.applies_to = ?""",
            (d["entry"]["id"], dialect)).fetchall()
        for r in rows:
            out.append({"line": d["line"], "call": d["call"],
                        "used": d["entry"]["qualified_name"],
                        "prefer": r["prefer_name"], "severity": r["severity"],
                        "headline": r["headline"], "rationale": r["rationale"]})
    order = {"unsafe": 0, "obsolete": 1, "prefer": 2}
    out.sort(key=lambda a: (order.get(a["severity"], 3), a["line"]))
    return out


def render_review(advs, color=True):
    import textwrap
    c = C if color and sys.stdout.isatty() else {k: "" for k in C}
    if not advs:
        return "no advisories"
    lines = []
    for a in advs:
        mark = SEVERITY_MARK.get(a["severity"], a["severity"]).upper()
        col = c["y"] if a["severity"] == "prefer" else c["m"]
        lines.append(f"{col}{mark:>8}{c['r']}  line {a['line']}: "
                     f"{c['b']}{a['used']}{c['r']}  ->  {a['prefer']}")
        if a["headline"]:
            lines.append(f"          {a['headline']}")
        if a["rationale"]:
            for w in textwrap.wrap(" ".join(a["rationale"].split()), 72):
                lines.append(f"          {c['dim']}{w}{c['r']}")
        lines.append("")
    n_unsafe = sum(1 for a in advs if a["severity"] == "unsafe")
    lines.append(f"{len(advs)} advisories ({n_unsafe} unsafe)")
    return "\n".join(lines)


def norm(s: str) -> str:
    return re.sub(r"[\s;]+", "", s or "")


def roundtrip(items):
    """syntax -> intent -> syntax. Reports what survives."""
    rows, ok = [], 0
    for d in items:
        e = d["entry"]
        tmpl = e["emit_template"]
        if not tmpl:
            rows.append((d["call"], None, False))
            continue
        back = codegen.render(tmpl, d["bindings"])
        # the sequence slot expands to begin()/end() again
        match = norm(back) == norm(d["call"] + ";") or norm(back) == norm(d["call"])
        ok += bool(match)
        rows.append((d["call"], back, match))
    return rows, ok


def main():
    ap = argparse.ArgumentParser(
        description="render C++ back into the intent layer")
    ap.add_argument("code", nargs="*")
    ap.add_argument("--file", "-f")
    ap.add_argument("--semantic", action="store_true",
                    help="render the program as intent, one line per statement")
    ap.add_argument("--dialect", default="cpp",
                    help="which language's advice applies (cpp, c, ...)")
    ap.add_argument("--review", action="store_true",
                    help="flag calls that have a safer alternative")
    ap.add_argument("--roundtrip", action="store_true",
                    help="syntax -> intent -> syntax, and report what survives")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--locale", default="en",
                    help="render semantics in this human language")

    a = ap.parse_args()

    text = Path(a.file).read_text() if a.file else " ".join(a.code)
    if not text.strip():
        text = sys.stdin.read()

    con = open_db(a.locale)
    items = analyse(con, text, locale=a.locale)

    if a.json:
        print(json.dumps([{
            "line": d["line"], "call": d["call"],
            "qualified_name": d["entry"]["qualified_name"],
            "header": d["entry"]["header"], "intent": d["intent"],
            "summary": d["entry"]["summary"], "bindings": d["bindings"],
            "semantic": phrase(d),
        } for d in items], indent=2))
    elif a.review:
        print(render_review(advisories(con, items, a.dialect)))
    elif a.roundtrip:
        rows, ok = roundtrip(items)
        for orig, back, good in rows:
            mark = "ok  " if good else "DIFF"
            print(f"{mark}  {orig}")
            if not good:
                print(f"        -> {back}")
        print(f"\n{ok}/{len(rows)} statements round-tripped")
        return 0 if ok == len(rows) else 1
    elif a.semantic:
        print(render_semantic(items, cx=connectives(con, a.locale)))
    else:
        print(render_detail(items) or "nothing recognised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
