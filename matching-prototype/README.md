# Matching prototype (Python, real OpenAI)

Standalone test harness for the matching engine, using real OpenAI
embeddings + a cheap LLM rerank. Separate from the TypeScript module in
`backend/src/matching/` — that one's the eventual production target (NestJS,
Prisma); this is for fast iteration and manual testing against
`data/matching-testset/` before wiring anything into the real app.

The eligibility rules (`matcher/eligibility.py`, `matcher/dedup.py`) are a
direct port of the already-tested TypeScript logic — same hard rules, same
show-once dedup — so results are comparable across both implementations.

## 1. Add your key

```bash
cd matching-prototype
cp .env.example .env
```

Open `.env` and set:

```
OPENAI_API_KEY=sk-...
```

Everything else in `.env` already has sensible defaults (cheapest models,
ranking weights) — see the comments in `.env.example`.

## 2. Install (one-time)

```bash
cd matching-prototype
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Score it against the labelled test set

```bash
source .venv/bin/activate
python3 run_against_testset.py > predictions_openai.json
cd ../data/matching-testset
python3 evaluate.py ../../matching-prototype/predictions_openai.json
```

Compare the `mean_ndcg` / `synonym_recall` / `mean_recall_at_10` numbers
against the keyword baseline documented in that folder's README — this is
the real test of whether semantic embeddings actually help.

First run embeds all ~450 fixture entries once (a few cents, text-embedding-3-small
is $0.02/1M tokens) and caches them to `matcher/.embedding_cache.json`
(gitignored). Every run after that only re-embeds the one requirement text.

## 4. Try it in the browser

```bash
source .venv/bin/activate
uvicorn app:app --reload --port 8000
```

Open http://127.0.0.1:8000 — pick a publisher from the dropdown (these are
the existing sample profiles in `data/matching-testset/users.json`, so you
don't need to create anything), type a requirement, hit **Find matches**.
Toggle "Use LLM rerank" to compare the embedding-only ranking against the
LLM's reordering + one-line reasons.

## Models (cheapest available, Nov 2026)

| Step | Model | Price (per 1M tokens) |
|---|---|---|
| Embedding | `text-embedding-3-small` | $0.02 input |
| Rerank | `gpt-5-nano` | $0.05 input / $0.40 output |

Both are env vars (`MATCHING_EMBEDDING_MODEL`, `MATCHING_RERANK_MODEL`) —
if `gpt-5-nano` gets retired or misbehaves, swap in `gpt-4.1-nano` or
`gpt-4o-mini` in `.env`, nothing else changes. Set `MATCHING_LLM_RERANK=false`
to skip the LLM step entirely and only use embedding similarity.

## What the LLM rerank step actually does

`matcher/rerank.py` sends it only the shortlist the embedding step already
ranked — it can reorder and add a one-sentence reason per candidate, but can
never invent or drop an id. Any failure (timeout, bad JSON, the model
hallucinating an id) silently falls back to the pre-LLM order, so this step
can never make a result *worse* than not having it.

## Where this plugs into the real app later

Nothing here touches `backend/` or `frontend/`. Once you're happy with the
scores, the plan is: port the same `matcher/pipeline.py` logic into
`backend/src/matching/adapters/embedding/openai-embedding.provider.ts`
(already written, just untested against real traffic) and the equivalent
LLM reranker there, then switch `MatchingService` to use them instead of
the offline defaults. The eligibility/dedup/ranking rules don't change —
only which embedding/LLM calls back them.
