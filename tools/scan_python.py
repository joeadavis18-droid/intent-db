#!/usr/bin/env python3
"""
scan_python.py -- the Python standard library, by runtime introspection.

No model reasoning is spent enumerating a standard library. `inspect` already
knows every signature, every default, and -- unlike C++ -- exactly which
arguments are positional-only, keyword-only, or variadic. That distinction is
the Python analogue of "arguments and flags" and it matters more here than in
C++, because calling convention is part of the API.

Output: data/raw_decls_py.jsonl, in the same record shape build_base.py already
consumes.

    scan_python.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# Modules that are deprecated, interactive, or execute on import.
SKIP_MODULES = {
    "antigravity", "this", "idlelib", "turtledemo", "tkinter", "test",
    "lib2to3", "distutils", "ensurepip", "venv", "pydoc_data", "curses",
    "__main__", "__phello__", "site", "sitecustomize", "crypt", "nis",
}

PARAM_KIND = {
    inspect.Parameter.POSITIONAL_ONLY: "positional-only",
    inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional-or-keyword",
    inspect.Parameter.VAR_POSITIONAL: "var-positional",
    inspect.Parameter.KEYWORD_ONLY: "keyword-only",
    inspect.Parameter.VAR_KEYWORD: "var-keyword",
}


def annotation_of(value) -> str | None:
    if value is inspect.Parameter.empty:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "__name__", None) or str(value).replace("typing.", "")


def first_line(doc: str | None) -> str | None:
    if not doc:
        return None
    for line in doc.strip().splitlines():
        line = line.strip()
        if line:
            return line[:300]
    return None


def params_of(obj) -> tuple[list, str | None, bool]:
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        return [], None, False
    out, variadic = [], False
    for i, (name, p) in enumerate(sig.parameters.items()):
        if name in ("self", "cls") and i == 0:
            continue
        kind = PARAM_KIND.get(p.kind, "positional-or-keyword")
        if kind in ("var-positional", "var-keyword"):
            variadic = True
        out.append({
            "ordinal": len(out),
            "name": name,
            "type": annotation_of(p.annotation) or "Any",
            "raw_type": annotation_of(p.annotation),
            "canonical_type": annotation_of(p.annotation),
            "default_value": (None if p.default is inspect.Parameter.empty
                              else repr(p.default)[:80]),
            "is_pack": kind in ("var-positional", "var-keyword"),
            # Python's calling convention IS part of the API: a keyword-only
            # argument cannot be passed positionally, and the IDE must know.
            "param_kind": kind,
        })
    return out, annotation_of(sig.return_annotation), variadic


def record(obj, kind: str, module: str, qualname: str) -> dict | None:
    params, ret, variadic = params_of(obj)
    try:
        sig_text = f"{qualname}{inspect.signature(obj)}"
    except (ValueError, TypeError):
        sig_text = qualname
    return {
        "usr": f"py:{module}.{qualname}",
        "kind": kind,
        "name": qualname.rsplit(".", 1)[-1],
        "qualified_name": f"{module}.{qualname}",
        "namespace": module,
        "display": qualname,
        "file": module,
        "template_params": [],
        "params": params,
        "return_type": ret,
        "is_template": False, "is_static": False, "is_const": False,
        "is_variadic": variadic, "is_deprecated": False,
        "brief": first_line(inspect.getdoc(obj)),
        "signature": sig_text[:900],
        "constexpr_since": None, "is_constexpr": False, "is_consteval": False,
        "is_noexcept": False, "is_explicit": False, "is_nodiscard": False,
        # The Python analogue of a header is the module you import from.
        "headers": [f"import {module}"],
        "header": f"import {module}",
        "lang": "python",
        "impl": f"cpython-{sys.version_info.major}.{sys.version_info.minor}",
        "std_since": None,
        "_line": 0, "_quality": 3,
    }


def public_names(mod):
    declared = getattr(mod, "__all__", None)
    if isinstance(declared, (list, tuple)):
        return [n for n in declared if isinstance(n, str)]
    return [n for n in dir(mod) if not n.startswith("_")]


def scan_module(name: str, out: dict) -> int:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = importlib.import_module(name)
    except Exception:
        return 0
    found = 0
    for attr in public_names(mod):
        try:
            obj = getattr(mod, attr)
        except Exception:
            continue
        # only things this module actually defines
        owner = getattr(obj, "__module__", None)
        if owner and owner != name and not name.startswith(owner):
            continue

        if inspect.isfunction(obj) or inspect.isbuiltin(obj):
            rec = record(obj, "function", name, attr)
        elif inspect.isclass(obj):
            rec = record(obj, "class", name, attr)
            if rec and rec["usr"] not in out:
                out[rec["usr"]] = rec
                found += 1
            # methods are the bulk of a Python API surface
            for mname, meth in inspect.getmembers(obj):
                if mname.startswith("_") and mname != "__init__":
                    continue
                if not (inspect.isfunction(meth) or inspect.ismethod(meth)
                        or inspect.isbuiltin(meth)):
                    continue
                mrec = record(meth, "member_function", name,
                              f"{attr}.{mname}")
                if mrec and mrec["usr"] not in out:
                    out[mrec["usr"]] = mrec
                    found += 1
            continue
        else:
            continue

        if rec and rec["usr"] not in out:
            out[rec["usr"]] = rec
            found += 1
    return found


def main():
    names = sorted(n for n in sys.stdlib_module_names
                   if not n.startswith("_") and n not in SKIP_MODULES)
    out: dict = {}
    for i, name in enumerate(names, 1):
        n = scan_module(name, out)
        if n:
            print(f"  [{i:3}/{len(names)}] {name}: {n} (total {len(out)})",
                  flush=True)
    path = DATA / "raw_decls_py.jsonl"
    with open(path, "w") as fh:
        for rec in out.values():
            fh.write(json.dumps(rec) + "\n")
    print(f"\nwrote {len(out)} Python declarations -> {path}")


if __name__ == "__main__":
    main()
