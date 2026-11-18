# Jyoti's matching workflow: results

Code lives in `matching-prototype/` (repo root), not inside this folder, so it can also run as a standalone FastAPI test page — see that folder's own README for setup and the live UI.

## v2 update (2026-11-14)

Re-run against the merged v2 dataset (37 requirements, 4,130 entries, `experience_years`/`location` fields on entries and requirements). `rerank.py`'s prompt and payload now use those real fields directly (never guessed from text) for both ours and Akshaya's A0/A1/A/B.

| Metric | Baseline | A0 | A1 | A | **B** | Ours |
|---|---|---|---|---|---|---|
| Hidden people shown | 0 | 0 | 0 | 0 | 0 | 0 |
| nDCG@10 | 0.759 | 0.711 | 0.934 | 0.921 | **0.962** | 0.881 |
| Precision@10 | 0.781 | 0.674 | 0.963 | 0.960 | **0.986** | 0.900 |
| Recall (whole list) | 0.692 | 0.426 | 0.702 | 0.723 | **0.970** | 0.595 |
| Precision (whole list) | 0.878 | 0.971 | 0.996 | **1.000** | 0.840 | 0.938 |
| Synonym-only found | 29/101 | 17/101 | 39/101 | 37/101 | **83/101** | 26/101 |
| Show once | 16/37 | 25/25 | 34/34 | 34/34 | 51/51 | 30/30 |

Same conclusion as v1, wider gap now the test set is bigger and harder: **B wins clearly**, especially recall and synonym-only (83/101 vs our 26/101) — the no-retrieval-ceiling advantage described in Akshaya's `RESULTS.md` holds at this scale too.

Cost/time for this regeneration (all real OpenAI calls, `text-embedding-3-small` + `gpt-5-nano`):
- Ours: 37 requirements, $0.0084 total, ~106s wall-clock.
- One real finding from this run: a naive attempt to thread the write-time embedding step (large per-chunk payloads) made it **9x slower** (3566s vs 376s sequential) in this environment, not faster — reverted. Threading the per-requirement *rerank/judge* calls (small, independent) was safe and gave a real speedup instead, used in both `run.py` (Akshaya's designs) and `run_against_testset.py` (ours, two-pass: sequential embedding, then threaded rerank).

## Design C — full-pool judge, then a second rerank call (not yet scored)

Added `design_c.py` per an explicit request to compare costs if nothing is capped before the model: keyword+vector RRF fusion over the **whole** eligible pool (no `SHORTLIST_K` cutoff like B uses above 200 entries), every survivor of a skill-fit judge call then gets a **second**, separate model call that scores years/location fit (B does this with plain arithmetic instead — one model call, not two).

Flagging the known cost risk before anyone runs `run.py C`/`C_decisions`/`C_jev` against the full v2 set: B's own `SHORTLIST_OVER=200` threshold exists because judging an uncapped pool scales LLM calls linearly with pool size (127-147 entries per requirement here; unbounded in production as entries grow). Design C intentionally skips that cap, and adds a second full round of calls on top for rerank — expect this to be the most expensive design in the comparison, by design, not by mistake. Not yet run against the test set or added to `compare.py`'s table above; do that before drawing any accuracy/cost conclusion about it.

## Design (original, v1)

Closest to Akshaya's **A1** (retrieve, then rerank), not her B:

## Design

Closest to Akshaya's **A1** (retrieve, then rerank), not her B:

```
write time   nothing stored yet (no DB wiring) -- embeddings computed and
             disk-cached per run, keyed by (model, text)
query time   1. hard rules first (circle, audience, blocks, availability,
                own-entry handling, staleness window) -- plain code
             2. embed the requirement + every eligible entry
                (text-embedding-3-small)
             3. cosine similarity, collapse duplicate taggings of the same
                person into one ("show once"), combine with a flat trust
                score + recency decay + vouch-count boost
             4. drop anything below a similarity floor, keep top 10
             5. optional: send that top-10 shortlist to gpt-5-nano
                (reasoning_effort=minimal, seed=42) to reorder + add a
                one-line reason. Never allowed to invent or drop an id;
                any failure falls back to step 4's order silently.
```

No write-time LLM profiling (role/years/city extraction) like Design B does. Years/location aren't parsed out of free text at all yet -- that's the main capability gap versus B.

## Accuracy (OpenAI, compared via `../compare.py`)

| Metric | Baseline | A0 | A1 | A | B | **Jyoti** |
|---|---|---|---|---|---|---|
| Hidden people shown | 0 | 0 | 0 | 0 | 0 | **0** |
| nDCG@5 | 0.833 | 0.813 | 0.983 | 0.984 | **1.000** | 0.95-0.98 (seed variance) |
| Precision@5 | 0.840 | 0.813 | 1.000 | 1.000 | 1.000 | **0.987** |
| Recall@10 | 0.718 | 0.609 | 0.884 | 0.869 | **0.911** | 0.87-0.88 |
| Synonym-only found | 2/15 | 5/15 | 10/15 | 9/15 | **14/15** | 10-11/15 |
| Lexical traps in top 5 | 0 | 0 | 0 | 0 | 0 | **0** |
| Show once | 3/13 | 12/12 | 15/15 | 15/15 | 15/15 | **15/15** |
| Empty cases (R12, R13) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | **2/2** |

Tracks A1 closely, as expected -- same shape of pipeline (vector retrieve, then LLM rerank), different model (`gpt-5-nano` here vs Akshaya's `gpt-6-luna`) and a smaller rerank window (top 10, not top 15).

## Cost and speed

| | Jyoti |
|---|---|
| Model calls at match time | 1 embed + 1 rerank per requirement |
| Tokens in/out (rerank, avg) | ~960 in / ~330 out |
| Cost per requirement | ~$0.00018 (rerank) + negligible embedding |
| Full 17-requirement run | **$0.0029 total** |
| Seconds per requirement (rerank only, after the reasoning_effort fix) | ~1.5-2s |

Found one real bug while measuring this: `gpt-5-nano` defaults to deep internal reasoning even for trivial output (347 tokens, 320 of them hidden reasoning, on a one-line test call) -- this silently blew past an 8s client timeout on every single rerank call in the first real run, falling back to embedding-only order without erroring. Fixed with `reasoning_effort='minimal'`, which cut that same test call to 24 tokens / 1.4s. Logging (added specifically to catch this) is what surfaced it -- worth flagging for anyone else using a `gpt-5-*` model for a similarly small task.

## Where this loses to B

Design B judges **every** eligible entry with the model; this design only reranks whatever cosine similarity already put in the top 10. If the right person scores outside the top 10 on raw embedding similarity (plausible for a synonym-only match with no keyword overlap at all), this design never gets a chance to find them -- B doesn't have that ceiling. That's almost certainly the whole gap in synonym recall (10-11/15 vs B's 14/15) and Akshaya's grade-2-cutoff test (RESULTS.md's harder scenario): B stays accurate under a stricter relevance bar, retrieve-then-rerank designs lose more.

## Recommendation

Agree with Akshaya's RESULTS.md: **B is the stronger design** for production, precisely because it has no retrieval ceiling. This design (A1-shaped) is simpler and already has a working standalone test page (`matching-prototype/`), which made it useful for validating the hard-rule logic (eligibility, trust, dedup) independently -- those rules are identical in spirit to B's, just implemented separately. If B becomes the adopted design, this folder's eligibility/trust/dedup code (`matching-prototype/matcher/eligibility.py`, `dedup.py`) is directly reusable as-is; only the scoring step (embed+rerank-top-K vs profile+judge-everyone) would need to change.
