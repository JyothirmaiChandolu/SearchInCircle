from __future__ import annotations

import hmac
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Pasted .env values on Vercel can carry a trailing newline, which breaks HTTP
# headers ("Invalid header value b'Bearer ...\n'"). Trim them before anything reads them.
for _k in ('OPENAI_API_KEY', 'JEV_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY',
           'TEAM_PASSCODE', 'SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'OPENROUTER_API_KEY'):
    if _k in os.environ:
        os.environ[_k] = os.environ[_k].strip().strip('"\'')

from matcher.akshaya_bridge import DESIGNS, FINAL_PICK, VARIANT_LABELS, run_akshaya_design
from matcher.config import DATASET_DIR, load_config
from matcher.data_loader import Dataset

app = FastAPI(title='Matching prototype')

config = load_config()
dataset = Dataset(DATASET_DIR)

class _LiveLog(io.TextIOBase):
    """Replaces sys.stderr for the whole server: every line still goes to the
    real terminal, and is also kept in memory so a running request can stream
    the same lines to the page while a run is going.
    Keeps only the last LOG_MAX_CHARS characters."""

    LOG_MAX_CHARS = 200_000

    def __init__(self, terminal) -> None:
        self.terminal = terminal
        self.lock = threading.Lock()
        self.text = ''
        self.offset = 0   # absolute position of self.text[0] in the full stream

    def write(self, s: str) -> int:
        self.terminal.write(s)
        with self.lock:
            self.text += s
            overflow = len(self.text) - self.LOG_MAX_CHARS
            if overflow > 0:
                self.text = self.text[overflow:]
                self.offset += overflow
        return len(s)

    def flush(self) -> None:
        self.terminal.flush()

    def since(self, pos: int) -> tuple[str, int]:
        with self.lock:
            start = max(pos - self.offset, 0)
            return self.text[start:], self.offset + len(self.text)

    def end(self) -> int:
        with self.lock:
            return self.offset + len(self.text)


live_log = _LiveLog(sys.stderr)
sys.stderr = live_log


# Shared team passcode. When TEAM_PASSCODE is set, every /api/ route needs it in
# the X-Passcode header; unset (local use) means open.
PASSCODE = os.environ.get('TEAM_PASSCODE', '')


def require_passcode(request: Request) -> None:
    if PASSCODE and not hmac.compare_digest(request.headers.get('x-passcode', ''), PASSCODE):
        raise HTTPException(401, 'passcode required')


class MatchRequest(BaseModel):
    publisher_id: str
    text: str
    design: str = FINAL_PICK
    location: str | None = None
    min_experience_years: int | None = None
    judge_cap: int | None = None             # judge only the top N by fused rank; None = whole pool


class RatingRequest(BaseModel):
    run_id: str
    tester: str
    design: str
    publisher_id: str
    text: str
    match_ids: list[str]                      # in the order shown, so "good at rank k" can be computed later
    verdicts: dict[str, Literal['good', 'bad']] = {}
    list_score: int | None = None             # 1-5, how good the whole list is
    comment: str = ''
    stats: dict = {}


# Ratings go to Supabase (table `ratings`, see deploy/README.md) when SUPABASE_URL and
# SUPABASE_SERVICE_KEY are set -- required on Vercel, where the disk is read-only.
# Without them (local use) they go to a JSON-lines file; re-saving the same run_id
# supersedes the earlier line.
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
RATINGS_PATH = Path(__file__).resolve().parent / 'ratings.jsonl'
_ratings_lock = threading.Lock()


def _supabase(method: str, path: str, body=None, extra_headers: dict | None = None):
    request = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/{path}', method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'apikey': SUPABASE_KEY,
                 # new-style sb_secret_ keys are not JWTs: send them only as apikey
                 **({'Authorization': f'Bearer {SUPABASE_KEY}'} if SUPABASE_KEY.startswith('eyJ') else {}),
                 'Content-Type': 'application/json', **(extra_headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raise RuntimeError(f'Supabase {err.code}: {err.read().decode()[:200]}') from err


def _store_rating(row: dict) -> None:
    if USE_SUPABASE:
        _supabase('POST', 'ratings?on_conflict=run_id', {'run_id': row['run_id'], 'saved_at': row['saved_at'], 'data': row},
                  {'Prefer': 'resolution=merge-duplicates,return=minimal'})
    elif os.environ.get('VERCEL'):
        raise RuntimeError('ratings storage is not configured (set SUPABASE_URL and SUPABASE_SERVICE_KEY)')
    else:
        with _ratings_lock, RATINGS_PATH.open('a') as f:
            f.write(json.dumps(row) + '\n')


def _load_ratings() -> list[dict]:
    if USE_SUPABASE:
        rows = _supabase('GET', 'ratings?select=data&order=saved_at.desc&limit=5000') or []
        return [r['data'] for r in rows]
    if not RATINGS_PATH.exists():
        return []
    latest: dict[str, dict] = {}
    for line in RATINGS_PATH.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row['run_id']] = row
    return sorted(latest.values(), key=lambda r: r['saved_at'], reverse=True)


@app.get('/api/auth', dependencies=[Depends(require_passcode)])
def auth() -> dict:
    return {'ok': True, 'passcode_required': bool(PASSCODE)}


@app.get('/api/publishers', dependencies=[Depends(require_passcode)])
def list_publishers() -> list[dict]:
    return [{'id': u['id'], 'name': u['name']} for u in dataset.users]


@app.get('/api/designs', dependencies=[Depends(require_passcode)])
def list_designs() -> list[dict]:
    return [{'id': d[0], 'label': d[1], 'group': d[2], 'final': d[0] == FINAL_PICK} for d in DESIGNS]


@app.post('/api/match', dependencies=[Depends(require_passcode)])
def match(req: MatchRequest) -> StreamingResponse:
    """Streams newline-delimited JSON: {"t":"log","text":...} lines while the run
    is going (the same lines the server prints), then one {"t":"result",...} or
    {"t":"error","message":...}. Streaming keeps the log live without a second
    request, which a serverless deploy can't route to the same instance."""
    if not req.text.strip():
        raise HTTPException(400, 'text is required')
    if req.design not in VARIANT_LABELS:
        raise HTTPException(400, f'unknown design {req.design!r}, pick one of {list(VARIANT_LABELS)}')

    outcome: dict = {}

    def work() -> None:
        stats: dict = {}
        t0 = time.time()
        try:
            matches = _run_match(req, stats)
            stats['total_seconds'] = round(time.time() - t0, 2)
            outcome['result'] = {'t': 'result', 'run_id': uuid.uuid4().hex, 'matches': matches, 'stats': stats}
        except HTTPException as err:
            outcome['result'] = {'t': 'error', 'message': str(err.detail)}
        except Exception as err:
            print(f'[request] failed: {type(err).__name__}: {err}', file=sys.stderr)
            outcome['result'] = {'t': 'error', 'message': f'{type(err).__name__}: {err}'}

    def events():
        pos = live_log.end()
        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        while worker.is_alive():
            text, pos = live_log.since(pos)
            if text:
                yield json.dumps({'t': 'log', 'text': text}) + '\n'
            worker.join(timeout=0.3)
        text, pos = live_log.since(pos)
        if text:
            yield json.dumps({'t': 'log', 'text': text}) + '\n'
        yield json.dumps(outcome['result']) + '\n'

    return StreamingResponse(events(), media_type='application/x-ndjson',
                             headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'})


@app.post('/api/ratings', dependencies=[Depends(require_passcode)])
def save_rating(req: RatingRequest) -> dict:
    if not req.tester.strip():
        raise HTTPException(400, 'tester name is required')
    if req.list_score is not None and not 1 <= req.list_score <= 5:
        raise HTTPException(400, 'list_score must be 1-5')
    row = req.model_dump()
    row['tester'] = req.tester.strip()
    row['design_label'] = VARIANT_LABELS.get(req.design, req.design)
    row['saved_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        _store_rating(row)
    except Exception as err:
        print(f'[rating] save failed: {err}', file=sys.stderr)
        raise HTTPException(500, f'could not save the rating: {err}') from err
    print(f"[rating] {row['tester']} rated {row['design_label']}: "
          f"{sum(v == 'good' for v in req.verdicts.values())} good / "
          f"{sum(v == 'bad' for v in req.verdicts.values())} bad, list score {req.list_score}", file=sys.stderr)
    return {'ok': True, 'saved_at': row['saved_at']}


@app.get('/api/ratings', dependencies=[Depends(require_passcode)])
def ratings_summary() -> dict:
    try:
        rows = _load_ratings()
    except Exception as err:
        raise HTTPException(500, f'could not load ratings: {err}') from err
    by_design: dict[str, dict] = {}
    for r in rows:
        cap = (r.get('stats') or {}).get('judge_cap')
        key = f"{r['design']}|{cap}"
        label = r['design_label'] + (f' (judge top {cap})' if cap else '')
        d = by_design.setdefault(key, {'design': r['design'], 'label': label, 'runs': 0,
                                               'good': 0, 'bad': 0, 'scores': [], 'seconds': [], 'costs': [],
                                               'testers': set()})
        d['runs'] += 1
        d['good'] += sum(v == 'good' for v in r['verdicts'].values())
        d['bad'] += sum(v == 'bad' for v in r['verdicts'].values())
        if r.get('list_score'):
            d['scores'].append(r['list_score'])
        if r.get('stats', {}).get('total_seconds') is not None:
            d['seconds'].append(r['stats']['total_seconds'])
        if r.get('stats', {}).get('cost') is not None:
            d['costs'].append(r['stats']['cost'])
        d['testers'].add(r['tester'])

    avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else None
    designs = []
    for d in by_design.values():
        rated = d['good'] + d['bad']
        designs.append({'design': d['design'], 'label': d['label'], 'final': d['design'] == FINAL_PICK,
                        'runs': d['runs'], 'testers': len(d['testers']), 'good': d['good'], 'bad': d['bad'],
                        'good_rate': round(d['good'] / rated, 3) if rated else None,
                        'avg_list_score': avg(d['scores']), 'avg_seconds': avg(d['seconds']),
                        'avg_cost': avg(d['costs'])})
    designs.sort(key=lambda d: (d['good_rate'] is None, -(d['good_rate'] or 0)))
    recent = [{'saved_at': r['saved_at'], 'tester': r['tester'], 'design_label': r['design_label'],
               'text': r['text'], 'good': sum(v == 'good' for v in r['verdicts'].values()),
               'bad': sum(v == 'bad' for v in r['verdicts'].values()), 'shown': len(r['match_ids']),
               'list_score': r.get('list_score'), 'comment': r.get('comment', '')} for r in rows[:50]]
    return {'designs': designs, 'recent': recent, 'total_runs': len(rows),
            'testers': len({r['tester'] for r in rows})}


def _run_match(req: MatchRequest, stats: dict) -> list[dict]:
    print(
        f"\n[request] design={VARIANT_LABELS[req.design]!r} publisher={req.publisher_id} text={req.text[:80]!r} "
        f"location={req.location!r} min_experience_years={req.min_experience_years}",
        file=sys.stderr,
    )

    if not config.openai_api_key:
        raise HTTPException(500, 'OPENAI_API_KEY is not set -- add it to matching-prototype/.env and restart.')
    matches = run_akshaya_design(
        req.design,
        dataset,
        req.publisher_id,
        req.text,
        requirement_location=req.location,
        requirement_min_experience_years=req.min_experience_years,
        judge_cap=req.judge_cap,
        stats=stats,
    )
    print(f'[request] returned {len(matches)} match(es)', file=sys.stderr)

    return matches


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).resolve().parent / 'static' / 'index.html').read_text()
