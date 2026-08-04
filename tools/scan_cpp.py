#!/usr/bin/env python3
"""
scan_cpp.py -- mechanical extraction of the C++ standard-library surface.

Two passes:
  A) parse every public standard header ON ITS OWN at -std=c++23, so each decl
     can be attributed to the public header(s) that actually provide it.
  B) parse one combined TU at each -std level (98/11/14/17/20/23) and diff the
     USR sets, so `std_since` is DERIVED from the compiler rather than guessed.

Output: data/raw_decls.jsonl   (one JSON object per unique USR)
        data/header_sets.json  (public header -> [usr, ...])
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import clang.cindex as ci

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

for cand in (
    "/usr/lib/x86_64-linux-gnu/libclang-18.so.1",
    "/usr/lib/llvm-18/lib/libclang.so.1",
):
    if os.path.exists(cand):
        ci.Config.set_library_file(cand)
        break

STD_LEVELS = ["c++98", "c++11", "c++14", "c++17", "c++20", "c++23"]

# Public standard headers, per [headers] in the standard. Deliberately explicit
# rather than globbing /usr/include/c++/13 so we never index libstdc++ internals
# as if they were standard API.
CXX_HEADERS = """
algorithm any array atomic barrier bit bitset charconv chrono codecvt compare
complex concepts condition_variable coroutine deque exception execution
expected filesystem flat_map flat_set format forward_list fstream functional
future generator initializer_list iomanip ios iosfwd iostream istream iterator
latch limits list locale map mdspan memory memory_resource new numbers numeric
optional ostream print queue random ranges ratio regex scoped_allocator
semaphore set shared_mutex source_location span spanstream sstream stack
stacktrace stdexcept stdfloat stop_token streambuf string string_view
syncstream system_error thread tuple type_traits typeindex typeinfo unordered_map
unordered_set utility valarray variant vector version
""".split()

C_COMPAT_HEADERS = """
cassert cctype cerrno cfenv cfloat cinttypes climits clocale cmath csetjmp
csignal cstdarg cstddef cstdint cstdio cstdlib cstring ctime cuchar cwchar
cwctype
""".split()

ALL_HEADERS = CXX_HEADERS + C_COMPAT_HEADERS

# Cursor kinds we care about.
KIND_MAP = {
    ci.CursorKind.FUNCTION_DECL: "function",
    ci.CursorKind.FUNCTION_TEMPLATE: "function_template",
    ci.CursorKind.CXX_METHOD: "member_function",
    ci.CursorKind.CONSTRUCTOR: "constructor",
    ci.CursorKind.DESTRUCTOR: "destructor",
    ci.CursorKind.CONVERSION_FUNCTION: "conversion",
    ci.CursorKind.CLASS_DECL: "class",
    ci.CursorKind.STRUCT_DECL: "struct",
    ci.CursorKind.UNION_DECL: "union",
    ci.CursorKind.CLASS_TEMPLATE: "class_template",
    ci.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION: "class_template",
    ci.CursorKind.ENUM_DECL: "enum",
    ci.CursorKind.TYPEDEF_DECL: "alias",
    ci.CursorKind.TYPE_ALIAS_DECL: "alias",
    ci.CursorKind.TYPE_ALIAS_TEMPLATE_DECL: "alias",
    ci.CursorKind.CONCEPT_DECL: "concept",
    ci.CursorKind.VAR_DECL: "variable",
}
RECURSE_KINDS = {
    ci.CursorKind.NAMESPACE,
    ci.CursorKind.CLASS_DECL,
    ci.CursorKind.STRUCT_DECL,
    ci.CursorKind.CLASS_TEMPLATE,
    ci.CursorKind.TRANSLATION_UNIT,
    ci.CursorKind.UNEXPOSED_DECL,      # extern "C++" { ... }
    ci.CursorKind.LINKAGE_SPEC,
}

RESERVED = re.compile(r"^_")

# Macros worth indexing: public spellings only. Implementation macros are
# reserved (leading underscore) or vendor-prefixed and are not lexicon.
MACRO_SKIP = re.compile(r"^(_|__|_GLIBCXX|_GLIBCPP|GCC_)")


def emit_macro(cur, out: dict):
    name = cur.spelling
    if not name or MACRO_SKIP.match(name):
        return
    if cur.location.file is None:
        return                      # builtin, not from a header
    path = str(cur.location.file)
    if "/include/" not in path and "/usr/" not in path:
        return
    usr = f"macro:{name}"
    if usr in out:
        return
    toks = [t.spelling for t in cur.get_tokens()]
    body = " ".join(toks[1:])[:200] if len(toks) > 1 else None
    out[usr] = {
        "usr": usr, "kind": "macro", "name": name, "qualified_name": name,
        "namespace": None, "display": name, "file": path,
        "template_params": [], "params": [], "return_type": None,
        "is_template": False, "is_static": False, "is_const": False,
        # this binding has no is_macro_functionlike(); a function-like macro
        # is one whose '(' immediately follows the name with no space
        "is_variadic": bool(len(toks) > 1 and toks[1] == "("),
        "is_deprecated": False, "brief": None,
        "signature": f"#define {name}" + (f" {body}" if body else ""),
        "constexpr_since": None, "is_constexpr": False, "is_consteval": False,
        "is_noexcept": False, "is_explicit": False, "is_nodiscard": False,
        "_line": cur.extent.start.line, "_quality": 3,
    }


def is_reserved(name: str) -> bool:
    """Leading-underscore names are implementation reserved, not public API."""
    return bool(name) and RESERVED.match(name) is not None


def is_transparent_namespace(name: str) -> bool:
    """ABI-versioning inline namespaces the user never writes.

    libstdc++ uses __cxx11, libc++ uses __1. walk() must DESCEND into these or
    the entire library is invisible -- it is not enough for clean_namespace to
    strip them from the qualified name afterwards.
    """
    return name == "__cxx11" or re.fullmatch(r"__\d+", name) is not None


def clean_namespace(parts: list[str]) -> list[str] | None:
    """Drop inline implementation namespaces (std::__cxx11); reject detail ones."""
    out = []
    for p in parts:
        if is_reserved(p):
            # Both implementations wrap everything in an inline namespace for
            # ABI versioning -- libstdc++ uses __cxx11, libc++ uses __1. They
            # are transparent to users and must not be treated as internal, or
            # the entire library disappears.
            if p == "__cxx11" or re.fullmatch(r"__\d+", p):
                continue
            return None               # genuinely internal
        out.append(p)
    return out


def qualified_parts(cur) -> list[str] | None:
    parts = []
    c = cur
    while c is not None and c.kind != ci.CursorKind.TRANSLATION_UNIT:
        sp = c.spelling
        if c.kind == ci.CursorKind.NAMESPACE and not sp:
            c = c.semantic_parent
            continue                   # anonymous namespace -> internal
        # extern "C" { ... } is a LINKAGE SPEC, not a scope. It has an empty
        # spelling, and treating it as a namespace segment made every C library
        # function look like it lived outside std -- which dropped the entire C
        # standard library (malloc, printf, strlen, ...) on the floor.
        if not sp and c.kind in (ci.CursorKind.LINKAGE_SPEC,
                                 ci.CursorKind.UNEXPOSED_DECL):
            c = c.semantic_parent
            continue
        parts.append(sp)
        c = c.semantic_parent
    parts.reverse()
    return parts


def template_param_list(cur) -> list[str]:
    out = []
    for ch in cur.get_children():
        if ch.kind in (
            ci.CursorKind.TEMPLATE_TYPE_PARAMETER,
            ci.CursorKind.TEMPLATE_NON_TYPE_PARAMETER,
            ci.CursorKind.TEMPLATE_TEMPLATE_PARAMETER,
        ):
            toks = " ".join(t.spelling for t in ch.get_tokens())
            out.append(toks or ch.spelling)
    return out


# libstdc++ spells its template parameters with reserved names. Users read the
# standard's names, so translate the common ones and strip leading underscores
# from everything else -- __first -> first, _Compare -> Compare.
UGLY_MAP = {
    "_RAIter": "RandomIt", "_RandomAccessIterator": "RandomIt",
    "_FIter": "ForwardIt", "_ForwardIterator": "ForwardIt",
    "_IIter": "InputIt", "_InputIterator": "InputIt",
    "_OIter": "OutputIt", "_OutputIterator": "OutputIt",
    "_BIter": "BidirIt", "_BidirectionalIterator": "BidirIt",
    "_Tp": "T", "_Up": "U", "_Vp": "V", "_Val": "T", "_Key": "Key",
    "_Alloc": "Allocator", "_CharT": "CharT", "_Traits": "Traits",
    "_Compare": "Compare", "_Predicate": "Pred", "_Pred": "Pred",
    "_UnaryOperation": "UnaryOp", "_BinaryOperation": "BinaryOp",
    "_UnaryFunction": "UnaryFunc", "_Funct": "Func", "_Fn": "F",
    "_Size": "Size", "_Distance": "Distance", "_Args": "Args",
    "_Generator": "Generator", "_Hash": "Hash", "_Res": "R",
}
_IDENT = re.compile(r"\b_+[A-Za-z]\w*\b")
_GLIBCXX_MACRO = re.compile(r"\b_GLIBCXX\w*\b")


def deuglify(s: str | None) -> str | None:
    if not s:
        return s
    s = _GLIBCXX_MACRO.sub("", s)
    s = _IDENT.sub(lambda m: UGLY_MAP.get(m.group(0), m.group(0).lstrip("_")), s)
    return re.sub(r"\s+", " ", s).strip()


def param_list(cur) -> list[dict]:
    """FUNCTION_TEMPLATE cursors expose no get_arguments(); walk PARM_DECLs."""
    args = list(cur.get_arguments() or [])
    if not args:
        args = [c for c in cur.get_children()
                if c.kind == ci.CursorKind.PARM_DECL]
    out = []
    for i, a in enumerate(args):
        toks = [t.spelling for t in a.get_tokens()]
        default = None
        if "=" in toks:
            default = deuglify(" ".join(toks[toks.index("=") + 1:]))
        out.append({
            "ordinal": i,
            "name": deuglify(a.spelling) or None,
            "type": deuglify(a.type.spelling),
            "raw_type": a.type.spelling,
            "canonical_type": a.type.get_canonical().spelling,
            "default_value": default,
            "is_pack": "..." in a.type.spelling,
        })
    return out


def decl_record(cur, kind: str, qname: list[str]) -> dict:
    is_fn = kind in (
        "function", "function_template", "member_function",
        "constructor", "destructor", "conversion",
    )
    rec = {
        "usr": cur.get_usr(),
        "kind": kind,
        "name": cur.spelling,
        "qualified_name": "::".join(qname),
        "namespace": "::".join(qname[:-1]) or None,
        "display": cur.displayname,
        "file": str(cur.location.file) if cur.location.file else None,
        "template_params": [deuglify(t) for t in template_param_list(cur)],
        "params": param_list(cur) if is_fn else [],
        "return_type": deuglify(cur.result_type.spelling) if is_fn else None,
        "is_template": kind.endswith("_template") or bool(template_param_list(cur)),
        "is_static": bool(cur.is_static_method()) if kind == "member_function" else False,
        "is_const": bool(cur.is_const_method()) if kind == "member_function" else False,
        "is_variadic": bool(cur.type.is_function_variadic())
                       if is_fn and cur.type.kind == ci.TypeKind.FUNCTIONPROTO else False,
        "is_deprecated": any(
            c.kind == ci.CursorKind.UNEXPOSED_ATTR and "deprecated" in
            " ".join(t.spelling for t in c.get_tokens())
            for c in cur.get_children()
        ),
        "brief": cur.brief_comment,
    }
    toks = None
    if is_fn:
        try:
            toks = " ".join(t.spelling for t in cur.get_tokens())
        except Exception:
            toks = None
    rec["signature"] = normalize_sig(toks) if toks else deuglify(cur.displayname)
    # _GLIBCXX20_CONSTEXPR means "constexpr since C++20" -- capture the level.
    m = re.search(r"_GLIBCXX(\d\d)?_CONSTEXPR", toks or "")
    rec["constexpr_since"] = ("C++" + m.group(1)) if (m and m.group(1)) else \
                             ("C++11" if m else None)
    rec["is_constexpr"] = bool(m) or bool(toks and re.search(r"\bconstexpr\b", toks))
    rec["is_consteval"] = bool(toks and re.search(r"\bconsteval\b", toks))
    rec["is_noexcept"] = bool(toks and re.search(r"\bnoexcept\b", toks))
    rec["is_explicit"] = bool(toks and re.search(r"\bexplicit\b", toks))
    rec["is_nodiscard"] = bool(toks and re.search(r"nodiscard|_GLIBCXX_NODISCARD", toks))
    rec["_line"] = cur.extent.start.line
    return rec


def normalize_sig(toks: str) -> str:
    s = deuglify(re.sub(r"\s+", " ", toks))
    s = s.split("{")[0].strip()
    s = re.sub(r"\s*([(,])\s*", r"\1", s)
    s = re.sub(r"\s*\)\s*", ") ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(";")
    return s[:900]


def walk(cur, out: dict, depth=0):
    for ch in cur.get_children():
        k = ch.kind
        if k in RECURSE_KINDS or k == ci.CursorKind.CLASS_TEMPLATE:
            if (k == ci.CursorKind.NAMESPACE and is_reserved(ch.spelling)
                    and not is_transparent_namespace(ch.spelling)):
                continue
            if k in (ci.CursorKind.CLASS_DECL, ci.CursorKind.STRUCT_DECL,
                     ci.CursorKind.CLASS_TEMPLATE):
                if is_reserved(ch.spelling) or not ch.spelling:
                    continue
                emit(ch, out)
            walk(ch, out, depth + 1)
            continue
        if k == ci.CursorKind.MACRO_DEFINITION:
            emit_macro(ch, out)
            continue
        if k in KIND_MAP:
            emit(ch, out)


def emit(cur, out: dict):
    kind = KIND_MAP.get(cur.kind)
    if not kind:
        return
    name = cur.spelling
    if not name or (is_reserved(name) and not name.startswith("operator")):
        return
    # clang names anonymous entities after their source location, e.g.
    # "(anonymous union at .../stl_iterator.h:2253:5)". Those are not API.
    if "(" in name or "anonymous" in name or "unnamed" in name:
        return
    parts = qualified_parts(cur)
    if parts is None or not parts:
        return
    cleaned = clean_namespace(parts[:-1])
    if cleaned is None:
        return
    qname = cleaned + [parts[-1]]
    # Only index std::*, std::ranges::*, ... and the C-compat global functions.
    if qname[0] != "std" and len(qname) > 1:
        return
    usr = cur.get_usr()
    if not usr:
        return
    prev = out.get(usr)
    if prev is not None and prev.get("_quality", 0) >= 3:
        return                      # already have a fully-named declaration
    rec = decl_record(cur, kind, qname)
    # A symbol is often forward-declared without parameter names before the
    # real declaration. Keep whichever spelling carries the most information.
    rec["_quality"] = (
        sum(1 for p in rec["params"] if p.get("name"))
        + (1 if rec.get("brief") else 0)
        + (1 if rec["params"] and all(p.get("name") for p in rec["params"]) else 0)
    )
    if prev is None or rec["_quality"] > prev.get("_quality", -1):
        out[usr] = rec


# No single standard-library implementation ships all of C++23. libstdc++ 14
# has <print> and <generator>; libc++ 18 has <mdspan> and not those. A complete
# lexicon therefore has to merge implementations, and record which one provided
# each declaration.
STDLIB_ARGS = {
    # -fsized-deallocation is required for libstdc++ to expose <generator>,
    # which gates on __cpp_sized_deallocation.
    "libstdc++": ["-fsized-deallocation"],
    "libc++": ["-nostdinc++", "-isystem", "/usr/lib/llvm-18/include/c++/v1",
               "-fsized-deallocation"],
}
STDLIB = "libstdc++"


def parse_tu(index, src: str, std: str, extra=()):
    args = [
        "-x", "c++", f"-std={std}", "-fsyntax-only",
        *STDLIB_ARGS.get(STDLIB, []),
        "-D_GLIBCXX_USE_DEPRECATED=1",
        # libstdc++ 13 gates <expected> on __cpp_concepts >= 202002L, which
        # clang 18 under-reports as 201907L although it implements the
        # feature. Without this the whole header silently vanishes.
        "-D__cpp_concepts=202002L",
        "-Wno-builtin-macro-redefined",
        "-Wno-everything",
        *extra,
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        return index.parse(
            path, args=args,
            options=ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
            | ci.TranslationUnit.PARSE_INCOMPLETE
            | ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )
    finally:
        os.unlink(path)


def combined_src(headers) -> str:
    lines = []
    for h in headers:
        lines.append(f"#if __has_include(<{h}>)")
        lines.append(f"#include <{h}>")
        lines.append("#endif")
    return "\n".join(lines) + "\n"


def main(stdlib="libstdc++", out_name="raw_decls.jsonl"):
    global STDLIB
    STDLIB = stdlib
    print(f"stdlib: {stdlib}", flush=True)
    index = ci.Index.create()

    # ---- Pass A: per-header attribution -------------------------------------
    print("pass A: per-header attribution (-std=c++23)", flush=True)
    all_decls: dict[str, dict] = {}
    header_sets: dict[str, list[str]] = {}
    for i, h in enumerate(ALL_HEADERS, 1):
        tu = parse_tu(index, combined_src([h]), "c++23")
        found: dict[str, dict] = {}
        walk(tu.cursor, found)
        header_sets[f"<{h}>"] = sorted(found)
        for usr, rec in found.items():
            all_decls.setdefault(usr, rec)
        print(f"  [{i:3}/{len(ALL_HEADERS)}] <{h}>: {len(found)} decls "
              f"(total {len(all_decls)})", flush=True)

    # ---- Pass B: std_since via level sweep ----------------------------------
    print("pass B: -std sweep for std_since", flush=True)
    since: dict[str, str] = {}
    for std in STD_LEVELS:
        tu = parse_tu(index, combined_src(ALL_HEADERS), std)
        found: dict[str, dict] = {}
        walk(tu.cursor, found)
        label = "C++" + std.split("+")[-1].lstrip("+")
        new = 0
        for usr in found:
            if usr not in since:
                since[usr] = label
                new += 1
        print(f"  {std}: {len(found)} visible, {new} first-seen", flush=True)

    hsets = {h: set(us) for h, us in header_sets.items()}
    providers: dict[str, list[str]] = defaultdict(list)
    for h, us in hsets.items():
        for usr in us:
            providers[usr].append(h)
    # Most specific provider = the smallest header that offers it.
    for usr, rec in all_decls.items():
        rec["impl"] = stdlib
        rec["std_since"] = since.get(usr)
        hs = sorted(providers.get(usr, []), key=lambda h: (len(hsets[h]), h))
        rec["headers"] = hs
        rec["header"] = hs[0] if hs else None

    with open(DATA / out_name, "w") as f:
        for rec in all_decls.values():
            f.write(json.dumps(rec) + "\n")
    with open(DATA / "header_sets.json", "w") as f:
        json.dump({h: len(u) for h, u in header_sets.items()}, f, indent=1)

    print(f"\nwrote {len(all_decls)} decls -> {DATA/out_name}")


if __name__ == "__main__":
    main(*sys.argv[1:])
