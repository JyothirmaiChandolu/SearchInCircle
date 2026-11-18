from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from openai import OpenAI

from .usage import UsageTracker, format_cost

CACHE_PATH = Path(__file__).resolve().parent / '.embedding_cache.json'

# OpenAI's embeddings endpoint rejects more than 2048 inputs per request
# (and caps total tokens per request); 1000 short entries stays well under both.
EMBED_BATCH = 1000


class EmbeddingClient:
    """OpenAI embeddings with a disk cache keyed by (model, text) -- the
    fixture pool (~470 entries) never changes between runs, so without this
    every script run or web request would re-pay for the same embeddings."""

    def __init__(self, api_key: str, model: str, usage: UsageTracker | None = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.usage = usage
        self._cache: dict[str, list[float]] = {}
        if CACHE_PATH.exists():
            try:
                self._cache = json.loads(CACHE_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def _key(self, text: str) -> str:
        return hashlib.sha256(f'{self.model}::{text}'.encode()).hexdigest()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float] | None] = [None] * len(texts)
        to_fetch: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cached = self._cache.get(self._key(text))
            if cached is not None:
                results[i] = cached
            else:
                to_fetch.append((i, text))

        cache_hits = len(texts) - len(to_fetch)
        if self.usage:
            self.usage.record_cache_hits(cache_hits)

        if to_fetch:
            print(f'[embeddings] requesting {len(to_fetch)} new embedding(s), {cache_hits} served from cache', file=sys.stderr)
            tokens = 0
            for start in range(0, len(to_fetch), EMBED_BATCH):
                chunk = to_fetch[start:start + EMBED_BATCH]
                response = self.client.embeddings.create(model=self.model, input=[t for _, t in chunk])
                for (i, text), item in zip(chunk, response.data):
                    results[i] = item.embedding
                    self._cache[self._key(text)] = item.embedding
                tokens += response.usage.total_tokens if getattr(response, 'usage', None) else 0
            self._save_cache()

            cost = self.usage.record_embedding(tokens) if self.usage else None
            print(f'[embeddings] used {tokens} token(s), cost {format_cost(cost)}', file=sys.stderr)
        elif cache_hits:
            print(f'[embeddings] all {cache_hits} embedding(s) served from cache, no API call', file=sys.stderr)

        return results  # all slots are filled by now

    def embed_one(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.write_text(json.dumps(self._cache))
        except OSError:
            pass  # cache is a pure optimisation -- never fail a request over it


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
