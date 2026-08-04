#!/usr/bin/env python3
"""
scan_unix.py -- command-line tools, their arguments and their flags.

A large share of engineering intent is not a library call: "find files changed
in the last day" is `find . -mtime -1`. Those tools already publish a machine-
readable interface -- `--help` lists every flag with a description -- so no
model reasoning is spent enumerating them either.

Flags map onto the same schema as function parameters: a flag IS a parameter,
with `param_kind` recording whether it takes a value.

SAFETY. This executes binaries, so it is deliberately conservative:
  * only files in a small set of system directories
  * an explicit denylist of destructive, interactive and long-running commands
  * stdin from /dev/null, a hard timeout, output captured and never a tty
Anything that misbehaves is skipped rather than retried.

    scan_unix.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

SEARCH_DIRS = ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]

# Never execute these, even with --help: destructive, interactive, or they
# ignore the flag and do the thing.
DENY = {
    "rm", "rmdir", "dd", "mkfs", "fdisk", "sfdisk", "cfdisk", "parted",
    "shutdown", "reboot", "halt", "poweroff", "init", "telinit", "systemctl",
    "kill", "killall", "pkill", "xkill", "fuser", "chroot", "mount", "umount",
    "swapoff", "swapon", "passwd", "su", "sudo", "login", "sulogin", "nologin",
    "vi", "vim", "nano", "emacs", "less", "more", "top", "htop", "man",
    "python", "python3", "perl", "ruby", "node", "irb", "bash", "sh", "zsh",
    "dash", "csh", "tcsh", "fish", "screen", "tmux", "ssh", "telnet", "ftp",
    "nc", "netcat", "yes", "sleep", "watch", "tail", "cat", "head", "sort",
    "shred", "wipe", "userdel", "groupdel", "deluser", "delgroup", "apt",
    "apt-get", "dpkg", "snap", "reset", "clear", "startx", "X", "Xorg",
    "gdb", "gdbserver", "strace", "ltrace", "chsh", "chfn", "visudo",
    "crontab", "at", "batch", "halt.local", "pivot_root", "kexec",
}

# --version is safer than --help for a first probe on unknown tools, but --help
# is what carries the flags, so we go straight to it for the allowed set.
HELP_FLAGS = ["--help", "-h"]

# -x, --long, --long=VALUE, --long VALUE, -x VALUE
FLAG_RE = re.compile(r"""
    ^\s{1,10}
    (?P<short>-[A-Za-z0-9])?
    (?:,\s*)?
    (?P<long>--[a-zA-Z0-9][\w-]*)?
    (?P<arg>[ =]\[?[A-Z][A-Z_\-]*\]?|[ =]<[^>]+>)?
    \s\s+
    (?P<desc>\S.*)$
""", re.X)


def run_help(path: str) -> str | None:
    for flag in HELP_FLAGS:
        try:
            p = subprocess.run(
                [path, flag],
                stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=4,
                env={**os.environ, "COLUMNS": "200", "LC_ALL": "C",
                     "TERM": "dumb"},
            )
        except (subprocess.TimeoutExpired, OSError,
                UnicodeDecodeError, MemoryError):
            continue
        text = (p.stdout or "") + "\n" + (p.stderr or "")
        if len(text.strip()) > 60 and ("-" in text):
            return text[:200000]
    return None


def parse_flags(text: str) -> list:
    out, seen = [], set()
    for line in text.splitlines():
        if len(line) > 400:
            continue
        m = FLAG_RE.match(line.rstrip())
        if not m:
            continue
        short, long_, arg, desc = (m.group("short"), m.group("long"),
                                   m.group("arg"), m.group("desc"))
        if not (short or long_):
            continue
        name = long_ or short
        if name in seen:
            continue
        seen.add(name)
        takes_value = bool(arg and arg.strip())
        out.append({
            "ordinal": len(out),
            "name": name.lstrip("-"),
            "type": (arg.strip(" =") if takes_value else "flag"),
            "raw_type": None, "canonical_type": None,
            "default_value": None,
            "is_pack": False,
            "optional": 1,
            "param_kind": "option-with-value" if takes_value else "boolean-flag",
            "spelling": " / ".join(x for x in (short, long_) if x),
            "doc": re.sub(r"\s+", " ", desc).strip()[:240],
        })
    return out


def summary_of(text: str, name: str) -> str | None:
    """The one-line description most --help output opens with."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("-"):
            continue
        low = s.lower()
        if low.startswith(("usage:", "usage :", name.lower() + " ")):
            continue
        if len(s) > 15:
            return s[:280]
    return None


def candidates() -> list:
    seen, out = set(), []
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            if entry in DENY or entry in seen or entry.startswith("."):
                continue
            path = os.path.join(d, entry)
            if not (os.path.isfile(path) and os.access(path, os.X_OK)):
                continue
            if os.path.islink(path) and os.path.basename(
                    os.path.realpath(path)) in DENY:
                continue
            seen.add(entry)
            out.append((entry, path))
    return out


def main():
    cmds = candidates()
    print(f"probing {len(cmds)} commands ({len(DENY)} denied)", flush=True)
    out = {}
    for i, (name, path) in enumerate(cmds, 1):
        text = run_help(path)
        if not text:
            continue
        flags = parse_flags(text)
        if not flags:
            continue
        out[f"unix:{name}"] = {
            "usr": f"unix:{name}",
            "kind": "function",
            "name": name,
            "qualified_name": name,
            "namespace": None,
            "display": name,
            "file": path,
            "template_params": [],
            "params": flags,
            "return_type": "exit status",
            "is_template": False, "is_static": False, "is_const": False,
            "is_variadic": True, "is_deprecated": False,
            "brief": summary_of(text, name),
            "signature": f"{name} [options] [arguments]",
            "constexpr_since": None, "is_constexpr": False,
            "is_consteval": False, "is_noexcept": False,
            "is_explicit": False, "is_nodiscard": False,
            "headers": [], "header": None,
            "lang": "unix",
            "impl": "gnu-linux",
            "std_since": None,
            "_line": 0, "_quality": 3,
        }
        if i % 100 == 0 or len(flags) > 40:
            print(f"  [{i}/{len(cmds)}] {name}: {len(flags)} flags "
                  f"(total {len(out)})", flush=True)
    path = DATA / "raw_decls_unix.jsonl"
    with open(path, "w") as fh:
        for rec in out.values():
            fh.write(json.dumps(rec) + "\n")
    total_flags = sum(len(r["params"]) for r in out.values())
    print(f"\nwrote {len(out)} commands, {total_flags} flags -> {path}")


if __name__ == "__main__":
    main()
