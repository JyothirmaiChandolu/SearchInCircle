# Matching test set, 10,000-candidate scale

The same kind of data as [`../matching-testset/`](../matching-testset/), generated 10 times larger.
Use it to check how a matcher behaves, and what it costs, when one requirement has
up to about 10,000 candidates to choose from.

All rules, file formats and the answer-key rules are the same as in the
[main test set README](../matching-testset/README.md). Read that first.
**Do not read `answer_key/` from a matcher.**

## Size

| | |
|---|---|
| Users | 6,980 |
| Entries | 39,169 (8,012 self-entries and 31,157 tags) |
| Kinds of person | 138 job roles, hobbies and things to lend, plus 12 keyword traps |
| Requirements | 45 (the same texts as the main set) |
| Candidates per requirement, after the hard rules | from 336 to **11,237** |
| Good or strong people per requirement | from 0 to 1,115 |

| Candidates per requirement | Requirements |
|---|---|
| 11,237 | R03, R04, R17, R20, R21, R38 |
| 7,859 | R28, R29, R30, R31, R41 |
| 5,936 | R10, R23, R24, R36 |
| 2,000 to 3,100 | R01, R02, R05, R06, R09, R14, R18, R19, R22, R26, R27, R37, R39, R40, R42 |
| 1,000 to 1,600 | R07, R08, R15, R16, R33, R34, R43, R45 |
| 336 to 538 | R11, R12, R25, R32, R35, R44 |
| 0 (closed) | R13 |

The largest circle has 1,999 subscribers. That is above the size the PRD plans
for, and it is on purpose: this set is a stress test.

## What each entry holds

- **Skill tags:** `skills[]` on every tag and self-entry, 2 to 9 per entry (median 5), taken from the
  person's skills, specialty and tools. About 2,400 different tags. A self-entry also keeps `skill`, its main skill (FR-13).
- **Description:** a job-specific profile, median 48 words on a tag and 55 on a self-entry: the role,
  then concrete work the person has done, sometimes tools, a certificate and the city. Missing on about 1 tag in 20.
- **Experience:** `experience_years`, a whole number, or `null` when it is not known (about 1 entry in 5).
- **Location:** `location`, a city, or `null` (about 1 entry in 7).
- **Alias:** `alias` on a tag (about 1 tag in 5). When it is set, everyone except the tag's creator must see the alias, never the real name (FR-17). The real name must not be sent to a model either.

## How to use it

Make your matcher read this folder instead of `../matching-testset/`, write the
usual predictions file, then score it with the evaluator in the main set:

```bash
cd data/matching-testset
python3 baseline_keyword.py --data ../matching-testset-10k > predictions_baseline_10k.json
python3 evaluate.py predictions_baseline_10k.json --data ../matching-testset-10k
```

To compare several matchers side by side:

```bash
cd backend/matching-experiments
python3 compare.py --data ../../data/matching-testset-10k akshaya/<file>.json jyoti/<file>.json
```

Keyword baseline on this set: no hidden person shown, nDCG@10 0.766, recall 0.506,
synonym-only people found 217 of 1,121.

## How it was made

```bash
cd data/matching-testset
python3 generate.py --scale 10 --out ../matching-testset-10k     # seed 42
```

Use the committed files, and do not regenerate for a comparison: a different
Python version may give different ids. Generated with Python 3.12.
