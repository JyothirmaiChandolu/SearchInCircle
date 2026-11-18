#!/usr/bin/env python3
"""Run the decided design (full-pool hybrid, judge then rerank) against
OpenRouter-hosted models -- free Google models, and paid Google/Anthropic
models through the same gateway -- on the v2 test set (37 requirements,
4,130 entries), per the explicit call to test v2, not the current v3 set.

Usage:  python3 run_openrouter.py <variant> [<variant> ...]
        python3 run_openrouter.py all

Variants (judge model / rerank model, both OpenRouter ids):
  or_gemma31_free     google/gemma-4-31b-it:free (both stages)        -- free tier
  or_gemma26_free     google/gemma-4-26b-a4b-it:free (both stages)    -- free tier
  or_gemini_flash     google/gemini-3.1-flash-lite (both stages)      -- cheap paid Google
  or_gemini_mixed     judge gemini-3.1-flash-lite, rerank gemini-3.1-pro-preview
  or_claude_haiku     anthropic/claude-haiku-5.5 (both stages)        -- cheap paid Claude
  or_claude_mixed     judge claude-haiku-5.5, rerank claude-sonnet-5.5

Writes out/predictions_<variant>.json, out/details_<variant>.json and
out/metrics_<variant>.json, scored against the v2 answer key.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

os.environ.setdefault("MATCH_DATA_DIR", str(HERE.parents[3] / "data" / "matching-testset-v2"))
sys.path.insert(0, str(HERE.parent))

from common import DATA, Eligibility, Meter, load_entries, load_requirements  # noqa: E402  (after MATCH_DATA_DIR is set)
from design_c_openrouter import DesignCOpenRouter  # noqa: E402

# $ per 1M tokens, (input, output) -- OpenRouter's own live pricing, read from
# GET /api/v1/models the day this was written. Free models are $0/$0.
MODEL_PRICE = {
    "google/gemma-4-31b-it:free": (0.0, 0.0),
    "google/gemma-4-26b-a4b-it:free": (0.0, 0.0),
    "google/gemini-3.1-flash-lite": (0.25, 1.5),
    "google/gemini-3.1-pro-preview": (2.0, 12.0),
    "anthropic/claude-haiku-5.5": (0.1, 0.5),
    "anthropic/claude-sonnet-5.5": (2.0, 10.0),
}

VARIANTS = {
    "or_gemma31_free": ("google/gemma-4-31b-it:free", "google/gemma-4-31b-it:free"),
    "or_gemma26_free": ("google/gemma-4-26b-a4b-it:free", "google/gemma-4-26b-a4b-it:free"),
    "or_gemini_flash": ("google/gemini-3.1-flash-lite", "google/gemini-3.1-flash-lite"),
    "or_gemini_mixed": ("google/gemini-3.1-flash-lite", "google/gemini-3.1-pro-preview"),
    "or_claude_haiku": ("anthropic/claude-haiku-5.5", "anthropic/claude-haiku-5.5"),
    "or_claude_mixed": ("anthropic/claude-haiku-5.5", "anthropic/claude-sonnet-5.5"),
}

# These are JSON-schema-strict/non-strict-tier models answering one small
# batch at a time, not the decided design's own 8-worker pool -- openrouter's
# own throttle in common.py already serializes most of this, so a smaller
# outer pool avoids stacking two queues that both end up waiting on the same
# per-minute budget.
REQUIREMENT_WORKERS = 2


def _price_for(model: str) -> tuple[float, float]:
    return MODEL_PRICE.get(model, (0.0, 0.0))


def run(variant: str) -> dict:
    OUT.mkdir(exist_ok=True)
    judge_model, rerank_model = VARIANTS[variant]
    entries = load_entries()
    rules = Eligibility()
    t0 = time.time()
    matcher = DesignCOpenRouter(entries, judge_model=judge_model, rerank_model=rerank_model)
    print(f"[{variant}] write-time work done in {time.time() - t0:.0f}s, data={DATA}", flush=True)

    def process_one(req: dict) -> tuple[str, list[str], dict, dict]:
        pool = rules.pool(req, entries)
        meter = Meter()
        req_meta = {"min_experience_years": req.get("min_experience_years"), "location": req.get("location")}
        ids, detail = matcher.match(req["text"], pool, meter, req_meta=req_meta)
        allowed = {e.id for e in pool}
        assert all(i in allowed for i in ids), "a matcher may only return entries from the eligible pool"
        print(f"[{variant}] {req['id']} pool={len(pool)} shown={len(ids)} {meter.as_dict()}", flush=True)
        return req["id"], ids, detail, dict(pool=len(pool), shown=len(ids), **meter.as_dict())

    preds, details, per_req = {}, {}, {}
    with ThreadPoolExecutor(max_workers=REQUIREMENT_WORKERS) as ex:
        for req_id, ids, detail, per_req_entry in ex.map(process_one, load_requirements()):
            preds[req_id], details[req_id], per_req[req_id] = ids, detail, per_req_entry

    pred_file = OUT / f"predictions_{variant}.json"
    pred_file.write_text(json.dumps(preds, indent=2))
    (OUT / f"details_{variant}.json").write_text(json.dumps(details, indent=2))
    ev = subprocess.run([sys.executable, str(DATA / "evaluate.py"), str(pred_file), "--data", str(DATA), "--json"],
                        capture_output=True, text=True)
    try:
        score = json.loads(ev.stdout)
    except json.JSONDecodeError:
        print(f"[{variant}] evaluate.py failed: {ev.stderr}", file=sys.stderr)
        raise

    open_reqs = [m for m in per_req.values() if m["pool"]]
    n = len(open_reqs) or 1
    avg = lambda k: round(sum(m[k] for m in open_reqs) / n, 2)

    cost_by_stage: dict[str, dict] = {}
    model_by_tag = {"judge": judge_model, "rerank": rerank_model}
    for m in per_req.values():
        for tag, b in m.get("by_tag", {}).items():
            t = cost_by_stage.setdefault(tag, {"calls": 0, "tokens_in": 0, "tokens_out": 0})
            t["calls"] += b["calls"]
            t["tokens_in"] += b["tokens_in"]
            t["tokens_out"] += b["tokens_out"]
    for tag, b in cost_by_stage.items():
        inp, outp = _price_for(model_by_tag.get(tag, judge_model))
        b["cost"] = round(b["tokens_in"] * inp / 1e6 + b["tokens_out"] * outp / 1e6, 4)

    result = dict(
        variant=variant, judge_model=judge_model, rerank_model=rerank_model,
        accuracy=score["summary"], failures=score["failures"], rows=score["rows"],
        per_requirement_avg=dict(llm_calls=avg("llm_calls"), tokens_in=avg("tokens_in"), tokens_out=avg("tokens_out"),
                                 seconds_one_after_another=avg("llm_seconds"),
                                 seconds_if_parallel=avg("parallel_seconds"), fallbacks=sum(m["fallbacks"] for m in open_reqs)),
        cost_by_stage=cost_by_stage,
        write_time_total=dict(entries=len(entries), **matcher.write_meter.as_dict()),
        per_requirement=per_req,
    )
    (OUT / f"metrics_{variant}.json").write_text(json.dumps(result, indent=2))
    print(f"[{variant}] {json.dumps(score['summary'])}", flush=True)
    print(f"[{variant}] cost by stage: {json.dumps(cost_by_stage)}", flush=True)
    return result


if __name__ == "__main__":
    names = sys.argv[1:] or ["all"]
    if names == ["all"]:
        names = list(VARIANTS)
    for name in names:
        run(name)
