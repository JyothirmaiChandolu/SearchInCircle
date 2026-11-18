#!/usr/bin/env python3
"""Score several prediction files with the test set's evaluator and print them side by side.

Usage:  python3 compare.py akshaya/out-openai/predictions_B.json jyoti/out/predictions.json [...]
Each file maps a requirement id to entry ids, best first. The column name is the folder and file name.
"""
import json
import subprocess
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parents[2] / "data" / "matching-testset" / "evaluate.py"
ROWS = [("hard_failures", "Hidden people shown"), ("mean_ndcg", "nDCG@10"), ("mean_precision_at_k", "Precision@10"),
        ("mean_recall", "Recall (whole list)"), ("mean_precision", "Precision (whole list)"),
        ("synonym_recall", "Synonym-only found"), ("lexical_trap_hits", "Lexical traps in top 10"),
        ("show_once_ok", "Show once"), ("empty_cases_ok", "Empty cases")]


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 2
    results, names = [], []
    for p in paths:
        r = subprocess.run([sys.executable, str(EVAL), p, "--json"], capture_output=True, text=True)
        if not r.stdout:
            print(f"{p}: evaluator failed\n{r.stderr}")
            return 1
        results.append(json.loads(r.stdout))
        names.append(f"{Path(p).parent.parent.name}/{Path(p).stem}")
    width = max(len(n) for n in names + ["Metric"]) + 2
    print("Metric".ljust(24) + "".join(n.ljust(width) for n in names))
    for key, label in ROWS:
        print(label.ljust(24) + "".join(str(r["summary"][key]).ljust(width) for r in results))
    for n, r in zip(names, results):
        for f in r["failures"][:5]:
            print(f"  {n}: {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
