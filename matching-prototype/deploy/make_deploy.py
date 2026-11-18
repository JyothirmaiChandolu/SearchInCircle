#!/usr/bin/env python3
"""Builds the self-contained folder you deploy to Vercel: deploy/out/.

    cd matching-prototype && . .venv/bin/activate && pip install numpy
    python deploy/make_deploy.py

The folder holds the app, the experiment code (engine/), the small v2 test
dataset (4,130 entries) plus ready-made entry vectors (data/vectors.npz, float16),
and the Vercel config. The big 39k-entry set and the 1.9 GB caches stay local:
a serverless function has neither the disk nor the memory for them.
Run it again after any code change, then redeploy.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
REPO = PROTO.parent
ENGINE_SRC = REPO / 'backend' / 'matching-experiments' / 'akshaya'
DATA_SRC = REPO / 'data' / 'matching-testset-v2'
OUT = Path(__file__).resolve().parent / 'out'

DATA_FILES = ['users.json', 'self_entries.json', 'tags.json', 'trust_connections.json',
              'blocks.json', 'rules.json', 'requirements.json']   # never answer_key/


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / 'engine' / 'openrouter').mkdir(parents=True)
    (OUT / 'data').mkdir()

    shutil.copy(PROTO / 'app.py', OUT / 'app.py')
    shutil.copytree(PROTO / 'matcher', OUT / 'matcher', ignore=shutil.ignore_patterns('__pycache__', '.embedding_cache.json'))
    shutil.copytree(PROTO / 'static', OUT / 'static')
    for name in ('common.py', 'design_b.py', 'design_c.py'):
        shutil.copy(ENGINE_SRC / name, OUT / 'engine' / name)
    for name in ('design_c_openrouter.py', 'run_native_v2.py'):
        shutil.copy(ENGINE_SRC / 'openrouter' / name, OUT / 'engine' / 'openrouter' / name)
    for name in DATA_FILES:
        shutil.copy(DATA_SRC / name, OUT / 'data' / name)

    (OUT / 'requirements.txt').write_text('fastapi>=0.115,<1.0\npydantic>=2.9,<3.0\npython-dotenv>=1.0,<2.0\nopenai>=1.54,<2.0\nnumpy>=1.26\n')
    (OUT / 'vercel.json').write_text('{\n  "functions": { "app.py": { "maxDuration": 300 } }\n}\n')
    (OUT / '.python-version').write_text('3.12\n')
    (OUT / '.vercelignore').write_text('__pycache__\n*.pyc\n.env\n')

    build_vectors()
    size = sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()) / 1e6
    print(f'\nBundle ready: {OUT}  ({size:.0f} MB uncompressed; Vercel allows 250 MB)')


def build_vectors() -> None:
    """Entry vectors for the v2 set, from the same embeddings the experiments already
    paid for (disk cache hit; a miss would embed the 4,130 texts, about $0.01)."""
    import numpy as np
    os.environ['MATCH_DATA_DIR'] = str(DATA_SRC)
    sys.path.insert(0, str(ENGINE_SRC))
    import common
    entries = common.load_entries()
    texts = sorted({e.text for e in entries})
    print(f'embedding {len(texts)} distinct entry texts (cached if seen before)...')
    vecs = np.array(common.embed(texts), dtype=np.float16)
    np.savez_compressed(OUT / 'data' / 'vectors.npz', texts=np.array(texts), vecs=vecs)
    print(f'vectors: {vecs.shape}, {(OUT / "data" / "vectors.npz").stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
