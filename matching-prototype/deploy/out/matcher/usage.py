from __future__ import annotations

from dataclasses import dataclass

# USD per 1M tokens, Nov 2026. Keep in sync with README.md if models change.
PRICES: dict[str, dict[str, float]] = {
    'text-embedding-3-small': {'input': 0.02, 'output': 0.0},
    'gpt-5-nano': {'input': 0.05, 'output': 0.40},
    'gpt-4.1-nano': {'input': 0.10, 'output': 0.40},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
}


def _cost(model: str, input_tokens: int, output_tokens: int = 0) -> float | None:
    price = PRICES.get(model)
    if price is None:
        return None  # unknown model -- report "unknown", never a silently-wrong $0.00
    return (input_tokens * price['input'] + output_tokens * price['output']) / 1_000_000


def format_cost(cost: float | None) -> str:
    return f'${cost:.6f}' if cost is not None else 'unknown (model not priced in matcher/usage.py)'


@dataclass
class UsageTracker:
    """Accumulates real OpenAI usage across a run (or a server's lifetime).
    Cache hits are never charged -- only actual API calls add tokens here."""

    embedding_model: str
    rerank_model: str
    embedding_input_tokens: int = 0
    embedding_calls: int = 0
    embedding_cache_hits: int = 0
    rerank_input_tokens: int = 0
    rerank_output_tokens: int = 0
    rerank_calls: int = 0

    def record_embedding(self, input_tokens: int) -> float | None:
        self.embedding_calls += 1
        self.embedding_input_tokens += input_tokens
        return _cost(self.embedding_model, input_tokens)

    def record_cache_hits(self, count: int) -> None:
        self.embedding_cache_hits += count

    def record_rerank(self, input_tokens: int, output_tokens: int) -> float | None:
        self.rerank_calls += 1
        self.rerank_input_tokens += input_tokens
        self.rerank_output_tokens += output_tokens
        return _cost(self.rerank_model, input_tokens, output_tokens)

    @property
    def embedding_cost(self) -> float | None:
        return _cost(self.embedding_model, self.embedding_input_tokens)

    @property
    def rerank_cost(self) -> float | None:
        return _cost(self.rerank_model, self.rerank_input_tokens, self.rerank_output_tokens)

    @property
    def total_cost(self) -> float | None:
        e, r = self.embedding_cost, self.rerank_cost
        return None if e is None or r is None else e + r

    def summary(self) -> str:
        return (
            f'[usage] embedding ({self.embedding_model}): {self.embedding_calls} call(s), '
            f'{self.embedding_cache_hits} cache hit(s), {self.embedding_input_tokens} token(s), '
            f'cost {format_cost(self.embedding_cost)}\n'
            f'[usage] rerank ({self.rerank_model}): {self.rerank_calls} call(s), '
            f'{self.rerank_input_tokens} in / {self.rerank_output_tokens} out token(s), '
            f'cost {format_cost(self.rerank_cost)}\n'
            f'[usage] TOTAL cost so far: {format_cost(self.total_cost)}'
        )
