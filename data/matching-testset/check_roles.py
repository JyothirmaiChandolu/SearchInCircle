"""Check a roles_*.py content file before the generator uses it.

Usage: python3.12 check_roles.py roles_tech.py [more files ...]

Each file defines two dicts:
  EXTEND  existing archetype key -> extra content for it
  NEW     new archetype key      -> a full role (same fields as archetypes._a, plus duties)
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from archetypes import A

ROLE_FIELDS = {"label", "group", "kind", "local", "roles", "skills", "syn", "tools", "certs", "does", "syn_does",
               "specs", "related", "duties", "syn_duties"}
OPTIONAL = {"spec_duties"}
EXTEND_FIELDS = {"duties", "syn_duties", "spec_duties", "more_syn", "more_tools"}
GROUPS = {"tech", "health", "home", "services", "learn", "hobby", "resource"}
KINDS = {"pro", "hobby", "resource"}
BANNED = re.compile(r"\b(our|us|we|my|me|he|she|his|her|him|they|their|friend|neighbou?r|colleague|cousin|"
                    r"recommended|great job|reliable|trustworthy)\b", re.I)
CITY = re.compile(r"\b(Austin|Houston|Seattle|Dallas|San Jose|Hyderabad|Bengaluru|Bangalore|Chennai|Pune|"
                  r"Vijayawada|London|Manchester|Toronto|Vancouver)\b")
YEARS = re.compile(r"\b\d+\+?\s*(years?|yrs?)\b", re.I)


def has_word(needle: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(needle.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def load(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "EXTEND", {}), getattr(mod, "NEW", {})


def check_phrase(where: str, p: str, errs: list[str], duty: bool) -> None:
    if not isinstance(p, str) or not p.strip():
        errs.append(f"{where}: empty or not a string")
        return
    if BANNED.search(p):
        errs.append(f"{where}: pronoun or relationship word '{BANNED.search(p).group(0)}' in: {p}")
    if CITY.search(p):
        errs.append(f"{where}: city name in: {p}")
    if YEARS.search(p):
        errs.append(f"{where}: years of experience in: {p}")
    if duty:
        if p[0] != p[0].lower() and not p.split()[0].isupper():
            errs.append(f"{where}: duty must start lowercase (past-tense verb): {p}")
        if p.endswith("."):
            errs.append(f"{where}: no trailing full stop: {p}")
        n = len(p.split())
        if not 7 <= n <= 24:
            errs.append(f"{where}: duty has {n} words, want 7-24: {p}")


def check(paths: list[str]) -> int:
    errs: list[str] = []
    all_new: dict[str, dict] = {}
    loaded = []
    for path in paths:
        ext, new = load(path)
        loaded.append((path, ext, new))
        for k in new:
            if k in A or k in all_new:
                errs.append(f"{path}: NEW key '{k}' already exists")
            all_new[k] = new[k]
    known = set(A) | set(all_new)
    labels = {a["label"].lower() for a in A.values()}
    for path, ext, new in loaded:
        for k, e in ext.items():
            if k not in A:
                errs.append(f"{path}: EXTEND key '{k}' is not an existing archetype")
                continue
            bad = set(e) - EXTEND_FIELDS
            if bad:
                errs.append(f"{path}: EXTEND {k}: unknown fields {bad}")
            canon = A[k]["skills"] + A[k]["roles"]
            if len(e.get("duties", [])) < 6:
                errs.append(f"{path}: EXTEND {k}: want at least 6 duties")
            if len(e.get("syn_duties", [])) < 4:
                errs.append(f"{path}: EXTEND {k}: want at least 4 syn_duties")
            for p in e.get("duties", []):
                check_phrase(f"{k}.duties", p, errs, True)
            for p in e.get("syn_duties", []):
                check_phrase(f"{k}.syn_duties", p, errs, True)
                for w in canon:
                    if has_word(w, p):
                        errs.append(f"{k}.syn_duties leaks canonical word '{w}': {p}")
            for p in e.get("more_syn", []):
                for w in canon:
                    if has_word(w, p):
                        errs.append(f"{k}.more_syn leaks canonical word '{w}': {p}")
            for s, ds in e.get("spec_duties", {}).items():
                if s not in A[k]["specs"]:
                    errs.append(f"{k}.spec_duties: '{s}' is not one of its specs {list(A[k]['specs'])}")
                for p in ds:
                    check_phrase(f"{k}.spec_duties.{s}", p, errs, True)
        for k, r in new.items():
            missing, bad = ROLE_FIELDS - set(r), set(r) - ROLE_FIELDS - OPTIONAL
            if missing:
                errs.append(f"{path}: NEW {k}: missing {missing}")
                continue
            if bad:
                errs.append(f"{path}: NEW {k}: unknown fields {bad}")
            if r["group"] not in GROUPS:
                errs.append(f"{k}: group must be one of {GROUPS}")
            if r["kind"] not in KINDS:
                errs.append(f"{k}: kind must be one of {KINDS}")
            if r["label"].lower() in labels:
                errs.append(f"{k}: label duplicates an existing role")
            for f, lo in (("roles", 2), ("skills", 4), ("syn", 3), ("tools", 3), ("does", 2), ("syn_does", 2),
                          ("duties", 6), ("syn_duties", 4)):
                if len(r[f]) < lo:
                    errs.append(f"{k}.{f}: want at least {lo}, got {len(r[f])}")
            if not 2 <= len(r["specs"]) <= 4:
                errs.append(f"{k}.specs: want 2-4 specialties")
            for s, v in r["specs"].items():
                if not (isinstance(v, tuple) and len(v) == 2 and len(v[0]) >= 2 and len(v[1]) >= 1):
                    errs.append(f"{k}.specs.{s}: want ([2+ focus phrases], [1+ skills])")
            for rel in r["related"]:
                if rel not in known:
                    errs.append(f"{k}.related: unknown key '{rel}'")
            canon = r["skills"] + r["roles"]
            for f in ("syn", "syn_does", "syn_duties"):
                for p in r[f]:
                    for w in canon:
                        if has_word(w, p):
                            errs.append(f"{k}.{f} leaks canonical word '{w}': {p}")
            for s, (foci, _) in r["specs"].items():
                for p in foci:
                    check_phrase(f"{k}.specs.{s}", p, errs, False)
                    for w in canon:
                        if has_word(w, p):
                            errs.append(f"{k}.specs.{s} focus leaks canonical word '{w}': {p}")
            for f in ("duties", "syn_duties"):
                for p in r[f]:
                    check_phrase(f"{k}.{f}", p, errs, True)
            for s, ds in r.get("spec_duties", {}).items():
                if s not in r["specs"]:
                    errs.append(f"{k}.spec_duties: '{s}' is not one of its specs")
                for p in ds:
                    check_phrase(f"{k}.spec_duties.{s}", p, errs, True)
        print(f"{path}: EXTEND {len(ext)}, NEW {len(new)}")
    for e in errs:
        print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} errors")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(check(sys.argv[1:]))
