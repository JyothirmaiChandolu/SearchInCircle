from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).resolve().parent
# matching-prototype/matcher -> matching-prototype -> repo root -> data/matching-testset
# A deploy bundle ships its own small dataset next to the app (matching-prototype/data/);
# locally the repo's full test set is used.
_BUNDLED_DATA = (HERE / '..' / 'data').resolve()
DATASET_DIR = _BUNDLED_DATA if (_BUNDLED_DATA / 'users.json').exists() else (HERE / '..' / '..' / 'data' / 'matching-testset').resolve()


@dataclass(frozen=True)
class Config:
    openai_api_key: str | None
    embedding_model: str
    rerank_model: str
    rerank_enabled: bool
    min_similarity: float
    top_k: int
    weight_similarity: float
    weight_trust: float
    weight_recency: float
    weight_vouch: float
    recency_half_life_days: int


def load_config() -> Config:
    return Config(
        openai_api_key=os.environ.get('OPENAI_API_KEY'),
        embedding_model=os.environ.get('MATCHING_EMBEDDING_MODEL', 'text-embedding-3-small'),
        # Cheapest chat-capable OpenAI model as of Nov 2026. If it's retired
        # or misbehaves, switch MATCHING_RERANK_MODEL in .env to
        # gpt-4.1-nano or gpt-4o-mini -- nothing else here needs to change.
        rerank_model=os.environ.get('MATCHING_RERANK_MODEL', 'gpt-5-nano'),
        rerank_enabled=os.environ.get('MATCHING_LLM_RERANK', 'true').lower() == 'true',
        min_similarity=float(os.environ.get('MATCHING_MIN_SIMILARITY', '0.15')),
        top_k=int(os.environ.get('MATCHING_TOP_K', '10')),
        weight_similarity=float(os.environ.get('MATCHING_WEIGHT_SIMILARITY', '0.7')),
        weight_trust=float(os.environ.get('MATCHING_WEIGHT_TRUST', '0.15')),
        weight_recency=float(os.environ.get('MATCHING_WEIGHT_RECENCY', '0.1')),
        weight_vouch=float(os.environ.get('MATCHING_WEIGHT_VOUCH', '0.05')),
        recency_half_life_days=int(os.environ.get('MATCHING_RECENCY_HALF_LIFE_DAYS', '180')),
    )
