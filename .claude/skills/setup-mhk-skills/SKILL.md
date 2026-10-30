---
name: setup-mhk-skills
description: "One-time setup for MHK-TECH-INC's engineering skills (to-spec, to-tickets, tdd, diagnosing-bugs, improve-codebase-architecture) in any org repo: confirms the issue tracker, branch/PR conventions, and domain-doc layout against this org's actual GitHub conventions instead of asking generic questions. Run once before first use of the other engineering skills in a repo."
disable-model-invocation: true
---

# Setup MHK-TECH-INC Skills

MHK-TECH-INC-specific replacement for upstream `mattpocock/skills`' `setup-matt-pocock-skills`: most
of what that skill asks the user is already a known fact about this org, so this version states it
and only asks about what's genuinely repo-specific.

## What's already known (org-wide — state it, don't ask)

- **Issue tracker: GitHub Issues, via the `gh` CLI.** Every MHK-TECH-INC repo checked uses GitHub as
  its remote. There is no GitLab, Jira, or Linear tracker in org-wide use.
- **PR workflow: one logical change per PR, never bundle unrelated work.** Confirmed by direct
  correction inside this org — splitting unrelated additions into separate PRs is the expectation,
  not an edge case.
- **The default branch is protected; branch off it, never push to it directly.** Confirmed via
  `MHK-Skills`: PRs required, at least one approving review, force-push and branch deletion both
  blocked, enforced even for admins. Don't assume every repo matches exactly — verify per repo (see
  Explore, below), since protection is configured per repo.
- **Self-approval is blocked and must not be worked around.** Don't try to approve your own PR
  (through any account you control) to satisfy the review requirement — Claude Code's own
  guardrails refuse this, and routing around it defeats the point of requiring review. Get an
  actual second reviewer, or ask the user to approve it themselves.
- **The canonical triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`)
  are NOT in use.** This org's repos carry GitHub's stock default label set instead (`bug`,
  `documentation`, `duplicate`, `enhancement`, `good first issue`, `help wanted`, `invalid`,
  `question`, `wontfix`). Don't create the canonical triage labels unless the user explicitly asks
  for the `triage` skill's workflow — it isn't part of this org's skill set yet, so skip that
  section of setup entirely (same as upstream does when `triage` isn't installed).

## Process

### 1. Explore (repo-specific facts only — the org-wide facts above are already settled)

- `gh repo view --json defaultBranchRef,nameWithOwner` — confirm this repo is actually on GitHub and
  get its real default branch name. Don't assume `main`: at least one MHK-TECH-INC repo
  (`HR-Portal`) defaults to `dev`.
- `gh api repos/{owner}/{repo}/branches/{default_branch}/protection` — this specific repo's actual
  protection rules. Report what's found rather than asserting `MHK-Skills`' numbers apply
  unconditionally; a repo without protection configured yet is worth flagging, not silently assumed
  equivalent.
- `CLAUDE.md` and `AGENTS.md` at the repo root — does either exist? Is there already an
  `## Agent skills` section in one of them?
- `GLOSSARY.md` / `GLOSSARY-MAP.md` and `docs/adr/` — does domain documentation already exist?
  (`docs/adr/NNNN-slug.md` is already this org's convention via the `architect` and `docs-sync`
  skills, so finding one here is normal, not something this skill introduces.)
- `gh label list` — this repo's actual labels, so generated docs reference real ones instead of
  assuming the canonical triage five.
- Monorepo signals (`pnpm-workspace.yaml`, a `workspaces` field in `package.json`, populated
  `packages/*` each with their own `src/`) — confirm before assuming single-context; rare in this
  org's repos checked so far.

### 2. Present findings, ask only what's genuinely unresolved

State the org-wide defaults as already decided — present them as findings, not questions. Ask only
about what exploration didn't settle:

- If this repo's remote isn't GitHub (unlikely, but check): ask how issues are actually tracked here
  instead of assuming.
- If this repo's branch protection differs materially from `MHK-Skills`' (no review requirement, no
  force-push block): say so plainly and ask whether to proceed as-is or flag it for the user to fix
  in GitHub settings — this skill does not change branch protection itself.
- If `CLAUDE.md` and `AGENTS.md` both don't exist: ask which to create. Never create one when the
  other already exists, and never create one just because this skill ran — some repos (this one
  included, see ADR 0003 in `docs/adr/`) deliberately have neither.
- If monorepo signals were found: confirm single- vs. multi-context domain docs.

### 3. Write

Write `docs/agents/issue-tracker.md` from [issue-tracker-github.md](./issue-tracker-github.md) (this
repo's actual default branch and protection findings, one-PR-per-logical-change, no self-approval)
and `docs/agents/domain.md` from [domain.md](./domain.md) (single-context unless multi-context was
confirmed in step 2). Skip `docs/agents/triage-labels.md` entirely — this org hasn't adopted that
convention.

Add or update the `## Agent skills` block in whichever of `CLAUDE.md` / `AGENTS.md` is in use (or
skip this step entirely if neither exists and the user didn't ask to create one):

```markdown
## Agent skills

### Issue tracker

GitHub Issues, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

[single-context | multi-context]. See `docs/agents/domain.md`.
```

If an `## Agent skills` block already exists, update it in place rather than duplicating it. Don't
touch surrounding sections of the file.

### 4. Done

Tell the user setup is complete, which engineering skills now read from these files (`to-spec`,
`to-tickets`, `tdd`, `diagnosing-bugs`, `improve-codebase-architecture`), and that
`docs/agents/*.md` can be hand-edited later — re-running this skill is only needed to switch
conventions or start over.
