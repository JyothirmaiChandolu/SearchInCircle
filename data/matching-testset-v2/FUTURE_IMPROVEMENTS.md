# Future decisions and improvements

This file lists two kinds of items:
- things we chose to postpone
- open questions found while building the matching test data

Each item gives the current behaviour, the open question, and how to change it.

Last updated: 2026-11-13.

---

## Already decided (2026-11-12, Akshaya)

For reference. These are built into the test data.

| # | Decision |
|---|---|
| 1 | Tags never go stale for now, and no reconfirmation reminders are sent (see A1) |
| 2 | The publisher's own tags match their own requirements |
| 3 | Tags need nobody's permission. The creator has full control, and a tag matches as soon as it's created (PRD v1.3, FR-20/22/23) |
| 4 | Blocking works both ways. Neither person sees the other's entries |
| 5 | A person appears once in results, with a note like "2 people in your circle vouch for Ravi" (see B1 for a limit) |
| 6 | Onsite job, candidate in another city or country: ranked lower, still shown |
| 7 | (2026-11-13) The data set must be large and varied: one requirement can have 10, 20 or 100+ matches |
| 8 | (2026-11-13) Entries and requirements carry `location` and experience fields (see B4) |

---

## A. Postponed decisions

### A1. Reconfirmation reminders and stale tags (FR-52)

- **Now:** tags never go stale. If Priya tagged Ravi as a plumber a year ago and
  never confirmed it again, Ravi still shows up. No reminders are sent.
- **To decide later:**
  - Do we send "Is this still accurate?" reminders? How often? (For example, every 90 / 180 / 365 days.)
  - If nobody confirms, what happens? Options:
    - hide the tag from matches
    - rank it lower
    - show it with an "unconfirmed for a long time" label
  - How long is the grace period between the reminder and the consequence?
- **Related:** issue #14, PRD FR-52.
- **To switch on in the test data:** set `RECONFIRM_WINDOW_DAYS` in
  `generate.py` to a number of days, then run `python3 generate.py`.

---

## B. Open questions found while building the test data

### B1. "Show once" can't be guaranteed for tagged non-users

- **The problem:** decision 5 says to show a person once. PRD v1.3 (section 12.1
  and FR-24) also says:
  - tags store no phone or email
  - a person tagged by two subscribers is stored as two separate tags

  The system has only a first and last name to go on, and names aren't unique.
- **Example:** Priya tags "Ravi Kumar, plumber" and Sam tags "Ravi Kumar,
  plumber". They might be the same Ravi or two different Ravis. The system
  can't tell.
- **What works today:** when the tagged person **has an account**, the tag links
  to them, so the system can merge reliably and show "2 people vouch for Ravi".
- **Options for non-users:**
  1. **Show both (safest, matches the PRD today).** Each result says who in your circle knows the person.
  2. **Merge by exact name and skill.** Cleaner, but it wrongly merges two different people who share a name. The test data includes this trap (`same_name_different_person`).
  3. **Collect an optional phone or email per tag** to link people across taggers. The PRD considered this and rejected it for now, because it adds personal data.
- **The test data:** plants both cases. It scores only the reliable merges
  (registered users) and reports other duplicates without failing.
- **Decision needed from:** PRD owner, with Jyoti.

### B2. PRD wording for own tags

- Decision 2 (own tags match) goes beyond FR-32. FR-32 mentions only "tags
  those subscribers created".
- **To do:** update FR-32 in the next PRD version, so the PRD and the code agree.

### B3. GitHub issue #1 is older than PRD v1.3

- Issue #1 still describes:
  - tag consent
  - contact details on tags
  - structured requirement fields (salary, location, experience)
  - resume upload
- PRD v1.3 removed or replaced all of these.
- **To do:** update issue #1 and its sub-issues (#5, #6, #7, #8), PRD v1.3 is added to the repo's `docs/` in PR #23.

### B4. Location and experience fields are not in PRD v1.3

- **Now:** the test data has `location` and `experience_years` on self-entries
  and tags, and `location` and `min_experience_years` on requirements (decision 8).
- **The gap:** PRD v1.3 has no such fields. A tag has a name, skills, an alias
  and a description (FR-14 to FR-17), and a requirement is free text (FR-26).
- **To do:** add the fields to the next PRD version and to the Prisma schema, or
  decide that the matcher must read them from the free text. Until then, a
  matcher can ignore the fields and still be scored.

---

## C. Numbers the PRD still leaves open

None of these changes the test data today.

- **Minimum relevance score** before a match is shown (FR-49, "to be tuned during testing"). This test set is meant for tuning it.
- **Precision and recall targets**, and the size of the test set (PRD section 12.2).
- **Invite expiry** (FR-10), **rate limits**, **chat retention**, and **tag retention after account deletion** (FR-48).

---

## D. Improvements to the test data itself

Not needed now. Worth doing once Jyoti's first version runs.

1. **An even bigger data set.** Today: 698 users, about 4,100 entries, circles up to 199. `--scale 2.5` gives a 500-subscriber circle to check speed against the 5-second target (NFR-01).
2. **Requirement edits and re-matching** (FR-35, FR-51). Add "before and after edit" cases, "new tag added later" cases, and "never notify the same match twice" cases.
3. **Score notifications and display names.** The answer key already has `expected_notify`, `must_not_notify` and `display_name_for_publisher`. The evaluator doesn't score them yet.
4. **Match explanations** (FR-50). Check that each result comes with a short "why it matched" text.
5. **Helpful / not helpful feedback** (FR-53). Add sample feedback rows once that table exists.
6. **One skill per match** (FR-15). Tags with several skills are scored as a whole today. Decide whether results should point to the specific skill.
7. **Load into the real database.** Once the Prisma schema has the real tables, add a seed script that loads these JSON files into Postgres.
8. **Even messier text.** The data has typos, lowercase and abbreviations. Still missing: Hinglish or Telugu-English mixes, and requirements that ask for two things at once.
