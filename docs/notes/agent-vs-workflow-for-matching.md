# Agent or fixed workflow for matching?

Reference note, written 2026-11-13. It records the reasoning for a decision we
may revisit: should an AI agent that chooses its own steps do the matching, or
should matching be a fixed workflow with model calls at set points?

**Decision for v1: a fixed workflow.** A model is used inside it at fixed steps
(read the requirement, grade candidates). No agent decides the path.

## Why not an agent for the matching itself

An agent is worth its cost when the path changes from one input to the next and
something has to decide what to do next. Matching does not have that. Every
requirement goes through the same steps in the same order.

| Concern | Fixed workflow | Agent that picks its own steps |
|---|---|---|
| Hard rules (blocks, audience, anonymity, direct circle only) | Applied in code, the same way every time | The agent writes its own queries, so it can skip or misapply a rule. One hidden person shown is a hard failure in our evaluator |
| Privacy (NFR-12, NFR-19) | The model gets only skill text under opaque ids | An agent with database tools can reach names, aliases and the publisher unless every tool is locked down |
| Cost (NFR-13) | A known number of model calls per requirement | May take 3 steps or 15 for the same requirement |
| Speed (NFR-01, 5 seconds) | Predictable, and the calls can run in parallel | Steps run one after another, each waiting on the model |
| Repeatability | Same input gives the same result | The same requirement can give different results on different runs, which also makes A/B comparison noisy |
| Debugging | Each step has a clear input and output | You have to read a transcript to learn what happened |

Our own research on similar products reached the same result: it rates agentic
matching "Skip for v1: hard to guarantee visibility rules".

## Where an agent would help

These are the places where the path does change from case to case.

1. **Requirement intake.** Someone posts "need help with my app". An agent asks
   the follow-up questions (which skill, which city, remote or in person, how
   many years) before matching runs. This is the best use, because a clearer
   requirement improves every later step.
2. **No-match follow-up.** When nothing is found, an agent suggests how to widen
   the requirement, or which subscribers to ask for a tag.
3. **Offline analysis.** An agent goes through the evaluator's failures and
   explains why each wrong match happened. It runs on test data, so the privacy
   and speed limits do not apply.
4. **Tag writing help.** When a subscriber writes a thin tag ("good with
   computers"), an agent asks one or two questions to make it findable.

## Rules to follow if we add an agent later

- Give it only the already-filtered pool. It must never be able to query
  entries outside the publisher's circle.
- Give it tools that return skill text under opaque ids only. No names, aliases,
  contact details or publisher identity.
- Put a hard limit on steps and tokens per run.
- Keep the fixed workflow as the fallback when the agent fails or times out.
- Score it with `data/matching-testset/evaluate.py` against the same test set,
  and run it several times to measure how much its results vary.

## If we want to test it anyway

Run an agent as a third contender on the test set. Expected result: about the
same accuracy as the model-judge step in the workflow, at a higher cost, and
with slower and less repeatable runs. The prototypes and the comparison are in
`backend/matching-experiments/akshaya/`.
