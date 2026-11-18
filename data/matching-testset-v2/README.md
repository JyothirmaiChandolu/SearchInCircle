# Matching test set

Dummy data for building and testing the matching engine (issue #11). It has a
labelled answer key, so a matcher gets a score, not only a "looks right".

The data model follows **PRD v1.3**, which is newer than GitHub issue #1:
- Requirements are free text.
- Tags hold a name, skills, an optional description and an optional alias.
- Tags have no contact details and no approval step.
- **Two fields go beyond PRD v1.3** (asked for on 2026-11-13): `location` and
  `experience_years` on entries, and `location` and `min_experience_years` on
  requirements. Either can be `null` when it is not known. See FUTURE_IMPROVEMENTS.md item B4.

## How big and how varied it is

| | |
|---|---|
| Users | 698, in 12 communities (for example Hyderabad tech, Houston healthcare, Austin neighbourhood) |
| Trust circles | From 10 to 199 subscribers per publisher |
| Entries | About 800 self-entries and 3,300 tags |
| Kinds of skill | 52: tech, health, home services, professional services, teaching, hobbies, and things to lend (a pickup truck, a spare room, power tools) |
| Specialties | 3–4 per skill (for example ICU / paediatric / home-care / emergency nurse) |
| Requirements | 37, written in different styles: detailed, short, casual, worded with synonyms |
| Matches per requirement | **0, a few (3–6), 10–25, 30–50, and 110** good-or-strong people |

People cluster the way real circles do: a tech worker mostly knows tech workers.
That is why "Python backend developer" in a 199-person Hyderabad tech circle
has 110 good matches, while the same skill in a 59-person Seattle circle has 24.

Text is assembled from parts (role name, specialty, how the years are written,
tools, voice, style, and sometimes typos or all-lowercase), so almost no two
descriptions are the same: 2,850 of 2,880 tag descriptions are unique.

Everything is fake. Emails use `example.com`. US numbers use the reserved
`555-01xx` range, and UK numbers use the Ofcom drama range.

## Quick start

```bash
cd data/matching-testset
python3 generate.py                                    # rebuild (deterministic, seed 42); --scale 0.3 for a small set
python3 baseline_keyword.py > predictions_baseline.json
python3 evaluate.py predictions_baseline.json          # exit code 1 on any hard failure
```

Python 3.10+ and the standard library only. **To review the data by eye, open
[`answer_key/REVIEW.md`](answer_key/REVIEW.md).** It shows one table per
requirement: what it should find, what it must hide, and why.

## What your matcher reads and writes

**Input:** read only the public files below. **Do not read `answer_key/`.**
It holds the hidden labels, so reading it is cheating.

**Output:** a JSON object that maps each requirement id to the entry ids you
would surface, best first. Use `[]` when nothing clears your relevance bar (FR-49).

```json
{ "R01": ["T0163", "S0040", "T0012"], "R12": [], "R13": [] }
```

## Files

| File | Rows | Contents |
|---|---|---|
| `users.json` | 698 | `id, username, nickname, name, email, phone, bio, location` |
| `trust_connections.json` | ~3,460 | `requester_id, addressee_id, status`: `accepted` / `pending` / `rejected` / `removed` |
| `blocks.json` | 12 | `blocker_id, blocked_id` |
| `self_entries.json` | ~800 | FR-13: `owner_user_id, skill, description, experience_years, location, availability_status` |
| `tags.json` | ~3,300 | FR-14–17: `owner_user_id` (the tagger), `subject_user_id` (set only when the tagged person is a user), `first_name, last_name, alias, skills[], description` (may be `null`), `experience_years, location` (may be `null`), `availability_status, last_confirmed_at` |
| `requirements.json` | 37 | FR-26/27/54: `publisher_id, text, location` (`null` = remote), `min_experience_years, status, anonymous, audience_user_ids` |
| `rules.json` | 1 | `reference_date` (treat as "today"), `reconfirm_window_days` (`null` = tags never go stale), `include_own_tags` |
| `answer_key/REVIEW.md` | | Human-readable review page |
| `answer_key/ground_truth.json` | | Per requirement: eligible entries, exclusion reasons, graded relevance, expected notifications, show-once groups |
| `answer_key/ground_truth.csv` | | The graded rows flattened, for a spreadsheet |
| `answer_key/entry_labels.json` | | The hidden truth for every entry: archetype, real person, years, city |

How the fields and the text relate:
- `experience_years` and `location` hold the fact when the entry's author knows it.
  About 1 entry in 6 leaves one of them `null`.
- The description sometimes repeats the years or the city, in many forms
  ("5 yrs exp", "doing this since 2021", "Austin area"), and sometimes doesn't.
- A description covers experience or specialty only (FR-16). It never says how
  the tagger knows the person.
- A tag can list an extra, unrelated skill of the same person (FR-15), for
  example a Java developer who also plays tennis.

## Rules the answer key uses

### 1. Eligibility: hard rules, never break them

The circle for requirement R, posted by P, is P's accepted subscribers (FR-32).
That covers their self-entries and the tags they created, plus **P's own tags**
(decided 2026-11-12).

An entry **must not** be returned if any of these is true:

| Reason code | Condition |
|---|---|
| `requirement_closed` | R is closed (FR-30) |
| `own_self_entry` | It is P's own self-entry. P doesn't need to find themself |
| `not_in_direct_circle` | No accepted connection between P and the owner. **This includes friends-of-friends** (FR-32) |
| `pending_connection` | The invite was never accepted (FR-05) |
| `removed_connection` | One of them removed the other (FR-08) |
| `blocked` | Either side blocked the other. Neither sees the other's entries (FR-46, decided 2026-11-12) |
| `outside_audience` | R is shown only to chosen subscribers, and the owner isn't one of them (FR-27/28) |
| `not_open` | Marked unavailable (FR-31/33) |
| `subject_is_publisher` | A subscriber's tag describes P themself |
| `stale_unconfirmed` | **Off for now.** Tags never go stale (decided 2026-11-12). See FUTURE_IMPROVEMENTS.md |

Tags need nobody's permission. A tag is active as soon as it's created (FR-23).

### 2. Relevance: graded 0–3, for ranking

Each entry has a hidden archetype (for example "React Native developer"), and so does each requirement.

- **Same archetype:** start at 3 and subtract misses. A miss counts only when the entry states the fact (the field is not `null`).
  - Experience short by 1–2 years: −1. Short by more: −2.
  - Onsite or hybrid job, candidate in another city of the same country: −1. In another country: −2.
  - The requirement asks for a specialty and the entry states a different one (an ICU job, a paediatric nurse): −1.
  - Rank lower, but still show: they might relocate or commute (decided 2026-11-12).
  - Result: 0 misses → **3**, 1 miss → **2**, 2 or more misses → **1**.
- **Listed only as an extra skill** on a tag about something else: **2**. The skill is there, with no detail to back it.
- **Related archetype** (for example iOS dev for a React Native job): **1**.
- **Anything else: 0.** This includes lexical traps.

An entry can't be penalised for a fact it doesn't state. A tag with only skills,
no description and empty fields counts as **3** if the skill fits.

Each graded row in the answer key has a `why` list that names the lost points,
for example `["experience 2 yrs short", "other city: Pune"]`.

### 3. Show once (decided 2026-11-12)

If one person appears more than once, show them once, with a note such as
"2 people in your circle vouch for Ravi". `expected_merges` lists the groups the
system *can* detect: a self-entry and a tag about the same **registered** user.

For tagged **non-users**, PRD v1.3 stores no contact details. Two tags with the
same name may or may not be the same person, so the data plants both cases.
See FUTURE_IMPROVEMENTS.md item B1.

### 4. Notifications and display (for #12)

- Self-entry match: notify the publisher and the entry owner (FR-36).
- Tag match: notify only the tag's creator, never the tagged person (FR-37).
- If a tag has an alias, everyone except its creator sees the alias (FR-17).
  `display_name_for_publisher` gives the expected name.
- An anonymous requirement (R07) must never reveal the publisher. Per NFR-19,
  that includes AI prompts.

## Scenarios planted per requirement

| Scenario | What it tests | Expected |
|---|---|---|
| `strong_self_entry`, `strong_tag` | Basic retrieval | Show, relevance 3 |
| `synonym_only` | Describes the skill **only** in other words ("Expo" for React Native) | Show, relevance 3. Keyword matching misses it |
| `skills_only_tag` | A tag with skills and no description | Show, relevance 3 |
| `aliased_tag` | The tag has an alias | Show it under the alias |
| `own_tag` | P's own tag | Show (decided 2026-11-12) |
| `old_confirmation` | Last confirmed 200–400 days ago | Show. Old tags must **not** be hidden |
| `duplicate_registered_person` | A subscriber tags a user who also has a matching self-entry | Show the person **once** |
| `duplicate_same_name` | Two subscribers tag the same non-user, same name | The same person, but the system can't prove it |
| `same_name_different_person` | Two different people with the same name | Both must be shown. Merging by name loses one |
| `partial_experience` | 1–2 years below the requirement | Relevance 2 |
| `partial_location` | Onsite job, candidate in another country | Relevance 1, still shown |
| `partial_specialty` | Right skill, different specialty | Relevance 2 |
| `related_archetype` | Adjacent skill set | Relevance 1 |
| `lexical_trap` | Shares a keyword, means something else (ball **python** keeper, **Java** coffee roaster, **cricket** pest control, canvas **painter**, **sales force** manager, food **truck**, oil **pipe**line inspector, and more) | Relevance 0 |
| `own_self_entry`, `not_open`, `two_hop_owner`, `pending_connection`, `removed_connection`, `blocked_owner`, `subject_is_publisher`, `outside_audience` | The hard rules | Relevant on content, but **must be hidden** |

On top of the planted rows, each requirement has many ordinary matching people
(`background` in the answer key), with a spread of strong, good and weak.
REVIEW.md shows a sample of them with the reason for each grade.

Special requirements:
- **R12** (harp teacher): the only harpists are outside the circle or not open. **Expected: no matches.**
- **R13**: closed. **Expected: `[]`.**
- **R09**: shown to only half of the publisher's circle.
- **R07**: anonymous.
- **R17**: the requirement itself uses only synonyms ("bug hunting", "quality assurance").
- **R19, R24**: written casually, in lowercase with abbreviations.
- **R20 and R26**: the same skill (Python backend) asked by two publishers. Each must get only their own circle's people.
- **R11, R25, R32, R35, R37**: small circles with only a few matches.
- **R18, R37**: resources (a pickup truck, a spare room), not skills.

## Evaluator metrics

All metrics are per real person: duplicates count once and are reported in the `dup` column.
Return as many entries as are relevant; the list can be any length.

- **Hard failures:** any hidden entry returned, or results for a closed requirement. Exit code 1.
- **nDCG@10:** how good the ranking of the top 10 is, using the graded relevance.
- **P@10:** the share of the top 10 that are good or strong.
- **recall:** the share of all good-or-strong people that appear anywhere in the list.
- **prec:** the share of returned people that are relevant at all. This stops a matcher from returning everyone.
- **syn:** people described only in other words that were found.
- **trap:** lexical traps in the top 10.
- **once:** detectable duplicates shown exactly once.
- **Empty cases:** R12 and R13 must return no relevant results.

Keyword baseline (seed 42):

| Metric | Score |
|---|---|
| Hard failures | 0 |
| nDCG@10 | 0.76 |
| Recall | 0.69 |
| Precision | 0.88 |
| Synonym recall | **29/101** |
| Show once | 16/37 |

A semantic (embedding) matcher should beat it clearly on recall and synonym recall.
A perfect matcher scores 1.0 everywhere and 101/101 on synonyms.

## Changing a rule

Decisions still open are in [FUTURE_IMPROVEMENTS.md](FUTURE_IMPROVEMENTS.md).

To change a rule, edit `relevance()` / `exclusion_reasons()` in `generate.py`
and regenerate. Those two functions are the single source of truth for the
answer key. The skill vocabulary lives in `archetypes.py`.
