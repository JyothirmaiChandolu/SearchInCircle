# Matching prototypes: results

Run on 2026-11-13 against `data/matching-testset` (17 requirements, 448 entries, seed 42).
Final run: OpenAI `gpt-6-luna` (reasoning effort none) for model steps, `text-embedding-3-small` for embeddings.
An earlier run on local models (`qwen3:8b`, `nomic-embed-text`) is kept in `out/` for comparison.

## What was compared

| Variant | What it does |
|---|---|
| Baseline | Keyword overlap (`baseline_keyword.py`) |
| A0 | Vector search only, fixed cosine cutoff, no model call |
| A1 | Vector search, then a model reranks the top 15. This is the colleague's pipeline with its optional rerank on |
| A | Keyword + vector search joined by RRF, then a model reranks the top 15. The colleague's pipeline with my review changes |
| **B** | The new design. A model profiles each entry when it is saved. At match time a model grades every eligible entry on skill fit, and plain arithmetic handles years and place |

All variants share the same hard rules (circle, audience, blocks, availability), applied in code before any model call, and the same "show once" merge. The answer key was never read while building.

## Accuracy (OpenAI)

| Metric | Baseline | A0 | A1 | A | B |
|---|---|---|---|---|---|
| Hidden people shown | 0 | 0 | 0 | 0 | 0 |
| nDCG@5 | 0.833 | 0.813 | 0.983 | 0.984 | **1.000** |
| Precision@5 | 0.840 | 0.813 | 1.000 | 1.000 | 1.000 |
| Recall@10 | 0.718 | 0.609 | 0.884 | 0.869 | **0.911** |
| Synonym-only people found | 2/15 | 5/15 | 10/15 | 9/15 | **14/15** |
| Lexical traps in the top 5 | 0 | 0 | 0 | 0 | 0 |
| Show once | 3/13 | 12/12 | 15/15 | 15/15 | 15/15 |
| Empty cases (R12, R13) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

Local-model run for comparison (nDCG@5 / Recall@10 / synonyms): A1 0.995 / 0.846 / 13 of 15, A 0.993 / 0.823 / 13 of 15, B 0.993 / 0.885 / 14 of 15.

## Accuracy when only strong and good matches are shown (grade 2 and 3)

FR-49 asks for a minimum relevance cutoff. Each variant grades its people 0 to 3, so I re-scored with grade 1 ("related") hidden.

| Metric | A1 | A | B |
|---|---|---|---|
| nDCG@5 | 0.878 | 0.914 | **0.991** |
| Recall@10 | 0.585 | 0.619 | **0.852** |
| Synonym-only people found | 3/15 | 2/15 | **14/15** |
| People shown (all requirements) | 98 | 102 | 142 |
| People shown for R12 (should be none) | 0 | 0 | 0 |

A's reranker judges years and place itself, and it marks people down to grade 1 for them. The answer key still counts those people as good (relevance 2). B grades skill only and subtracts years and place in code, so a cutoff at grade 2 hurts it far less.

## Cost and speed, per requirement (average over the 16 open requirements)

| | A0 | A1 | A | B |
|---|---|---|---|---|
| Model calls | 0 | 1 | 2 | 7.1 |
| Tokens in / out | 0 | 686 / 407 | 991 / 467 | 4,818 / 1,146 |
| Cost at `gpt-6-luna` list price ($0.10 in, $0.50 out per 1M tokens) | about $0 | $0.00027 | $0.00033 | $0.00105 |
| Seconds, all model steps added up (embedding not counted) | 0 | 4.7 | 6.7 | 6.2 with batches in parallel (23.0 one after another) |

- B's write-time work (profiling each entry) costs about $0.011 for all 448 entries, or $0.00002 per entry saved.
- Embedding all 448 entries costs well under a cent.
- Cost figures are calculated from token counts and list prices. They are not billed amounts.
- Seconds are measured on single calls with no other load. They are close to the 5-second target (NFR-01), and none of the designs includes the database query, notifications or network time. Treat the time as a rough guide, not a pass.
- At 1,000 requirements a month, A1 costs about $0.27 and B about $1.05 in model fees.

## Complexity

| | A | B |
|---|---|---|
| Code (design file) | 109 lines | 168 lines |
| Stored per entry | embedding per entry and skill, keyword index | profile (role, other names, years, city, country), embedding, keyword index |
| Background jobs on save | embed | embed, model profile |
| Settings to tune | 5 (RRF constant, retrieve size, rerank size, vouch boost, cosine cutoff) | 2 active (judge batch size, penalty sizes) |
| Model calls at match time | 2 | 7, growing by one per 20 entries in the circle |
| Reason shown to the user | written by the model | built from stored fields, no extra model call |

## What the numbers say

1. **B is the most accurate on every measure**, and its lead is largest on synonym-only people (14/15 against 9 to 10/15) and when a relevance cutoff is applied.
2. **The model rerank matters most.** Vector search alone drops below the keyword baseline on OpenAI embeddings (nDCG 0.813). Adding the rerank lifts it to 0.983.
3. **My keyword addition did not help.** A is level with A1 on ranking and slightly lower on recall, and it costs one more model call. This test has few short codes like "CA" or "GST", where keyword search usually helps, so real data may differ.
4. **B costs about 4 times A1 in model fees.** That is about one-tenth of a cent per requirement.
5. **The test set is small.** 17 requirements, and the top-5 scores of A1, A and B are within 0.02 of each other. The clear gaps are recall, synonyms and the grade-2 cutoff.

## Problems found

- **B shows many weak matches.** With grade 1 included it showed 270 people against 175 for A1, and for R12 (harp teacher, expects no one) it showed 5 related people, such as a guitar coach and Telugu teachers. The evaluator passes this, but a user would not like it. Fix: show grade 2 and above (see the cutoff table, where B shows no one for R12).
- **The model sometimes answered in prose, not JSON.** This happened once in the first B run, and the 20 candidates in that batch were silently graded 0. I added one retry. In production, count and alert on this, because a silent 0 hides a good person.
- **Not tested:** pools over 200 entries (the shortlist path), the reverse path (new tag against open requirements), repeat runs for variation, and load or rate limits.
- The local `qwen3:8b` model over-graded in B (a guitar coach got grade 3 for a harp request). The OpenAI model does not.

## Recommendation: choose B

- It finds the most good people and the most synonym-only people, which is the worst error for this product to make in a small trusted circle.
- It still works when a relevance cutoff is applied. A and A1 lose about a third of their recall.
- Years and place are plain code, so they are testable and the reasons shown to the user cost no model call.
- It costs about $0.001 per requirement. That is affordable at pilot volume.

Before the final decision:
1. Set the cutoff to grade 2 and above (FR-49), and check with the product owner whether "related" people (grade 1) should ever appear.
2. Measure real latency in the backend, including the database query. B needs batches to run in parallel to stay near 6 seconds. Consider a smaller judge batch or a faster model if the 5-second target is firm.
3. Test the reverse path and the shortlist path, and rerun with several seeds.

If the 5-second target cannot be met, **A1** is the fallback: vector search plus model rerank, hard rules first, no keyword search. It is fastest (4.7 seconds) and cheapest of the model-backed variants, but expect lower recall.

## Model choice

- Chat: `gpt-6-luna`, reasoning effort `none`. It is OpenAI's cheapest current model and it passed these tasks. If a harder test shows over-grading, try `gpt-6.1-terra` for the judge step only.
- Embeddings: `text-embedding-3-small`.
- Not compared: other OpenAI models. Only `gpt-6-luna` was run, so "suitable" means it works well enough, not that it is the best choice.

## Run it

```bash
cd backend/matching-experiments/akshaya
python3.12 run.py all        # uses OPENAI_API_KEY from .env; results in out-openai/
```

Settings: `MATCH_CHAT_MODEL`, `MATCH_EMBED_MODEL`, `MATCH_REASONING`, `MATCH_PROVIDER=ollama`.
Calls are cached per model in `.cache/`, so a rerun costs nothing.
