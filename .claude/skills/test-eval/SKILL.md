---
name: test-eval
description: >
  Testing and evaluation — designing test coverage for code changes, and building rubric-based
  evals for LLM/agent output quality. Use when the user asks to write tests for a change, review
  test coverage, design a test strategy, or evaluate/score the quality of generated output
  (prompts, agent responses, generated docs/code) against defined criteria.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
context: fork
---

## Role

You cover two related but distinct jobs: writing/reviewing **tests** for code, and building
**evals** for output quality (especially LLM/agent output where correctness isn't just pass/fail).
Work out which one the request needs before starting — they use different tools.

## Testing code

1. **Test the behavior, not the implementation.** A test that breaks whenever internals are
   refactored, even though behavior is unchanged, is a liability, not a safety net.
2. **Cover the boundary cases first**: empty input, single item, the max/min of any bound, invalid
   input, concurrent access if relevant, and the specific bug being fixed (a regression test should
   fail on the old code and pass on the new).
3. **Match the existing test structure and tooling** in the repo — don't introduce a second test
   framework or a new assertion style alongside an established one.
4. **No mocking what you're actually trying to verify.** Mocking a dependency to isolate the unit
   under test is fine; mocking away the exact integration point the test exists to catch defeats
   the test's purpose.
5. **A failing test you can't yet explain is a finding, not noise** — investigate root cause before
   loosening an assertion or adding a retry/skip to make it pass.
6. When reviewing coverage rather than writing tests: identify what's untested, prioritized by
   blast radius (a silent data-corruption path outranks an uncovered log message), and record the
   result in `docs/testing.md` if this repo uses that as its test-strategy doc.

## Evaluating output quality (LLM/agent evals)

Use this when "correct" isn't binary — grading agent responses, generated docs, prompts, or other
output where quality is graded, not just pass/fail.

1. **Define the rubric before looking at outputs.** Pick 3-6 concrete, checkable criteria (e.g.
   "cites a source for every factual claim," "under 200 words," "doesn't invent an API that doesn't
   exist"). Vague criteria ("is it good?") produce unusable evals.
2. **Build a small labeled set first.** A handful of known-good and known-bad examples to validate
   the rubric actually discriminates between them before running it at scale.
3. **Prefer objective, automatable checks where they exist** (schema validation, a regex, a unit
   test on generated code) over LLM-judge grading; reserve LLM-as-judge for criteria that genuinely
   need judgment (tone, relevance, reasoning quality), and say explicitly which criteria are graded
   which way.
4. **Score with evidence, not a bare number.** Each score should cite the specific part of the
   output that earned or lost points — an ungrounded "7/10" isn't actionable.
5. **Watch for the eval being gamed** — an output that satisfies the rubric's letter while missing
   its intent (e.g. citing a source that doesn't actually support the claim) is a rubric bug, not a
   passing case; tighten the criterion.
6. **Report failure modes, not just an aggregate score** — which criteria failed, on which
   examples, and whether failures cluster (one bad criterion vs. broadly weak output).
