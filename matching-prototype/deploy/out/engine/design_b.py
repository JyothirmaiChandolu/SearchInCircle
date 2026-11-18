"""Design B: understand once, judge everyone.

The trust circle is already a shortlist (127-147 entries per requirement in the
test set, at most a few hundred in production), so there is no retrieval stage
to lose people in. A model grades every eligible entry on skill fit alone, and
plain arithmetic handles years and place.

  write time   model reads each entry once -> role, other names, years, city, country
               (plus an embedding, used only for the large-pool shortlist and tie-breaks)
  query time   1. hard rules first (circle, audience, blocks, availability)
               2. model reads the requirement -> role, minimum years, place, in person or remote
               3. shortlist only when the pool is larger than SHORTLIST_OVER
               4. model grades every candidate 0-3 on skill fit (batches, can run in parallel)
               5. arithmetic: lower the grade for missing years or a different place
               6. order by grade, then how many entries vouch, then similarity; drop grade 0
               7. the reason shown to the user is built from the stored fields, no extra model call
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from common import PARALLEL, BM25, Entry, Meter, chat_json, cosine, decisions_call, embed, jev_call, parse_requirement, show_once

ENRICH_BATCH = 8
JUDGE_BATCH = 20
SHORTLIST_OVER = 200   # pools up to this size skip the shortlist
SHORTLIST_K = 100

ENRICH_SCHEMA = {
    "type": "object",
    "properties": {"profiles": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "role": {"type": "string"},
            "other_names": {"type": "array", "items": {"type": "string"}},
            "years": {"type": ["integer", "null"]},
            "city": {"type": ["string", "null"]},
            "country": {"type": ["string", "null"]},
        },
        "required": ["id", "role", "other_names", "years", "city", "country"]}}},
    "required": ["profiles"],
}

ENRICH_SYSTEM = """You turn short skill descriptions into small profiles. Return JSON only, one profile per id.
- role: what kind of work or activity this person does, in 2-4 plain words.
- other_names: up to 4 other common names for that role.
- years: years of experience as a whole number, only if the text states it; otherwise null.
- city: the city the person is in, only if the text states it; otherwise null.
- country: the country of that city; null when city is null.
Use only what the text says. Do not guess years or a city."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"grades": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "grade": {"type": "integer"}},
        "required": ["id", "grade"]}}},
    "required": ["grades"],
}

JUDGE_SYSTEM = """You judge whether each candidate does the kind of work a request asks for. Return JSON only.
Look only at the kind of work and the skills. Ignore years of experience and location; they are checked elsewhere.
Different words can mean the same work (a tool name, a synonym, an abbreviation). The same word can mean different work.
Grade every candidate:
3 = clearly does this kind of work
2 = probably does this kind of work, but the description is thin or only partly covers it
1 = a related or neighbouring kind of work
0 = a different kind of work, even if some words are the same
Give one grade per candidate id."""

# Same rubric as JUDGE_SYSTEM above, phrased per-candidate -- the Decisions
# API and Jev don't take a separate system prompt, only a shared `input`/
# `state` plus each question's own instructions.
JUDGE_LEVELS = [
    {"label": "different kind of work", "description": "even if some words are the same"},
    {"label": "related or neighbouring kind of work"},
    {"label": "does this kind of work, but the description is thin or only partly covers it"},
    {"label": "clearly does this kind of work"},
]
JUDGE_QUESTION_PREFIX = (
    "Look only at the kind of work and the skills; ignore years of experience and location, they are "
    "checked elsewhere. Different words can mean the same work (a tool name, a synonym, an abbreviation). "
    "The same word can mean different work. Candidate: "
)


class DesignB:
    name = "B"

    def __init__(self, entries: list[Entry], judge_backend: str = "chat") -> None:
        # "chat": existing gpt-6-luna chat completion, one JSON call per batch.
        # "decisions": OpenAI's Decisions API -- same model family, $0 output cost.
        # "jev": TypeSafe's Jev -- different model family, cheapest input price.
        # Only the judge step changes; write-time profiling, arithmetic,
        # dedup and ranking are identical across all three, so the cost
        # comparison isolates just this one call.
        self.judge_backend = judge_backend
        self.write_meter = Meter()
        # ---- write time: done once when an entry is saved
        self.profile: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
            list(ex.map(self._enrich, [entries[i:i + ENRICH_BATCH] for i in range(0, len(entries), ENRICH_BATCH)]))
        vecs = embed([e.text for e in entries], self.write_meter)
        self.vec = {e.id: v for e, v in zip(entries, vecs)}
        self.bm25 = BM25({e.id: e.text + " " + " ".join(self.profile[e.id]["other_names"]) for e in entries})

    def _enrich(self, batch: list[Entry]) -> None:
        ids = {f"c{i + 1}": e for i, e in enumerate(batch)}
        user = "\n".join(f"{cid}: {e.text}" for cid, e in ids.items())
        out, _ = chat_json(ENRICH_SYSTEM, user, ENRICH_SCHEMA, self.write_meter, tag="enrich")
        got = {p["id"]: p for p in out.get("profiles", []) if p.get("id") in ids}
        for cid, e in ids.items():
            p = got.get(cid)
            if p is None:
                self.write_meter.fallbacks += 1
                p = {"role": e.skills[0], "other_names": [], "years": None, "city": None, "country": None}
            self.profile[e.id] = p

    # ---- query time
    def match(self, req_text: str, pool: list[Entry], meter: Meter, req_meta: dict | None = None) -> tuple[list[str], dict]:
        if not pool:
            return [], {}
        need = parse_requirement(req_text, meter)
        meta = req_meta or {}
        # PRD v1.3: real stated fields beat the LLM's guess from free text,
        # both for the requirement and for each entry -- only fall back to
        # the guess when the real field is null.
        req_min_years = meta.get("min_experience_years") if meta.get("min_experience_years") is not None else need["min_years"]
        req_location = meta.get("location") or need["city"]
        qvec = embed([req_text], meter, kind="query")[0]
        cos = {e.id: cosine(qvec, self.vec[e.id]) for e in pool}

        if len(pool) > SHORTLIST_OVER:
            query = " ".join([req_text, need["role"], *need["other_names"], *need["skills"]])
            by_vec = sorted(pool, key=lambda e: -cos[e.id])
            by_kw = sorted(pool, key=lambda e: -self.bm25.score(query, e.id))
            fused = {e.id: 0.0 for e in pool}
            for ranking in (by_vec, by_kw):
                for i, e in enumerate(ranking):
                    fused[e.id] += 1.0 / (60 + i + 1)
            pool = sorted(pool, key=lambda e: -fused[e.id])[:SHORTLIST_K]

        # judge everyone: batches are independent, so they run in parallel when the provider allows it
        grade: dict[str, int] = {}

        def judge_chat(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            user = ("Request:\n" + req_text + "\n\nCandidates:\n"
                    + "\n".join(f"{cid}: {e.text}" for cid, e in ids.items()))
            out, secs = chat_json(JUDGE_SYSTEM, user, JUDGE_SCHEMA, meter, tag="judge")
            got = {g["id"]: g["grade"] for g in out.get("grades", []) if g.get("id") in ids}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                grade[e.id] = max(0, min(3, int(got.get(cid, 0))))
            return secs

        def judge_decisions(batch: list[Entry]) -> float:
            # "type": "score" was tried first -- it returns a continuous
            # expected value (e.g. 0.88, 0.93) instead of a discrete pick, and
            # that value is biased upward for the bottom level (probability
            # mass can only leak up from level 0, never down), so round()
            # pushed most true 0s to grade 1. "choice" returns a direct pick
            # from the given labels -- no averaging, no bias.
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            labels = [lvl["label"] for lvl in JUDGE_LEVELS]
            questions = [
                {
                    "type": "choice",
                    "name": cid,
                    "instructions": JUDGE_QUESTION_PREFIX + e.text,
                    "choices": [{"value": label} for label in labels],
                }
                for cid, e in ids.items()
            ]
            t0 = time.time()
            out = decisions_call(req_text, questions, meter, tag="judge")
            secs = time.time() - t0
            got = {a["name"]: labels.index(a["choice"]) for a in out.get("answers", [])
                   if a.get("name") in ids and a.get("choice") in labels}
            for cid, e in ids.items():
                if cid not in got:
                    meter.fallbacks += 1
                grade[e.id] = max(0, min(3, got.get(cid, 0)))
            return secs

        def judge_jev(batch: list[Entry]) -> float:
            ids = {f"c{j + 1}": e for j, e in enumerate(batch)}
            questions = {
                cid: {
                    "type": "score",
                    "instructions": JUDGE_QUESTION_PREFIX + e.text,
                    "criteria": [lvl["label"] for lvl in JUDGE_LEVELS],
                }
                for cid, e in ids.items()
            }
            t0 = time.time()
            out = jev_call(req_text, questions, meter, tag="judge")
            secs = time.time() - t0
            answers = out.get("answers", {})
            for cid, e in ids.items():
                a = answers.get(cid)
                if a is None or "score" not in a:
                    meter.fallbacks += 1
                    grade[e.id] = 0
                else:
                    grade[e.id] = max(0, min(3, round(a["score"])))
            return secs

        judge = {"chat": judge_chat, "decisions": judge_decisions, "jev": judge_jev}[self.judge_backend]

        batches = [pool[i:i + JUDGE_BATCH] for i in range(0, len(pool), JUDGE_BATCH)]
        with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
            times = list(ex.map(judge, batches))
        meter.stage(times)

        # arithmetic for years and place -- real stated fields (PRD v1.3)
        # beat the write-time LLM guess; the guess only fills in for an
        # entry that left experience_years / location null.
        final, why = {}, {}
        for e in pool:
            g, p, notes = grade[e.id], self.profile[e.id], []
            years = e.experience_years if e.experience_years is not None else p["years"]
            location = e.location or p["city"]
            if g >= 2:
                if req_min_years and years is not None and years < req_min_years:
                    short = req_min_years - years
                    g -= 1 if short <= 2 else 2
                    notes.append(f"{years} years, {req_min_years} asked")
                elif years is not None:
                    notes.append(f"{years} years")
                if need["work_mode"] in ("in_person", "hybrid") and req_location and location:
                    if _norm(location) != _norm(req_location):
                        # A single location string, not city+country, so this
                        # can't tell "same country" from "different country"
                        # the way the old city/country guess could -- one flat
                        # tier instead of two. Real location data is reliable
                        # enough that this trade is worth it.
                        g -= 1
                        notes.append(f"in {location}, work is in {req_location}")
                    else:
                        notes.append(f"in {location}")
                g = max(1, g)
            final[e.id] = g
            why[e.id] = "; ".join([p["role"], *notes])

        ranked = sorted([e for e in pool if final[e.id] > 0], key=lambda e: -final[e.id])
        _, vouches = show_once(ranked)
        ranked.sort(key=lambda e: (-final[e.id], -vouches[e.person_key], -cos[e.id]))
        people, _ = show_once(ranked)
        detail = {e.id: {"grade": final[e.id], "skill_grade": grade[e.id], "reason": why[e.id],
                         "vouches": vouches[e.person_key]} for e in people}
        return [e.id for e in people], detail


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())
