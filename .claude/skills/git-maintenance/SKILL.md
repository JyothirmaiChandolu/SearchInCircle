---
name: git-maintenance
description: >
  Git best practices and repository maintenance — commit hygiene, branch strategy, safe history
  rewrites, stale-branch/tag cleanup, .gitignore upkeep, secret scanning before push, and pre-push
  review checklists. Use when the user asks to clean up a repo, review commit/branch hygiene,
  prepare a rebase/squash/force-push, write a .gitignore, or set git conventions for a project.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(git *)
context: fork
---

## Role

You advise on and carry out git hygiene and repository maintenance. You favor reversible operations
by default and only perform destructive ones (`reset --hard`, `push --force`, branch deletion,
history rewrites) with explicit user confirmation and a clear statement of what will be lost.

## Commit hygiene

- One logical change per commit. Don't bundle an unrelated refactor into a feature commit.
- Write commit messages that explain *why*, not just *what* — the diff already shows what changed.
- Imperative mood, concise subject line (~50 chars), blank line, body if the "why" needs more room.
- Never commit secrets, credentials, `.env` files, or large binaries. If one slipped into history,
  treat it as compromised (rotate it) — removing it from history alone does not undo exposure.
- Before staging with a broad `git add`, run `git status`/`git diff --staged` and read what's
  actually included. Don't blind-add.

## Branch strategy

- Keep `main`/`master` always deployable; do work on short-lived feature branches.
- Prefer rebase-and-merge or squash-merge for feature branches to keep history linear and
  readable; avoid merge commits that interleave unrelated branches' history.
- Delete branches after merge (local and remote) — stale branches accumulate and obscure what's
  actually in flight. List candidates with:
  `git branch --merged main | grep -v '\* \|main'`
- Tag releases (`git tag -a vX.Y.Z -m "..."`) rather than relying on commit SHAs for reference
  points.

## History rewrites (destructive — confirm first)

- `git rebase -i`, `git commit --amend`, `git reset --hard`, and squashing all rewrite history.
  Never do these on a branch others may have already pulled without warning them — rewritten
  history diverges from what they have, and their next pull/push breaks.
- Before any rewrite that could discard work: `git status` first, and stash (`git stash -u`) or
  commit anything uncommitted.
- After a local rewrite that supersedes already-pushed commits, the corresponding push must be
  `git push --force-with-lease` (preferred over plain `--force` — it fails safely if the remote has
  commits you haven't seen, instead of silently clobbering them) or an explicit `--force` only when
  the user has confirmed they want to overwrite the remote unconditionally.
- Never force-push to a shared `main`/`master` without explicit, scoped user confirmation for that
  specific push — a prior approval doesn't carry forward to the next one.

## Repository cleanup

- `.gitignore`: cover OS artifacts (`.DS_Store`), editor dirs (`.vscode/`, `.idea/`), dependency
  dirs (`node_modules/`, `venv/`, `__pycache__/`), build output, logs, and secret/env files
  (`.env`, `.env.*`, with an explicit `!.env.example` if one exists). Keep it scoped to what the
  project actually produces — don't paste a generic mega-template nobody reads.
- If a file matching a new `.gitignore` rule is already tracked, `.gitignore` alone won't stop it
  from showing up in diffs — untrack it explicitly (`git rm --cached <path>`) after confirming with
  the user that it should no longer be tracked.
- Large files / binaries that don't belong in git history: recommend Git LFS or removal, and flag
  it rather than silently working around it.
- Prune remote-tracking refs for branches that no longer exist upstream: `git fetch --prune`.

## Pre-push checklist

1. `git status` — anything unintended staged or unstaged?
2. `git diff --staged` (or the full range being pushed) — read it, don't skim it. Look for secrets,
   debug code, commented-out blocks left behind.
3. Does the branch build/test clean at HEAD?
4. Is this push force/destructive? If yes, has the user explicitly confirmed *this specific* push?
5. Commit message(s) accurate and free of internal-only context that shouldn't be public?
