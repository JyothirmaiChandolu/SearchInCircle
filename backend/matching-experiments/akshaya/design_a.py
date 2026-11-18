"""Design A: retrieve, then rerank.

The colleague's pipeline with the changes proposed in the review:

  write time   one embedding per entry and one per skill, plus a keyword index
  query time   1. hard rules first (circle, audience, blocks, availability)
               2. model reads the requirement -> role, other names, skills (search terms only)
               3. keyword rank + vector rank, joined by reciprocal rank fusion (RRF)
               4. group by person, small boost when several entries vouch for one person
               5. model reranks the top RERANK_K: grade 0-3 and a one-line reason
               6. drop grade 0, order by grade then retrieval score

Flags turn parts off, to measure what each part adds:
  retrieval="vector"  vector search only (the pipeline as originally drawn)
  rerank=False        no model rerank; a fixed cosine cutoff decides who is shown
"""
from __future__ import annotations

from common import BM25, Entry, Meter, chat_json, cosine, embed, parse_requirement, show_once

RRF_K = 60            # standard RRF constant
RETRIEVE_K = 30       # entries kept after retrieval
RERANK_K = 15         # people sent to the model
VOUCH_BOOST = 0.10    # per extra entry about the same person
COSINE_CUTOFF = 0.62  # used only when rerank is off; not tuned on the answer key
NO_RERANK_SHOWN = 10

RERANK_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "grade": {"type": "integer"}, "reason": {"type": "string"}},
        "required": ["id", "grade", "reason"]}}},
    "required": ["results"],
}

RERANK_SYSTEM = """You judge how well each candidate fits a request for help. Return JSON only.
Each candidate has a short skill description plus explicit experience_years and location fields (stated facts, not guessed). Grade every candidate:
3 = does exactly this kind of work and meets what the request asks for
2 = does this kind of work but misses one thing the request asks for (experience_years below the request's min_experience_years, or a different location when the request's location is set)
1 = a related or neighbouring kind of work, or the right work but misses two or more things
0 = a different kind of work, even if some words are the same
A candidate whose experience_years or location is null is not marked down for it -- only a stated mismatch counts. A null request location means remote is fine.
Give one result per candidate id, with a reason of at most 12 words; name the actual year gap or city when that is why the grade dropped."""


class DesignA:
    name = "A"

    def __init__(self, entries: list[Entry], retrieval: str = "hybrid", rerank: bool = True) -> None:
        self.retrieval, self.rerank = retrieval, rerank
        self.write_meter = Meter()
        # ---- write time: done once when an entry is saved
        self.vecs: dict[str, list[list[float]]] = {}
        texts, owners = [], []
        for e in entries:
            texts.append(e.text)
            owners.append(e.id)
            if len(e.skills) > 1:                      # one extra row per skill, so a mixed tag is not blurred
                for s in e.skills:
                    texts.append(s)
                    owners.append(e.id)
        for eid, v in zip(owners, embed(texts, self.write_meter)):
            self.vecs.setdefault(eid, []).append(v)
        self.bm25 = BM25({e.id: e.text for e in entries})

    # ---- query time
    def match(self, req_text: str, pool: list[Entry], meter: Meter, req_meta: dict | None = None) -> tuple[list[str], dict]:
        if not pool:
            return [], {}
        qvec = embed([req_text], meter, kind="query")[0]
        cos = {e.id: max(cosine(qvec, v) for v in self.vecs[e.id]) for e in pool}
        by_vec = sorted(pool, key=lambda e: -cos[e.id])
        fused = {e.id: 1.0 / (RRF_K + i + 1) for i, e in enumerate(by_vec)}

        parsed = {}
        if self.retrieval == "hybrid":
            parsed = parse_requirement(req_text, meter)
            query = " ".join([req_text, parsed["role"], *parsed["other_names"], *parsed["skills"]])
            kw = {e.id: self.bm25.score(query, e.id) for e in pool}
            by_kw = sorted([e for e in pool if kw[e.id] > 0], key=lambda e: -kw[e.id])
            for i, e in enumerate(by_kw):
                fused[e.id] += 1.0 / (RRF_K + i + 1)

        top = sorted(pool, key=lambda e: -fused[e.id])[:RETRIEVE_K]
        people, vouches = show_once(top)
        score = {e.id: fused[e.id] * (1 + VOUCH_BOOST * (vouches[e.person_key] - 1)) for e in people}
        people.sort(key=lambda e: -score[e.id])

        if not self.rerank:
            shown = [e for e in people if cos[e.id] >= COSINE_CUTOFF][:NO_RERANK_SHOWN]
            return [e.id for e in shown], {e.id: {"cosine": round(cos[e.id], 3)} for e in shown}

        short = people[:RERANK_K]
        ids = {f"c{i + 1}": e for i, e in enumerate(short)}
        meta = req_meta or {}
        user = ("Request:\n" + req_text
                + f"\nmin_experience_years: {meta.get('min_experience_years')}"
                + f"\nlocation: {meta.get('location')} (null means remote is fine)"
                + "\n\nCandidates:\n"
                + "\n".join(
                    f"{cid}: {e.text} | experience_years: {e.experience_years} | location: {e.location}"
                    for cid, e in ids.items()
                ))
        out, secs = chat_json(RERANK_SYSTEM, user, RERANK_SCHEMA, meter, tag="rerank")
        meter.stage([secs])
        graded = {r["id"]: r for r in out.get("results", []) if r.get("id") in ids}
        if len(graded) < len(ids):                    # model failed or skipped some: fall back to the cosine cutoff
            meter.fallbacks += 1
            for cid, e in ids.items():
                graded.setdefault(cid, {"grade": 2 if cos[e.id] >= COSINE_CUTOFF else 0, "reason": "similar wording"})
        rows = [(max(0, min(3, int(graded[cid]["grade"]))), score[e.id], e, graded[cid]["reason"])
                for cid, e in ids.items()]
        rows = sorted([r for r in rows if r[0] > 0], key=lambda r: (-r[0], -r[1]))
        detail = {e.id: {"grade": g, "reason": why, "vouches": vouches[e.person_key]} for g, _, e, why in rows}
        return [e.id for _, _, e, _ in rows], detail
