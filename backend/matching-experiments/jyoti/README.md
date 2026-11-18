# Jyoti's matching workflow

Add the code here.

When it is in place, write a results file in the same style as [`../akshaya/RESULTS.md`](../akshaya/RESULTS.md). Save the predictions as `out/predictions.json`, then compare from the parent folder:

```bash
python3 compare.py akshaya/out-openai/predictions_B.json jyoti/out/predictions.json
```

Keep API keys in `jyoti/.env`. It is git-ignored.
