---
name: bug-fix-lifecycle
description: A disciplined lifecycle for fixing bugs in any codebase - locate the code, confirm the bug is real, fix it, check the blast radius, hunt for the same bug elsewhere, then verify. Use this skill whenever the user asks to fix a bug, an error, a failing test, a regression, a reported issue, or a list of issues, even if they only say "this is broken", "can you fix this", "users are seeing X", or "solve these one by one". Also use it when the user asks to make sure a fix doesn't break anything else or to check for similar problems.
---

# Bug fix lifecycle

Bug reports are often partly wrong: stale, mis-described, or already fixed. Fixes often break neighbours or leave the same defect in a sibling file. This lifecycle exists to prevent both. Run it **once per bug**, in order. For several bugs, finish one fully before starting the next, so each fix stays small and attributable.

## 1. Locate
Find the code that produces the reported behaviour. Search for the symptom (error text, UI label, endpoint, function name) and follow it to where the behaviour is decided. Read the real code path, including validation, callers and config; don't guess from the report. If the report points at files or lines, treat them as hints, not facts.

## 2. Confirm it is a real bug
Reproduce or prove it from the code before changing anything: run it, write a failing test, or trace the path and state exactly which input produces the wrong output. Then give one verdict:
- **Real bug** - proceed.
- **Already fixed / not reproducible** - say so with evidence and stop. Don't "fix" what isn't broken.
- **Intended behaviour** - say so, and cite where the intent is visible (comment, spec, other code).
- **Needs a product decision** - the correct behaviour is ambiguous. Note it and move on; don't invent requirements.

Report the verdict to the user briefly. This is the step that most protects against wasted or harmful changes.

## 3. Fix
Make the smallest change that fixes the root cause rather than the symptom. Match the surrounding code's style, naming and comment density. Put shared logic in one helper rather than copying it. Validate on the server/authoritative side, not only in the UI. Don't refactor unrelated code in the same change.

## 4. Check the blast radius
Anything you changed can affect other code. Find out, don't assume:
- Search for every caller, importer and consumer of what you touched (functions, fields, endpoints, constants, CSS classes, enum values).
- Check data: existing records that the new rule would now reject, migrations, defaults, serialized shapes.
- Check related surfaces: other UI that renders the same data, background jobs, scripts, tests, docs.
- Run the existing tests and linters/build for the affected area.
If something is affected, fix it or flag it explicitly.

## 5. Hunt for the same bug elsewhere
The same mistake usually exists in sibling code: duplicated validation lists, copy-pasted handlers, parallel endpoints, other pages using the same pattern. Search for the pattern (a distinctive string, call, or idiom), not just the filename. Fix confirmed instances using this same lifecycle (steps 2-4 for each); list the ones you deliberately left alone and why.

## 6. Verify
Prove the fix works: a regression test or script that fails before and passes after, or a run of the real flow. Prefer a test that stays in the repo. Never claim "fixed" on the strength of reading the code alone; say plainly what you ran and what you did not.

## Boundaries
- Don't commit, push, or touch git history unless the user asks.
- Don't run database migrations or destructive data changes against a database whose environment you haven't confirmed; write the migration and hand it over.
- Don't widen scope silently: unrelated problems you notice go in the report, not the diff.

## Final report
Keep it short. Per bug: verdict, what changed, what you checked for blast radius and similar instances, how it was verified. Then one list of anything still open (decisions needed, unapplied steps, untested areas).
