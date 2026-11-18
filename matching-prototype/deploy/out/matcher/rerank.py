from __future__ import annotations

import json
import sys

from openai import OpenAI

from .usage import UsageTracker, format_cost

SYSTEM_PROMPT = """You are ranking an ALREADY-ELIGIBLE shortlist of circle contacts against one posted requirement. Eligibility (who is even allowed to be shown) was already decided before you saw this list -- your only job is relevance and explanation.

Rules:
- You may ONLY reorder the given entry ids. Never invent an id that was not given to you. Never drop one.
- Judge skill relevance the way a careful human would, not by shared words. A synonym or rephrasing counts as a real match (e.g. "Expo" for "React Native", "quality assurance" for "testing", "ICU nursing" for "critical care").
- A shared keyword that means something unrelated in context is NOT a match (e.g. a pet python vs. the Python programming language, a tennis "elbow" clinic vs. a tennis player, a plant nursery vs. a nurse).
- Each candidate carries explicit "experience_years" and "location" fields (not guessed from text) -- use them directly, and the requirement's own "min_experience_years" / "location" fields the same way:
  - A candidate below the stated minimum by 1-2 years is a minor miss (mention it, rank slightly lower). Short by more is a bigger miss (rank lower still). Never invent a shortfall when either field is null -- a candidate can't be penalised for a fact nobody stated.
  - A requirement with a non-null location implies on-site/in-person work; a candidate elsewhere is a miss, worse the further away, but still worth showing (they might relocate or commute) -- never hide them for this alone. A null requirement location means remote is fine, so location never counts against anyone.
- Write each reason as one short, plain sentence -- what a non-technical person reading a match list would want to know (mention a real experience or location gap by name when it's the deciding factor), not a restatement of the skill tags.

Respond with JSON only, no prose: {"order": ["id1", "id2", ...], "reasons": {"id1": "...", "id2": "..."}}
"""


class LlmReranker:
    """Reranks only the shortlist the embedding step already produced --
    never asked to invent or drop candidates. Any failure (timeout, bad
    JSON, hallucinated/dropped ids) degrades silently back to the original
    order: this step is optional by design and must never be the thing that
    breaks a match result."""

    def __init__(self, api_key: str, model: str, timeout_s: float = 20.0, usage: UsageTracker | None = None):
        self.client = OpenAI(api_key=api_key, timeout=timeout_s)
        self.model = model
        self.usage = usage

    def rerank(
        self,
        requirement_text: str,
        shortlist: list[dict],
        requirement_meta: dict | None = None,
    ) -> list[dict]:
        if not shortlist:
            return shortlist
        print(f'[rerank] model={self.model} candidates={len(shortlist)}', file=sys.stderr)
        try:
            candidates = [
                {
                    'id': m['entry_id'],
                    'similarity': round(m['similarity'], 3),
                    'vouch_count': m['vouch_count'],
                    'skills': m.get('skills'),
                    'description': m.get('description'),
                    'experience_years': m.get('experience_years'),
                    'location': m.get('location'),
                }
                for m in shortlist
            ]
            meta = requirement_meta or {}
            user_content = (
                f"Requirement: {requirement_text}\n"
                f"Requirement min_experience_years: {meta.get('min_experience_years')}\n"
                f"Requirement location: {meta.get('location')} (null means remote is fine)\n\n"
                f"Candidates: {json.dumps(candidates)}"
            )
            # seed makes repeated runs on the same input comparable -- without
            # it, re-running the matcher can shift nDCG by ~0.02 just from
            # sampling variance, which makes A/B comparisons noisy.
            extra: dict = {'seed': 42}
            if self.model.startswith('gpt-5'):
                # Reasoning models (gpt-5-*) default to deep internal "thinking"
                # even for trivial output -- 'minimal' cuts reasoning tokens to
                # ~0 and latency from ~3.5s to ~1.4s for this task. Reranking a
                # shortlist doesn't need multi-step reasoning. Non-reasoning
                # models (gpt-4.1-nano, gpt-4o-mini) don't accept this param.
                extra['reasoning_effort'] = 'minimal'

            response = self.client.chat.completions.create(
                model=self.model,
                response_format={'type': 'json_object'},
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_content},
                ],
                **extra,
            )
            content = response.choices[0].message.content or '{}'
            parsed = json.loads(content)

            if self.usage and getattr(response, 'usage', None):
                cost = self.usage.record_rerank(response.usage.prompt_tokens, response.usage.completion_tokens)
                print(
                    f'[rerank] used {response.usage.prompt_tokens} in / {response.usage.completion_tokens} out '
                    f'token(s), cost {format_cost(cost)}',
                    file=sys.stderr,
                )

            return _apply(shortlist, parsed)
        except Exception as err:
            print(f'[rerank] failed ({err}); keeping embedding-only order', file=sys.stderr)
            return shortlist


def _apply(original: list[dict], parsed: dict) -> list[dict]:
    by_id = {m['entry_id']: m for m in original}
    order = [entry_id for entry_id in parsed.get('order', []) if entry_id in by_id]
    if len(order) != len(original):
        # The model dropped or invented an id -- trust our own order over a half-valid one.
        order = [m['entry_id'] for m in original]

    reasons = parsed.get('reasons', {})
    result = []
    for entry_id in order:
        match = dict(by_id[entry_id])
        if entry_id in reasons:
            match['llm_reason'] = reasons[entry_id]
        result.append(match)
    return result
