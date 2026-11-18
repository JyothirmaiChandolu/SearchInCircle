#!/usr/bin/env python3
"""One-off: the decided design (judge via Jev, rerank via chat) on v2, with
the chat/rerank model swapped from gpt-6-luna to gpt-5-nano, so it can be
compared against the luna/jev numbers already measured on the same v2 set.
Writes to its own file -- out-openai/metrics_C_jev_nano_v2.json -- instead of
reusing metrics_C_jev_chat.json, which already holds the v3-scale record."""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["MATCH_CHAT_MODEL"] = "gpt-5-nano"
os.environ["MATCH_REASONING"] = "minimal"
os.environ.setdefault("MATCH_DATA_DIR", str(HERE.parents[2] / "data" / "matching-testset-v2"))

from common import DATA, OUT, CHAT_MODEL, Eligibility, Meter, load_entries, load_requirements
from design_c import DesignC

VARIANT = "C_jev_nano_v2"
PRICES = {"chat": (0.05, 0.40), "jev": (0.042, 0.0)}   # gpt-5-nano pricing, per matching-prototype/matcher/usage.py
TAG_BACKEND = {"judge": "jev", "rerank": "chat"}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    print(f"[{VARIANT}] CHAT_MODEL={CHAT_MODEL} DATA={DATA}", flush=True)
    entries = load_entries()
    rules = Eligibility()
    t0 = time.time()
    matcher = DesignC(entries, judge_backend="jev", rerank_backend="chat")
    print(f"[{VARIANT}] write-time work done in {time.time() - t0:.0f}s", flush=True)

    def process_one(req: dict) -> tuple[str, list[str], dict, dict]:
        pool = rules.pool(req, entries)
        meter = Meter()
        req_meta = {"min_experience_years": req.get("min_experience_years"), "location": req.get("location")}
        ids, detail = matcher.match(req["text"], pool, meter, req_meta=req_meta)
        allowed = {e.id for e in pool}
        assert all(i in allowed for i in ids)
        print(f"[{VARIANT}] {req['id']} pool={len(pool)} shown={len(ids)} {meter.as_dict()}", flush=True)
        return req["id"], ids, detail, dict(pool=len(pool), shown=len(ids), **meter.as_dict())

    preds, details, per_req = {}, {}, {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for req_id, ids, detail, per_req_entry in ex.map(process_one, load_requirements()):
            preds[req_id], details[req_id], per_req[req_id] = ids, detail, per_req_entry

    pred_file = OUT / f"predictions_{VARIANT}.json"
    pred_file.write_text(json.dumps(preds, indent=2))
    (OUT / f"details_{VARIANT}.json").write_text(json.dumps(details, indent=2))
    import subprocess
    ev = subprocess.run([sys.executable, str(DATA / "evaluate.py"), str(pred_file), "--json"],
                        capture_output=True, text=True)
    try:
        score = json.loads(ev.stdout)
    except json.JSONDecodeError:
        print(f"[{VARIANT}] evaluate.py failed: {ev.stderr}", file=sys.stderr)
        raise

    open_reqs = [m for m in per_req.values() if m["pool"]]
    n = len(open_reqs) or 1
    avg = lambda k: round(sum(m[k] for m in open_reqs) / n, 2)

    cost_by_stage: dict[str, dict] = {}
    for m in per_req.values():
        for tag, b in m.get("by_tag", {}).items():
            t = cost_by_stage.setdefault(tag, {"calls": 0, "tokens_in": 0, "tokens_out": 0})
            t["calls"] += b["calls"]; t["tokens_in"] += b["tokens_in"]; t["tokens_out"] += b["tokens_out"]
    for tag, b in cost_by_stage.items():
        inp, outp = PRICES.get(TAG_BACKEND.get(tag, "chat"), PRICES["chat"])
        b["cost"] = round(b["tokens_in"] * inp / 1e6 + b["tokens_out"] * outp / 1e6, 4)

    result = dict(variant=VARIANT, chat_model="gpt-5-nano", accuracy=score["summary"], failures=score["failures"],
                  per_requirement_avg=dict(llm_calls=avg("llm_calls"), tokens_in=avg("tokens_in"), tokens_out=avg("tokens_out"),
                                           seconds_one_after_another=avg("llm_seconds"), seconds_if_parallel=avg("parallel_seconds"),
                                           fallbacks=sum(m["fallbacks"] for m in open_reqs)),
                  cost_by_stage=cost_by_stage, write_time_total=dict(entries=len(entries), **matcher.write_meter.as_dict()),
                  per_requirement=per_req)
    (OUT / f"metrics_{VARIANT}.json").write_text(json.dumps(result, indent=2))
    print(f"[{VARIANT}] {json.dumps(score['summary'])}", flush=True)
    print(f"[{VARIANT}] per requirement avg: {json.dumps(result['per_requirement_avg'])}", flush=True)
    print(f"[{VARIANT}] cost by stage: {json.dumps(cost_by_stage)}", flush=True)


if __name__ == "__main__":
    main()
