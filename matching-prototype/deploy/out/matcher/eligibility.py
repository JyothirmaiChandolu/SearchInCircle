from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class Verdict:
    eligible: bool
    reason: str | None = None


def pair_key(a: str, b: str) -> frozenset[str]:
    return frozenset((a, b))


# A pair can have more than one historical row (request -> accept -> later
# removed -> re-requested). The most recently updated row wins -- an older
# "accepted" never outranks a newer "removed".
def resolve_connections(connections: list[dict]) -> dict[frozenset[str], dict]:
    resolved: dict[frozenset[str], dict] = {}
    for c in connections:
        if c['requester_id'] == c['addressee_id']:
            continue  # corrupt self-loop row -- ignore defensively
        key = pair_key(c['requester_id'], c['addressee_id'])
        timestamp = c.get('responded_at') or c['created_at']
        existing = resolved.get(key)
        existing_ts = (existing.get('responded_at') or existing['created_at']) if existing else None
        if existing is None or existing_ts is None or timestamp >= existing_ts:
            resolved[key] = c
    return resolved


def resolve_blocks(blocks: list[dict]) -> set[frozenset[str]]:
    return {pair_key(b['blocker_id'], b['blocked_id']) for b in blocks}


# Direct, accepted connections only -- this never walks past one hop.
# Friends-of-friends are deliberately out of scope.
def check_circle_eligibility(
    owner_id: str,
    publisher_id: str,
    is_own_tag: bool,
    connections: dict[frozenset[str], dict],
    blocks: set[frozenset[str]],
    audience_ids: list[str],
    rules: dict,
) -> Verdict:
    if owner_id == publisher_id:
        if not is_own_tag:
            return Verdict(False, 'own_self_entry')
        return Verdict(True) if rules['include_own_tags'] else Verdict(False, 'own_tag_excluded')

    connection = connections.get(pair_key(owner_id, publisher_id))
    if not connection:
        return Verdict(False, 'not_in_direct_circle')

    status = connection['status']
    if status == 'pending':
        return Verdict(False, 'pending_connection')
    if status == 'removed':
        return Verdict(False, 'removed_connection')
    if status != 'accepted':
        # 'rejected' or anything unrecognised: same bucket as never connected.
        return Verdict(False, 'not_in_direct_circle')

    if pair_key(owner_id, publisher_id) in blocks:
        return Verdict(False, 'blocked')
    if audience_ids and owner_id not in audience_ids:
        return Verdict(False, 'outside_audience')
    return Verdict(True)


# Availability + content-level constraints -- who's allowed to see whom
# lives in check_circle_eligibility; this only asks "is the entry usable."
def check_basic_eligibility(kind: str, entry: dict, publisher_id: str, rules: dict) -> Verdict:
    if entry.get('availability_status') != 'open':
        return Verdict(False, 'not_open')

    if kind == 'tag':
        if entry.get('subject_user_id') == publisher_id:
            return Verdict(False, 'subject_is_publisher')

        window = rules.get('reconfirm_window_days')
        if window is not None:
            last_confirmed = entry.get('last_confirmed_at')
            if not last_confirmed:
                return Verdict(False, 'stale_unconfirmed')
            ref = dt.date.fromisoformat(rules['reference_date'])
            last = dt.date.fromisoformat(last_confirmed)
            if (ref - last).days > window:
                return Verdict(False, 'stale_unconfirmed')

    return Verdict(True)
