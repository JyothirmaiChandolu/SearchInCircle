# Matching experiments

Two independent matching workflows, built separately and scored on the same test set.

| Folder | Owner | Contents |
|---|---|---|
| [`akshaya/`](akshaya/) | Akshaya | Design A (retrieve, then rerank) and design B (profile on save, model grades everyone), in Python. Start with [`akshaya/RESULTS.md`](akshaya/RESULTS.md) |
| [`jyoti/`](jyoti/) | Jyoti | Jyoti's workflow. Add your code here |

Keep each person's code inside their own folder. The shared test set is in [`data/matching-testset/`](../../data/matching-testset/).

## How to compare

Every matcher must write one JSON file that maps each requirement id to entry ids, best first (`[]` when nothing fits). The format is in the [test set README](../../data/matching-testset/README.md).

```bash
cd backend/matching-experiments
python3 compare.py akshaya/out-openai/predictions_B.json jyoti/out/predictions.json
```

`compare.py` scores each file with the test set's `evaluate.py` and prints the results side by side. A matcher may only read the public test-set files. **Do not read `data/matching-testset/answer_key/`.**

## Cost and speed

`evaluate.py` measures accuracy only. For a fair comparison, record these for each workflow in the same way, and put them in the folder's own results file:

- model calls, input tokens and output tokens per requirement
- seconds per requirement, including the database query when one exists
- code size and the number of settings to tune
- what is stored when a tag is saved

Akshaya's numbers are in [`akshaya/RESULTS.md`](akshaya/RESULTS.md) as an example of the format.

## Secrets

API keys go in a `.env` file inside your own folder. `.env` files are git-ignored. Never commit a key.
