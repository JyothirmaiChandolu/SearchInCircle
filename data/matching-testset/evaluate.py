#!/usr/bin/env python3
"""Score a matching algorithm's output against the answer key.

Usage:  python3 evaluate.py predictions.json [--k 10] [--json] [--data ../matching-testset-10k]

predictions.json maps each requirement id to the entry ids (self-entry "S..."
or tag "T...") the algorithm would surface, best first. Return [] when nothing
clears your relevance bar:

    {"R01": ["T0163", "S0040"], "R12": [], ...}

Hard failures (exit code 1):
  * returning an entry the publisher must never see (outside the direct
    circle, pending or removed connection, blocked, not open, outside the
    audience, the publisher's own self-entry, a tag about the publisher)
  * returning anything for a closed requirement

Quality metrics are per real person, so two entries about one person count once.
A requirement can have from 0 to 100+ matching people, so the list may be any length:
  nDCG@k      ranking quality of the top k, using the 0-3 grades
  P@k         share of the top k that are good or strong (out of min(k, number of good people))
  recall      share of all good-or-strong people that appear anywhere in the list
  precision   share of returned people that are relevant at all (grade >= 1)
  syn         people described only in other words (synonyms) that were found
  trap        lexical traps in the top k
  once        "show once" merges for entries about the same registered user
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def dcg(rels: list[int]) -> float:
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("predictions", type=Path)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--data", type=Path, default=HERE,
                    help="folder that holds the data set to score against, for example ../matching-testset-10k")
    ap.add_argument("--key", type=Path, default=None, help="ground_truth.json (default: <data>/answer_key/)")
    ap.add_argument("--json", action="store_true", help="print machine-readable results")
    args = ap.parse_args()

    key = json.loads((args.key or args.data / "answer_key" / "ground_truth.json").read_text())["requirements"]
    labels = json.loads((args.data / "answer_key" / "entry_labels.json").read_text())
    person = {eid: lab["true_person_id"] for eid, lab in labels.items()}
    preds = json.loads(args.predictions.read_text())
    k = args.k

    rows, failures = [], []
    agg = dict(ndcg=[], p=[], r=[], prec=[], syn=0, syn_n=0, traps=0, merged=0, merge_n=0)
    for rid, r in key.items():
        pred = preds.get(rid)
        if pred is None:
            failures.append(f"{rid}: missing from predictions (use [] for no matches)")
            continue
        eligible = set(r["eligible_entry_ids"])
        hidden_why = {g["entry_id"]: g["exclusion_reasons"] for g in r["graded"] if not g["eligible"]}
        for eid in pred:
            if eid not in eligible:
                why = hidden_why.get(eid) or (["no connection to the publisher, or not open"] if eid in person
                                              else ["unknown_entry_id"])
                failures.append(f"{rid}: returned {eid} which must be hidden ({', '.join(why)})")

        rel_by_person: dict[str, int] = {}
        for g in r["graded"]:
            if g["eligible"]:
                rel_by_person[g["true_person_id"]] = max(rel_by_person.get(g["true_person_id"], 0), g["relevance"])
        seen, ranked, dupes = set(), [], 0
        for eid in pred:
            if eid not in eligible:
                continue
            p = person.get(eid)
            if p in seen:
                dupes += 1
                continue
            seen.add(p)
            ranked.append(rel_by_person.get(p, 0))

        row = dict(id=rid, returned=len(pred), duplicates=dupes)
        if r["status"] != "open" or r["expect_no_matches"]:
            row["expect_empty"] = True
            row["ok"] = len(pred) == 0 if r["status"] != "open" else not any(x >= 2 for x in ranked)
            if r["status"] != "open" and pred:
                failures.append(f"{rid}: requirement is closed but {len(pred)} results were returned")
            rows.append(row)
            continue

        ideal = sorted(rel_by_person.values(), reverse=True)
        ndcg = dcg(ranked[:k]) / dcg(ideal[:k]) if dcg(ideal[:k]) else 0.0
        good = {p for p, v in rel_by_person.items() if v >= 2}
        p_at_k = sum(1 for x in ranked[:k] if x >= 2) / max(1, min(k, len(good)))
        recall = len(good & seen) / len(good) if good else 1.0
        precision = sum(1 for x in ranked if x >= 1) / len(ranked) if ranked else 0.0

        # Every eligible person who is good or strong but described only in other words.
        syn = {g["true_person_id"] for g in r["graded"]
               if g["variant"] == "synonym" and g["eligible"] and g["relevance"] >= 2}
        syn -= {g["true_person_id"] for g in r["graded"]
                if g["variant"] != "synonym" and g["eligible"] and g["relevance"] >= 2}
        syn_found = len(syn & seen)
        traps = {g["entry_id"] for g in r["graded"] if "lexical_trap" in g["scenarios"]}
        trap_hits = sum(1 for e in pred[:k] if e in traps)
        # Show once: of each mergeable group, at most one entry should be returned.
        merged = sum(1 for m in r["expected_merges"] if sum(e in pred for e in m["entry_ids"]) == 1)
        shown = sum(1 for m in r["expected_merges"] if any(e in pred for e in m["entry_ids"]))

        row.update(good=len(good), ndcg=round(ndcg, 3), p_at_k=round(p_at_k, 3), recall=round(recall, 3),
                   precision=round(precision, 3),
                   synonym=f"{syn_found}/{len(syn)}", trap_hits=trap_hits, merged=f"{merged}/{shown}")
        rows.append(row)
        agg["ndcg"].append(ndcg)
        agg["p"].append(p_at_k)
        agg["r"].append(recall)
        agg["prec"].append(precision)
        agg["syn"] += syn_found
        agg["syn_n"] += len(syn)
        agg["traps"] += trap_hits
        agg["merged"] += merged
        agg["merge_n"] += shown

    n = max(len(agg["ndcg"]), 1)
    summary = dict(
        hard_failures=len(failures),
        mean_ndcg=round(sum(agg["ndcg"]) / n, 3),
        mean_precision_at_k=round(sum(agg["p"]) / n, 3),
        mean_recall=round(sum(agg["r"]) / n, 3),
        mean_precision=round(sum(agg["prec"]) / n, 3),
        synonym_recall=f"{agg['syn']}/{agg['syn_n']}",
        lexical_trap_hits=agg["traps"],
        show_once_ok=f"{agg['merged']}/{agg['merge_n']}",
        empty_cases_ok=f"{sum(1 for x in rows if x.get('expect_empty') and x['ok'])}/"
                       f"{sum(1 for x in rows if x.get('expect_empty'))}",
    )

    if args.json:
        print(json.dumps(dict(summary=summary, rows=rows, failures=failures), indent=2))
    else:
        print(f"{'req':4} {'good':>4} {'ret':>4} {'dup':>4} {'nDCG@' + str(k):>8} {'P@' + str(k):>6} {'recall':>6} "
              f"{'prec':>6} {'syn':>6} {'trap':>5} {'once':>6}")
        for x in rows:
            if x.get("expect_empty"):
                print(f"{x['id']:4} {0:4} {x['returned']:4} {x['duplicates']:4}   expects no matches -> "
                      f"{'OK' if x['ok'] else 'FAIL'}")
            else:
                print(f"{x['id']:4} {x['good']:4} {x['returned']:4} {x['duplicates']:4} {x['ndcg']:8.3f} "
                      f"{x['p_at_k']:6.2f} {x['recall']:6.2f} {x['precision']:6.2f} {x['synonym']:>6} "
                      f"{x['trap_hits']:5} {x['merged']:>6}")
        print("\nSummary:", json.dumps(summary, indent=2))
        if failures:
            print(f"\nHARD FAILURES ({len(failures)}):")
            for f in failures[:50]:
                print("  -", f)
            if len(failures) > 50:
                print(f"  ... {len(failures) - 50} more")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
