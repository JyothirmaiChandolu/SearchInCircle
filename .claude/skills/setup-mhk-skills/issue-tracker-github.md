# Issue tracker

**Tracker:** GitHub Issues, in this repo (`<owner>/<repo>`), via the `gh` CLI.

**Default branch:** `<default_branch>` (verified via `gh repo view` — don't assume `main`).

**Branch protection on `<default_branch>`:** `<summary of required reviews / force-push / deletion
findings from Explore step>`.

## Conventions for agent skills reading this file

- **One logical change per PR.** Don't bundle multiple unrelated skills, features, or fixes into a
  single PR — open a separate branch and PR for each.
- **Never push directly to `<default_branch>`.** Branch off it, open a PR, wait for the required
  review(s).
- **Never attempt to self-approve a PR to satisfy the review requirement**, through this account or
  any other you control. If a self-approval is blocked, stop and ask the user to review it, or route
  it to an actual second reviewer — don't look for a workaround.
- **Creating an issue:** `gh issue create --title "..." --body "..."`.
- **Creating a PR:** `gh pr create --base <default_branch> --head <branch> --title "..." --body
  "..."`.
- **Labels in use in this repo:** `<list from \`gh label list\`>`. This org has not adopted the
  canonical `needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` triage vocabulary —
  don't create those labels unless the user explicitly asks for the `triage` skill's workflow.
