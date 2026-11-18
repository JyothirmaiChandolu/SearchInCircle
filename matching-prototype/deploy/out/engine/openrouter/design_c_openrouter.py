"""Design C, with judge and rerank answered by any provider's model -- the
decided architecture (full-pool hybrid retrieval, judge every candidate,
then a second rerank call on the survivors), unchanged from design_c.py.
Only the backend differs: `judge_client`/`rerank_client` are callables
shaped like common.openrouter_chat_json (system, user, schema, meter, model,
tag="") -> (dict, float), so this design can be pointed at OpenRouter's
models, or -- once a provider's own API key is set -- at Anthropic/Google
directly (common.anthropic_chat_json, common.gemini_chat_json), bypassing
OpenRouter's account credit and shared-capacity limits entirely.

Kept in its own folder, separate from the decided design's own file, so this
feasibility work (rate limiting, truncation defenses, multi-provider
testing) doesn't touch the file the cost/accuracy decision was already made
against.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # akshaya/ -- common.py, design_b.py

from common import BM25, Entry, Meter, cosine, embed, openrouter_chat_json, parse_requirement, show_once
from design_b import JUDGE_SCHEMA, JUDGE_SYSTEM
from design_c import RERANK_SCHEMA, RERANK_SYSTEM

RRF_K = 60
BATCH = 20

ModelClient = Callable[..., tuple[dict, float]]


def _as_list(value) -> list:
    """Defense in depth: a backend's own double-encoding fix (see
    common._unwrap_double_encoded) can still miss a call -- Claude's
    tool-use formatting isn't deterministic run to run on these model
    tiers (no temperature control), so the same bug can slip through on a
    later retry even after being fixed once. Treat a stringified list the
    same as a real one instead of crashing the whole requirement over it."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


MAX_RETRIES = 2


def _call_with_retry(client: ModelClient, system: str, user: str, schema: dict, meter: Meter, model: str,
                      tag: str, ids: dict, list_field: str, value_field: str) -> tuple[dict[str, int], float]:
    """One call, then up to MAX_RETRIES retries for whatever candidate ids
    still haven't come back -- each retry only re-asks for what's missing so
    far, naming the exact ids. Returns (id -> raw value for whatever was
    recovered, total seconds spent on this batch across every attempt); the
    caller still owns clamping/validating each value and falling back for
    ids still missing after this."""
    out, total_secs = client(system, user, schema, meter, model, tag=tag)
    got = {item.get("id"): item.get(value_field) for item in _as_list(out.get(list_field)) if isinstance(item, dict)}
    for attempt in range(1, MAX_RETRIES + 1):
        missing = [cid for cid in ids if cid not in got]
        if not missing:
            break
        retry_user = user + ("\n\nYou missed some candidates. Give exactly one "
                              f"{value_field} for every one of these ids, no exceptions: " + ", ".join(missing))
        out2, secs2 = client(system, retry_user, schema, meter, model, tag=f"{tag}+retry{attempt}")
        total_secs += secs2
        got2 = {item.get("id"): item.get(value_field) for item in _as_list(out2.get(list_field)) if isinstance(item, dict)}
        for cid in missing:
            if cid in got2:
                got[cid] = got2[cid]
    return got, total_secs


class DesignCOpenRouter:
    name = "C_openrouter"

    def __init__(self, entries: list[Entry], judge_model: str, rerank_model: str | None = None,
                 judge_client: ModelClient = openrouter_chat_json, rerank_client: ModelClient | None = None) -> None:
        self.judge_model = judge_model
        self.rerank_model = rerank_model or judge_model
        self.judge_client = judge_client
        self.rerank_client = rerank_client or judge_client
        self.write_meter = Meter()
        self.vec = {e.id: v for e, v in zip(entries, embed([e.text for e in entries], self.write_meter))}
        self.bm25 = BM25({e.id: e.text for e in entries})

    def match(self, req_text: str, pool: list[Entry], meter: Meter, req_meta: dict | None = None) -> tuple[list[str], dict]:
        if not pool:
            return [], {}
        need = parse_requirement(req_text, meter)
        meta = req_meta or {}
        req_min_years = meta.get("min_experience_years") if meta.get("min_experience_years") is not None else need["min_years"]
        req_location = meta.get("location") or need["city"]
        qvec = embed([req_text], meter, kind="query")[0]
        cos = {e.id: cosine(qvec, self.vec[e.id]) for e in pool}

        query = " ".join([req_text, need["role"], *need["other_names"], *need["skills"]])
        by_vec = sorted(pool, key=lambda e: -cos[e.id])
        by_kw = sorted(pool, key=lambda e: -self.bm25.score(query, e.id))
        fused = {e.id: 0.0 for e in pool}
        for ranking in (by_vec, by_kw):
            for i, e in enumerate(ranking):
                fused[e.id] += 1.0 / (RRF_K + i + 1)
        ranked_pool = sorted(pool, key=lambda e: -fused[e.id])
        # Optional, off by default (the decided design judges the whole pool). When
        # req_meta carries judge_cap=N, only the top N by fused rank are judged; the
        # rest drop out exactly as if the judge had graded them 0.
        if meta.get("judge_cap"):
            ranked_pool = ranked_pool[:meta["judge_cap"]]

        grade: dict[str, int] = {}

        def judge(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            user = ("Request:\n" + req_text + "\n\nCandidates:\n"
                    + "\n".join(f"{cid}: {e.text}" for cid, e in ids.items()))
            try:
                got, secs = _call_with_retry(self.judge_client, JUDGE_SYSTEM, user, JUDGE_SCHEMA, meter, self.judge_model,
                                              "judge", ids, "grades", "grade")
            except RuntimeError as err:
                # exhausted the backend's own retry (rate limit, transient 5xx, or an
                # auth/billing error) -- fall back to grade 0 for this batch instead of
                # crashing the whole requirement, same spirit as design_c's moderation fallback
                print(f"[design C/openrouter] judge call failed for {self.judge_model}, "
                      f"grading batch 0: {', '.join(e.id for e in batch)} -- {err}", file=sys.stderr)
                for e in batch:
                    meter.fallbacks += 1
                    grade[e.id] = 0
                return 0.0
            for cid, e in ids.items():
                v = got.get(cid)
                try:
                    grade[e.id] = max(0, min(3, int(v)))
                except (TypeError, ValueError):
                    meter.fallbacks += 1
                    grade[e.id] = 0
            return secs

        batches = [ranked_pool[i:i + BATCH] for i in range(0, len(ranked_pool), BATCH)]
        with ThreadPoolExecutor(max_workers=4) as ex:   # lower than design_c's 8 -- openrouter's own throttle serializes most of this anyway
            meter.stage(list(ex.map(judge, batches)))

        survivors = [e for e in ranked_pool if grade[e.id] > 0]

        rerank_score: dict[str, int] = {}

        def rerank(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            user = ("Request:\n" + req_text
                    + f"\nmin_experience_years: {req_min_years}\nlocation: {req_location} (null means remote is fine)"
                    + "\n\nCandidates:\n"
                    + "\n".join(f"{cid}: {e.text} | experience_years: {e.experience_years} | location: {e.location}"
                               for cid, e in ids.items()))
            try:
                got, secs = _call_with_retry(self.rerank_client, RERANK_SYSTEM, user, RERANK_SCHEMA, meter, self.rerank_model,
                                              "rerank", ids, "scores", "score")
            except RuntimeError as err:
                print(f"[design C/openrouter] rerank call failed for {self.rerank_model}, "
                      f"falling back to judge grade for: {', '.join(e.id for e in batch)} -- {err}", file=sys.stderr)
                for cid, e in ids.items():
                    meter.fallbacks += 1
                    rerank_score[e.id] = grade[e.id]
                return 0.0
            for cid, e in ids.items():
                v = got.get(cid)
                try:
                    rerank_score[e.id] = max(0, min(3, int(v)))
                except (TypeError, ValueError):
                    meter.fallbacks += 1
                    rerank_score[e.id] = grade[e.id]
            return secs

        if survivors:
            batches2 = [survivors[i:i + BATCH] for i in range(0, len(survivors), BATCH)]
            with ThreadPoolExecutor(max_workers=4) as ex:
                meter.stage(list(ex.map(rerank, batches2)))

        ranked = sorted(survivors, key=lambda e: -rerank_score[e.id])
        _, vouches = show_once(ranked)
        ranked.sort(key=lambda e: (-rerank_score[e.id], -grade[e.id], -vouches[e.person_key], -cos[e.id]))
        people, _ = show_once(ranked)
        detail = {e.id: {"grade": rerank_score[e.id], "skill_grade": grade[e.id], "vouches": vouches[e.person_key]}
                  for e in people}
        return [e.id for e in people], detail
