#!/usr/bin/env python3
"""Run one matcher over the test set, score it, and record cost and speed.

Usage:  python3 run.py <variant> [<variant> ...]
        python3 run.py all

Variants:
  A0           vector search only, cosine cutoff, no model call     (the pipeline as drawn, without the optional rerank)
  A1           vector search + model rerank of the top 15           (the pipeline as drawn, with the rerank)
  A            keyword + vector search (RRF) + model rerank         (the reviewed version of that pipeline)
  B            model profile at write time, model grades everyone, judge via gpt-6-luna chat completions
  B_decisions  same as B, judge via OpenAI's Decisions API (gpt-6-luna, $0 output tokens)
  B_jev        same as B, judge via TypeSafe's Jev ($0.042/1M input, $0 output -- cheapest, different model family)
  C            full pool to keyword+vector fusion (no cap), model judges everyone, then a SECOND model
               call reranks the survivors on years/location -- judge via gpt-6-luna chat completions
  C_decisions  same as C, both calls via OpenAI's Decisions API
  C_jev        same as C, both calls via TypeSafe's Jev
  C_jev_chat       same as C, judge via Jev (cheapest, touches the whole pool), rerank via chat
  C_chat_jev       same as C, judge via chat, rerank via Jev (cheapest rerank, judge untouched)
  C_jev_decisions  same as C, judge via Jev, rerank via OpenAI's Decisions API

Writes out/predictions_<variant>.json, out/details_<variant>.json and out/metrics_<variant>.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from common import DATA, OUT, Eligibility, Meter, load_entries, load_requirements
from design_a import DesignA
from design_b import DesignB
from design_c import DesignC

VARIANTS = {
    "A0": lambda entries: DesignA(entries, retrieval="vector", rerank=False),
    "A1": lambda entries: DesignA(entries, retrieval="vector", rerank=True),
    "A": lambda entries: DesignA(entries, retrieval="hybrid", rerank=True),
    "B": lambda entries: DesignB(entries, judge_backend="chat"),
    "B_decisions": lambda entries: DesignB(entries, judge_backend="decisions"),
    "B_jev": lambda entries: DesignB(entries, judge_backend="jev"),
    "C": lambda entries: DesignC(entries, judge_backend="chat"),
    "C_decisions": lambda entries: DesignC(entries, judge_backend="decisions"),
    "C_jev": lambda entries: DesignC(entries, judge_backend="jev"),
    # Mixed combos: judging is 85-95% of C's cost (it touches the whole
    # uncapped pool; rerank only touches judge's survivors), so pairing a
    # cheap judge backend with a pricier rerank backend costs far less than
    # the reverse -- these three test that asymmetry directly.
    "C_jev_chat": lambda entries: DesignC(entries, judge_backend="jev", rerank_backend="chat"),
    "C_chat_jev": lambda entries: DesignC(entries, judge_backend="chat", rerank_backend="jev"),
    "C_jev_decisions": lambda entries: DesignC(entries, judge_backend="jev", rerank_backend="decisions"),
}

# Tag -> backend actually used, per variant -- for the cost-by-stage pricing
# below. "parse" and "enrich" always go through chat_json regardless of
# variant (no backend knob for those stages), so they default to "chat".
TAG_BACKEND = {
    "A1": {"rerank": "chat"}, "A": {"rerank": "chat"},
    "B": {"judge": "chat"}, "B_decisions": {"judge": "decisions"}, "B_jev": {"judge": "jev"},
    "C": {"judge": "chat", "rerank": "chat"},
    "C_decisions": {"judge": "decisions", "rerank": "decisions"},
    "C_jev": {"judge": "jev", "rerank": "jev"},
    "C_jev_chat": {"judge": "jev", "rerank": "chat"},
    "C_chat_jev": {"judge": "chat", "rerank": "jev"},
    "C_jev_decisions": {"judge": "jev", "rerank": "decisions"},
}

# Requirements are independent, and each one only makes small calls at match
# time (one tiny query embedding, one rerank/judge completion) -- the one big
# embedding call already happened once at write time, outside this loop. That
# is a different shape of request than the large per-chunk embedding downloads
# that got slower under concurrency (see common.py's _embed_raw comment), so
# this loop is safe to thread. B's match() already runs its own judge batches
# through an 8-worker pool per call; capping this outer pool at 4 keeps total
# concurrency (up to 32 small completions at once) reasonable rather than
# stacking two full-sized pools.
REQUIREMENT_WORKERS = 4

# For the cost-by-stage breakdown only (judge vs rerank vs parse/enrich).
# $ per 1M tokens, (input, output). Decisions and Jev are $0 output by design.
PRICES = {"chat": (0.10, 0.50), "decisions": (0.10, 0.0), "jev": (0.042, 0.0)}


def _price_for(variant: str, tag: str) -> tuple[float, float]:
    return PRICES[TAG_BACKEND.get(variant, {}).get(tag, "chat")]


def run(variant: str) -> dict:
    OUT.mkdir(exist_ok=True)
    entries = load_entries()
    rules = Eligibility()
    t0 = time.time()
    matcher = VARIANTS[variant](entries)
    print(f"[{variant}] write-time work done in {time.time() - t0:.0f}s", flush=True)

    def process_one(req: dict) -> tuple[str, list[str], dict, dict]:
        pool = rules.pool(req, entries)
        meter = Meter()
        req_meta = {"min_experience_years": req.get("min_experience_years"), "location": req.get("location")}
        ids, detail = matcher.match(req["text"], pool, meter, req_meta=req_meta)     # text + stated facts only, never the publisher
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
    ev = subprocess.run([sys.executable, str(DATA / "evaluate.py"), str(pred_file), "--json"],
                        capture_output=True, text=True)
    score = json.loads(ev.stdout)

    open_reqs = [m for m in per_req.values() if m["pool"]]
    n = len(open_reqs)
    avg = lambda k: round(sum(m[k] for m in open_reqs) / n, 2)

    cost_by_stage: dict[str, dict] = {}
    for m in per_req.values():
        for tag, b in m.get("by_tag", {}).items():
            t = cost_by_stage.setdefault(tag, {"calls": 0, "tokens_in": 0, "tokens_out": 0})
            t["calls"] += b["calls"]
            t["tokens_in"] += b["tokens_in"]
            t["tokens_out"] += b["tokens_out"]
    for tag, b in cost_by_stage.items():
        inp, outp = _price_for(variant, tag)
        b["cost"] = round(b["tokens_in"] * inp / 1e6 + b["tokens_out"] * outp / 1e6, 4)

    result = dict(
        variant=variant,
        accuracy=score["summary"],
        failures=score["failures"],
        rows=score["rows"],
        per_requirement_avg=dict(llm_calls=avg("llm_calls"), tokens_in=avg("tokens_in"), tokens_out=avg("tokens_out"),
                                 seconds_one_after_another=avg("llm_seconds"),
                                 seconds_if_parallel=avg("parallel_seconds"), fallbacks=sum(m["fallbacks"] for m in open_reqs)),
        cost_by_stage=cost_by_stage,
        write_time_total=dict(entries=len(entries), **matcher.write_meter.as_dict()),
        per_requirement=per_req,
    )
    (OUT / f"metrics_{variant}.json").write_text(json.dumps(result, indent=2))
    print(f"[{variant}] {json.dumps(score['summary'])}", flush=True)
    print(f"[{variant}] per requirement: {json.dumps(result['per_requirement_avg'])}", flush=True)
    print(f"[{variant}] cost by stage: {json.dumps(cost_by_stage)}", flush=True)
    return result


if __name__ == "__main__":
    names = sys.argv[1:] or ["all"]
    if names == ["all"]:
        names = list(VARIANTS)
    for name in names:
        run(name)
