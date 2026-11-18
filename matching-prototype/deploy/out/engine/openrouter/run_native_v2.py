#!/usr/bin/env python3
"""The decided design (judge via Jev, rerank via a cheap model) on v2, with
the rerank backend swapped to native Anthropic/Google calls -- bypasses
OpenRouter entirely, so this isn't blocked by its account credit or
free-tier congestion. Mirrors run_nano_v2.py's shape, same v2 dataset, same
comparison basis.

Usage: python3 run_native_v2.py <variant> [<variant> ...]
       python3 run_native_v2.py all

Variants:
  jev_claude_haiku    judge=Jev, rerank=claude-haiku-5-5 (Anthropic, direct)
  jev_claude_sonnet   judge=Jev, rerank=claude-sonnet-5-5 (Anthropic, direct)
  jev_claude_opus     judge=Jev, rerank=claude-opus-5-5 (Anthropic, direct)
  jev_gemini_flash    judge=Jev, rerank=gemini-3.1-flash-lite (Google, direct)
  jev_gemini_flash35  judge=Jev, rerank=gemini-3.5-flash-lite (Google, direct)

gemini-3.1-pro-preview and plain gemini-3.5-flash were tried and dropped:
pro-preview hits a real quota/billing wall on this key (HTTP 429, not a
rate-limit retry -- "check your plan and billing"), and flash (non-lite)
works but took 75s for one tiny call (likely default extended thinking) --
too slow to batch.
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

from common import DATA, Eligibility, Meter, anthropic_chat_json, gemini_chat_json, jev_call  # noqa: E402
from design_c_openrouter import DesignCOpenRouter  # noqa: E402

# $ per 1M tokens, (input, output). Jev: $0.042/$0 (see common.py). Anthropic
# and Google list prices as of this run, direct from each provider -- not
# OpenRouter's markup.
PRICE_JEV = (0.042, 0.0)
VARIANTS = {
    "jev_claude_haiku": ("claude-haiku-5-5", anthropic_chat_json, (0.1, 0.5)),
    "jev_claude_sonnet": ("claude-sonnet-5-5", anthropic_chat_json, (2.0, 10.0)),
    "jev_claude_opus": ("claude-opus-5-5", anthropic_chat_json, (4.0, 20.0)),
    "jev_gemini_flash": ("gemini-3.1-flash-lite", gemini_chat_json, (0.25, 1.5)),
    "jev_gemini_flash35": ("gemini-3.5-flash-lite", gemini_chat_json, (0.3, 2.5)),
}

REQUIREMENT_WORKERS = 4


def run(variant: str) -> dict:
    OUT.mkdir(exist_ok=True)
    rerank_model, rerank_client, rerank_price = VARIANTS[variant]
    from common import load_entries, load_requirements
    entries = load_entries()
    rules = Eligibility()
    t0 = time.time()
    matcher = DesignCOpenRouter(entries, judge_model="jev-latest", rerank_model=rerank_model,
                                 judge_client=_jev_as_client, rerank_client=rerank_client)
    print(f"[{variant}] write-time work done in {time.time() - t0:.0f}s, data={DATA}", flush=True)

    def process_one(req: dict) -> tuple[str, list[str], dict, dict]:
        pool = rules.pool(req, entries)
        meter = Meter()
        req_meta = {"min_experience_years": req.get("min_experience_years"), "location": req.get("location")}
        ids, detail = matcher.match(req["text"], pool, meter, req_meta=req_meta)
        allowed = {e.id for e in pool}
        assert all(i in allowed for i in ids)
        print(f"[{variant}] {req['id']} pool={len(pool)} shown={len(ids)} {meter.as_dict()}", flush=True)
        return req["id"], ids, detail, dict(pool=len(pool), shown=len(ids), **meter.as_dict())

    preds, details, per_req = {}, {}, {}
    with ThreadPoolExecutor(max_workers=REQUIREMENT_WORKERS) as ex:
        for req_id, ids, detail, per_req_entry in ex.map(process_one, load_requirements()):
            preds[req_id], details[req_id], per_req[req_id] = ids, detail, per_req_entry

    pred_file = OUT / f"predictions_{variant}.json"
    pred_file.write_text(json.dumps(preds, indent=2))
    (OUT / f"details_{variant}.json").write_text(json.dumps(details, indent=2))
    ev = subprocess.run([sys.executable, str(DATA / "evaluate.py"), str(pred_file), "--json"],
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
    for m in per_req.values():
        for tag, b in m.get("by_tag", {}).items():
            t = cost_by_stage.setdefault(tag, {"calls": 0, "tokens_in": 0, "tokens_out": 0})
            t["calls"] += b["calls"]; t["tokens_in"] += b["tokens_in"]; t["tokens_out"] += b["tokens_out"]
    for tag, b in cost_by_stage.items():
        inp, outp = PRICE_JEV if tag in ("judge", "parse") else rerank_price
        b["cost"] = round(b["tokens_in"] * inp / 1e6 + b["tokens_out"] * outp / 1e6, 4)

    result = dict(variant=variant, judge_model="jev-latest", rerank_model=rerank_model,
                  accuracy=score["summary"], failures=score["failures"],
                  per_requirement_avg=dict(llm_calls=avg("llm_calls"), tokens_in=avg("tokens_in"), tokens_out=avg("tokens_out"),
                                           seconds_one_after_another=avg("llm_seconds"), seconds_if_parallel=avg("parallel_seconds"),
                                           fallbacks=sum(m["fallbacks"] for m in open_reqs)),
                  cost_by_stage=cost_by_stage, write_time_total=dict(entries=len(entries), **matcher.write_meter.as_dict()),
                  per_requirement=per_req)
    (OUT / f"metrics_{variant}.json").write_text(json.dumps(result, indent=2))
    print(f"[{variant}] {json.dumps(score['summary'])}", flush=True)
    print(f"[{variant}] cost by stage: {json.dumps(cost_by_stage)}", flush=True)
    return result


def _jev_as_client(system, user, schema, meter, model, tag=""):
    """Adapter: DesignCOpenRouter calls judge_client(system, user, schema,
    meter, model, tag=...) for a JUDGE_SCHEMA-shaped batch (list of
    {id, grade}) -- translate that into jev_call's own (state, questions)
    shape so the judge stage can stay on Jev (still the cheapest backend
    measured) while only the rerank stage swaps providers."""
    import re
    # user text is "Request:\n<req>\n\nCandidates:\n<id>: <text>\n..." -- pull per-candidate text back out
    body = user.split("\n\nCandidates:\n", 1)[1]
    cand_lines = body.split("\n")
    ids = {}
    for line in cand_lines:
        cid, _, text = line.partition(": ")
        if cid:
            ids[cid] = text
    req_text = user.split("\n\nCandidates:\n", 1)[0][len("Request:\n"):]
    from design_b import JUDGE_LEVELS, JUDGE_QUESTION_PREFIX
    questions = {cid: {"type": "score", "instructions": JUDGE_QUESTION_PREFIX + text,
                       "criteria": [lvl["label"] for lvl in JUDGE_LEVELS]} for cid, text in ids.items()}
    out = jev_call(req_text, questions, meter, tag=tag)
    answers = out.get("answers", {})
    grades = []
    for cid in ids:
        a = answers.get(cid)
        grades.append({"id": cid, "grade": round(a["score"]) if a and "score" in a else 0})
    return {"grades": grades}, 0.0


if __name__ == "__main__":
    names = sys.argv[1:] or ["all"]
    if names == ["all"]:
        names = list(VARIANTS)
    for name in names:
        run(name)
