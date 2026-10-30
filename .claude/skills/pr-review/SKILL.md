---
name: pr-review
description: >
  Reviews a pull request end-to-end against its task's Definition of Done, the code itself,
  integration/test coverage, and — when the change touches UI — live browser verification. Use
  when the user asks to "review this PR", "check this against the ticket/DoD", wants a full review
  before merge, or asks for a code review that should also verify things in the browser.
allowed-tools: Read, Grep, Glob, Bash(git *) Bash(gh *), WebFetch
agent: code-reviewer
context: fork
---

## PR context (current branch)

!`gh pr view --json number,title,body,url,headRefName 2>/dev/null || echo "(no PR found for the current branch — ask the user for the PR number/URL and the task/ticket link)"`

## Diff

!`gh pr diff 2>/dev/null || git diff main...HEAD 2>/dev/null || git diff`

## Task

Hand off to the `code-reviewer` subagent with the PR context and diff above.

- If a task/ticket link or explicit Definition of Done wasn't provided by the user and isn't
  already in the PR description, ask for it before the subagent finalizes its DoD checklist —
  never invent acceptance criteria.
- If the diff touches UI/frontend files, tell the subagent to run its browser verification step;
  otherwise tell it to skip that step explicitly and say so in its report.
- This skill only gathers fresh context (PR metadata + diff); `code-reviewer` does the actual
  review. It can also be invoked directly via the Agent tool for ad hoc reviews outside a skill
  context — see [ADR 0004](../../../docs/adr/0004-code-reviewer-subagent-exception.md) for why this
  is the one skill in this repo that isn't fully self-contained.
