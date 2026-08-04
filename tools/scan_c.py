#!/usr/bin/env python3
"""
scan_c.py -- the C standard library, parsed AS C.

Not a re-tag of what came in through <cstdlib>. Those declarations arrived via
C++ headers, in namespace-less form but compiled as C++; this parses the real C
headers with -x c at each -std= level, so `std_since` means C89/C99/C11/C17/C23
rather than a C++ standard.

Output: data/raw_decls_c.jsonl, the same shape build_base.py already consumes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import clang.cindex as ci

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import scan_cpp as S   # reuse the walker, the de-uglifier and the record shape

for cand in ("/usr/lib/x86_64-linux-gnu/libclang-18.so.1",
             "/usr/lib/llvm-18/lib/libclang.so.1"):
    if os.path.exists(cand):
        ci.Config.set_library_file(cand)
        break

# ISO C: the standard library every conforming implementation has.
ISO_HEADERS = """
assert.h complex.h ctype.h errno.h fenv.h float.h inttypes.h iso646.h
limits.h locale.h math.h setjmp.h signal.h stdalign.h stdarg.h stdatomic.h
stdbit.h stdbool.h stdckdint.h stddef.h stdint.h stdio.h stdlib.h stdnoreturn.h
string.h tgmath.h threads.h time.h uchar.h wchar.h wctype.h
""".split()

# POSIX: the C API that Unix is actually built on. open(), socket(), fork()
# and pthread_create() are C functions with headers -- a different layer from
# the shell commands in scan_unix.py, which are argv and flags. Without these
# `stat` resolves to the command-line tool and the syscall is simply absent.
POSIX_HEADERS = """
unistd.h fcntl.h dirent.h pthread.h semaphore.h sched.h termios.h
sys/stat.h sys/types.h sys/mman.h sys/wait.h sys/socket.h sys/select.h
sys/time.h sys/times.h sys/resource.h sys/uio.h sys/un.h sys/ioctl.h
sys/file.h sys/utsname.h sys/statvfs.h sys/epoll.h sys/inotify.h
sys/eventfd.h sys/signalfd.h sys/timerfd.h sys/random.h sys/sysinfo.h
netinet/in.h netinet/tcp.h arpa/inet.h netdb.h ifaddrs.h poll.h
grp.h pwd.h glob.h fnmatch.h regex.h dlfcn.h syslog.h utime.h
libgen.h ftw.h iconv.h langinfo.h monetary.h nl_types.h spawn.h
strings.h sys/param.h aio.h mqueue.h
""".split()

C_HEADERS = ISO_HEADERS + POSIX_HEADERS

STD_LEVELS = [("c89", "C89"), ("c99", "C99"), ("c11", "C11"),
              ("c17", "C17"), ("c2x", "C23")]


def parse(index, src, std, gnu=True):
    """gnu=True exposes the POSIX surface; gnu=False keeps the compiler strict.

    The version sweep must run strict: _GNU_SOURCE makes C99 declarations
    visible even at -std=c89, which collapses every ISO function to "C89".
    """
    args = ["-x", "c", f"-std={std}", "-fsyntax-only", "-Wno-everything"]
    if gnu:
        args += ["-D_GNU_SOURCE=1", "-D_POSIX_C_SOURCE=200809L",
                 "-D_DEFAULT_SOURCE=1"]
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        return index.parse(path, args=args,
                           options=ci.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
                           | ci.TranslationUnit.PARSE_INCOMPLETE
                           | ci.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    finally:
        os.unlink(path)


def src_for(headers):
    return "\n".join(f"#if __has_include(<{h}>)\n#include <{h}>\n#endif"
                     for h in headers) + "\n"


def main():
    index = ci.Index.create()
    all_decls, header_sets = {}, {}

    print("pass A: per-header attribution (-std=c17)", flush=True)
    for i, h in enumerate(C_HEADERS, 1):
        tu = parse(index, src_for([h]), "c17")
        found = {}
        S.walk(tu.cursor, found)
        header_sets[f"<{h}>"] = set(found)
        for usr, rec in found.items():
            all_decls.setdefault(usr, rec)
        print(f"  [{i:2}/{len(C_HEADERS)}] <{h}>: {len(found)} "
              f"(total {len(all_decls)})", flush=True)

    print("pass B: -std sweep for std_since", flush=True)
    since = {}
    for std, label in STD_LEVELS:
        # ISO headers only, and strictly: this pass exists to date the ISO
        # library, and POSIX has no C standard version to report.
        tu = parse(index, src_for(ISO_HEADERS), std, gnu=False)
        found = {}
        S.walk(tu.cursor, found)
        new = 0
        for usr in found:
            if usr not in since:
                since[usr] = label
                new += 1
        print(f"  {std}: {len(found)} visible, {new} first-seen", flush=True)

    providers = {}
    for h, us in header_sets.items():
        for usr in us:
            providers.setdefault(usr, []).append(h)
    iso = {f"<{h}>" for h in ISO_HEADERS}
    for usr, rec in all_decls.items():
        # std_since is derived from which -std= level first sees a declaration.
        # That is only meaningful for ISO C: POSIX headers are exposed by
        # _GNU_SOURCE at every level, so they appeared as "C89", which is
        # false and would be read as a portability guarantee.
        # providers[] is populated above; rec["headers"] is not assigned until
        # a few lines below, so reading it here saw an empty list and marked
        # every declaration POSIX -- including malloc.
        hdrs = providers.get(usr, [])
        rec["std_since"] = (since.get(usr)
                            if any(h in iso for h in hdrs) else "POSIX")
        hs = sorted(providers.get(usr, []),
                    key=lambda h: (len(header_sets[h]), h))
        rec["headers"] = hs
        rec["header"] = hs[0] if hs else None
        rec["lang"] = "c"

    out = ROOT / "data" / "raw_decls_c.jsonl"
    with open(out, "w") as f:
        for rec in all_decls.values():
            f.write(json.dumps(rec) + "\n")
    print(f"\nwrote {len(all_decls)} C declarations -> {out}")


if __name__ == "__main__":
    main()
