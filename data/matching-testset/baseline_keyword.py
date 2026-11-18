#!/usr/bin/env python3
"""Naive keyword-overlap matcher. A reference point, not a proposal.

Reads ONLY the public files (never answer_key/). It applies the eligibility
rules from README.md itself, which also proves the public data is enough to
apply them. Ranking is plain token overlap, so it is expected to miss
synonym-only entries; a real (semantic) matcher should beat it.

Usage:  python3 baseline_keyword.py > predictions_baseline.json
        python3 evaluate.py predictions_baseline.json
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Optional: --data <folder> reads another data set, for example ../matching-testset-10k
DATA = Path(sys.argv[sys.argv.index("--data") + 1]).resolve() if "--data" in sys.argv else HERE
STOP = set("a an and the of for to in on with at by our my we i need someone who is are be or as this that "
           "from your have has years year experience about known looking want can lives based".split())


def load(name: str):
    return json.loads((DATA / name).read_text())


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if t not in STOP and len(t) > 1}


def main() -> None:
    rules = load("rules.json")
    ref = dt.date.fromisoformat(rules["reference_date"])
    window = rules["reconfirm_window_days"]
    conns = load("trust_connections.json")
    status = {frozenset((c["requester_id"], c["addressee_id"])): c["status"] for c in conns}
    blocked = {frozenset((b["blocker_id"], b["blocked_id"])) for b in load("blocks.json")}
    entries = ([("self_entry", e, " ".join(e.get("skills") or [e["skill"]]) + " " + e["description"]) for e in load("self_entries.json")]
               + [("tag", e, " ".join([*e["skills"], e["description"] or ""])) for e in load("tags.json")])

    out = {}
    for r in load("requirements.json"):
        P = r["publisher_id"]
        if r["status"] != "open":
            out[r["id"]] = []
            continue
        q = tokens(r["text"])
        scored = []
        for kind, e, text in entries:
            o = e["owner_user_id"]
            pair = frozenset((P, o))
            if o == P:
                if kind == "self_entry" or not rules["include_own_tags"]:
                    continue
            elif (status.get(pair) != "accepted" or pair in blocked
                  or (r["audience_user_ids"] and o not in r["audience_user_ids"])):
                continue
            if e["availability_status"] != "open":
                continue
            if kind == "tag":
                if e["subject_user_id"] == P:
                    continue
                if window is not None and (ref - dt.date.fromisoformat(e["last_confirmed_at"])).days > window:
                    continue
            d = tokens(text)
            s = len(q & d) / math.sqrt(len(q) * len(d)) if q and d else 0.0
            if s >= 0.12:
                scored.append((s, e["id"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out[r["id"]] = [eid for _, eid in scored]  # no cap: a requirement can have 100+ matches
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
