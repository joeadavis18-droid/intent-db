#!/usr/bin/env python3
"""
lexicon.py -- the human-language layer.

Everything here maps C++ spelling onto the words a person actually uses when
they describe what they are trying to do. This is the file to edit when a
lookup "should have worked but didn't".
"""
from __future__ import annotations

# --------------------------------------------------------------- domains ----
# Public header -> the domain segment of a canonical key.
HEADER_DOMAIN = {
    "<algorithm>": "algorithm", "<numeric>": "math", "<cmath>": "math",
    "<complex>": "math", "<valarray>": "math", "<numbers>": "math",
    "<random>": "random", "<ratio>": "math", "<bit>": "bits",
    "<vector>": "container", "<array>": "container", "<deque>": "container",
    "<list>": "container", "<forward_list>": "container", "<map>": "container",
    "<set>": "container", "<unordered_map>": "container",
    "<unordered_set>": "container", "<queue>": "container",
    "<stack>": "container", "<bitset>": "container", "<span>": "container",
    "<mdspan>": "container", "<flat_map>": "container", "<flat_set>": "container",
    "<string>": "text", "<string_view>": "text", "<charconv>": "text",
    "<format>": "text", "<regex>": "text", "<locale>": "text",
    "<codecvt>": "text", "<cctype>": "text", "<cstring>": "text",
    "<cwchar>": "text", "<cwctype>": "text", "<cuchar>": "text",
    "<iostream>": "io", "<ostream>": "io", "<istream>": "io", "<ios>": "io",
    "<fstream>": "io", "<sstream>": "io", "<iomanip>": "io", "<print>": "io",
    "<streambuf>": "io", "<spanstream>": "io", "<syncstream>": "io",
    "<iosfwd>": "io", "<cstdio>": "io",
    "<filesystem>": "filesystem",
    "<thread>": "concurrency", "<mutex>": "concurrency",
    "<shared_mutex>": "concurrency", "<condition_variable>": "concurrency",
    "<future>": "concurrency", "<atomic>": "concurrency",
    "<semaphore>": "concurrency", "<latch>": "concurrency",
    "<barrier>": "concurrency", "<stop_token>": "concurrency",
    "<execution>": "concurrency", "<coroutine>": "async",
    "<generator>": "async",
    "<memory>": "memory", "<memory_resource>": "memory", "<new>": "memory",
    "<scoped_allocator>": "memory", "<cstdlib>": "memory",
    "<chrono>": "time", "<ctime>": "time",
    "<type_traits>": "meta", "<concepts>": "meta", "<typeinfo>": "meta",
    "<typeindex>": "meta", "<limits>": "meta", "<version>": "meta",
    "<compare>": "meta", "<source_location>": "meta",
    "<utility>": "core", "<tuple>": "core", "<optional>": "core",
    "<variant>": "core", "<any>": "core", "<expected>": "core",
    "<functional>": "callable", "<iterator>": "iterator", "<ranges>": "range",
    "<exception>": "error", "<stdexcept>": "error", "<system_error>": "error",
    "<cerrno>": "error", "<cassert>": "error", "<stacktrace>": "error",
    "<csignal>": "error", "<csetjmp>": "error",
    "<initializer_list>": "core", "<cstddef>": "core", "<cstdint>": "core",
    "<cstdarg>": "core", "<cinttypes>": "core", "<cfloat>": "math",
    "<climits>": "math", "<cfenv>": "math", "<stdfloat>": "math",
    "<clocale>": "text",
}

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

# ------------------------------------------------------- object nouns -------
# Class -> the words people use for it. First entry drives the canonical key.
OBJECT_NOUNS = {
    "vector": ["vector", "dynamic-array", "list", "resizable-array"],
    "array": ["array", "fixed-array"],
    "deque": ["deque", "double-ended-queue"],
    "list": ["linked-list", "list"],
    "forward_list": ["singly-linked-list", "forward-list"],
    "map": ["sorted-map", "ordered-map", "dictionary", "tree-map"],
    "multimap": ["sorted-multimap", "multi-key-map"],
    "set": ["sorted-set", "ordered-set", "tree-set"],
    "multiset": ["sorted-multiset"],
    "unordered_map": ["hash-map", "dictionary", "hash-table", "map"],
    "unordered_multimap": ["hash-multimap"],
    "unordered_set": ["hash-set", "set"],
    "unordered_multiset": ["hash-multiset"],
    "flat_map": ["flat-map"], "flat_set": ["flat-set"],
    "queue": ["queue", "fifo"],
    "priority_queue": ["priority-queue", "heap"],
    "stack": ["stack", "lifo"],
    "bitset": ["bitset", "bit-flags"],
    "span": ["span", "view-over-array"],
    "mdspan": ["multidimensional-span"],
    "basic_string": ["string", "text"], "string": ["string", "text"],
    "basic_string_view": ["string-view", "borrowed-string"],
    "string_view": ["string-view", "borrowed-string"],
    "path": ["path", "file-path", "filename"],
    "directory_entry": ["directory-entry", "dir-entry"],
    "unique_ptr": ["unique-pointer", "owning-pointer"],
    "shared_ptr": ["shared-pointer", "refcounted-pointer"],
    "weak_ptr": ["weak-pointer", "non-owning-pointer"],
    "optional": ["optional", "maybe-value", "nullable"],
    "variant": ["variant", "tagged-union", "sum-type"],
    "expected": ["expected", "result", "value-or-error"],
    "any": ["any", "type-erased-value"],
    "tuple": ["tuple", "fixed-record"], "pair": ["pair", "two-tuple"],
    "function": ["function-object", "callable", "std-function"],
    "thread": ["thread"], "jthread": ["joining-thread"],
    "mutex": ["mutex", "lock"], "shared_mutex": ["shared-mutex", "rw-lock"],
    "condition_variable": ["condition-variable", "wait-signal"],
    "future": ["future", "async-result"], "promise": ["promise"],
    "atomic": ["atomic", "lock-free-value"],
    "duration": ["duration", "time-span"],
    "time_point": ["time-point", "timestamp"],
    "basic_ostream": ["output-stream"], "ostream": ["output-stream"],
    "basic_istream": ["input-stream"], "istream": ["input-stream"],
    "basic_ofstream": ["output-file"], "ofstream": ["output-file"],
    "basic_ifstream": ["input-file"], "ifstream": ["input-file"],
    "basic_stringstream": ["string-stream"], "stringstream": ["string-stream"],
    "basic_regex": ["regex", "regular-expression"],
    "regex": ["regex", "regular-expression"],
}

# ------------------------------------------------------------- verbs --------
# token -> {a: canonical action, say: [phrase templates], sum: summary template}
# '{o}' is the object with its article already applied ("a vector", "a range").
# The `say` templates are what make plain-English lookups land: a user who
# types "stick something on the end of a vector" should reach push_back.
def _v(a, say=(), sum=None, obj=None, alts=(), term=None):
    """obj/alts let a concept declare WHAT it acts on when the parameter list
    cannot say it: malloc(size_t) looks like it takes a count, but the thing
    being acted on is memory."""
    return {"a": a, "say": list(say), "sum": sum,
            "obj": obj, "alts": list(alts), "term": term}

VERBS = {
 "sort":      _v("sort", ["put-{o}-in-order", "order-{o}", "arrange-{o}", "rank-{o}"],
                 "Sort {o} into ascending order."),
 "stable":    _v("sort-stable", ["sort-{o}-keeping-equal-items-in-order"],
                 "Sort {o}, preserving the relative order of equivalent elements."),
 "find":      _v("find", ["look-for-something-in-{o}", "search-{o}", "locate-an-item-in-{o}", "where-is-it-in-{o}"],
                 "Find the first matching element in {o}."),
 "search":    _v("search", ["find-a-subsequence-in-{o}", "find-a-pattern-in-{o}"],
                 "Search {o} for a subsequence."),
 "count":     _v("count", ["how-many-items-in-{o}", "tally-{o}", "count-matches-in-{o}"],
                 "Count the matching elements in {o}."),
 "copy":      _v("copy", ["duplicate-{o}", "clone-{o}", "copy-{o}-somewhere-else"],
                 "Copy elements out of {o} into a destination."),
 "move":      _v("move", ["transfer-{o}", "steal-the-contents-of-{o}", "relocate-{o}"],
                 "Move elements out of {o}, leaving the sources valid but unspecified."),
 "fill":      _v("fill", ["set-every-element-of-{o}", "populate-{o}"],
                 "Assign one value to every element of {o}."),
 "generate":  _v("generate", ["produce-the-values-of-{o}", "make-each-element-of-{o}"],
                 "Fill {o} by calling a generator for each element."),
 "transform": _v("map", ["apply-a-function-to-each-item-of-{o}", "map-over-{o}", "convert-each-item-of-{o}"],
                 "Apply a function to each element of {o} and write the results out."),
 "accumulate":_v("accumulate", ["sum-up-{o}", "add-everything-in-{o}", "total-{o}", "fold-{o}-left-to-right"],
                 "Fold {o} down to a single value, strictly left to right."),
 "reduce":    _v("reduce", ["fold-{o}", "combine-everything-in-{o}", "aggregate-{o}"],
                 "Fold {o} to a single value, in unspecified order (parallelisable)."),
 "replace":   _v("replace", ["swap-out-values-in-{o}", "substitute-values-in-{o}"],
                 "Replace matching elements of {o} with a new value."),
 "remove":    _v("remove", ["strip-items-out-of-{o}", "drop-items-from-{o}", "filter-{o}"],
                 "Move unwanted elements of {o} to the end and return the new logical end."),
 "erase":     _v("erase", ["delete-an-item-from-{o}", "get-rid-of-part-of-{o}", "take-something-out-of-{o}"],
                 "Erase elements from {o}, shrinking it."),
 "insert":    _v("insert", ["add-an-item-to-{o}", "put-something-into-{o}", "splice-into-{o}"],
                 "Insert one or more elements into {o}."),
 "emplace":   _v("construct-in-place", ["build-an-item-directly-inside-{o}", "add-to-{o}-without-copying"],
                 "Construct an element directly inside {o}, avoiding a copy or move."),
 "push":      _v("push", ["stick-something-on-the-end-of-{o}", "add-to-the-end-of-{o}", "append-to-{o}"],
                 "Add an element to {o}."),
 "pop":       _v("pop", ["take-the-last-item-off-{o}", "drop-the-end-of-{o}", "remove-from-the-end-of-{o}"],
                 "Remove an element from {o}."),
 "append":    _v("append", ["add-to-the-end-of-{o}", "concatenate-onto-{o}", "tack-onto-{o}"],
                 "Append to the end of {o}."),
 "assign":    _v("assign", ["overwrite-the-contents-of-{o}", "set-the-contents-of-{o}"],
                 "Replace the entire contents of {o}."),
 "clear":     _v("clear", ["empty-{o}", "remove-everything-from-{o}", "reset-{o}"],
                 "Remove all elements from {o}, leaving it empty."),
 "resize":    _v("resize", ["change-the-size-of-{o}", "grow-{o}", "shrink-{o}"],
                 "Change the number of elements in {o}."),
 "reserve":   _v("reserve-capacity", ["preallocate-space-in-{o}", "stop-{o}-from-reallocating"],
                 "Reserve capacity in {o} so later growth does not reallocate."),
 "shrink":    _v("shrink-to-fit", ["release-the-spare-memory-of-{o}", "compact-{o}"],
                 "Ask {o} to release memory it is not using."),
 "swap":      _v("swap", ["exchange-{o}-with-another", "trade-the-contents-of-{o}"],
                 "Exchange contents with another object, without copying."),
 "reverse":   _v("reverse", ["flip-the-order-of-{o}", "put-{o}-backwards"],
                 "Reverse the order of the elements of {o}."),
 "rotate":    _v("rotate", ["shift-{o}-around", "cycle-{o}"],
                 "Rotate {o} so a chosen element becomes first."),
 "shuffle":   _v("shuffle", ["randomize-the-order-of-{o}", "mix-up-{o}"],
                 "Randomly permute the elements of {o}."),
 "sample":    _v("sample", ["pick-a-random-subset-of-{o}", "randomly-select-from-{o}"],
                 "Select n elements from {o} at random."),
 "partition": _v("partition", ["split-{o}-by-a-condition", "group-{o}-by-a-test"],
                 "Reorder {o} so elements satisfying a predicate come first."),
 "unique":    _v("dedupe", ["remove-duplicates-from-{o}", "collapse-repeats-in-{o}"],
                 "Collapse consecutive duplicate elements of {o}."),
 "merge":     _v("merge", ["combine-two-sorted-copies-of-{o}", "interleave-{o}"],
                 "Merge two sorted ranges into one sorted output."),
 "min":       _v("minimum", ["find-the-smallest-in-{o}", "lowest-value-in-{o}"],
                 "Return the smallest value."),
 "max":       _v("maximum", ["find-the-largest-in-{o}", "highest-value-in-{o}", "biggest-in-{o}"],
                 "Return the largest value."),
 "minmax":    _v("min-and-max", ["find-both-extremes-of-{o}"],
                 "Return the smallest and largest values together."),
 "clamp":     _v("clamp", ["limit-a-value-to-a-range", "constrain-a-value"],
                 "Clamp a value into the closed interval [lo, hi]."),
 "abs":       _v("absolute-value", ["drop-the-sign", "magnitude-of-a-number"],
                 "Return the absolute value."),
 "begin":     _v("first-position", ["get-the-start-of-{o}", "iterator-to-the-front-of-{o}"],
                 "Return an iterator to the first element of {o}."),
 "end":       _v("past-the-end-position", ["get-the-end-of-{o}", "iterator-one-past-the-last-of-{o}"],
                 "Return an iterator one past the last element of {o}."),
 "cbegin":    _v("first-position-const", ["read-only-start-of-{o}"],
                 "Return a const iterator to the first element of {o}."),
 "cend":      _v("past-the-end-const", ["read-only-end-of-{o}"],
                 "Return a const iterator one past the last element of {o}."),
 "rbegin":    _v("reverse-first-position", ["walk-{o}-backwards-from-the-end"],
                 "Return a reverse iterator to the last element of {o}."),
 "rend":      _v("reverse-past-the-end", ["end-of-walking-{o}-backwards"],
                 "Return a reverse iterator one before the first element of {o}."),
 "size":      _v("size", ["how-many-elements-are-in-{o}", "length-of-{o}"],
                 "Return the number of elements in {o}."),
 "empty":     _v("is-empty", ["is-{o}-empty", "does-{o}-have-anything-in-it"],
                 "Report whether {o} holds no elements."),
 "front":     _v("first-element", ["get-the-first-item-of-{o}", "head-of-{o}"],
                 "Return a reference to the first element of {o}."),
 "back":      _v("last-element", ["get-the-last-item-of-{o}", "tail-of-{o}"],
                 "Return a reference to the last element of {o}."),
 "at":        _v("checked-element-access", ["index-{o}-safely", "get-from-{o}-with-bounds-checking"],
                 "Access an element of {o} by index, throwing if out of range."),
 "data":      _v("raw-pointer", ["get-the-underlying-buffer-of-{o}", "c-array-behind-{o}"],
                 "Return a pointer to the contiguous storage backing {o}."),
 "substr":    _v("substring", ["take-a-slice-of-{o}", "get-part-of-{o}"],
                 "Return a substring of {o}."),
 "compare":   _v("compare", ["which-of-two-is-bigger", "order-two-values"],
                 "Three-way compare two values."),
 "contains":  _v("contains", ["does-{o}-have-this-item", "is-it-in-{o}", "membership-test-on-{o}"],
                 "Report whether {o} contains the given key."),
 "starts":    _v("starts-with", ["does-{o}-begin-with-this", "prefix-test-on-{o}"],
                 "Report whether {o} begins with the given prefix."),
 "ends":      _v("ends-with", ["does-{o}-end-with-this", "suffix-test-on-{o}"],
                 "Report whether {o} ends with the given suffix."),
 "make":      _v("construct", ["create-{o}", "build-{o}", "new-{o}"],
                 "Construct and return a new object."),
 "get":       _v("get", ["read-from-{o}", "fetch-from-{o}", "access-{o}"],
                 "Retrieve a value."),
 "set":       _v("set", ["write-to-{o}", "store-into-{o}"],
                 "Store a value."),
 "to":        _v("convert-to", ["turn-{o}-into-something-else", "render-{o}-as-text"],
                 "Convert to another representation."),
 "from":      _v("convert-from", ["parse-{o}-from-text", "read-{o}-out-of-a-string"],
                 "Construct from another representation."),
 "stoi":      _v("parse-integer", ["string-to-int", "turn-text-into-a-number", "parse-a-number"],
                 "Parse an integer out of a string."),
 "stod":      _v("parse-double", ["string-to-double", "turn-text-into-a-float"],
                 "Parse a floating-point value out of a string."),
 "is":        _v("test", ["check-if-{o}-is", "does-{o}-qualify"],
                 "Report whether the condition holds."),
 "has":       _v("test-has", ["check-{o}-for", "does-{o}-have-it"],
                 "Report whether the property is present."),
 "lock":      _v("lock", ["acquire-{o}", "take-the-lock", "enter-the-critical-section"],
                 "Acquire the lock, blocking until it is available."),
 "unlock":    _v("unlock", ["release-{o}", "give-up-the-lock"],
                 "Release the lock."),
 "try":       _v("try", ["attempt-without-blocking", "non-blocking-attempt"],
                 "Attempt the operation without blocking; report success."),
 "wait":      _v("wait", ["block-until-something-happens", "sleep-until-signalled", "pause-until-ready"],
                 "Block until the condition is signalled."),
 "notify":    _v("notify", ["wake-up-a-waiter", "signal-that-it-is-ready"],
                 "Wake threads waiting on this object."),
 "join":      _v("join", ["wait-for-the-thread-to-finish", "block-until-the-thread-is-done"],
                 "Block until the thread finishes."),
 "detach":    _v("detach", ["let-the-thread-run-free", "fire-and-forget-a-thread"],
                 "Detach the thread so it runs independently."),
 "open":      _v("open", ["start-using-a-file", "open-a-file"],
                 "Open the associated file."),
 "close":     _v("close", ["finish-with-a-file", "release-the-file-handle"],
                 "Close the associated file."),
 "read":      _v("read", ["load-data-in", "pull-bytes-in", "ingest"],
                 "Read data in."),
 "write":     _v("write", ["save-data-out", "emit-bytes", "output-data"],
                 "Write data out."),
 "flush":     _v("flush", ["force-the-buffer-out", "commit-buffered-output"],
                 "Flush buffered output to the underlying device."),
 "print":     _v("print", ["show-it-on-screen", "display-text", "output-text"],
                 "Format and print to an output stream."),
 "format":    _v("format", ["interpolate-values-into-a-string", "build-a-string-from-parts", "printf-style-formatting"],
                 "Format arguments into a string using a format specification."),
 "parse":     _v("parse", ["read-a-value-out-of-text", "scan-text"],
                 "Parse a value from text."),
 "allocate":  _v("allocate", ["get-raw-memory", "reserve-storage"],
                 "Allocate raw storage."),
 "deallocate":_v("deallocate", ["give-the-memory-back", "free-storage"],
                 "Release previously allocated storage."),
 "release":   _v("release-ownership", ["hand-off-the-pointer", "disown-the-pointer"],
                 "Give up ownership and return the raw pointer."),
 "reset":     _v("reset", ["point-{o}-at-something-else", "clear-and-replace-{o}"],
                 "Replace the managed object, destroying the old one."),
 "next":      _v("advance", ["step-forward", "move-ahead-one"],
                 "Return an iterator advanced forward."),
 "prev":      _v("retreat", ["step-backward", "move-back-one"],
                 "Return an iterator moved backward."),
 "advance":   _v("advance-by", ["jump-forward-n", "skip-ahead"],
                 "Advance an iterator in place by n positions."),
 "distance":  _v("distance", ["how-far-apart-are-two-iterators", "gap-between-iterators"],
                 "Return the number of steps between two iterators."),
 "hash":      _v("hash", ["digest-a-value", "bucket-key-for-a-value"],
                 "Compute a hash value."),
 "seek":      _v("seek", ["jump-to-a-file-position", "move-the-file-cursor"],
                 "Move the stream position."),
 "tell":      _v("current-position", ["where-am-i-in-the-file", "current-file-offset"],
                 "Report the current stream position."),
 "value":     _v("value", ["unwrap-{o}", "get-the-contained-thing-out-of-{o}"],
                 "Return the contained value, throwing if there is none."),
 "visit":     _v("visit", ["dispatch-on-the-active-type", "match-on-the-alternative"],
                 "Invoke a visitor on the currently held alternative."),
 "apply":     _v("apply-tuple", ["spread-a-tuple-into-a-call", "unpack-and-call"],
                 "Call a function with the elements of a tuple as its arguments."),
 "invoke":    _v("invoke", ["just-call-it", "run-the-callable"],
                 "Invoke a callable with the given arguments."),
 "bind":      _v("bind", ["partially-apply-a-function", "pre-fill-some-arguments"],
                 "Bind arguments to a callable, producing a new callable."),
 "async":     _v("run-async", ["do-it-in-the-background", "run-it-concurrently"],
                 "Run a callable asynchronously and return a future for its result."),
 "sleep":     _v("sleep", ["pause-for-a-while", "delay-this-thread"],
                 "Block this thread for a duration."),
 "exists":    _v("exists", ["is-the-file-there", "does-the-path-exist"],
                 "Report whether the path exists."),
 "create":    _v("create", ["make-a-new-directory", "mkdir"],
                 "Create the requested filesystem object."),
 "rename":    _v("rename", ["move-a-file", "change-a-file-name"],
                 "Rename or move a filesystem object."),
 "equal":     _v("equal", ["are-they-the-same", "compare-two-ranges-for-equality"],
                 "Report whether two ranges compare equal."),
 "lower":     _v("lower-bound", ["first-item-not-less-than", "where-would-i-insert-it"],
                 "Return the first position at which a value could be inserted in order."),
 "upper":     _v("upper-bound", ["first-item-greater-than"],
                 "Return the last position at which a value could be inserted in order."),
 "binary":    _v("binary-search", ["fast-lookup-in-a-sorted-range", "is-it-present-in-sorted-data"],
                 "Report whether a value exists in a sorted range, in logarithmic time."),
 "nth":       _v("nth-element", ["find-the-kth-smallest", "partially-sort-to-position-n"],
                 "Place the nth element as if sorted, partitioning around it."),
 "iota":      _v("fill-sequential", ["number-the-elements", "fill-with-0-1-2-3"],
                 "Fill {o} with successively incremented values."),
 "all":       _v("all-of", ["do-they-all-match", "is-every-element-ok"],
                 "Report whether every element satisfies the predicate."),
 "any":       _v("any-of", ["is-there-at-least-one-match", "does-anything-match"],
                 "Report whether at least one element satisfies the predicate."),
 "none":      _v("none-of", ["is-nothing-matching", "are-they-all-non-matching"],
                 "Report whether no element satisfies the predicate."),
 "for":       _v("for-each", ["do-something-to-each-item-of-{o}", "loop-over-{o}"],
                 "Apply a callable to every element of {o}."),
 "swap_ranges": _v("swap-ranges", ["exchange-two-ranges"],
                 "Exchange the elements of two ranges."),
}

# Trailing tokens that modify the action rather than name it.
MODIFIERS = {
    "back": "at-end", "front": "at-start", "if": "matching-predicate",
    "not": "negated", "n": "n-times", "copy": "into-new-range",
    "bound": "", "of": "", "each": "", "element": "", "search": "",
    "with": "", "to": "", "in": "", "place": "in-place", "fit": "",
    "heap": "on-heap", "sorted": "sorted", "permutation": "permutation",
    "until": "until", "range": "over-range", "view": "as-view",
    "ptr": "pointer", "cast": "cast", "unique": "unique", "shared": "shared",
    "for": "", "all": "", "why": "",
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

# Disambiguator derived from the differentiating parameter role -- this is how
# overloads get distinct-but-guessable keys.
ROLE_DISAMBIG = {
    "comparator": "with-comparator",
    "predicate": "matching-predicate",
    "policy": "parallel",
    "allocator": "with-allocator",
    "projection": "with-projection",
    "count": "n-elements",
    "output": "into-destination",
    "deleter": "with-deleter",
    "flags": "with-flags",
    "callable": "with-callable",
    # 'range' is deliberately absent: nearly every algorithm takes one, so it
    # distinguishes nothing and only lengthens keys.
}


# ------------------------------------------------------- header resolution --
import os as _os


def home_header(defining_file: str | None, providers: list[str]) -> str | None:
    """Pick the header a user should actually #include for a declaration.

    Priority: the curated home for its bits/*.h file, then name affinity
    between that detail file and a providing header, then the smallest
    providing header that is not a known aggregator.
    """
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
        for h in providers:                       # prefix affinity
            n = h.strip("<>")
            if n.startswith(bare) or bare.startswith(n):
                return h
    plain = [h for h in providers if h not in HEADER_DEMOTE]
    return (plain or providers)[0]

# Kinds that are not callable but still belong in a lexicon.
NONCALLABLE_KINDS = {
    "class", "class_template", "struct", "union", "enum", "alias",
    "concept", "variable", "variable_template", "keyword", "statement",
    "preprocessor", "attribute", "literal_suffix", "punctuator", "macro",
}


# Objects the range-flavoured summary templates are written for. Deliberately
# NOT every object noun: a path or a mutex is not a sequence, so those get a
# plain "<Action> <object>." summary instead of "copy elements out of ...".
RANGE_LIKE = {
    "range", "sequence", "collection", "vector", "dynamic-array", "list",
    "resizable-array", "array", "fixed-array", "deque", "double-ended-queue",
    "linked-list", "singly-linked-list", "forward-list", "sorted-map",
    "ordered-map", "dictionary", "tree-map", "sorted-set", "ordered-set",
    "tree-set", "hash-map", "hash-table", "hash-set", "sorted-multiset",
    "sorted-multimap", "flat-map", "flat-set", "queue", "fifo", "stack",
    "lifo", "priority-queue", "heap", "span", "view-over-array", "bitset",
    "string", "text", "string-view", "borrowed-string",
}


# Class templates users almost never spell out. std::string IS
# std::basic_string<char>, so a lookup for "std::string::substr" must land on
# std::basic_string::substr. These generate extra symbolic aliases.
TYPEDEF_ALIASES = {
    "basic_string": ["string", "wstring", "u8string", "u16string", "u32string"],
    "basic_string_view": ["string_view", "wstring_view"],
    "basic_ostream": ["ostream", "wostream"],
    "basic_istream": ["istream", "wistream"],
    "basic_iostream": ["iostream"],
    "basic_ofstream": ["ofstream"], "basic_ifstream": ["ifstream"],
    "basic_fstream": ["fstream"],
    "basic_ostringstream": ["ostringstream"],
    "basic_istringstream": ["istringstream"],
    "basic_stringstream": ["stringstream"],
    "basic_streambuf": ["streambuf"], "basic_filebuf": ["filebuf"],
    "basic_stringbuf": ["stringbuf"], "basic_regex": ["regex", "wregex"],
    "basic_ios": ["ios"], "match_results": ["smatch", "cmatch"],
    "sub_match": ["ssub_match", "csub_match"],
    "regex_iterator": ["sregex_iterator"],
    "regex_token_iterator": ["sregex_token_iterator"],
}

# Namespaces that themselves name the object being acted on.
NAMESPACE_OBJECT = {
    "std::this_thread": ("thread", ["current-thread"]),
    "std::filesystem": ("path", ["file", "filename"]),
    "std::chrono": ("time", ["clock", "duration"]),
    "std::ranges": ("range", ["sequence", "collection"]),
    "std::views": ("range-view", ["lazy-range"]),
    "std::pmr": ("memory-resource", ["arena"]),
    "std::execution": ("execution-policy", ["parallelism"]),
    "std::numbers": ("constant", ["math-constant"]),
    "std::literals": ("literal", ["suffix"]),
}


# Filler words carry no lookup signal. Stripping them lets "wait for A thread
# to finish" match the key "wait-for-THE-thread-to-finish".
FILLER = {
    "a", "an", "the", "my", "this", "that", "these", "those", "it", "its",
    "some", "any", "of", "to", "in", "into", "on", "at", "for", "from",
    "with", "and", "or", "is", "are", "be", "do", "does", "did", "i",
    "how", "what", "where", "can", "should", "would", "want", "need",
    "please", "just", "get", "make", "so", "then", "there", "something",
}

# Common English words that are also C++ keywords. Matching one of these
# against an entry NAME is almost always coincidence, not intent.
NAME_STOPWORDS = {
    "this", "if", "for", "do", "new", "delete", "and", "or", "not", "default",
    "case", "while", "return", "break", "continue", "switch", "try", "catch",
    "class", "struct", "union", "public", "private", "protected", "auto",
    "const", "int", "char", "bool", "float", "double", "long", "short",
    "void", "using", "template", "operator", "export", "import", "module",
    "true", "false", "inline", "static", "virtual", "friend", "throw",
    "enum", "namespace", "final", "override", "asm", "register", "signed",
    "unsigned", "typedef", "mutable", "explicit", "concept", "requires",
    "value", "values", "data", "size", "at", "end", "begin", "left", "right",
}

# Words that make an intent findable even though the identifier never says
# them. Applied when building intent_text.
MOD_SYNONYMS = {
    "unique": "unique ownership exclusive owner single owner owning "
              "non copyable smart pointer",
    "shared": "shared ownership reference counted refcounted smart pointer",
    "pointer": "smart pointer raw pointer handle",
    "at-end": "back tail append push end of the container last position",
    "at-start": "front head prepend beginning first position",
    "matching-predicate": "conditionally where the predicate holds filtered",
    "n-times": "a given number of times count limited",
    "into-new-range": "writing results elsewhere without modifying the input",
    "in-place": "modifying the original without a copy",
    "on-heap": "heap ordered priority queue",
}


# ============================================================================
# PARAPHRASE LAYER
# ----------------------------------------------------------------------------
# One intent, many surface forms. "list all X" and "show me all X" mean the
# same thing, so BOTH must be keys pointing at the same entry. This table is
# the interchangeable-verb half; PHRASE_FRAMES is the sentence-shape half.
# Keyed on the canonical action produced by VERBS[...]["a"].
# ============================================================================

VERB_SYNONYMS = {
    "sort":        ["sort", "order", "arrange", "rank", "put-in-order", "sequence"],
    "sort-stable": ["stable-sort", "sort-preserving-order", "sort-keeping-ties"],
    "find":        ["find", "search", "locate", "look-for", "look-up", "lookup",
                    "retrieve", "seek", "get"],
    "search":      ["search-for", "find-a-pattern", "match-a-subsequence"],
    "count":       ["count", "tally", "how-many", "number-of", "total-up"],
    "size":        ["size", "length", "how-many", "count-of", "how-big",
                    "number-of-elements"],
    "is-empty":    ["is-empty", "check-if-empty", "has-nothing", "is-blank",
                    "any-elements"],
    "clear":       ["clear", "empty", "wipe", "reset", "blank", "purge",
                    "remove-everything-from", "delete-everything-in"],
    "push":        ["add-to", "append-to", "push-onto", "stick-on-the-end-of",
                    "tack-onto", "put-on-the-end-of"],
    "pop":         ["pop", "remove-the-last-item-from", "take-the-end-off",
                    "drop-the-last-item-of"],
    "append":      ["append-to", "concatenate-onto", "add-to-the-end-of", "join-onto"],
    "insert":      ["insert-into", "add-to", "put-into", "place-into", "splice-into"],
    "construct-in-place": ["emplace-into", "construct-inside",
                           "build-in-place-in", "add-without-copying-to"],
    "erase":       ["erase-from", "delete-from", "remove-from", "get-rid-of-part-of",
                    "take-out-of", "drop-from"],
    "remove":      ["remove-from", "strip-out-of", "filter-out-of", "drop-from"],
    "copy":        ["copy", "duplicate", "clone", "replicate"],
    "move":        ["move", "transfer", "relocate", "shift"],
    "swap":        ["swap", "exchange", "trade", "switch"],
    "reverse":     ["reverse", "flip", "invert", "put-backwards"],
    "rotate":      ["rotate", "cycle", "shift-around"],
    "shuffle":     ["shuffle", "randomize", "mix-up", "scramble"],
    "map":         ["transform", "map-over", "apply-to-each-of", "convert-each-of",
                    "project"],
    "accumulate":  ["sum", "add-up", "total", "fold", "accumulate", "aggregate"],
    "reduce":      ["reduce", "fold", "combine", "aggregate", "sum"],
    "dedupe":      ["dedupe", "deduplicate", "remove-duplicates-from", "uniquify",
                    "collapse-repeats-in", "drop-repeats-in"],
    "replace":     ["replace-in", "substitute-in", "swap-out-in", "change-values-in"],
    "fill":        ["fill", "populate", "set-every-element-of"],
    "generate":    ["generate", "produce", "make-each-element-of"],
    "partition":   ["partition", "split", "group-by-condition"],
    "merge":       ["merge", "combine-sorted", "interleave"],
    "for-each":    ["for-each", "loop-over", "iterate", "walk", "go-through",
                    "visit-each-of", "run-over"],
    "all-of":      ["all-match", "do-they-all-match", "every-element-satisfies",
                    "check-all-of"],
    "any-of":      ["any-match", "at-least-one-matches", "does-anything-match"],
    "none-of":     ["none-match", "nothing-matches", "no-element-satisfies"],
    "minimum":     ["min", "smallest", "lowest", "minimum"],
    "maximum":     ["max", "largest", "biggest", "highest", "maximum"],
    "clamp":       ["clamp", "constrain", "limit-to-a-range"],
    "lower-bound": ["lower-bound", "first-not-less-than", "insertion-point"],
    "upper-bound": ["upper-bound", "first-greater-than"],
    "binary-search": ["binary-search", "fast-lookup-in", "is-it-present-in-sorted"],
    "checked-element-access": ["get-at-index", "index-into", "element-at",
                               "safe-index-into"],
    "first-element": ["first-item-of", "head-of", "front-of"],
    "last-element":  ["last-item-of", "tail-of", "back-of"],
    "first-position": ["start-of", "beginning-of", "begin-iterator-of"],
    "past-the-end-position": ["end-of", "end-iterator-of", "one-past-the-end-of"],
    "contains":    ["contains", "has", "is-it-in", "does-it-include",
                    "membership-test-on"],
    "starts-with": ["starts-with", "begins-with", "has-the-prefix"],
    "ends-with":   ["ends-with", "has-the-suffix"],
    "substring":   ["substring-of", "slice-of", "part-of", "chunk-of"],
    "reserve-capacity": ["reserve-space-in", "preallocate-in", "presize"],
    "resize":      ["resize", "grow", "shrink", "change-the-size-of"],
    "shrink-to-fit": ["shrink-to-fit", "release-spare-memory-of", "compact"],
    "lock":        ["lock", "acquire", "take-the-lock-on", "enter-the-critical-section"],
    "unlock":      ["unlock", "release", "give-up-the-lock-on"],
    "wait":        ["wait", "block-until", "await", "pause-until", "hold-until"],
    "notify":      ["notify", "wake-up", "signal"],
    "join":        ["join", "wait-for-the-thread", "block-until-the-thread-is-done"],
    "detach":      ["detach", "let-the-thread-run-free", "fire-and-forget"],
    "run-async":   ["run-async", "run-in-the-background", "do-concurrently",
                    "kick-off-in-parallel"],
    "sleep":       ["sleep", "pause", "delay", "wait-a-bit"],
    "print":       ["print", "show", "display", "output", "write-out", "echo"],
    "format":      ["format", "interpolate", "build-a-string", "printf-style"],
    "parse":       ["parse", "scan", "read-from-text", "decode"],
    "parse-integer": ["string-to-int", "parse-an-int", "text-to-number",
                      "convert-a-string-to-a-number"],
    "parse-double": ["string-to-double", "parse-a-float", "text-to-decimal"],
    "convert-to":  ["convert-to", "turn-into", "cast-to", "render-as", "change-into"],
    "exists":      ["exists", "is-there", "is-present", "check-whether-it-exists"],
    "create":      ["create", "make", "make-new", "set-up"],
    "construct":   ["create", "make", "build", "construct", "instantiate", "new"],
    "allocate":    ["allocate", "get-memory-for", "reserve-storage-for"],
    "allocate-memory": ["allocate", "allocate-memory-for", "reserve",
                        "reserve-memory-for", "assign", "assign-memory-for",
                        "get", "set-aside", "claim", "request", "acquire",
                        "obtain", "carve-out", "secure", "provision",
                        "make-room-for", "grab", "book"],
    "allocate-zeroed-memory": ["allocate-cleared-memory-for",
                        "reserve-zeroed-memory-for", "assign-blank-memory-for"],
    "allocate-aligned-memory": ["allocate-aligned-memory-for",
                        "reserve-aligned-memory-for"],
    "resize-allocation": ["resize-the-memory-for", "grow-the-allocation-for",
                        "change-the-reserved-memory-for"],
    "release-memory": ["release-the-memory-for", "free-the-memory-for",
                        "give-back-the-memory-for", "hand-back-memory-for"],
    "copy-bytes":  ["copy-the-bytes-of", "block-copy", "raw-copy"],
    "fill-bytes":  ["fill-the-bytes-of", "zero-out", "blank-the-memory-of"],
    "length-of-text": ["length-of", "how-long-is", "character-count-of"],
    "print-formatted": ["print-formatted", "print-with-formatting",
                        "write-formatted-text"],
    "open-file":   ["open-a-file", "open", "get-a-handle-on-a-file"],
    "terminate-program": ["quit-the-program", "exit-the-program", "stop-the-program"],
    "square-root": ["square-root-of", "root-of"],
    "raise-to-power": ["raise-to-the-power-of", "exponentiate"],
    "deallocate":  ["deallocate", "free", "give-the-memory-back-for"],
    "open":        ["open", "start-using"],
    "close":       ["close", "finish-with", "release"],
    "read":        ["read", "load", "pull-in", "ingest"],
    "write":       ["write", "save", "emit", "put-out"],
    "flush":       ["flush", "force-out", "commit-the-buffer-of"],
    "rename":      ["rename", "move", "change-the-name-of"],
    "hash":        ["hash", "digest", "get-a-hash-of"],
    "invoke":      ["invoke", "call", "run"],
    "visit":       ["visit", "dispatch-on", "match-on"],
    "distance":    ["distance-between", "how-far-apart", "gap-between"],
    "advance":     ["advance", "step-forward", "move-ahead"],
    "assign":      ["assign-to", "overwrite", "set-the-contents-of"],
    "test":        ["check-whether", "test-whether", "is-it"],
    "equal":       ["are-they-equal", "compare-for-equality", "are-they-the-same"],
    "compare":     ["compare", "which-is-bigger", "order-two"],
    "fill-sequential": ["fill-with-0-1-2-3", "number-the-elements-of",
                        "fill-sequentially"],
    "value":       ["unwrap", "get-the-value-out-of", "the-contained-value-of"],
    "release-ownership": ["release-ownership-of", "hand-off-the-pointer-from",
                          "disown"],
    "raw-pointer": ["raw-pointer-to", "underlying-buffer-of", "c-array-behind"],
}

# Sentence shapes. {v} is a verb synonym, {o} the articled object. The bare
# frame is the colloquial key; the rest are the question modality. This is the
# half that makes "list all X" and "show me all X" both resolve.
PHRASE_FRAMES = [
    ("colloquial", "{v}-{o}"),
    ("question",   "how-do-i-{v}-{o}"),
    ("question",   "how-to-{v}-{o}"),
    ("question",   "whats-the-way-to-{v}-{o}"),
    ("colloquial", "i-want-to-{v}-{o}"),
    ("colloquial", "i-need-to-{v}-{o}"),
]

# Enumeration phrasings, added for actions that walk or measure a collection --
# the "list all X" / "show me all X" family named explicitly in the design.
ENUM_FRAMES = [
    "list-all-{o}", "show-me-all-{o}", "get-all-{o}", "display-all-{o}",
    "enumerate-{o}", "print-all-{o}", "walk-all-{o}", "iterate-all-{o}",
    "go-through-all-{o}", "show-every-{o}",
]
ENUM_ACTIONS = {"for-each", "size", "first-position", "past-the-end-position",
                "count", "first-element", "last-element", "map", "find"}

# Request wrappers stripped from a QUERY before matching, so the infinite tail
# of phrasings collapses onto the stored keys instead of needing its own key.
QUERY_FRAMES = [
    "show me how to", "show me all", "show me the", "show me",
    "list all of the", "list all the", "list all", "list every", "list the",
    "give me all", "give me the", "give me",
    "whats the best way to", "what is the best way to",
    "whats the way to", "what is the way to", "whats the",  "what is the",
    "how do i", "how do you", "how to", "how can i", "way to",
    "i want to", "i need to", "i would like to", "i am trying to",
    "is there a way to", "best way to", "need to", "want to",
    "get all of the", "get all the", "get all",
    "display all", "print all", "enumerate all", "iterate over all",
]


# ============================================================================
# GENERIC OBJECTS -- the bridge to a language-neutral intent key.
# "vector" is a C++ word; "sequence" is the idea. Python's list, Rust's Vec and
# C++'s vector all bind to intents phrased in the right-hand column. Without
# this, Photon would inherit C++ vocabulary rather than C++ semantics.
# ============================================================================
GENERIC_OBJECT = {
    "vector": "sequence", "dynamic-array": "sequence", "array": "sequence",
    "fixed-array": "sequence", "deque": "sequence", "list": "sequence",
    "linked-list": "sequence", "singly-linked-list": "sequence",
    "forward-list": "sequence", "resizable-array": "sequence",
    "range": "sequence", "collection": "sequence", "span": "sequence",
    "view-over-array": "sequence", "sequence": "sequence",
    "queue": "queue", "fifo": "queue", "stack": "stack", "lifo": "stack",
    "priority-queue": "priority-queue", "heap": "priority-queue",
    "sorted-map": "mapping", "ordered-map": "mapping", "dictionary": "mapping",
    "tree-map": "mapping", "hash-map": "mapping", "hash-table": "mapping",
    "flat-map": "mapping", "sorted-multimap": "multimapping",
    "hash-multimap": "multimapping",
    "sorted-set": "set", "ordered-set": "set", "tree-set": "set",
    "hash-set": "set", "flat-set": "set", "sorted-multiset": "multiset",
    "string": "text", "text": "text", "string-view": "text",
    "borrowed-string": "text",
    "path": "path", "file-path": "path", "filename": "path",
    "unique-pointer": "owned-reference", "owning-pointer": "owned-reference",
    "shared-pointer": "shared-reference", "refcounted-pointer": "shared-reference",
    "weak-pointer": "weak-reference", "non-owning-pointer": "weak-reference",
    "optional": "optional", "maybe-value": "optional", "nullable": "optional",
    "variant": "union-value", "tagged-union": "union-value", "sum-type": "union-value",
    "expected": "result", "result": "result", "value-or-error": "result",
    "tuple": "record", "fixed-record": "record", "pair": "record",
    "two-tuple": "record",
    "thread": "thread", "joining-thread": "thread", "current-thread": "thread",
    "mutex": "lock", "lock": "lock", "shared-mutex": "rw-lock", "rw-lock": "rw-lock",
    "condition-variable": "signal", "wait-signal": "signal",
    "future": "async-result", "async-result": "async-result", "promise": "promise",
    "atomic": "atomic", "lock-free-value": "atomic",
    "duration": "duration", "time-span": "duration",
    "time-point": "instant", "timestamp": "instant", "time": "instant",
    "output-stream": "output-stream", "input-stream": "input-stream",
    "output-file": "output-file", "input-file": "input-file",
    "string-stream": "text-stream", "stream": "stream",
    "regex": "pattern", "regular-expression": "pattern",
    "bitset": "bit-flags", "bit-flags": "bit-flags",
    "function-object": "callable", "callable": "callable",
    "std-function": "callable", "any": "dynamic-value",
    "type-erased-value": "dynamic-value",
    "value": "value", "thing": "value", "self": "self",
}


# ============================================================================
# CONCEPT MAP -- identifier -> MEANING, for names that hide their intent.
#
# The semantics must describe what the operation DOES, not how C spells it.
# "malloc" is not an intent; "allocate memory for" is. Anything here overrides
# name tokenisation entirely, which is what keeps the intent layer portable:
# C's malloc, C++'s operator new and Rust's alloc all reach 'allocate-memory'.
# Keyed on the bare identifier. Same shape as VERBS.
# ============================================================================
CONCEPT_MAP = {
 # --- POSIX: the C API Unix is built on ---------------------------------------
 # C headers carry no doc comments, so these identifiers are as opaque as
 # malloc: nothing in the name "mmap" says "map a file into memory".
 "open":    _v("open-file-descriptor", ["open-a-file", "get-a-file-descriptor",
              "open-a-file-for-reading-or-writing"],
              "Open a file and return a file descriptor.", obj="file"),
 "creat":   _v("create-file", ["create-a-new-file", "make-a-file"],
              "Create a file and open it for writing.", obj="file"),
 "close":   _v("close-file-descriptor", ["close-a-file-descriptor",
              "release-a-file-descriptor"],
              "Close a file descriptor.", obj="file"),
 "lseek":   _v("seek-file", ["move-the-file-offset", "jump-to-a-file-position"],
              "Reposition the offset of an open file.", obj="file"),
 "mmap":    _v("map-memory", ["map-a-file-into-memory",
              "memory-map-a-file", "share-memory-between-processes"],
              "Map a file or device into the address space.", obj="memory"),
 "munmap":  _v("unmap-memory", ["unmap-a-mapped-region"],
              "Remove a memory mapping.", obj="memory"),
 "fork":    _v("fork-process", ["create-a-child-process", "duplicate-this-process",
              "spawn-a-process"],
              "Create a child process duplicating the caller.", obj="process"),
 "execve":  _v("replace-process-image", ["run-another-program",
              "replace-this-program", "exec-a-binary"],
              "Replace the current process image with a new program.",
              obj="process"),
 "waitpid": _v("wait-for-child", ["wait-for-a-child-process",
              "reap-a-child-process", "collect-a-child-exit-status"],
              "Wait for a child process to change state.", obj="process"),
 "pipe":    _v("create-pipe", ["make-a-pipe-between-processes",
              "connect-two-processes"],
              "Create a unidirectional inter-process channel.", obj="channel"),
 "dup2":    _v("duplicate-file-descriptor", ["redirect-a-file-descriptor",
              "point-stdout-somewhere-else"],
              "Duplicate a file descriptor onto a chosen number.", obj="file"),
 "socket":  _v("create-socket", ["create-a-network-socket", "open-a-network-endpoint"],
              "Create a communication endpoint.", obj="socket"),
 "connect": _v("connect-socket", ["connect-to-a-server", "dial-a-remote-host"],
              "Connect a socket to a remote address.", obj="socket"),
 "listen":  _v("listen-socket", ["accept-incoming-connections",
              "start-listening-for-clients"],
              "Mark a socket as accepting connections.", obj="socket"),
 "accept":  _v("accept-connection", ["accept-a-client-connection",
              "take-the-next-incoming-connection"],
              "Accept a connection on a listening socket.", obj="socket"),
 "select":  _v("wait-for-readiness", ["wait-until-a-descriptor-is-ready",
              "multiplex-file-descriptors"],
              "Wait until any of a set of descriptors is ready.", obj="file"),
 "poll":    _v("poll-readiness", ["wait-for-io-readiness", "poll-descriptors"],
              "Wait for events on a set of file descriptors.", obj="file"),
 "epoll_wait": _v("wait-for-events-scalably",
              ["wait-for-many-descriptors-efficiently", "scalable-io-polling"],
              "Wait for I/O events, scalably, on many descriptors.", obj="file"),
 "stat":    _v("file-metadata", ["get-file-information", "check-a-files-size-or-type",
              "get-file-metadata"],
              "Retrieve information about a file.", obj="file"),
 "unlink":  _v("delete-file", ["delete-a-file", "remove-a-file-from-disk"],
              "Remove a name from the filesystem.", obj="file"),
 "opendir": _v("open-directory", ["open-a-directory-for-reading",
              "start-listing-a-directory"],
              "Open a directory stream.", obj="directory"),
 "readdir": _v("read-directory-entry", ["list-directory-contents",
              "iterate-a-directory", "read-the-next-directory-entry"],
              "Read the next entry from a directory stream.", obj="directory"),
 "pthread_create": _v("start-thread", ["start-a-thread", "run-work-on-another-thread",
              "spawn-a-thread"],
              "Create a new thread.", obj="thread"),
 "pthread_join": _v("join-thread", ["wait-for-a-thread-to-finish"],
              "Wait for a thread to terminate.", obj="thread"),
 "pthread_mutex_lock": _v("lock-mutex", ["take-a-lock", "enter-a-critical-section"],
              "Lock a mutex, blocking until it is available.", obj="lock"),

 # --- memory -----------------------------------------------------------------
 "malloc":  _v("allocate-memory", ["allocate-{o}", "get-a-block-of-{o}",
                "reserve-raw-{o}", "grab-some-{o}"],
               "Allocate an uninitialised block of memory.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "calloc":  _v("allocate-zeroed-memory", ["allocate-cleared-memory",
                "get-zeroed-memory", "allocate-and-zero"],
               "Allocate memory and zero every byte of it.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "realloc": _v("resize-allocation", ["grow-an-allocation", "resize-a-memory-block",
                "change-the-size-of-an-allocation"],
               "Resize an existing allocation, moving it if necessary.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "free":    _v("release-memory", ["give-the-memory-back", "release-an-allocation",
                "hand-memory-back-to-the-system"],
               "Release memory obtained from an allocator.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "memcpy":  _v("copy-bytes", ["copy-raw-bytes", "block-copy-memory",
                "copy-a-buffer"], "Copy a block of bytes between non-overlapping buffers.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "memmove": _v("move-bytes", ["copy-bytes-that-may-overlap",
                "safely-shift-a-buffer"], "Copy bytes between possibly overlapping buffers.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "memset":  _v("fill-bytes", ["set-every-byte", "zero-a-buffer", "blank-memory"],
               "Set every byte of a block to one value.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "memcmp":  _v("compare-bytes", ["compare-two-buffers", "byte-wise-compare"],
               "Compare two blocks of memory byte by byte.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 "addressof": _v("address-of", ["get-the-real-address-of", "true-address-of"],
               "Get an object's address even if operator& is overloaded."),
 "aligned_alloc": _v("allocate-aligned-memory", ["get-aligned-memory",
                "allocate-on-a-boundary"], "Allocate memory on a given alignment boundary.",
               obj="memory", alts=["storage", "space", "a-buffer", "heap-memory", "raw-memory",
                      "a-block-of-bytes", "a-region", "working-memory"]),
 # --- text -------------------------------------------------------------------
 "strlen":  _v("length-of-text", ["how-long-is-a-string", "length-of-a-c-string",
                "count-the-characters"], "Length of a null-terminated string."),
 "strcmp":  _v("compare-text", ["compare-two-strings", "are-two-strings-equal"],
               "Compare two null-terminated strings."),
 "strcpy":  _v("copy-text", ["copy-a-string", "duplicate-a-c-string"],
               "Copy a null-terminated string."),
 "strcat":  _v("concatenate-text", ["join-two-strings", "append-one-string-to-another"],
               "Append one null-terminated string to another."),
 "strstr":  _v("find-substring", ["find-text-inside-text", "search-for-a-substring"],
               "Find the first occurrence of a substring."),
 "strtok":  _v("split-text", ["split-a-string-on-delimiters", "tokenise-text"],
               "Split a string into tokens on delimiter characters."),
 "atoi":    _v("parse-integer", ["turn-text-into-a-number", "string-to-int"],
               "Parse an integer from text (no error reporting)."),
 "atof":    _v("parse-double", ["turn-text-into-a-decimal", "string-to-double"],
               "Parse a floating-point value from text."),
 "toupper": _v("change-case", ["make-it-uppercase", "capitalise-a-character"],
               "Convert a character to upper case."),
 "tolower": _v("change-case-lower", ["make-it-lowercase"],
               "Convert a character to lower case."),
 "isalpha": _v("classify-character", ["is-this-a-letter", "check-a-character-class"],
               "Report whether a character is a letter."),
 "isdigit": _v("classify-digit", ["is-this-a-number-character", "is-it-a-digit"],
               "Report whether a character is a decimal digit."),
 # --- io ---------------------------------------------------------------------
 "printf":  _v("print-formatted", ["print-with-formatting", "write-formatted-text",
                "printf-style-output"], "Write formatted text to standard output."),
 "sprintf": _v("format-into-buffer", ["build-a-string-with-formatting",
                "format-into-a-char-array"], "Write formatted text into a buffer."),
 "snprintf": _v("format-into-buffer-bounded", ["format-safely-into-a-buffer"],
               "Write formatted text into a buffer with a size limit."),
 "scanf":   _v("read-formatted", ["read-values-from-input", "parse-standard-input"],
               "Read formatted values from standard input."),
 "puts":    _v("print-line", ["print-a-line-of-text", "write-a-string-and-newline"],
               "Write a string followed by a newline."),
 "fopen":   _v("open-file", ["open-a-file-by-name", "get-a-file-handle"],
               "Open a file and return a stream handle."),
 "fclose":  _v("close-file", ["close-a-file-handle", "finish-with-a-file"],
               "Close an open file stream."),
 "fread":   _v("read-bytes", ["read-raw-bytes-from-a-file", "load-binary-data"],
               "Read raw bytes from a stream."),
 "fwrite":  _v("write-bytes", ["write-raw-bytes-to-a-file", "save-binary-data"],
               "Write raw bytes to a stream."),
 "getline": _v("read-line", ["read-one-line-of-input", "get-a-line-of-text"],
               "Read one line of text from a stream."),
 # --- math -------------------------------------------------------------------
 "sqrt":    _v("square-root", ["square-root-of-a-number", "take-the-root"],
               "Square root."),
 "pow":     _v("raise-to-power", ["raise-a-number-to-a-power", "exponentiate"],
               "Raise a value to a power."),
 "fmod":    _v("floating-remainder", ["remainder-of-a-division-of-decimals"],
               "Floating-point remainder of a division."),
 "fabs":    _v("absolute-value", ["drop-the-sign-of-a-decimal", "magnitude"],
               "Absolute value of a floating-point number."),
 "ceil":    _v("round-up", ["round-a-number-up", "next-whole-number-up"], "Round up."),
 "floor":   _v("round-down", ["round-a-number-down", "next-whole-number-down"],
               "Round down."),
 "round":   _v("round-nearest", ["round-to-the-nearest-whole-number"],
               "Round to the nearest integer."),
 "lerp":    _v("interpolate", ["blend-two-values", "linear-interpolation-between"],
               "Linearly interpolate between two values."),
 "gcd":     _v("greatest-common-divisor", ["largest-shared-factor",
                "highest-common-factor"], "Greatest common divisor."),
 "lcm":     _v("least-common-multiple", ["smallest-shared-multiple"],
               "Least common multiple."),
 "rand":    _v("random-number", ["get-a-random-number", "roll-a-random-value"],
               "Produce a pseudo-random number (prefer <random>)."),
 "srand":   _v("seed-random", ["set-the-random-seed", "seed-the-generator"],
               "Seed the legacy pseudo-random generator."),
 "popcount": _v("count-set-bits", ["how-many-bits-are-set", "hamming-weight"],
               "Count the set bits in a value."),
 "byteswap": _v("swap-byte-order", ["change-endianness", "flip-byte-order"],
               "Reverse the byte order of a value."),
 "bit_cast": _v("reinterpret-bits-safely", ["type-pun-without-undefined-behaviour",
                "reinterpret-the-bit-pattern"],
               "Reinterpret a value's bits as another type, defined behaviour."),
 # --- process / environment --------------------------------------------------
 "exit":    _v("terminate-program", ["quit-the-program", "end-the-process"],
               "Terminate the program, running static destructors."),
 "abort":   _v("terminate-abnormally", ["crash-out-immediately", "hard-stop"],
               "Terminate abnormally without cleanup."),
 "getenv":  _v("read-environment-variable", ["read-an-env-var",
                "get-an-environment-setting"], "Read an environment variable."),
 "system":  _v("run-shell-command", ["shell-out", "run-an-external-command"],
               "Run a command through the system shell."),
 "assert":  _v("check-invariant", ["assert-an-assumption", "crash-if-this-is-false"],
               "Abort if a condition is false (disabled by NDEBUG)."),
 "offsetof": _v("field-offset", ["byte-offset-of-a-member", "where-a-field-sits"],
               "Byte offset of a member within a struct."),
 # --- time -------------------------------------------------------------------
 "clock":   _v("processor-time", ["how-much-cpu-time-was-used"],
               "Processor time consumed by the program."),
 "difftime": _v("time-difference", ["how-long-between-two-times", "elapsed-time"],
               "Difference between two calendar times, in seconds."),
 "strftime": _v("format-time", ["format-a-date-as-text", "render-a-timestamp"],
               "Format a calendar time as text."),
 # --- misc C++ ---------------------------------------------------------------
 "qsort":   _v("sort", ["sort-with-a-comparison-callback"],
               "Sort an array using a comparison callback (prefer std::sort)."),
 "bsearch": _v("binary-search", ["fast-lookup-in-a-sorted-array"],
               "Binary search an array using a comparison callback."),
 "declval": _v("unevaluated-value", ["pretend-to-have-a-value-of-this-type"],
               "Produce a value of a type for use in unevaluated contexts only."),
 "forward": _v("perfect-forward", ["pass-arguments-through-unchanged",
                "preserve-value-category"], "Forward an argument preserving its value category."),
 "launder": _v("refresh-pointer", ["revalidate-a-pointer-after-placement-new"],
               "Obtain a usable pointer to an object placed in existing storage."),
 "exchange": _v("swap-and-return-old", ["set-a-new-value-and-get-the-old-one"],
               "Replace a value and return the previous one."),
 "tie":     _v("bind-references", ["unpack-into-existing-variables",
                "structured-assign"], "Make a tuple of references, for unpacking."),
 "invoke":  _v("invoke", ["just-call-it", "call-any-callable-uniformly"],
               "Invoke any callable, including member pointers, uniformly."),
}


# Mass nouns take no article: "allocate memory", never "allocate a memory".
MASS_NOUNS = {
    "memory", "storage", "space", "heap-memory", "raw-memory", "working-memory",
    "text", "data", "io", "time", "input", "output", "state", "capacity",
    "parallelism", "ownership", "self", "value",
}


# Real namespaces. Anything else in the qualifier position is a CLASS, which is
# how a templated member function (which clang reports as 'function_template',
# not 'member_function') is told apart from a free function.
KNOWN_NAMESPACES = {
    "", "std", "std::ranges", "std::views", "std::chrono", "std::filesystem",
    "std::this_thread", "std::pmr", "std::execution", "std::literals",
    "std::numbers", "std::regex_constants", "std::rel_ops",
    "std::placeholders", "std::literals::chrono_literals",
    "std::literals::string_literals", "std::literals::string_view_literals",
    "std::literals::complex_literals", "std::chrono::literals",
    "std::experimental", "std::linalg", "std::inplace_vector",
}


# ============================================================================
# CANONICAL TERMS
# ----------------------------------------------------------------------------
# Aliases are broad on the way in. The canonical term is precise on the way
# out: imperative, specific, and naming the distinction that makes this intent
# different from its neighbours. `{o}` is the GENERIC object, so the term reads
# the same whatever language is bound to it.
# ============================================================================

# Appended to the base term, one clause per qualifier on the intent. This is
# what keeps 'sort' and 'sort with a comparator' from collapsing into one
# indistinguishable phrase.
QUALIFIER_TERMS = {
    "with-comparator":    "using a caller-supplied comparator",
    "matching-predicate": "selecting elements that satisfy a predicate",
    "parallel":           "under an execution policy, permitting parallel execution",
    "with-projection":    "comparing a projection of each element",
    "with-allocator":     "using a caller-supplied allocator",
    "n-elements":         "for a caller-specified count",
    "into-destination":   "writing the result to a separate destination",
    "with-deleter":       "using a caller-supplied deleter",
    "with-flags":         "with caller-supplied flags",
    "with-callable":      "combining elements with a caller-supplied operation",
    "on-heap":            "maintaining the heap invariant",
    "at-end":             "at the end",
    "at-start":           "at the beginning",
    "in-place":           "in place, without allocating",
    "const":              "without modifying the object",
    "move":               "taking ownership of the argument",
    "copy":               "copying the argument",
}

# Explicit terms where the summary template is not phrased as an imperative,
# or where precision demands wording the summary does not carry.
DECLARED_TERMS = {
    "sequence.push.at-end":        "append an element to the end of a sequence",
    "sequence.pop.at-end":         "remove the last element of a sequence",
    "sequence.construct-in-place.at-end":
        "construct an element in place at the end of a sequence",
    "sequence.checked-element-access":
        "access an element by index with bounds checking",
    "sequence.reserve-capacity":
        "reserve capacity without changing the number of elements",
    "sequence.shrink-to-fit":      "release capacity not currently in use",
    "sequence.clear":              "remove every element, leaving the container empty",
    "sequence.size":               "report the number of elements",
    "sequence.is-empty":           "report whether the container holds no elements",
    "sequence.dedupe":             "remove consecutive duplicate elements",
    "sequence.find":               "find the first element equal to a value",
    "sequence.sort":               "sort a sequence into ascending order",
    "sequence.reverse":            "reverse the order of the elements",
    "sequence.binary-search":      "test whether a value is present in a sorted sequence",
    "sequence.lower-bound":        "find the first position not ordered before a value",
    "sequence.upper-bound":        "find the first position ordered after a value",
    "memory.allocate-memory":      "allocate a block of uninitialised memory",
    "memory.allocate-zeroed-memory": "allocate a block of memory with every byte zeroed",
    "memory.release-memory":       "release a previously allocated block of memory",
    "memory.resize-allocation":    "resize a previously allocated block of memory",
    "memory.copy-bytes":           "copy bytes between non-overlapping buffers",
    "memory.move-bytes":           "copy bytes between possibly overlapping buffers",
    "memory.fill-bytes":           "set every byte of a block to one value",
    "text.length-of-text":         "report the number of characters in a string",
    "text.find-substring":         "find the first occurrence of a substring",
    "mapping.find":                "find the element stored under a key",
    "mapping.contains":            "report whether a key is present",
    "thread.join":                 "block until the thread finishes",
    "thread.detach":               "let the thread run independently of its handle",
    "path.exists":                 "report whether the path exists on the filesystem",
    "path.copy.file":              "copy a file to a new location",
    "path.create.directory":       "create a directory",
}


# ============================================================================
# PARAMETER DOCUMENTATION
# ----------------------------------------------------------------------------
# How to supply a parameter: what it is, what counts as valid, and why. Keyed
# by port kind; PARAM_OVERRIDES handles the cases where the generic wording
# would be wrong or would omit a real precondition.
#
# Constraints here must be TRUE. An invented rule ("sizes must be multiples of
# 8") is worse than none: it teaches a false fact to exactly the developer who
# came here because they did not know the real one.
# ============================================================================
PROMPTS = {
    "count":      {"prompt": "How many?",
                   "help": "A non-negative count. Passing more than the "
                           "container holds is undefined behaviour.",
                   "input_kind": "number", "example": "0"},
    "position":   {"prompt": "Which index?",
                   "help": "Zero-based. Must be less than the container size.",
                   "input_kind": "number", "example": "0"},
    "value":      {"prompt": "What value?",
                   "help": "Must be comparable with the container's element type.",
                   "input_kind": "expression", "example": "x"},
    "comparator": {"prompt": "How should two elements be ordered?",
                   "help": "Return true when the first argument comes strictly "
                           "before the second. Must be a strict weak ordering: "
                           "never true for equal elements, or the sort is "
                           "undefined behaviour.",
                   "input_kind": "lambda",
                   "example": "[](const auto& a, const auto& b){ return a < b; }"},
    "predicate":  {"prompt": "Which elements should match?",
                   "help": "Return true to select an element. Must not modify "
                           "the element and must give the same answer for the "
                           "same input.",
                   "input_kind": "lambda",
                   "example": "[](const auto& x){ return x > 0; }"},
    "callable":   {"prompt": "What operation should be applied?",
                   "help": "Invoked once per element; its return value is used.",
                   "input_kind": "lambda",
                   "example": "[](const auto& x){ return x; }"},
    "projection": {"prompt": "Which part of each element should be compared?",
                   "help": "Applied to each element before comparing.",
                   "input_kind": "lambda", "example": "&T::field"},
    "policy":     {"prompt": "Run sequentially or in parallel?",
                   "help": "std::execution::seq is ordered and safe. par and "
                           "par_unseq may run concurrently: your callable must "
                           "then be free of data races.",
                   "input_kind": "enum", "example": "std::execution::seq"},
    "allocator":  {"prompt": "Which allocator?",
                   "help": "Defaults to std::allocator. Supply one only if the "
                           "memory must come from elsewhere.",
                   "input_kind": "expression", "example": "std::allocator<T>{}"},
    "path":       {"prompt": "Which file or directory?",
                   "help": "A filesystem path. It is not required to exist "
                           "unless the operation says so.",
                   "input_kind": "path", "example": '"./file.txt"'},
    "stream":     {"prompt": "Which stream?",
                   "help": "An open stream. Writing to a failed stream is "
                           "silently ignored -- check it afterwards.",
                   "input_kind": "expression", "example": "std::cout"},
    "flags":      {"prompt": "Which options?",
                   "help": "Bitwise-or the flags you want.",
                   "input_kind": "enum", "example": "{}"},
    "object":     {"prompt": "Which object?",
                   "help": "The object the call acts on.",
                   "input_kind": "identifier", "example": "v"},
    "sequence":   {"prompt": "Which range?",
                   "help": "A container or range. Begin and end are derived "
                           "from it.",
                   "input_kind": "inferred", "example": "v"},
    "pack":       {"prompt": "Which arguments?",
                   "help": "Any number of arguments, forwarded to the "
                           "constructor.",
                   "input_kind": "expression", "example": ""},
    "error":      {"prompt": None, "help": "Receives the error code; the "
                   "no-throw form reports failure here instead of throwing.",
                   "input_kind": "produced", "example": None},
    "result":     {"prompt": None, "help": "The value produced by the call.",
                   "input_kind": "produced", "example": None},
}

# Real, function-specific preconditions. Only facts that are actually true.
PARAM_OVERRIDES = {
    ("aligned_alloc", "size"): {
        "prompt": "How many bytes?",
        "help": "Must be an integral MULTIPLE OF alignment, and alignment must "
                "be a power of two supported by the implementation. Violating "
                "either is undefined behaviour.",
        "constraint": "size % alignment == 0",
        "input_kind": "number", "example": "64"},
    ("aligned_alloc", "alignment"): {
        "prompt": "What alignment, in bytes?",
        "help": "A power of two, and a valid alignment for the platform.",
        "constraint": "is_power_of_two(alignment)",
        "input_kind": "number", "example": "32"},
    ("malloc", "size"): {
        "prompt": "How many bytes?",
        "help": "The block is UNINITIALISED -- reading it before writing is "
                "undefined. Returns nullptr on failure, which you must check. "
                "Every successful call needs a matching free().",
        "constraint": "result must be checked for nullptr",
        "input_kind": "number", "example": "sizeof(T) * n"},
    ("calloc", "num"): {
        "prompt": "How many elements?",
        "help": "Total allocated is num * size, zero-filled.",
        "constraint": "num * size must not overflow size_t",
        "input_kind": "number", "example": "n"},
    ("free", "ptr"): {
        "prompt": "Which pointer?",
        "help": "Must have come from malloc/calloc/realloc and not been freed "
                "already. Freeing twice is undefined behaviour; freeing "
                "nullptr is explicitly safe.",
        "constraint": "ptr came from malloc family and is freed exactly once",
        "input_kind": "expression", "example": "p"},
    ("memcpy", "count"): {
        "prompt": "How many bytes?",
        "help": "The two buffers MUST NOT OVERLAP. Use memmove if they might.",
        "constraint": "source and destination do not overlap",
        "input_kind": "number", "example": "n"},
}

# Preconditions attached by port kind, independent of wording.
KIND_CONSTRAINTS = {
    "comparator": "strict weak ordering",
    "position":   "index < size()",
    "count":      "count >= 0",
    "policy":     "callable must be race-free under par / par_unseq",
}


# ============================================================================
# TEACHING HELP
# ----------------------------------------------------------------------------
# Read by someone who may not know what a variable IS. A rule ("must be a
# valid identifier") is not enough on its own; the help says what the thing is
# and why it matters. Constraints validate, help teaches.
# ============================================================================

SLOT_HELP = {
    ("declare_variable", "name"): (
        "The tag you will use to refer to this value everywhere else in the "
        "code. Letters, digits and underscores; it cannot start with a digit "
        "and cannot be a reserved word like `class` or `int`. Names are "
        "case-sensitive, so `total` and `Total` are two different variables."),
    ("declare_variable", "type"): (
        "What kind of value this variable holds. C++ checks types at compile "
        "time, so a variable declared to hold a whole number can never hold "
        "text -- mistakes surface when you build rather than when you run."),
    ("declare_variable", "init"): (
        "The value loaded into the variable at the moment it is created, "
        "before any input or calculation replaces it. If you leave this out "
        "for a built-in type the variable contains whatever was already in "
        "that memory -- reading it before assigning is undefined behaviour, "
        "so supplying a starting value is nearly always the right choice."),
    ("declare_constant", "init"): (
        "The value, fixed at compile time. Because it is known before the "
        "program runs, it costs nothing at run time and can be used where a "
        "constant is required, such as an array size."),
    ("loop_over_range", "binding"): (
        "The name each element takes inside the loop body. `const auto&` "
        "borrows each element without copying it; drop the `const` if you "
        "intend to modify elements; drop the `&` only if you deliberately "
        "want your own copy."),
    ("loop_over_range", "sequence"): (
        "The container to walk through. Every element is visited once, in "
        "order, and you never manage an index yourself -- which removes the "
        "most common source of off-by-one errors."),
    ("define_function", "ret"): (
        "The type of value the function hands back to its caller. Use `void` "
        "if it hands back nothing and exists only for its effect."),
}

# Enumerated choices, each explaining itself.
SLOT_CHOICES = {
    ("declare_variable", "type"): [
        ("int", "whole number",
         "Positive or negative, no fractional part. Holds roughly "
         "-2 to +2 billion. The default choice for counting."),
        ("double", "decimal number",
         "A number with a fractional part, about 15 significant digits. The "
         "default choice for measurements and anything not a whole count."),
        ("float", "smaller decimal number",
         "Like double but half the memory and only about 7 significant "
         "digits. Choose it when you have very many values and precision "
         "matters less."),
        ("bool", "true or false",
         "Holds exactly one of two values. Used for conditions and flags."),
        ("char", "single character",
         "One character or one byte, written in single quotes: 'a'."),
        ("std::string", "text",
         "Text of any length that grows as needed. Needs #include <string>."),
        ("std::vector<int>", "list of values",
         "An ordered, growable list holding many values of the same type. "
         "Needs #include <vector>."),
        ("auto", "let the compiler decide",
         "The type is deduced from the starting value. Convenient, but the "
         "reader can no longer see the type at a glance."),
    ],
    ("declare_constant", "type"): [
        ("int", "whole number", "Positive or negative, no fractional part."),
        ("double", "decimal number", "A number with a fractional part."),
        ("std::string_view", "fixed text",
         "Text that is not copied or modified. Needs #include <string_view>."),
    ],
}


# ============================================================================
# C STANDARD LIBRARY, global namespace.
# ----------------------------------------------------------------------------
# Fixing the extern "C" bug recovered the C library -- and also POSIX, because
# glibc declares both in the same headers. `write`, `index`, `open` and `link`
# are POSIX, not ISO C++, and their names are ordinary English words, so they
# outrank real answers on any query containing them. Anything global and not
# listed here is flagged non-standard and demoted; it stays reachable by its
# exact name.
# ============================================================================
C_STANDARD = set("""
printf fprintf sprintf snprintf vprintf vfprintf vsprintf vsnprintf
scanf fscanf sscanf vscanf vfscanf vsscanf
fopen freopen fclose fflush fread fwrite fseek ftell rewind fgetpos fsetpos
setbuf setvbuf tmpfile tmpnam remove rename perror
getc putc getchar putchar fgetc fputc fgets fputs puts ungetc
feof ferror clearerr
malloc calloc realloc free aligned_alloc
abort exit quick_exit at_quick_exit atexit getenv system
bsearch qsort
abs labs llabs div ldiv lldiv imaxabs imaxdiv
rand srand
atoi atol atoll atof strtol strtoll strtoul strtoull strtof strtod strtold
strtoimax strtoumax
mblen mbtowc wctomb mbstowcs wcstombs mbrlen mbrtowc wcrtomb mbsrtowcs wcsrtombs
memcpy memmove memcmp memchr memset
strcpy strncpy strcat strncat strcmp strncmp strcoll strxfrm
strchr strrchr strspn strcspn strpbrk strstr strtok strlen strerror
wcscpy wcsncpy wcscat wcsncat wcscmp wcsncmp wcslen wcschr wcsrchr wcsstr wcstok
isalnum isalpha isblank iscntrl isdigit isgraph islower isprint ispunct
isspace isupper isxdigit tolower toupper
iswalnum iswalpha iswblank iswcntrl iswdigit iswgraph iswlower iswprint
iswpunct iswspace iswupper iswxdigit towlower towupper
time clock difftime mktime asctime ctime gmtime localtime strftime timespec_get
sqrt cbrt pow exp exp2 expm1 log log2 log10 log1p
sin cos tan asin acos atan atan2 sinh cosh tanh asinh acosh atanh
ceil floor round trunc nearbyint rint lround llround lrint llrint
fabs fmod remainder remquo fma fmax fmin fdim hypot
frexp ldexp modf scalbn scalbln ilogb logb copysign nan nextafter nexttoward
erf erfc tgamma lgamma
isfinite isinf isnan isnormal signbit fpclassify
setjmp longjmp signal raise
va_start va_arg va_end va_copy
assert offsetof
""".split())


# How SPECIALISED a qualifier is, for deciding who wins a contested phrase.
# push_back and push_heap both qualify "push" with exactly one modifier, so a
# count of qualifiers cannot separate them -- but "at the end" is the ordinary
# meaning of pushing onto a container and "maintaining a heap" is not. Lower
# wins the plain phrase.
MOD_RANK = {
    "at-end": 0, "at-start": 0, "in-place": 0, "over-range": 0,
    "matching-predicate": 2, "into-new-range": 2, "n-times": 2,
    "sorted": 3, "unique": 3, "permutation": 4, "as-view": 4,
    "on-heap": 6, "until": 4, "negated": 3,
}
DEFAULT_MOD_RANK = 3


# ============================================================================
# MACROS
# ----------------------------------------------------------------------------
# The C library is largely macros, and a macro is usually a named CONSTANT or a
# marker rather than an operation -- so the verb analysis that works for
# functions produces nonsense for it ("null" is not an action). Well-known ones
# are authored; the rest get a constant-shaped concept and stay reachable by
# name.
# ============================================================================
MACRO_TERMS = {
 "NULL":        ("the null pointer constant",
                 ["a-pointer-to-nothing", "empty-pointer", "no-pointer",
                  "nothing-pointer"]),
 "EOF":         ("the end-of-file marker returned by character input",
                 ["end-of-file", "no-more-input", "input-finished"]),
 "errno":       ("the last error number set by a library call",
                 ["last-error-number", "what-went-wrong", "error-code-of-the-last-call"]),
 "EXIT_SUCCESS":("the exit status meaning the program succeeded",
                 ["exit-status-for-success", "program-worked"]),
 "EXIT_FAILURE":("the exit status meaning the program failed",
                 ["exit-status-for-failure", "program-failed"]),
 "RAND_MAX":    ("the largest value rand can return",
                 ["biggest-random-value", "range-of-rand"]),
 "INT_MAX":     ("the largest value an int can hold",
                 ["biggest-int", "largest-int-value", "int-upper-limit"]),
 "INT_MIN":     ("the smallest value an int can hold",
                 ["smallest-int", "most-negative-int"]),
 "UINT_MAX":    ("the largest value an unsigned int can hold", ["biggest-unsigned-int"]),
 "LONG_MAX":    ("the largest value a long can hold", ["biggest-long"]),
 "LLONG_MAX":   ("the largest value a long long can hold", ["biggest-long-long"]),
 "SIZE_MAX":    ("the largest value a size_t can hold", ["biggest-size-value"]),
 "CHAR_BIT":    ("the number of bits in a byte on this platform",
                 ["bits-per-byte", "how-many-bits-in-a-char"]),
 "INFINITY":    ("positive floating-point infinity", ["infinite-value", "float-infinity"]),
 "NAN":         ("a floating-point not-a-number value",
                 ["not-a-number", "invalid-float-result"]),
 "SEEK_SET":    ("seek relative to the start of the file", ["seek-from-the-beginning"]),
 "SEEK_CUR":    ("seek relative to the current position", ["seek-from-here"]),
 "SEEK_END":    ("seek relative to the end of the file", ["seek-from-the-end"]),
 "stdin":       ("the standard input stream", ["standard-input", "keyboard-input"]),
 "stdout":      ("the standard output stream", ["standard-output", "normal-output"]),
 "stderr":      ("the standard error stream", ["standard-error", "error-output"]),
 "assert":      ("abort if a condition is false, unless NDEBUG is defined",
                 ["check-an-assumption", "crash-if-this-is-false"]),
 "offsetof":    ("the byte offset of a member within a struct",
                 ["byte-offset-of-a-field", "where-a-field-sits-in-a-struct"]),
 "FLT_EPSILON": ("the smallest difference a float can represent near 1.0",
                 ["float-precision-limit", "smallest-float-step"]),
 "DBL_EPSILON": ("the smallest difference a double can represent near 1.0",
                 ["double-precision-limit"]),
 "BUFSIZ":      ("the default stream buffer size", ["default-buffer-size"]),
 "CLOCKS_PER_SEC": ("how many clock ticks make one second", ["clock-ticks-per-second"]),
 "va_start":    ("begin access to a variadic argument list", ["start-reading-varargs"]),
 "va_arg":      ("read the next variadic argument", ["get-the-next-vararg"]),
 "va_end":      ("finish access to a variadic argument list", ["done-reading-varargs"]),
}
