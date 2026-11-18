"""Design C: full-pool hybrid retrieval, then two model calls -- judge, then rerank.

Per the user's explicit choice: no cap between retrieval and judging (every
eligible candidate goes to the model), and rerank is a second, separate model
call rather than arithmetic. This costs more than A or B -- flagged in
RESULTS.md, not hidden here.

  write time   one embedding per entry, plus a keyword index
  query time   1. hard rules first (circle, audience, blocks, availability)        -- same as A/B
               2. model reads the requirement -> role, other names, skills, min years, place
               3. keyword rank + vector rank, joined by reciprocal rank fusion (RRF) -- the WHOLE pool, no cutoff
               4. model judges every candidate 0-3 on skill fit alone (batches, parallel)
               5. drop grade 0; the survivors go to a SECOND model call that scores
                  overall fit 0-3, now including the real experience_years/location fields
               6. order by rerank score, then judge grade, then vouches, then similarity

`judge_backend` / `rerank_backend` each pick "chat" (gpt-6-luna chat
completion), "decisions" (OpenAI Decisions API, $0 output), or "jev"
(TypeSafe's Jev, cheapest input price, $0 output). `rerank_backend` defaults
to the same value as `judge_backend` when not given. Judging touches the
whole uncapped pool every time (85-95% of this design's cost, measured);
reranking only touches judge's survivors (a fraction of the volume) -- so
mixing a cheap judge backend with a pricier rerank backend costs far less
than the reverse.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor

from common import BM25, Entry, Meter, ModerationFlagged, chat_json, cosine, decisions_call, embed, jev_call, parse_requirement, show_once
from design_b import JUDGE_LEVELS, JUDGE_QUESTION_PREFIX, JUDGE_SCHEMA, JUDGE_SYSTEM

RRF_K = 60
BATCH = 20

RERANK_SCHEMA = {
    "type": "object",
    "properties": {"scores": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "score": {"type": "integer"}},
        "required": ["id", "score"]}}},
    "required": ["scores"],
}

RERANK_SYSTEM = """Skill fit is already confirmed for every candidate below. Score overall fit now. Return JSON only.
Each candidate has a short skill description plus explicit experience_years and location fields (stated facts, not guessed). Score every candidate:
3 = meets or exceeds the request's stated minimum years and location
2 = misses one thing by a little (experience_years short by 1-2 years, or a different location when the request's location is set)
1 = misses one thing by a lot (experience_years short by 3 or more years, or a far different location)
0 = should not have reached this stage
A candidate whose experience_years or location is null is not marked down for it -- only a stated mismatch counts. A null request location means remote is fine.
Give one score per candidate id."""

RERANK_LEVELS = [
    {"label": "should not have reached this stage"},
    {"label": "misses stated years or location by a lot"},
    {"label": "misses stated years or location by a little"},
    {"label": "meets stated years and location"},
]


class DesignC:
    name = "C"

    def __init__(self, entries: list[Entry], judge_backend: str = "chat", rerank_backend: str | None = None) -> None:
        self.judge_backend = judge_backend
        self.rerank_backend = rerank_backend or judge_backend
        self.write_meter = Meter()
        # ---- write time: done once when an entry is saved
        self.vec = {e.id: v for e, v in zip(entries, embed([e.text for e in entries], self.write_meter))}
        self.bm25 = BM25({e.id: e.text for e in entries})

    # ---- query time
    def match(self, req_text: str, pool: list[Entry], meter: Meter, req_meta: dict | None = None) -> tuple[list[str], dict]:
        if not pool:
            return [], {}
        need = parse_requirement(req_text, meter)
        meta = req_meta or {}
        req_min_years = meta.get("min_experience_years") if meta.get("min_experience_years") is not None else need["min_years"]
        req_location = meta.get("location") or need["city"]
        qvec = embed([req_text], meter, kind="query")[0]
        cos = {e.id: cosine(qvec, self.vec[e.id]) for e in pool}

        # keyword + vector, full pool, no shortlist
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

        def judge_chat(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            user = ("Request:\n" + req_text + "\n\nCandidates:\n"
                    + "\n".join(f"{cid}: {e.text}" for cid, e in ids.items()))
            try:
                out, secs = chat_json(JUDGE_SYSTEM, user, JUDGE_SCHEMA, meter, tag="judge")
            except ModerationFlagged as err:
                print(f"[design C] moderation-flagged judge batch, falling back to grade 0 for: "
                      f"{', '.join(e.id for e in batch)} -- {err}", file=sys.stderr)
                for e in batch:
                    meter.fallbacks += 1
                    grade[e.id] = 0
                return 0.0
            got = {g["id"]: g["grade"] for g in out.get("grades", []) if g.get("id") in ids}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                grade[e.id] = max(0, min(3, int(got.get(cid, 0))))
            return secs

        def judge_decisions(batch: list[Entry]) -> float:
            # "choice" (direct pick from labels), not "score" (continuous
            # expected value, biased up from level 0 -- see design_b.py).
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            labels = [lvl["label"] for lvl in JUDGE_LEVELS]
            questions = [{"type": "choice", "name": cid, "instructions": JUDGE_QUESTION_PREFIX + e.text,
                         "choices": [{"value": label} for label in labels]} for cid, e in ids.items()]
            out = decisions_call(req_text, questions, meter, tag="judge")
            got = {a["name"]: labels.index(a["choice"]) for a in out.get("answers", [])
                   if a.get("name") in ids and a.get("choice") in labels}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                grade[e.id] = max(0, min(3, got.get(cid, 0)))
            return 0.0

        def judge_jev(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            questions = {cid: {"type": "score", "instructions": JUDGE_QUESTION_PREFIX + e.text,
                               "criteria": [lvl["label"] for lvl in JUDGE_LEVELS]} for cid, e in ids.items()}
            out = jev_call(req_text, questions, meter, tag="judge")
            answers = out.get("answers", {})
            for cid, e in ids.items():
                a = answers.get(cid)
                if a is None or "score" not in a:
                    meter.fallbacks += 1
                    grade[e.id] = 0
                else:
                    grade[e.id] = max(0, min(3, round(a["score"])))
            return 0.0

        judge = {"chat": judge_chat, "decisions": judge_decisions, "jev": judge_jev}[self.judge_backend]
        batches = [ranked_pool[i:i + BATCH] for i in range(0, len(ranked_pool), BATCH)]
        with ThreadPoolExecutor(max_workers=8) as ex:
            meter.stage(list(ex.map(judge, batches)))

        survivors = [e for e in ranked_pool if grade[e.id] > 0]

        rerank_score: dict[str, int] = {}

        def _fit_line(e: Entry) -> str:
            return (f"request needs min {req_min_years} years, location {req_location} (null means remote is fine); "
                    f"candidate has experience_years={e.experience_years}, location={e.location}")

        def rerank_chat(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            user = ("Request:\n" + req_text
                    + f"\nmin_experience_years: {req_min_years}\nlocation: {req_location} (null means remote is fine)"
                    + "\n\nCandidates:\n"
                    + "\n".join(f"{cid}: {e.text} | experience_years: {e.experience_years} | location: {e.location}"
                               for cid, e in ids.items()))
            try:
                out, secs = chat_json(RERANK_SYSTEM, user, RERANK_SCHEMA, meter, tag="rerank")
            except ModerationFlagged as err:
                print(f"[design C] moderation-flagged rerank batch, falling back to judge grade for: "
                      f"{', '.join(e.id for e in batch)} -- {err}", file=sys.stderr)
                for cid, e in ids.items():
                    meter.fallbacks += 1
                    rerank_score[e.id] = grade[e.id]
                return 0.0
            got = {s["id"]: s["score"] for s in out.get("scores", []) if s.get("id") in ids}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                rerank_score[e.id] = max(0, min(3, int(got.get(cid, grade[e.id]))))
            return secs

        def rerank_decisions(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            labels = [lvl["label"] for lvl in RERANK_LEVELS]
            questions = [{"type": "choice", "name": cid, "instructions": _fit_line(e),
                         "choices": [{"value": label} for label in labels]} for cid, e in ids.items()]
            out = decisions_call(req_text, questions, meter, tag="rerank")
            got = {a["name"]: labels.index(a["choice"]) for a in out.get("answers", [])
                   if a.get("name") in ids and a.get("choice") in labels}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                rerank_score[e.id] = max(0, min(3, got.get(cid, grade[e.id])))
            return 0.0

        def rerank_jev(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            questions = {cid: {"type": "score", "instructions": _fit_line(e),
                               "criteria": [lvl["label"] for lvl in RERANK_LEVELS]} for cid, e in ids.items()}
            out = jev_call(req_text, questions, meter, tag="rerank")
            answers = out.get("answers", {})
            for cid, e in ids.items():
                a = answers.get(cid)
                if a is None or "score" not in a:
                    meter.fallbacks += 1
                    rerank_score[e.id] = grade[e.id]
                else:
                    rerank_score[e.id] = max(0, min(3, round(a["score"])))
            return 0.0

        rerank = {"chat": rerank_chat, "decisions": rerank_decisions, "jev": rerank_jev}[self.rerank_backend]
        if survivors:
            batches2 = [survivors[i:i + BATCH] for i in range(0, len(survivors), BATCH)]
            with ThreadPoolExecutor(max_workers=8) as ex:
                meter.stage(list(ex.map(rerank, batches2)))

        ranked = sorted(survivors, key=lambda e: -rerank_score[e.id])
        _, vouches = show_once(ranked)
        ranked.sort(key=lambda e: (-rerank_score[e.id], -grade[e.id], -vouches[e.person_key], -cos[e.id]))
        people, _ = show_once(ranked)
        detail = {e.id: {"grade": rerank_score[e.id], "skill_grade": grade[e.id], "vouches": vouches[e.person_key]}
                  for e in people}
        return [e.id for e in people], detail
