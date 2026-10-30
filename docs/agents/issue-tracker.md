# Issue tracker

**Tracker:** GitHub Issues, in this repo (`MHK-TECH-INC/SearchInCircle`), via the `gh` CLI.

**Default branch:** `main` (repo is currently empty on GitHub — no commits/branches pushed yet, so
GitHub hasn't set a default branch. `main` is the convention to push as the first branch).

**Branch protection on `main`:** not yet configured — can't be set until the branch exists (first
push). Flag for the user to configure protection (required review, block force-push/deletion) in
GitHub repo settings once the initial push lands.

## Conventions for agent skills reading this file

- **One logical change per PR.** Don't bundle multiple unrelated skills, features, or fixes into a
  single PR — open a separate branch and PR for each.
- **Never push directly to `main`.** Branch off it, open a PR, wait for the required review(s).
- **Never attempt to self-approve a PR to satisfy the review requirement**, through this account or
  any other you control. If a self-approval is blocked, stop and ask the user to review it, or route
  it to an actual second reviewer — don't look for a workaround.
- **Creating an issue:** `gh issue create --title "..." --body "..."`.
- **Creating a PR:** `gh pr create --base main --head <branch> --title "..." --body "..."`.
- **Labels in use in this repo:** `bug`, `documentation`, `duplicate`, `enhancement`,
  `good first issue`, `help wanted`, `invalid`, `question`, `wontfix` (GitHub's stock default set).
  This org has not adopted the canonical `needs-triage` / `needs-info` / `ready-for-agent` /
  `ready-for-human` triage vocabulary — don't create those labels unless the user explicitly asks
  for the `triage` skill's workflow.
