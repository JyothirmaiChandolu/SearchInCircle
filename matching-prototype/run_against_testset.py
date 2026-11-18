#!/usr/bin/env python3
"""Real OpenAI-embeddings matcher, scored the same way as
data/matching-testset/baseline_keyword.py.

Usage:
    cd matching-prototype
    python3 run_against_testset.py > predictions_openai.json
    cd ../data/matching-testset
    python3 evaluate.py ../../matching-prototype/predictions_openai.json
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from matcher.config import DATASET_DIR, load_config  # noqa: E402
from matcher.data_loader import Dataset  # noqa: E402
from matcher.embeddings import EmbeddingClient  # noqa: E402
from matcher.pipeline import run_pipeline_for_requirement  # noqa: E402
from matcher.rerank import LlmReranker  # noqa: E402
from matcher.usage import UsageTracker  # noqa: E402

# Two passes on purpose, not one threaded loop:
#
# Pass 1 (sequential): embedding. Our EmbeddingClient sends every eligible
# candidate's text in ONE unchunked API call per requirement -- a big circle
# (one pool hit 605 entries against this dataset) makes that call far larger
# than Akshaya's 64-item chunks, which already got measurably SLOWER under
# concurrency in this environment (see akshaya/common.py's _embed_raw
# comment). Running several of these large calls at once would very likely
# repeat that, just worse. So embedding stays sequential here.
#
# Pass 2 (threaded): rerank. Once embeddings exist, reranking one
# requirement's already-short shortlist is a single small completion --
# same safe shape as Akshaya's per-requirement loop in run.py. Threading
# just this part is where the real wall-clock win is.
RERANK_WORKERS = 4


def main() -> None:
    config = load_config()
    if not config.openai_api_key:
        print('OPENAI_API_KEY is not set -- add it to matching-prototype/.env', file=sys.stderr)
        sys.exit(1)

    dataset = Dataset(DATASET_DIR)
    usage = UsageTracker(embedding_model=config.embedding_model, rerank_model=config.rerank_model)
    embedder = EmbeddingClient(config.openai_api_key, config.embedding_model, usage=usage)
    reranker = LlmReranker(config.openai_api_key, config.rerank_model, usage=usage) if config.rerank_enabled else None

    # Pass 1: sequential embedding + base ranking, no rerank yet.
    pre_rerank: dict[str, dict] = {}
    for requirement in dataset.requirements:
        print(f"\n=== {requirement['id']}: {requirement['text'][:80]}... ===", file=sys.stderr)
        result = run_pipeline_for_requirement(dataset, config, embedder, requirement, reranker=None)
        pre_rerank[requirement['id']] = result
        print(f"[matching] {requirement['id']}: {len(result['matches'])} match(es), status={result['status']}", file=sys.stderr)

    # Pass 2: rerank every non-empty shortlist concurrently.
    def rerank_one(requirement: dict) -> tuple[str, list[str]]:
        result = pre_rerank[requirement['id']]
        matches = result['matches']
        if reranker and matches:
            meta = {'location': requirement.get('location'), 'min_experience_years': requirement.get('min_experience_years')}
            matches = reranker.rerank(requirement['text'], matches, requirement_meta=meta)
        return requirement['id'], [m['entry_id'] for m in matches]

    out: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=RERANK_WORKERS) as ex:
        for req_id, ids in ex.map(rerank_one, dataset.requirements):
            out[req_id] = ids

    print('\n' + '=' * 60, file=sys.stderr)
    print(f'[run] {len(dataset.requirements)} requirement(s) processed', file=sys.stderr)
    print(usage.summary(), file=sys.stderr)
    print('=' * 60, file=sys.stderr)

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
