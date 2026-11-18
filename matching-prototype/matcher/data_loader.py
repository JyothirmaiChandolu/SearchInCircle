from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def _read(dataset_dir: Path, filename: str) -> Any:
    if filename.startswith('answer_key'):
        raise RuntimeError('Refusing to read answer_key/ -- it is the hidden grading data, not a matcher input.')
    return json.loads((dataset_dir / filename).read_text())


class Dataset:
    """Loads the public data/matching-testset files once. Never touches answer_key/."""

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir
        self.users: list[dict] = _read(dataset_dir, 'users.json')
        self.self_entries: list[dict] = _read(dataset_dir, 'self_entries.json')
        self.tags: list[dict] = _read(dataset_dir, 'tags.json')
        self.requirements: list[dict] = _read(dataset_dir, 'requirements.json')
        self.connections: list[dict] = _read(dataset_dir, 'trust_connections.json')
        self.blocks: list[dict] = _read(dataset_dir, 'blocks.json')
        self.rules: dict = _read(dataset_dir, 'rules.json')

    def requirement_by_id(self, req_id: str) -> dict | None:
        return next((r for r in self.requirements if r['id'] == req_id), None)

    def user_by_id(self, user_id: str) -> dict | None:
        return next((u for u in self.users if u['id'] == user_id), None)

    def entries(self) -> Iterator[tuple[str, dict]]:
        for e in self.self_entries:
            yield ('self_entry', e)
        for e in self.tags:
            yield ('tag', e)
