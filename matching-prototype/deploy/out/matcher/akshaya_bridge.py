from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Must run before importing Akshaya's `common` module below -- it reads
# OPENAI_API_KEY from os.environ at import time to pick its provider, so
# our own .env has to be loaded first regardless of caller import order.
load_dotenv()

import os

from .config import DATASET_DIR
from .data_loader import Dataset
from .pipeline import display_name_for

# The experiment code: a deploy bundle ships it as matching-prototype/engine/,
# locally it lives in backend/matching-experiments/akshaya.
_HERE = Path(__file__).resolve().parent
_BUNDLED_ENGINE = (_HERE / '..' / 'engine').resolve()
AKSHAYA_DIR = _BUNDLED_ENGINE if _BUNDLED_ENGINE.exists() else (
    _HERE / '..' / '..' / 'backend' / 'matching-experiments' / 'akshaya').resolve()
if str(AKSHAYA_DIR) not in sys.path:
    sys.path.insert(0, str(AKSHAYA_DIR))

# Point the experiment code at the same dataset the page lists publishers from
# (only matters for a bundle; locally both already agree). In a bundle the disk
# is read-only apart from /tmp, so its cache goes there. Must be set before
# `import common` below, which reads these at import time.
if _BUNDLED_ENGINE.exists():
    os.environ.setdefault('MATCH_DATA_DIR', str(DATASET_DIR))
    os.environ.setdefault('MATCH_CACHE_DIR', '/tmp/match-cache')

# Akshaya's modules use bare `from common import ...` style imports, which
# only resolve once her folder is on sys.path (done above). This bridge is
# the only place that depends on her code living at that exact path.
import common as akshaya_common  # noqa: E402
from design_c import DesignC  # noqa: E402

# Native-provider variants of the decided design (judge=Jev, rerank=Claude or
# Gemini called directly, with the throttle/retry/no-fallback machinery).
sys.path.insert(0, str(AKSHAYA_DIR / 'openrouter'))
from common import anthropic_chat_json, gemini_chat_json  # noqa: E402
from design_c_openrouter import DesignCOpenRouter  # noqa: E402
from run_native_v2 import _jev_as_client  # noqa: E402


def _install_vector_table() -> None:
    """If the bundle ships ready-made entry vectors (data/vectors.npz, built by
    deploy/build_vectors.py), serve them to the designs instead of embedding
    every entry text at startup -- that needs a 1 GB cache a serverless
    function doesn't have. Only document embeddings are served from the table;
    the one query embedding per run still calls the embeddings API."""
    path = DATASET_DIR / 'vectors.npz'
    if not path.exists():
        return
    import numpy as np
    blob = np.load(path, allow_pickle=False)
    texts, vecs = blob['texts'], blob['vecs']
    row_of = {str(t): i for i, t in enumerate(texts)}
    rows: dict[str, list[float]] = {}   # text -> vector, built on first use and shared by every design

    def vector(text: str):
        v = rows.get(text)
        if v is None:
            v = rows[text] = vecs[row_of[text]].astype('float32').tolist()
        return v

    original = akshaya_common.embed

    def embed(texts_in, meter=None, kind='document'):
        if kind == 'document' and all(t in row_of for t in texts_in):
            return [vector(t) for t in texts_in]
        return original(texts_in, meter, kind)

    for name in ('common', 'design_a', 'design_b', 'design_c', 'design_c_openrouter'):
        module = sys.modules.get(name)
        if module is not None and hasattr(module, 'embed'):
            module.embed = embed
    print(f'[data] using {len(row_of)} bundled entry vectors', file=sys.stderr)


_install_vector_table()


def _jev_plus(rerank_model: str, rerank_client):
    return lambda entries: DesignCOpenRouter(
        entries, judge_model='jev-latest', rerank_model=rerank_model,
        judge_client=_jev_as_client, rerank_client=rerank_client,
        # if Jev is down for a batch, the rerank model grades it instead of dropping those people
        fallback_judge_model=rerank_model, fallback_judge_client=rerank_client,
    )

# 'A1' (vector search, then LLM rerank of the top 15) is deliberately not
# listed here -- it's the same shape as our own 'embed_rerank_top10' design,
# just a different top-K and model, so keeping both would just duplicate
# one comparison point instead of adding a new one.
#
# (id, label, group, judge backend, rerank backend). The backends drive the
# per-run cost estimate below; None means that stage makes no model call.
GROUP_FULL_OPENAI = 'Full pool, judge + rerank (OpenAI / Jev)'
GROUP_FULL_NATIVE = 'Full pool, Jev judge + Claude / Gemini rerank'
FINAL_PICK = 'full_pool_jev_claude_haiku'

DESIGNS = [
    ('full_pool_hybrid_judge_rerank', 'Full Pool, Judge Then Rerank (chat/chat)', GROUP_FULL_OPENAI, 'chat', 'chat'),
    ('full_pool_hybrid_judge_rerank_decisions', 'Full Pool, Judge Then Rerank (Decisions/Decisions)', GROUP_FULL_OPENAI, 'decisions', 'decisions'),
    ('full_pool_hybrid_judge_rerank_jev', 'Full Pool, Judge Then Rerank (Jev/Jev)', GROUP_FULL_OPENAI, 'jev', 'jev'),
    ('full_pool_hybrid_judge_rerank_jev_chat', 'Full Pool, Judge (Jev) + Rerank (chat / luna)', GROUP_FULL_OPENAI, 'jev', 'chat'),
    ('full_pool_hybrid_judge_rerank_chat_jev', 'Full Pool, Judge (chat) + Rerank (Jev)', GROUP_FULL_OPENAI, 'chat', 'jev'),
    ('full_pool_hybrid_judge_rerank_jev_decisions', 'Full Pool, Judge (Jev) + Rerank (Decisions)', GROUP_FULL_OPENAI, 'jev', 'decisions'),
    ('full_pool_jev_claude_haiku', 'Full Pool, Judge (Jev) + Rerank (Claude Haiku 5.5) -- FINAL PICK', GROUP_FULL_NATIVE, 'jev', 'claude-haiku-5-5'),
    ('full_pool_jev_claude_sonnet', 'Full Pool, Judge (Jev) + Rerank (Claude Sonnet 5.5)', GROUP_FULL_NATIVE, 'jev', 'claude-sonnet-5-5'),
    ('full_pool_jev_claude_opus', 'Full Pool, Judge (Jev) + Rerank (Claude Opus 5.5)', GROUP_FULL_NATIVE, 'jev', 'claude-opus-5-5'),
    ('full_pool_jev_gemini_31_flash_lite', 'Full Pool, Judge (Jev) + Rerank (Gemini 3.1 Flash-Lite)', GROUP_FULL_NATIVE, 'jev', 'gemini-3.1-flash-lite'),
    ('full_pool_jev_gemini_35_flash_lite', 'Full Pool, Judge (Jev) + Rerank (Gemini 3.5 Flash-Lite)', GROUP_FULL_NATIVE, 'jev', 'gemini-3.5-flash-lite'),
]
VARIANT_LABELS = {d[0]: d[1] for d in DESIGNS}
_STAGE_BACKEND = {d[0]: {'judge': d[3], 'rerank': d[4]} for d in DESIGNS}

# $ per 1M tokens (input, output) -- same list prices the CLI test runs use
# (akshaya/run.py, openrouter/run_native_v2.py). 'chat' = gpt-6-luna.
PRICES = {
    'chat': (0.10, 0.50), 'decisions': (0.10, 0.0), 'jev': (0.042, 0.0), 'nano': (0.05, 0.40),
    'claude-haiku-5-5': (0.1, 0.5), 'claude-sonnet-5-5': (2.0, 10.0), 'claude-opus-5-5': (4.0, 20.0),
    'gemini-3.1-flash-lite': (0.25, 1.5), 'gemini-3.5-flash-lite': (0.3, 2.5),
}
EMBED_PRICE = 0.02   # text-embedding-3-small, $ per 1M input tokens


def estimate_cost(variant: str, by_tag: dict) -> float:
    """Model cost of one run from the meter's per-stage token counts. Any
    stage not named judge/rerank (requirement parsing, retries tagged
    'judge+retry1' etc. map to their base stage) goes through chat."""
    total = 0.0
    for tag, b in by_tag.items():
        stage = tag.split('+', 1)[0]
        backend = _STAGE_BACKEND.get(variant, {}).get(stage) or 'chat'
        inp, out = PRICES.get(backend, PRICES['chat'])
        total += b['tokens_in'] * inp / 1e6 + b['tokens_out'] * out / 1e6
    return total


_BUILDERS = {
    'full_pool_hybrid_judge_rerank': lambda entries: DesignC(entries, judge_backend='chat'),
    'full_pool_hybrid_judge_rerank_decisions': lambda entries: DesignC(entries, judge_backend='decisions'),
    'full_pool_hybrid_judge_rerank_jev': lambda entries: DesignC(entries, judge_backend='jev'),
    'full_pool_hybrid_judge_rerank_jev_chat': lambda entries: DesignC(entries, judge_backend='jev', rerank_backend='chat'),
    'full_pool_hybrid_judge_rerank_chat_jev': lambda entries: DesignC(entries, judge_backend='chat', rerank_backend='jev'),
    'full_pool_hybrid_judge_rerank_jev_decisions': lambda entries: DesignC(entries, judge_backend='jev', rerank_backend='decisions'),
    'full_pool_jev_claude_haiku': _jev_plus('claude-haiku-5-5', anthropic_chat_json),
    'full_pool_jev_claude_sonnet': _jev_plus('claude-sonnet-5-5', anthropic_chat_json),
    'full_pool_jev_claude_opus': _jev_plus('claude-opus-5-5', anthropic_chat_json),
    'full_pool_jev_gemini_31_flash_lite': _jev_plus('gemini-3.1-flash-lite', gemini_chat_json),
    'full_pool_jev_gemini_35_flash_lite': _jev_plus('gemini-3.5-flash-lite', gemini_chat_json),
}

# Display-only cap so every design shows a comparable number of results in
# the UI. Designs differ hugely in how many they return by default --
# vector_only and ours already stop at 10, hybrid_keyword_vector can return
# up to 15, and profile_at_save_judge_all returns every candidate that
# clears grade > 0 (can be dozens). This never touches Akshaya's actual
# design files or the predictions used for the real accuracy comparison in
# compare.py -- it only trims what this prototype's own page renders.
DISPLAY_TOP_N = 10

# ---- cost limits ----------------------------------------------------------
# Judging touches every eligible candidate, so cost grows with the circle's size.
# The decided design has no cap; this is a safety ceiling, well above the test
# set's pools (about 300). A pool above it is judged by fused rank, top N only.
MAX_JUDGE_CANDIDATES = int(os.environ.get('MAX_JUDGE_CANDIDATES', '1500'))
# A request asking for several kinds of people is searched once per kind; each
# search costs a full run, so the number is limited.
MAX_ROLES = int(os.environ.get('MAX_ROLES', '3'))

_MULTI_HINT = re.compile(r'\band\b|&|,|;|/|\+|\bplus\b|\balso\b|\bas well as\b', re.IGNORECASE)
SPLIT_SYSTEM = (
    "A person posts one request asking for help from people they know. Decide whether it asks for two or more "
    "DIFFERENT kinds of people (different jobs or roles, e.g. 'a UI designer and a backend developer'). "
    "If so, return one self-contained request per kind of person, copying any shared limits (place, years of "
    "experience) into each. If it asks for ONE kind of person, even when it lists several skills or tools "
    "('a Python and Django developer', 'a nurse who speaks Telugu'), return exactly one request: the original text, "
    "unchanged. At most " + str(MAX_ROLES) + " requests. Return JSON only."
)
SPLIT_SCHEMA = {"type": "object", "properties": {"requests": {"type": "array", "items": {"type": "string"}}},
                "required": ["requests"]}


def split_roles(text: str, meter) -> list[str]:
    """One request per kind of person asked for. Any doubt or failure means one request: the original."""
    if not _MULTI_HINT.search(text):
        return [text]           # nothing that could join two roles -- skip the model call
    try:
        out, secs = akshaya_common.chat_json(SPLIT_SYSTEM, text, SPLIT_SCHEMA, meter, tag='split')
        meter.stage([secs])
        parts = [p.strip() for p in out.get('requests', []) if isinstance(p, str) and p.strip()]
    except Exception as err:
        print(f'[match] could not split the request ({type(err).__name__}); searching it as one', file=sys.stderr)
        return [text]
    return parts[:MAX_ROLES] if len(parts) > 1 else [text]

_entries_cache: list | None = None
_eligibility_cache: akshaya_common.Eligibility | None = None
_matcher_cache: dict[str, object] = {}


def _entries() -> list:
    global _entries_cache
    if _entries_cache is None:
        _entries_cache = akshaya_common.load_entries()
        print(f'[data] loaded {len(_entries_cache)} entries from data/matching-testset', file=sys.stderr)
    return _entries_cache


def _eligibility() -> akshaya_common.Eligibility:
    global _eligibility_cache
    if _eligibility_cache is None:
        _eligibility_cache = akshaya_common.Eligibility()
    return _eligibility_cache


def _matcher(variant: str):
    if variant not in _matcher_cache:
        print(f'[match] building matcher (write-time work) -- first use only, then disk-cached...', file=sys.stderr)
        t0 = time.time()
        _matcher_cache[variant] = _BUILDERS[variant](_entries())
        print(f'[match] ready in {time.time() - t0:.1f}s', file=sys.stderr)
    return _matcher_cache[variant]


def run_akshaya_design(
    variant: str,
    dataset: Dataset,
    publisher_id: str,
    text: str,
    requirement_location: str | None = None,
    requirement_min_experience_years: int | None = None,
    judge_cap: int | None = None,
    stats: dict | None = None,
) -> list[dict]:
    """Runs one of the experiment designs and maps the result into this
    prototype's own match-card shape, so the frontend renders every design
    the same way. If `stats` is given, it is filled with this run's pool size,
    timing, model usage and estimated cost for the page's run summary."""
    matcher = _matcher(variant)
    rules = _eligibility()
    req = {
        'status': 'open',
        'publisher_id': publisher_id,
        'audience_user_ids': [],
        'location': requirement_location,
        'min_experience_years': requirement_min_experience_years,
    }
    pool = rules.pool(req, _entries())
    auto_capped = False
    if (judge_cap is None or judge_cap > MAX_JUDGE_CANDIDATES) and len(pool) > MAX_JUDGE_CANDIDATES:
        judge_cap, auto_capped = MAX_JUDGE_CANDIDATES, True
        print(f'[match] pool of {len(pool)} is above the cost limit; judging the top {judge_cap} by fused rank', file=sys.stderr)
    req_meta = {'location': requirement_location, 'min_experience_years': requirement_min_experience_years,
                'judge_cap': judge_cap}

    print(f'[match] pool={len(pool)} eligible entries', file=sys.stderr)
    t0 = time.time()
    meter = akshaya_common.Meter()
    roles = split_roles(text, meter)
    if len(roles) > 1:
        print(f'[match] request asks for {len(roles)} kinds of people; searching each: '
              + ' | '.join(r[:60] for r in roles), file=sys.stderr)
    per_role = [matcher.match(r, pool, meter, req_meta=req_meta) for r in roles]
    if len(roles) == 1:
        ids, detail = per_role[0]
        role_of: dict[str, str] = {}
    else:
        # Take turns across roles (best of role 1, best of role 2, ...) so every kind of person
        # shows up in the shown list; one person is listed once, under the first role that found them.
        person_of = {e.id: e.person_key for e in pool}
        ids, detail, role_of, seen_people = [], {}, {}, set()
        for rank in range(max((len(r[0]) for r in per_role), default=0)):
            for role, (role_ids, role_detail) in zip(roles, per_role):
                if rank < len(role_ids):
                    eid = role_ids[rank]
                    if person_of.get(eid) in seen_people:
                        continue
                    seen_people.add(person_of.get(eid))
                    ids.append(eid)
                    detail[eid] = role_detail.get(eid, {})
                    role_of[eid] = role
    elapsed = time.time() - t0
    unjudged = getattr(meter, 'unjudged_candidates', 0)
    judged_total = min(len(pool), judge_cap or len(pool)) * len(roles)
    if unjudged and unjudged >= judged_total - getattr(meter, 'injection_flags', 0):
        # every judge call failed -- an empty list here would read as "nobody matches"
        raise RuntimeError('every judge call failed (main and fallback judge), so no candidate could be graded. '
                           'Check the provider keys and status, then try again.')
    warnings = []
    if getattr(meter, 'injection_flags', 0):
        warnings.append(f"{meter.injection_flags} candidate(s) excluded: their text tries to give the model instructions")
    if getattr(meter, 'judge_fallback_candidates', 0):
        warnings.append(f"{meter.judge_fallback_candidates} candidates were graded by the fallback judge because the main judge failed")
    if unjudged:
        warnings.append(f"{unjudged} candidates could not be judged (main and fallback judge failed) and are missing from the results")
    if getattr(meter, 'rerank_failed_candidates', 0):
        warnings.append(f"{meter.rerank_failed_candidates} candidates could not be reranked; their years and location were not checked, "
                        f"so they are listed below the checked ones")
    if auto_capped:
        warnings.append(f'the pool of {len(pool)} is above the cost limit, so only the top {judge_cap} by relevance were judged')
    for w in warnings:
        print(f'[match] WARNING {w}', file=sys.stderr)
    total_found = len(ids)
    ids = ids[:DISPLAY_TOP_N]
    print(
        f'[match] matched in {elapsed:.2f}s -> {total_found} total, showing top {len(ids)}',
        file=sys.stderr,
    )
    print(
        f'[match] model usage: llm_calls={meter.llm_calls} tokens_in={meter.tokens_in} '
        f'tokens_out={meter.tokens_out} embed_calls={meter.embed_calls} fallbacks={meter.fallbacks} '
        + (f'(judge={matcher.judge_model}, rerank={matcher.rerank_model})' if isinstance(matcher, DesignCOpenRouter)
           else f'(model={akshaya_common.CHAT_MODEL}, provider={akshaya_common.PROVIDER})'),
        file=sys.stderr,
    )
    cost = estimate_cost(variant, meter.by_tag)  # the one query embedding is a few tokens, ~$0
    print(f'[match] estimated model cost for this run: ${cost:.4f}', file=sys.stderr)
    if stats is not None:
        stats.update(pool=len(pool), judge_cap=judge_cap, total_found=total_found, match_seconds=round(elapsed, 2),
                     llm_calls=meter.llm_calls, tokens_in=meter.tokens_in, tokens_out=meter.tokens_out,
                     fallbacks=meter.fallbacks, cost=round(cost, 4), roles=roles if len(roles) > 1 else [],
                     warnings=warnings, auto_capped=auto_capped,
                     injection_flags=getattr(meter, 'injection_flags', 0),
                     judge_fallback_candidates=getattr(meter, 'judge_fallback_candidates', 0))

    kind_by_id: dict[str, str] = {}
    record_by_id: dict[str, dict] = {}
    for e in dataset.self_entries:
        kind_by_id[e['id']] = 'self_entry'
        record_by_id[e['id']] = e
    for t in dataset.tags:
        kind_by_id[t['id']] = 'tag'
        record_by_id[t['id']] = t

    results = []
    for entry_id in ids:
        record = record_by_id.get(entry_id)
        if record is None:
            continue  # defensive -- should never happen, the matcher only returns ids from its own pool
        kind = kind_by_id[entry_id]
        d = detail.get(entry_id, {})
        grade = d.get('grade')
        final_score = (grade / 3) if grade is not None else d.get('cosine', 0.0)

        reasons = []
        if grade is not None:
            reasons.append(f'Model grade {grade}/3')
        elif 'cosine' in d:
            reasons.append(f"Cosine similarity {d['cosine']:.2f}")
        if d.get('rerank_failed'):
            reasons.append('Years and location not checked (rerank failed), listed below the checked matches')
        if eid_role := role_of.get(entry_id):
            reasons.insert(0, f'For: {eid_role[:70]}')
        vouches = d.get('vouches')
        if vouches and vouches > 1:
            reasons.append(f'Vouched by {vouches} people in your circle')

        results.append(
            {
                'entry_id': entry_id,
                'kind': kind,
                'display_name': display_name_for(kind, record, publisher_id),
                'skills': record.get('skills') or ([record.get('skill')] if kind == 'self_entry' else []),
                'description': record.get('description'),
                'experience_years': record.get('experience_years'),
                'location': record.get('location'),
                'final_score': final_score,
                'reasons': reasons,
                'llm_reason': d.get('reason'),
            }
        )

    return results
