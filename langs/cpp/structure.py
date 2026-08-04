#!/usr/bin/env python3
"""
langs/cpp/structure.py -- structural analysis of C++ declarations.

Per PROGRAMMING language, shared by every human-language pack. This decides
which parameter is the range and which is the comparator, and which header a
declaration should be included from. None of that depends on whether the
reader speaks English or Czech, so it must not live in a pack -- otherwise
every language inherits English's structural assumptions along with its words.

    langs/<lang>/structure.py   parameter roles, header homes   -> base.db
    packs/<locale>/lexicon.py   verbs, terms, aliases           -> pack_<x>.db
"""
from __future__ import annotations

import os as _os

# --------------------------------------------------- home-header mapping ----
# A declaration physically lives in a bits/*.h detail file that many public
# headers pull in transitively, so "which header do I include?" cannot be
# answered by the file path alone. This table names the conventional home
# header for the detail files that carry real API; anything unlisted falls back
# to name affinity, then to the smallest providing header.
BITS_HOME = {
    "stl_algo": "algorithm", "stl_algobase": "algorithm",
    "ranges_algo": "algorithm", "ranges_algobase": "algorithm",
    "stl_heap": "algorithm", "predefined_ops": "algorithm",
    "erase_if": "algorithm",
    "stl_numeric": "numeric", "ranges_numeric": "numeric",
    "stl_vector": "vector", "vector": "vector", "stl_bvector": "vector",
    "stl_deque": "deque", "stl_list": "list", "forward_list": "forward_list",
    "stl_map": "map", "stl_multimap": "map", "stl_tree": "map",
    "node_handle": "map",
    "stl_set": "set", "stl_multiset": "set",
    "unordered_map": "unordered_map", "unordered_set": "unordered_set",
    "hashtable": "unordered_map", "hashtable_policy": "unordered_map",
    "stl_queue": "queue", "stl_stack": "stack",
    "basic_string": "string", "char_traits": "string", "cow_string": "string",
    "string_view": "string_view", "basic_string_view": "string_view",
    "stl_iterator": "iterator", "stl_iterator_base_funcs": "iterator",
    "stl_iterator_base_types": "iterator", "stream_iterator": "iterator",
    "streambuf_iterator": "iterator",
    "stl_function": "functional", "functional_hash": "functional",
    "refwrap": "functional", "invoke": "functional", "ranges_cmp": "functional",
    "mofunc_impl": "functional", "funcwrap": "functional",
    "stl_pair": "utility", "move": "utility", "stl_relops": "utility",
    "utility": "utility",
    "shared_ptr": "memory", "shared_ptr_base": "memory",
    "shared_ptr_atomic": "memory", "unique_ptr": "memory",
    "stl_uninitialized": "memory", "stl_construct": "memory",
    "stl_tempbuf": "memory", "alloc_traits": "memory",
    "new_allocator": "memory", "allocator": "memory", "align": "memory",
    "ptr_traits": "memory", "uses_allocator": "memory",
    "fs_path": "filesystem", "fs_ops": "filesystem", "fs_dir": "filesystem",
    "fs_fwd": "filesystem",
    "chrono": "chrono", "chrono_io": "chrono", "parse_numbers": "chrono",
    "atomic_base": "atomic", "atomic_wait": "atomic", "atomic_timed_wait": "atomic",
    "std_mutex": "mutex", "unique_lock": "mutex", "std_thread": "thread",
    "this_thread_sleep": "thread", "semaphore_base": "semaphore",
    "ios_base": "ios", "basic_ios": "ios", "locale_facets": "locale",
    "locale_facets_nonio": "locale", "locale_classes": "locale",
    "locale_conv": "locale", "codecvt": "locale",
    "regex": "regex", "regex_automaton": "regex", "regex_compiler": "regex",
    "regex_error": "regex", "regex_executor": "regex", "regex_scanner": "regex",
    "random": "random", "uniform_int_dist": "random", "opt_random": "random",
    "valarray_array": "valarray", "valarray_after": "valarray",
    "valarray_before": "valarray", "slice_array": "valarray",
    "gslice": "valarray", "gslice_array": "valarray", "mask_array": "valarray",
    "indirect_array": "valarray",
    "concept_check": "concepts", "ranges_base": "ranges",
    "ranges_util": "ranges", "max_size_type": "ranges",
    "std_abs": "cmath", "specfun": "cmath", "mathcalls": "cmath",
    "stringfwd": "string", "postypes": "ios", "exception_ptr": "exception",
    "nested_exception": "exception", "stl_raise": "stdexcept",
    "quoted_string": "iomanip", "sstream": "sstream", "fstream": "fstream",
    "ostream": "ostream", "istream": "istream", "streambuf": "streambuf",
    "ostream_insert": "ostream", "text_encoding": "text_encoding",
    "charconv": "charconv", "out_ptr": "memory", "stop_token": "stop_token",
    "semaphore": "semaphore", "atomic_futex": "future", "std_function": "functional",
}

# Headers we prefer to name as the include when several provide a symbol and
# name affinity is inconclusive. Aggregators sink to the bottom.
HEADER_DEMOTE = {
    "<execution>", "<valarray>", "<regex>", "<chrono>", "<stacktrace>",
    "<random>", "<memory_resource>", "<syncstream>", "<spanstream>",
    "<scoped_allocator>", "<flat_map>", "<flat_set>", "<generator>",
    "<locale>", "<codecvt>", "<complex>",
}

# -------------------------------------------- parameter role inference ------
# (matcher-kind, pattern, role, semantic)
PARAM_NAME_ROLES = [
    ({"first", "first1", "__first", "begin"}, "range", "range.first"),
    ({"last", "last1", "__last", "end"}, "sentinel", "range.last"),
    ({"first2", "last2", "d_first", "result", "out", "dest", "d_last"},
     "output", "range.destination"),
    ({"comp", "cmp", "compare", "less"}, "comparator", "order.compare"),
    ({"pred", "predicate"}, "predicate", "test.predicate"),
    ({"proj", "proj1", "proj2"}, "projection", "access.projection"),
    ({"policy", "exec"}, "policy", "exec.policy"),
    ({"alloc", "allocator"}, "allocator", "memory.allocator"),
    ({"n", "count", "num", "size", "len", "length"}, "count", "amount.count"),
    ({"pos", "position", "idx", "index", "i", "offset"}, "position", "at.index"),
    ({"value", "val", "elem", "item"}, "value", "the.value"),
    ({"key", "k"}, "value", "lookup.key"),
    ({"f", "fn", "func", "g", "op", "unary_op", "binary_op", "callable"},
     "callable", "do.callable"),
    ({"init"}, "value", "fold.initial"),
    ({"str", "s", "text"}, "value", "the.text"),
    ({"path", "from", "to", "old_p", "new_p"}, "path", "fs.path"),
    ({"os", "out_stream", "ostr"}, "stream", "io.out"),
    ({"is", "in_stream", "istr"}, "stream", "io.in"),
    ({"rel_time", "abs_time", "timeout", "dur"}, "value", "time.duration"),
    ({"deleter", "del"}, "deleter", "memory.deleter"),
    ({"flags", "mode", "openmode", "fmtflags"}, "flags", "opt.flags"),
]

PARAM_TYPE_ROLES = [
    ("ExecutionPolicy", "policy", "exec.policy"),
    ("Compare", "comparator", "order.compare"),
    ("Pred", "predicate", "test.predicate"),
    ("Allocator", "allocator", "memory.allocator"),
    ("Iterator", "range", "range.iterator"),
    ("Iter", "range", "range.iterator"),
    ("Sentinel", "sentinel", "range.last"),
    ("Range", "range", "the.range"),
    ("Size", "count", "amount.count"),
    ("Distance", "count", "amount.distance"),
    ("size_t", "count", "amount.count"),
    ("duration", "value", "time.duration"),
    ("time_point", "value", "time.instant"),
    ("path", "path", "fs.path"),
    ("error_code", "output", "error.code"),
    ("...", "callable", "args.pack"),
]



def home_header(defining_file: str | None, providers: list[str]) -> str | None:
    """Pick the header a user should actually #include for a declaration."""
    if not providers:
        return None
    stem = _os.path.basename(defining_file or "").removesuffix(".h")
    if stem in BITS_HOME:
        cand = f"<{BITS_HOME[stem]}>"
        if cand in providers:
            return cand
    bare = stem.removeprefix("stl_").removeprefix("std_").removeprefix("ranges_")
    if bare:
        if f"<{bare}>" in providers:
            return f"<{bare}>"
        for h in providers:
            n = h.strip("<>")
            if n.startswith(bare) or bare.startswith(n):
                return h
    plain = [h for h in providers if h not in HEADER_DEMOTE]
    return (plain or providers)[0]


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
        q["role"], q["semantic"] = role, sem
        q["optional"] = bool(p.get("default_value"))
        out.append(q)
    return out
