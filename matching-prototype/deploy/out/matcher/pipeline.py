from __future__ import annotations

import datetime as dt
import math
import sys

from .config import Config
from .data_loader import Dataset
from .dedup import person_key
from .eligibility import check_basic_eligibility, check_circle_eligibility, resolve_blocks, resolve_connections
from .embeddings import EmbeddingClient, cosine_similarity
from .rerank import LlmReranker


def _content_for(kind: str, entry: dict) -> str:
    if kind == 'self_entry':
        parts = [entry.get('skill', ''), entry.get('description') or '']
    else:
        parts = [*(entry.get('skills') or []), entry.get('description') or '']
    return '. '.join(p.strip() for p in parts if p and p.strip())


def display_name_for(kind: str, entry: dict, viewer_id: str) -> str:
    # FR-17: an alias is shown to everyone except the tag's own creator. The
    # publisher is always the "viewer" here, since they're who sees the list.
    if kind == 'self_entry':
        return 'Circle member'
    alias = entry.get('alias')
    if alias and entry.get('owner_user_id') != viewer_id:
        return alias
    full_name = f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip()
    return full_name or alias or 'Unnamed contact'


def _recency_score(iso_date: str | None, reference_date: str, half_life_days: int) -> float:
    if not iso_date:
        return 0.5  # no timestamp to judge by -- stay neutral
    ref = dt.date.fromisoformat(reference_date)
    last = dt.date.fromisoformat(iso_date)
    age_days = max(0, (ref - last).days)
    return 0.5 ** (age_days / half_life_days)


def _trust_score(owner_id: str, publisher_id: str) -> float:
    # Flat for now -- richer trust tiers need connection-strength data
    # (mutual connections, interaction history) this system doesn't collect yet.
    return 1.0 if owner_id == publisher_id else 0.8


def _build_reasons(similarity: float, trust: float, recency: float, vouch_count: int) -> list[str]:
    reasons = []
    if similarity >= 0.75:
        reasons.append('Strong skill match')
    elif similarity >= 0.5:
        reasons.append('Good skill match')
    else:
        reasons.append('Possible skill match')
    reasons.append('Your own contact' if trust >= 1 else 'Trusted connection')
    if vouch_count > 1:
        reasons.append(f'Vouched by {vouch_count} people in your circle')
    if recency >= 0.8:
        reasons.append('Recently confirmed available')
    return reasons


def run_pipeline(
    dataset: Dataset,
    config: Config,
    embedder: EmbeddingClient,
    publisher_id: str,
    requirement_text: str,
    reranker: LlmReranker | None = None,
    audience_user_ids: list[str] | None = None,
    requirement_location: str | None = None,
    requirement_min_experience_years: int | None = None,
) -> list[dict]:
    rules = dataset.rules
    connections = resolve_connections(dataset.connections)
    blocks = resolve_blocks(dataset.blocks)
    audience = audience_user_ids or []

    total_entries = 0
    eligible: list[tuple[str, dict, str]] = []
    for kind, entry in dataset.entries():
        total_entries += 1
        owner_id = entry['owner_user_id']
        is_own_tag = kind == 'tag' and owner_id == publisher_id
        circle_verdict = check_circle_eligibility(owner_id, publisher_id, is_own_tag, connections, blocks, audience, rules)
        if not circle_verdict.eligible:
            continue
        basic_verdict = check_basic_eligibility(kind, entry, publisher_id, rules)
        if not basic_verdict.eligible:
            continue
        content = _content_for(kind, entry)
        if not content:
            continue
        eligible.append((kind, entry, content))

    print(f'[matching] step 2-3 eligibility: {len(eligible)} eligible out of {total_entries} entries scanned', file=sys.stderr)

    if not eligible:
        print('[matching] no eligible candidates -- returning empty result', file=sys.stderr)
        return []

    vectors = embedder.embed_batch([content for _, _, content in eligible])
    requirement_vector = embedder.embed_one(requirement_text)

    groups: dict[str, list[dict]] = {}
    for (kind, entry, content), vector in zip(eligible, vectors):
        similarity = cosine_similarity(requirement_vector, vector)
        key = person_key(kind, entry)
        groups.setdefault(key, []).append({'kind': kind, 'entry': entry, 'similarity': similarity})

    print(f'[matching] step 4 dedup: collapsed into {len(groups)} unique people', file=sys.stderr)

    ranked: list[dict] = []
    for key, members in groups.items():
        best = max(members, key=lambda m: m['similarity'])
        if best['similarity'] < config.min_similarity:
            continue  # clears nobody's relevance bar -- drop the whole person

        entry = best['entry']
        kind = best['kind']
        owner_id = entry['owner_user_id']
        last_confirmed = entry.get('last_confirmed_at') if kind == 'tag' else None
        recency = _recency_score(last_confirmed or entry.get('created_at'), rules['reference_date'], config.recency_half_life_days)
        trust = _trust_score(owner_id, publisher_id)
        vouch_count = len(members)
        vouch_boost = min(1.0, math.log2(vouch_count + 1) / 3)  # diminishing -- a 20th vouch shouldn't dominate

        final_score = (
            config.weight_similarity * best['similarity']
            + config.weight_trust * trust
            + config.weight_recency * recency
            + config.weight_vouch * vouch_boost
        )

        ranked.append(
            {
                'entry_id': entry['id'],
                'kind': kind,
                'owner_user_id': owner_id,
                'person_key': key,
                'display_name': display_name_for(kind, entry, publisher_id),
                'skills': entry.get('skills') or ([entry.get('skill')] if kind == 'self_entry' else []),
                'description': entry.get('description'),
                'experience_years': entry.get('experience_years'),
                'location': entry.get('location'),
                'similarity': best['similarity'],
                'trust_score': trust,
                'recency_score': recency,
                'vouch_count': vouch_count,
                'final_score': final_score,
                'reasons': _build_reasons(best['similarity'], trust, recency, vouch_count),
            }
        )

    ranked.sort(key=lambda m: (-m['final_score'], m['entry_id']))
    cleared = len(ranked)
    ranked = ranked[: config.top_k]
    print(
        f'[matching] step 5-6 scoring: {cleared} cleared the relevance bar (>= {config.min_similarity}), '
        f'keeping top {len(ranked)}',
        file=sys.stderr,
    )

    if reranker is not None and ranked:
        requirement_meta = {'location': requirement_location, 'min_experience_years': requirement_min_experience_years}
        try:
            ranked = reranker.rerank(requirement_text, ranked, requirement_meta=requirement_meta)
        except Exception as err:
            print(f'[matching] step 7 LLM rerank failed ({err}); keeping embedding-only order', file=sys.stderr)
    else:
        print('[matching] step 7 LLM rerank skipped (disabled or empty shortlist)', file=sys.stderr)

    return ranked


def run_pipeline_for_requirement(
    dataset: Dataset, config: Config, embedder: EmbeddingClient, requirement: dict, reranker: LlmReranker | None = None
) -> dict:
    if requirement['status'] != 'open':
        return {'status': 'closed', 'matches': []}
    text = (requirement.get('text') or '').strip()
    if not text:
        return {'status': 'invalid_requirement', 'matches': []}
    matches = run_pipeline(
        dataset,
        config,
        embedder,
        requirement['publisher_id'],
        text,
        reranker=reranker,
        audience_user_ids=requirement.get('audience_user_ids'),
        requirement_location=requirement.get('location'),
        requirement_min_experience_years=requirement.get('min_experience_years'),
    )
    return {'status': 'ok', 'matches': matches}
