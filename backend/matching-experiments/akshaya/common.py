"""Shared parts of the two matching prototypes.

Both designs use the same data loader, the same eligibility rules, the same
"show once" merge and the same local model client, so the comparison measures
only the part that differs: how candidates are scored and ordered.

Privacy rules applied here (PRD v1.3):
  NFR-12  a model only ever sees skill text under per-call opaque ids (c1, c2, ...).
          Names, aliases, user ids and entry ids are never put in a prompt.
  NFR-19  a model sees the requirement text only, never who published it.

Reads only the public test-set files. Never reads answer_key/.
Standard library only. Models come from OpenAI when OPENAI_API_KEY is set
(in the environment or in experiments/matching/.env), otherwise from a local Ollama.
Override with MATCH_PROVIDER=openai|ollama, MATCH_CHAT_MODEL, MATCH_EMBED_MODEL, MATCH_REASONING.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ["MATCH_DATA_DIR"]) if os.environ.get("MATCH_DATA_DIR") else HERE.parents[2] / "data" / "matching-testset"
CACHE = Path(os.environ["MATCH_CACHE_DIR"]) if os.environ.get("MATCH_CACHE_DIR") else HERE / ".cache"   # a deploy with a read-only disk points this at /tmp


def _dotenv() -> None:
    f = HERE / ".env"                      # git-ignored; one KEY=value per line
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_dotenv()
PROVIDER = os.environ.get("MATCH_PROVIDER") or ("openai" if os.environ.get("OPENAI_API_KEY") else "ollama")
OLLAMA = "http://localhost:11434"
OPENAI = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
_DEFAULTS = {"openai": ("gpt-6-luna", "text-embedding-3-small"), "ollama": ("qwen3:8b", "nomic-embed-text")}
CHAT_MODEL = os.environ.get("MATCH_CHAT_MODEL", _DEFAULTS[PROVIDER][0])
EMBED_MODEL = os.environ.get("MATCH_EMBED_MODEL", _DEFAULTS[PROVIDER][1])
OUT = HERE / ("out" if PROVIDER == "ollama" else "out-" + PROVIDER)   # local results are not overwritten
PARALLEL = 8 if PROVIDER == "openai" else 1     # model calls of one stage that may run at the same time
_LOCK = threading.Lock()


# ---------------------------------------------------------------- data

@dataclass
class Entry:
    id: str
    kind: str                 # "self_entry" | "tag"
    owner: str                # user id of the person who wrote it
    subject_user_id: str | None
    skills: list[str]
    description: str
    available: bool
    experience_years: int | None = None   # stated fact, PRD v1.3 -- not guessed from text
    location: str | None = None           # stated fact, PRD v1.3 -- not guessed from text

    @property
    def text(self) -> str:
        """The only part of an entry a model may see as free text. experience_years
        and location are sent to a model separately, as explicit fields, never
        folded in here -- keeps the skill-matching judgement and the years/place
        arithmetic from contaminating each other."""
        return (", ".join(self.skills) + ". " + self.description).strip()

    @property
    def person_key(self) -> str:
        """Who the entry is about, as far as the system can prove it.
        A self-entry and a tag about the same registered user share a key.
        Tags about non-users stay separate: no merging by name."""
        if self.kind == "self_entry":
            return self.owner
        return self.subject_user_id or self.id


def _load(name: str):
    return json.loads((DATA / name).read_text())


def load_entries() -> list[Entry]:
    out = []
    for e in _load("self_entries.json"):
        out.append(Entry(e["id"], "self_entry", e["owner_user_id"], None, [e["skill"]],
                         e["description"] or "", e["availability_status"] == "open",
                         e.get("experience_years"), e.get("location")))
    for e in _load("tags.json"):
        out.append(Entry(e["id"], "tag", e["owner_user_id"], e["subject_user_id"], list(e["skills"]),
                         e["description"] or "", e["availability_status"] == "open",
                         e.get("experience_years"), e.get("location")))
    return out


def load_requirements() -> list[dict]:
    return _load("requirements.json")


class Eligibility:
    """The hard rules. Plain code, no model. In production this is one SQL WHERE clause."""

    def __init__(self) -> None:
        self.rules = _load("rules.json")
        self.status = {frozenset((c["requester_id"], c["addressee_id"])): c["status"]
                       for c in _load("trust_connections.json")}
        self.blocked = {frozenset((b["blocker_id"], b["blocked_id"])) for b in _load("blocks.json")}

    def pool(self, req: dict, entries: list[Entry]) -> list[Entry]:
        if req["status"] != "open":
            return []
        p, audience = req["publisher_id"], req["audience_user_ids"]
        out = []
        for e in entries:
            if not e.available:
                continue
            if e.owner == p:
                if e.kind == "self_entry" or not self.rules["include_own_tags"]:
                    continue
            else:
                pair = frozenset((p, e.owner))
                if self.status.get(pair) != "accepted" or pair in self.blocked:
                    continue
                if audience and e.owner not in audience:
                    continue
            if e.kind == "tag" and e.subject_user_id == p:
                continue
            out.append(e)
        return out


def show_once(ranked: list[Entry]) -> tuple[list[Entry], dict[str, int]]:
    """Keep the best-ranked entry per person. Also return how many entries vouch for each."""
    seen: dict[str, int] = {}
    out = []
    for e in ranked:
        if e.person_key not in seen:
            out.append(e)
        seen[e.person_key] = seen.get(e.person_key, 0) + 1
    return out, seen


# ---------------------------------------------------------------- text

STOP = set("a an and the of for to in on with at by our my we i need someone who is are be or as this that "
           "from your have has years year experience about known looking want can lives based least".split())


def tokens(text: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9+#.]+", text.lower()):
        t = t.strip(".")
        if len(t) < 2 or t in STOP:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]                      # crude plural stemming, like a Postgres english dictionary
        out.append(t)
    return out


class BM25:
    """Stands in for Postgres full-text ranking."""

    def __init__(self, docs: dict[str, str], k1: float = 1.2, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tf = {i: _count(tokens(t)) for i, t in docs.items()}
        self.len = {i: sum(c.values()) for i, c in self.tf.items()}
        self.avg = sum(self.len.values()) / max(1, len(self.len))
        df: dict[str, int] = {}
        for c in self.tf.values():
            for t in c:
                df[t] = df.get(t, 0) + 1
        n = len(docs)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, query: str, doc_id: str) -> float:
        tf, s = self.tf[doc_id], 0.0
        for t in set(tokens(query)):
            f = tf.get(t, 0)
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (
                    f + self.k1 * (1 - self.b + self.b * self.len[doc_id] / self.avg))
        return s


def _count(items: list[str]) -> dict[str, int]:
    c: dict[str, int] = {}
    for i in items:
        c[i] = c.get(i, 0) + 1
    return c


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------- models

@dataclass
class Meter:
    """Counts model work, so cost and speed can be compared between designs."""
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    llm_seconds: float = 0.0            # sum over all calls (one after another)
    embed_calls: int = 0
    embed_seconds: float = 0.0
    stages: list[float] = field(default_factory=list)   # per stage: its slowest call (calls in a stage can run in parallel)
    fallbacks: int = 0
    by_tag: dict = field(default_factory=dict)   # tag ("judge"/"rerank"/"parse"/"enrich"/...) -> calls/tokens_in/tokens_out

    def stage(self, call_seconds: list[float]) -> None:
        if call_seconds:
            self.stages.append(max(call_seconds))

    def tag(self, tag: str, tokens_in: int, tokens_out: int) -> None:
        """Call-site bookkeeping by tag, so cost can be broken down by pipeline stage
        (e.g. judge vs rerank) instead of only as one lump sum per requirement."""
        b = self.by_tag.setdefault(tag or "untagged", {"calls": 0, "tokens_in": 0, "tokens_out": 0})
        b["calls"] += 1
        b["tokens_in"] += tokens_in
        b["tokens_out"] += tokens_out

    def as_dict(self) -> dict:
        return dict(llm_calls=self.llm_calls, tokens_in=self.tokens_in, tokens_out=self.tokens_out,
                    llm_seconds=round(self.llm_seconds, 2), embed_calls=self.embed_calls,
                    embed_seconds=round(self.embed_seconds, 2),
                    parallel_seconds=round(sum(self.stages), 2), fallbacks=self.fallbacks,
                    by_tag=self.by_tag)


def _cached(kind: str, payload: dict, compute):
    CACHE.mkdir(exist_ok=True)
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]
    f = CACHE / f"{kind}_{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    val = compute()
    f.write_text(json.dumps(val))
    return val


class ModerationFlagged(RuntimeError):
    """The provider refused to answer because it flagged the prompt itself
    (usage-policy / content moderation), not a transient or server error.
    A caller that can isolate the responsible batch should catch this and
    fall back per-batch instead of failing the whole run -- see
    design_c.py's rerank_chat for the one place that currently does."""


def _post(url: str, body: dict, auth_key: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if auth_key is not None:
        headers["Authorization"] = "Bearer " + auth_key
    elif PROVIDER == "openai":
        headers["Authorization"] = "Bearer " + os.environ["OPENAI_API_KEY"]
    data = json.dumps(body).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            return json.loads(urllib.request.urlopen(req, timeout=900).read())
        except urllib.error.HTTPError as err:
            if err.code == 400:
                detail = err.read().decode()[:500]
                if "usage polic" in detail.lower() or "invalid_prompt" in detail.lower():
                    raise ModerationFlagged(f"{url} -> HTTP 400 (moderation): {detail[:300]}") from None
                raise RuntimeError(f"{url} -> HTTP {err.code}: {detail[:300]}") from None
            if err.code not in (429, 500, 502, 503) or attempt == 3:
                raise RuntimeError(f"{url} -> HTTP {err.code}: {err.read().decode()[:300]}") from None
            time.sleep(2 ** attempt)
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as err:
            # Transient network failure, not an HTTP error -- e.g. a dropped
            # connection mid-read on a large response. Seen on the v2 dataset's
            # bigger embedding batches; retry the same as a 5xx.
            if attempt == 3:
                raise RuntimeError(f"{url} -> network error after 4 attempts: {err}") from None
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _embed_raw(texts: list[str]) -> list[list[float]]:
    # Tried running these chunks through the same ThreadPoolExecutor the
    # judge batches use (PARALLEL workers) -- measured ~9x SLOWER on this
    # dataset (3566s vs 376s sequential), not faster. Each 64-text chunk's
    # response is a sizeable JSON payload; 8 of those downloading at once
    # appears to be bandwidth/connection-bound in this environment rather
    # than request-rate-bound, so concurrency made every download crawl
    # instead of overlapping cleanly. Back to sequential on purpose.
    vecs = []
    for i in range(0, len(texts), 64):
        chunk = texts[i:i + 64]
        if PROVIDER == "openai":
            data = _post(OPENAI + "/embeddings", {"model": EMBED_MODEL, "input": chunk})["data"]
            vecs += [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
        else:
            vecs += _post(OLLAMA + "/api/embed", {"model": EMBED_MODEL, "input": chunk})["embeddings"]
    return vecs


def embed(texts: list[str], meter: Meter | None = None, kind: str = "document") -> list[list[float]]:
    """Embeddings, cached on disk with their original timing. kind is "document" or "query"."""
    if EMBED_MODEL.startswith("nomic"):                 # this model wants a task prefix
        texts = [f"search_{kind}: {t}" for t in texts]

    def run():
        t = time.time()
        return {"vecs": _embed_raw(texts), "seconds": time.time() - t}
    r = _cached("emb", {"m": EMBED_MODEL, "t": texts}, run)
    if meter:
        with _LOCK:
            meter.embed_calls += 1
            meter.embed_seconds += r["seconds"]
    return r["vecs"]


def _strict(schema):
    """OpenAI strict JSON output needs additionalProperties: false on every object."""
    if isinstance(schema, dict):
        out = {k: _strict(v) for k, v in schema.items()}
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(schema, list):
        return [_strict(v) for v in schema]
    return schema


def chat_json(system: str, user: str, schema: dict, meter: Meter, tag: str = "") -> tuple[dict, float]:
    """One model call that must return JSON matching `schema`.
    Returns (parsed JSON, seconds). Cached on disk, and a cache hit reports the
    original call's tokens and time, so reruns give the same cost numbers."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if PROVIDER == "openai":                           # Responses API with strict JSON output
        body = {"model": CHAT_MODEL, "input": messages,
                "reasoning": {"effort": os.environ.get("MATCH_REASONING", "none")},
                "text": {"format": {"type": "json_schema", "name": "result", "strict": True,
                                    "schema": _strict(schema)}}}
    else:
        body = {"model": CHAT_MODEL, "think": False, "stream": False, "format": schema,
                "options": {"temperature": 0, "seed": 7, "num_ctx": 8192}, "messages": messages}

    def run():
        t = time.time()
        if PROVIDER == "openai":
            r = _post(OPENAI + "/responses", body)
            text = "".join(c.get("text", "") for item in r.get("output", []) if item.get("type") == "message"
                           for c in item.get("content", []) if c.get("type") == "output_text")
            use = r.get("usage", {})
            return {"content": text, "in": use.get("input_tokens", 0),
                    "out": use.get("output_tokens", 0), "seconds": time.time() - t}
        r = _post(OLLAMA + "/api/chat", body)
        return {"content": r["message"]["content"], "in": r.get("prompt_eval_count", 0),
                "out": r.get("eval_count", 0), "seconds": time.time() - t}
    r = _cached("chat", {"body": body, "tag": tag}, run)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += r["in"]
        meter.tokens_out += r["out"]
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, r["in"], r["out"])
    try:
        return json.loads(r["content"]), r["seconds"]
    except json.JSONDecodeError:
        if tag.endswith("+retry"):
            return {}, r["seconds"]
        # the model sometimes answers in prose instead of JSON; ask once more, with a different seed
        return chat_json(system, user + "\n\nAnswer with the JSON object only.", schema, meter, tag=tag + "+retry")


# ---------------------------------------------------------------- cheap bounded-answer backends
#
# Both of these answer a fixed question with a typed, bounded answer instead
# of free text -- no output tokens, so no output cost at all. Used as
# alternatives to chat_json's "grade 0-3" judge call, to compare cost on the
# exact same task.

DECISIONS_MODEL = "gpt-6-luna"
JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")
JEV_BASE = os.environ.get("JEV_BASE_URL", "https://api.typesafe.ai/v1")


def decisions_call(input_text: str, questions: list[dict], meter: Meter, tag: str = "") -> dict:
    """One call to OpenAI's Decisions API (POST /v1/decisions). $0.10/1M
    input tokens, $0 output -- cached on disk like chat_json."""
    body = {"model": DECISIONS_MODEL, "input": input_text, "questions": questions}

    def run():
        t = time.time()
        return {"result": _post(OPENAI + "/decisions", body), "seconds": time.time() - t}

    r = _cached("decisions", {"body": body, "tag": tag}, run)
    usage = r["result"].get("usage", {})
    tin, tout = usage.get("input_tokens", usage.get("total_tokens", 0)), usage.get("output_tokens", 0)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += tin
        meter.tokens_out += tout
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, tin, tout)
    return r["result"]


def jev_call(state, questions: dict, meter: Meter, tag: str = "") -> dict:
    """One call to TypeSafe's Jev (POST /v1/systemone). $0.042/1M input
    tokens, $0 output -- a different model family entirely, not OpenAI."""
    jev_key = os.environ.get("JEV_API_KEY")
    if not jev_key:
        raise RuntimeError("JEV_API_KEY is not set -- add it to akshaya/.env")
    body = {"model": JEV_MODEL, "state": state, "questions": questions}

    def run():
        t = time.time()
        return {"result": _post(JEV_BASE + "/systemone", body, auth_key=jev_key), "seconds": time.time() - t}

    r = _cached("jev", {"body": body, "tag": tag}, run)
    usage = r["result"].get("usage", {})
    tin, tout = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += tin
        meter.tokens_out += tout
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, tin, tout)
    return r["result"]


def _make_throttle(max_rpm: float):
    """A proactive per-minute call limiter, shared across every thread and
    every requirement being processed at once -- not just the handful of
    batches one requirement's own thread pool spawns. Production will have
    many requirements in flight together, each with its own judge/rerank
    batches; without a limiter keyed at this level (one per provider, not
    one per requirement), concurrent requirements can collectively blow
    through an account's real rate limit even though each one alone looks
    fine. Returns a zero-argument function that blocks until it's safe to
    make one more call."""
    lock = threading.Lock()
    call_times: list[float] = []

    def throttle() -> None:
        min_gap = 60.0 / max_rpm
        while True:
            with lock:
                now = time.time()
                while call_times and now - call_times[0] > 60:
                    call_times.pop(0)
                if len(call_times) < max_rpm and (not call_times or now - call_times[-1] >= min_gap):
                    call_times.append(now)
                    return
            time.sleep(0.2)

    return throttle


OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MAX_RPM = float(os.environ.get("OPENROUTER_MAX_RPM", "15"))      # stay under the free tier's 20/min cap on purpose
OPENROUTER_MAX_TOKENS = int(os.environ.get("OPENROUTER_MAX_TOKENS", "1024"))
_openrouter_throttle = _make_throttle(OPENROUTER_MAX_RPM)


def _post_openrouter(body: dict, or_key: str) -> dict:
    """Like _post, but 429-aware in a way free-tier congestion actually needs:
    _post's 2/4/8s ladder gives up in under a minute, which a pilot run showed
    free models blow through routinely. This honors a Retry-After header when
    the provider sends one, otherwise backs off up to 60s, over 6 attempts."""
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + or_key}
    data = json.dumps(body).encode()
    for attempt in range(6):
        _openrouter_throttle()
        try:
            req = urllib.request.Request(OPENROUTER_BASE + "/chat/completions", data=data, headers=headers)
            return json.loads(urllib.request.urlopen(req, timeout=900).read())
        except urllib.error.HTTPError as err:
            detail = err.read().decode()[:500]
            if err.code != 429 or attempt == 5:
                raise RuntimeError(f"openrouter -> HTTP {err.code}: {detail[:300]}") from None
            retry_after = err.headers.get("Retry-After") if err.headers else None
            wait = float(retry_after) if retry_after else min(60.0, 3 * 2 ** attempt)
            print(f"[openrouter] 429 (attempt {attempt + 1}/6), waiting {wait:.0f}s -- {detail[:160]}", file=sys.stderr)
            time.sleep(wait)
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as err:
            if attempt == 5:
                raise RuntimeError(f"openrouter -> network error after 6 attempts: {err}") from None
            time.sleep(min(30.0, 2 ** attempt))
    raise RuntimeError("unreachable")


def _extract_json(content: str) -> dict:
    """Best-effort JSON read for models that don't cleanly honor JSON-only
    output: strips a ```json fence if present, then balances the first {...}
    found so leading/trailing prose around the answer doesn't fail the parse."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("no { found in content", text, 0)
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise json.JSONDecodeError("unbalanced braces", text, start)


def openrouter_chat_json(system: str, user: str, schema: dict, meter: Meter, model: str,
                          tag: str = "", strict: bool = True) -> tuple[dict, float]:
    """One call to any OpenRouter-hosted model -- free-tier Google models, or
    paid Google/Anthropic models, all through the same OpenAI-compatible
    endpoint, picked by `model` (an OpenRouter model id, e.g.
    'google/gemma-4-31b-it:free' or 'anthropic/claude-haiku-5.5').

    `strict=True` asks for strict JSON-schema output; on a bad parse we retry
    once more as-is, then drop to `strict=False` (plain json_object mode plus
    the shape spelled out in the prompt) for models that advertise
    response_format but not structured_outputs -- the free Gemma models, in
    the one pilot run this was checked against."""
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set -- add it to akshaya/.env")
    readable_system = system + "\n\nRespond with raw JSON only: no markdown code fences, no commentary, no reasoning text before or after it."
    if strict:
        response_format = {"type": "json_schema", "json_schema": {"name": "result", "strict": True, "schema": _strict(schema)}}
    else:
        readable_system += "\n\nMatch this JSON shape exactly, with every field present:\n" + json.dumps(schema)
        response_format = {"type": "json_object"}
    body = {
        "model": model,
        "messages": [{"role": "system", "content": readable_system}, {"role": "user", "content": user}],
        "response_format": response_format,
        "max_tokens": OPENROUTER_MAX_TOKENS,
        "reasoning": {"exclude": True},     # don't let a thinking model spend its budget on hidden reasoning tokens
        "temperature": 0,
    }

    def run():
        t = time.time()
        r = _post_openrouter(body, or_key)
        choice = r["choices"][0]
        if choice.get("finish_reason") == "length":
            print(f"[openrouter] {model} hit max_tokens={OPENROUTER_MAX_TOKENS} -- answer may be truncated "
                  f"(raise OPENROUTER_MAX_TOKENS if this tag keeps failing)", file=sys.stderr)
        content = choice["message"]["content"] or ""
        use = r.get("usage", {})
        return {"content": content, "in": use.get("prompt_tokens", 0), "out": use.get("completion_tokens", 0), "seconds": time.time() - t}

    r = _cached("openrouter", {"body": body, "tag": tag}, run)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += r["in"]
        meter.tokens_out += r["out"]
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, r["in"], r["out"])
    try:
        return _extract_json(r["content"]), r["seconds"]
    except json.JSONDecodeError:
        if tag.endswith("+retry"):
            print(f"[openrouter] {model} gave up on non-JSON output after retry (tag={tag}): {r['content'][:200]!r}", file=sys.stderr)
            return {}, r["seconds"]
        if strict:
            # strict schema mode itself may be the problem, not just a one-off miss -- drop it on retry, not just re-ask
            return openrouter_chat_json(system, user, schema, meter, model, tag=tag + "+retry", strict=False)
        return openrouter_chat_json(system, user + "\n\nAnswer with the JSON object only, matching the shape given.",
                                     schema, meter, model, tag=tag + "+retry", strict=False)


# ---------------------------------------------------------------- native provider clients
#
# Direct calls to Anthropic and Google, once their own API keys are set --
# bypasses OpenRouter entirely (no shared free-tier congestion, no account
# credit to run out of). Same (dict, float) return shape as chat_json /
# openrouter_chat_json, so a caller can swap backends without caring which
# provider answered.

ANTHROPIC_BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
ANTHROPIC_MAX_RPM = float(os.environ.get("ANTHROPIC_MAX_RPM", "25"))   # real testing hit 429s above this under concurrent load
_anthropic_throttle = _make_throttle(ANTHROPIC_MAX_RPM)


def _post2(url: str, body: dict, headers: dict) -> dict:
    """Like _post, but with the caller's own headers verbatim -- Anthropic's
    x-api-key scheme doesn't fit _post's Bearer-token assumption.

    429 gets the same patient, Retry-After-aware treatment _post_openrouter
    already uses: real testing under concurrent load showed Anthropic and
    Gemini both genuinely rate-limiting (not a parsing/schema issue at all --
    confirmed by grepping the actual error text), and the old 4-attempt/
    2-4-8s ladder gave up long before the account's real limit cleared,
    failing the whole batch at once every time it happened."""
    data = json.dumps(body).encode()
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            return json.loads(urllib.request.urlopen(req, timeout=900).read())
        except urllib.error.HTTPError as err:
            detail = err.read().decode()[:500]
            if err.code == 429:
                if attempt == 5:
                    raise RuntimeError(f"{url} -> HTTP 429 after 6 attempts: {detail[:300]}") from None
                retry_after = err.headers.get("Retry-After") if err.headers else None
                wait = float(retry_after) if retry_after else min(60.0, 3 * 2 ** attempt)
                print(f"[{url.split('//')[1].split('/')[0]}] 429 (attempt {attempt + 1}/6), waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if err.code not in (500, 502, 503) or attempt == 5:
                raise RuntimeError(f"{url} -> HTTP {err.code}: {detail[:300]}") from None
            time.sleep(min(30.0, 2 ** attempt))
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as err:
            if attempt == 5:
                raise RuntimeError(f"{url} -> network error after 6 attempts: {err}") from None
            time.sleep(min(30.0, 2 ** attempt))
    raise RuntimeError("unreachable")


def _unwrap_double_encoded(value):
    """Some tool_use calls (seen on claude-sonnet-5-5/claude-opus-5-5) put an
    array/object field's value in as a JSON *string* instead of the parsed
    value itself -- e.g. {"scores": "[{\\"id\\":\\"c1\\",...}]"} instead of
    {"scores": [{"id":"c1",...}]}. Recursively un-stringify anything that
    parses cleanly to a list or dict, so callers can treat tool input the
    same as any other backend's JSON."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return _unwrap_double_encoded(parsed) if isinstance(parsed, (list, dict)) else value
    if isinstance(value, dict):
        return {k: _unwrap_double_encoded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_unwrap_double_encoded(v) for v in value]
    return value


def anthropic_chat_json(system: str, user: str, schema: dict, meter: Meter, model: str, tag: str = "") -> tuple[dict, float]:
    """One call to Anthropic's Messages API, forced into `schema`'s shape via
    a single required tool call (Anthropic's own recommended way to get
    schema-exact JSON -- there's no separate "strict JSON mode" to ask for).
    `model` is a native Anthropic model id, e.g. 'claude-haiku-5-5'."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set -- add it to akshaya/.env")
    body = {
        # 4096, not 1024 -- a full 20-candidate batch's tool_use JSON is normally
        # a few hundred tokens, but 1024 left no margin at all, and a cut-off
        # response looked identical to a missing-ids response downstream (no
        # stop_reason check existed to tell them apart). This is the single
        # biggest source of the "whole batch missing" fallbacks seen under
        # concurrent load, where response time/length pressure is highest.
        "model": model, "max_tokens": 4096, "system": system,
        "messages": [{"role": "user", "content": user}],
        "tools": [{"name": "result", "description": "Submit the answer in this exact shape.", "input_schema": schema}],
        # "auto", not a forced {"type":"tool",...} -- newer model tiers (sonnet-5-5,
        # opus-5-5) reject a forced tool_choice outright ("not supported for this
        # model"). Offering exactly one tool reliably gets it called anyway.
        "tool_choice": {"type": "auto"},
    }
    headers = {"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}

    def run():
        t = time.time()
        _anthropic_throttle()
        r = _post2(ANTHROPIC_BASE + "/messages", body, headers)
        if r.get("stop_reason") == "max_tokens":
            print(f"[anthropic] {model} hit max_tokens=4096 -- answer is truncated, not just incomplete per-id", file=sys.stderr)
        block = next((b for b in r.get("content", []) if b.get("type") == "tool_use"), None)
        content = json.dumps(_unwrap_double_encoded(block["input"])) if block else ""
        use = r.get("usage", {})
        return {"content": content, "in": use.get("input_tokens", 0), "out": use.get("output_tokens", 0), "seconds": time.time() - t}

    r = _cached("anthropic", {"body": body, "tag": tag}, run)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += r["in"]
        meter.tokens_out += r["out"]
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, r["in"], r["out"])
    try:
        return json.loads(r["content"]) if r["content"] else {}, r["seconds"]
    except json.JSONDecodeError:
        return {}, r["seconds"]


GEMINI_BASE = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
GEMINI_MAX_RPM = float(os.environ.get("GEMINI_MAX_RPM", "15"))   # real testing (577/316 full-batch fallbacks, confirmed HTTP 429 in the logs) showed this account's real limit is well under 50
_gemini_throttle = _make_throttle(GEMINI_MAX_RPM)


def _gemini_schema(schema):
    """Gemini's responseSchema is a narrower subset of JSON schema than
    OpenAI/Anthropic's -- strips additionalProperties (unsupported, causes a
    400) while keeping type/properties/items/required/enum."""
    if isinstance(schema, dict):
        return {k: _gemini_schema(v) for k, v in schema.items() if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


def gemini_chat_json(system: str, user: str, schema: dict, meter: Meter, model: str, tag: str = "") -> tuple[dict, float]:
    """One call to Google's Gemini API, using its native JSON mode
    (responseMimeType + responseSchema). `model` is a native Gemini model id,
    e.g. 'gemini-3.1-flash-lite'."""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set -- add it to akshaya/.env")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        # maxOutputTokens was never set before -- Gemini fell back to its own
        # implicit default, which a full 20-candidate batch's JSON can run
        # close to under load. A cut response looks identical to a
        # missing-ids response downstream with no way to tell them apart, so
        # this (plus the finishReason check below) is the real fix for most
        # of Gemini's "whole batch missing" fallbacks, not just a retry.
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _gemini_schema(schema),
                             "temperature": 0, "maxOutputTokens": 4096},
    }
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={key}"

    def run():
        t = time.time()
        _gemini_throttle()
        r = _post2(url, body, {"Content-Type": "application/json"})
        cand = (r.get("candidates") or [{}])[0]
        if cand.get("finishReason") == "MAX_TOKENS":
            print(f"[gemini] {model} hit maxOutputTokens=4096 -- answer is truncated, not just incomplete per-id", file=sys.stderr)
        content = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        use = r.get("usageMetadata", {})
        return {"content": content, "in": use.get("promptTokenCount", 0), "out": use.get("candidatesTokenCount", 0), "seconds": time.time() - t}

    r = _cached("gemini", {"body": body, "tag": tag}, run)
    with _LOCK:
        meter.llm_calls += 1
        meter.tokens_in += r["in"]
        meter.tokens_out += r["out"]
        meter.llm_seconds += r["seconds"]
        meter.tag(tag, r["in"], r["out"])
    try:
        return _extract_json(r["content"]), r["seconds"]
    except json.JSONDecodeError:
        return {}, r["seconds"]


# ---------------------------------------------------------------- requirement understanding

PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string"},
        "other_names": {"type": "array", "items": {"type": "string"}},
        "skills": {"type": "array", "items": {"type": "string"}},
        "min_years": {"type": ["integer", "null"]},
        "work_mode": {"type": "string", "enum": ["in_person", "hybrid", "remote", "unspecified"]},
        "city": {"type": ["string", "null"]},
        "country": {"type": ["string", "null"]},
    },
    "required": ["role", "other_names", "skills", "min_years", "work_mode", "city", "country"],
}

PARSE_SYSTEM = """You read one request for help and turn it into search fields. Return JSON only.
- role: the kind of person wanted, in 2-4 plain words (for example "wedding photographer").
- other_names: up to 6 other words people use for the same role, tools or activity (synonyms, common tool names, abbreviations).
- skills: the specific skills or tools the request names.
- min_years: the minimum years of experience asked for, or null if none is stated.
- work_mode: "in_person" if the person must be physically present, "hybrid" if partly, "remote" if it can be done online, "unspecified" if the text does not say.
- city, country: where the work is, or null. Give the country for a named city."""


def parse_requirement(text: str, meter: Meter) -> dict:
    """Used by both designs. The prompt holds the requirement text only (NFR-19)."""
    out, secs = chat_json(PARSE_SYSTEM, text, PARSE_SCHEMA, meter, tag="parse")
    meter.stage([secs])
    out.setdefault("role", "")
    out.setdefault("other_names", [])
    out.setdefault("skills", [])
    out.setdefault("min_years", None)
    out.setdefault("work_mode", "unspecified")
    out.setdefault("city", None)
    out.setdefault("country", None)
    return out
