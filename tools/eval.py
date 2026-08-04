#!/usr/bin/env python3
"""
eval.py -- measure whether a lexicon edit helped or hurt.

A fixed set of intents phrased the way a person would phrase them, each with
the qualified name that should come back. Reports top-1 and top-5 accuracy so
changes to lexicon.py can be judged instead of guessed at.

Add cases freely -- a lookup that surprised you is exactly what belongs here.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import query as Q

CASES: list[tuple[str, str]] = [
    # --- plain-English intents ---------------------------------------------
    ("sort a vector", "std::sort"),
    ("put a range in order", "std::sort"),
    ("sort but keep equal elements in their original order", "std::stable_sort"),
    ("remove duplicates from a range", "std::unique"),
    ("stick something on the end of a vector", "std::vector::push_back"),
    ("build an item directly inside a vector without copying",
     "std::vector::emplace_back"),
    ("how many elements are in a vector", "std::vector::size"),
    ("is this container empty", "std::vector::empty"),
    ("reverse the order of a range", "std::reverse"),
    ("randomly shuffle a range", "std::shuffle"),
    ("sum up all the values in a range", "std::accumulate"),
    ("apply a function to each element and write the results out",
     "std::transform"),
    ("do something to every element", "std::for_each"),
    ("check whether every element matches", "std::all_of"),
    ("fast lookup in a sorted range", "std::binary_search"),
    ("where would I insert this to keep the range sorted", "std::lower_bound"),
    ("find the kth smallest element", "std::nth_element"),
    ("fill a range with 0 1 2 3", "std::iota"),
    ("limit a value to a range", "std::clamp"),
    ("swap two values", "std::swap"),

    # --- containers ---------------------------------------------------------
    ("preallocate space in a vector so it stops reallocating",
     "std::vector::reserve"),
    ("release the spare memory of a vector", "std::vector::shrink_to_fit"),
    ("index into a vector safely with bounds checking", "std::vector::at"),
    ("does this map contain the key", "std::unordered_map::contains"),
    ("look something up in a hash map", "std::unordered_map::find"),
    ("remove everything from a container", "std::vector::clear"),

    # --- strings and text ---------------------------------------------------
    ("take a slice of a string", "std::basic_string::substr"),
    ("does this string start with a prefix", "std::basic_string::starts_with"),
    ("turn text into a number", "std::stoi"),
    ("interpolate values into a string", "std::format"),

    # --- filesystem ---------------------------------------------------------
    ("does this file exist", "std::filesystem::exists"),
    ("copy a file", "std::filesystem::copy_file"),
    ("make a new directory", "std::filesystem::create_directory"),
    ("how big is this file", "std::filesystem::file_size"),
    ("rename or move a file", "std::filesystem::rename"),

    # --- concurrency --------------------------------------------------------
    ("wait for a thread to finish", "std::thread::join"),
    ("let a thread run free in the background", "std::thread::detach"),
    ("pause this thread for a while", "std::this_thread::sleep_for"),
    ("run a callable in the background and get a future", "std::async"),

    # --- memory -------------------------------------------------------------
    ("create a uniquely owned pointer", "std::make_unique"),
    ("create a reference counted pointer", "std::make_shared"),

    # --- language constructs (curated) --------------------------------------
    ("compute this at compile time", "constexpr"),
    ("prevent implicit conversion", "explicit"),
    ("make my class comparable", "operator<=>"),
    ("give each thread its own copy of a variable", "thread_local"),
    ("warn if someone ignores the return value", "nodiscard"),
    ("stop a header being included twice", "pragma"),
    ("write an inline function to pass to an algorithm", "lambda"),
    ("take any number of arguments", "parameter-pack"),
    ("check a condition at compile time", "static_assert"),
    ("safely downcast a pointer", "dynamic_cast"),
]


# Phrasing-equivalence: the same intent said several ways must land on the SAME
# entry. This is the metric that matters for "list all X" == "show me all X";
# top-1 accuracy alone does not capture it.
PARAPHRASE_SETS: list[list[str]] = [
    ["sort a vector", "order a vector", "arrange a vector",
     "put a vector in order", "how do I sort a vector",
     "whats the best way to sort a vector", "i need to sort a vector"],
    ["clear a vector", "empty a vector", "wipe a vector",
     "remove everything from a vector", "how do I empty a vector",
     "i want to clear a vector"],
    ["how many elements are in a vector", "size of a vector",
     "length of a vector", "how big is a vector", "count of a vector"],
    ["add to the end of a vector", "append to a vector",
     "push onto a vector", "stick something on the end of a vector",
     "how do I append to a vector"],
    ["find something in a hash map", "look up a hash map",
     "search a hash map", "locate an item in a hash map"],
    ["loop over a vector", "iterate a vector", "walk a vector",
     "go through a vector", "list all vectors", "show me all vectors"],
    ["wait for a thread to finish", "block until the thread is done",
     "join a thread", "how do I wait for a thread to finish"],
    ["remove duplicates from a range", "dedupe a range",
     "deduplicate a range", "collapse repeats in a range"],
    ["does this file exist", "is the file there", "check whether it exists a path",
     "how do I check if a file exists"],
    ["reverse a range", "flip a range", "put a range backwards",
     "invert a range"],
]


def paraphrase_report(con):
    print("\n" + "=" * 62)
    print("PHRASING EQUIVALENCE -- do variants of one intent agree?\n")
    agree_total = variants_total = 0
    for group in PARAPHRASE_SETS:
        tops = []
        for phrasing in group:
            recs = Q.search(con, phrasing, limit=1)
            tops.append(recs[0]["qualified_name"] if recs else "-")
        winner = max(set(tops), key=tops.count)
        agree = tops.count(winner)
        agree_total += agree
        variants_total += len(tops)
        flag = "ok " if agree == len(tops) else "SPLIT"
        print(f"  {flag} {agree}/{len(tops)} -> {winner}")
        if agree != len(tops):
            for phrasing, got in zip(group, tops):
                if got != winner:
                    print(f"          {phrasing!r} -> {got}")
    print(f"\nagreement  {agree_total}/{variants_total} "
          f"({100*agree_total/variants_total:.0f}%)")


def main():
    con = Q.open_db("en")
    top1 = top5 = 0
    misses = []
    for intent, expect in CASES:
        recs = Q.search(con, intent, limit=5)
        names = [r["qualified_name"] for r in recs]
        if names[:1] == [expect]:
            top1 += 1
            top5 += 1
        elif expect in names:
            top5 += 1
            misses.append((intent, expect, names[0], names.index(expect) + 1))
        else:
            misses.append((intent, expect, names[0] if names else "-", 0))

    n = len(CASES)
    for intent, expect, got, at in misses:
        where = f"rank {at}" if at else "ABSENT"
        print(f"  {where:>7}  {intent!r}\n           want {expect}  got {got}")
    print(f"\ntop-1  {top1}/{n}  ({100*top1/n:.0f}%)")
    print(f"top-5  {top5}/{n}  ({100*top5/n:.0f}%)")
    paraphrase_report(con)
    return 0


if __name__ == "__main__":
    sys.exit(main())
