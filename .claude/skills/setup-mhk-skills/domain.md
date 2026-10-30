# Domain docs

**Layout:** `<single-context | multi-context>` (confirmed in setup; single-context is the default
and fits almost every repo).

## Single-context (default)

- `GLOSSARY.md` at the repo root — canonical domain vocabulary. Create it lazily: only when the
  first term needs recording, via the `domain-modeling` skill.
- `docs/adr/NNNN-slug.md` — architecture decision records, numbered sequentially, never reused or
  deleted (a reversed decision gets a new ADR marking the old one "Superseded by NNNN"). This is
  already MHK-TECH-INC's convention via the `architect` and `docs-sync` skills, independent of this
  setup skill — if `docs/adr/` already exists in this repo, these conventions apply to it as-is.

## Multi-context (only if confirmed during setup)

- `GLOSSARY-MAP.md` at the repo root, pointing to each context's own `GLOSSARY.md` and
  `docs/adr/`.

## Consumer rules

- Skills that read code/terminology (`tdd`, `diagnosing-bugs`, `codebase-design`,
  `improve-codebase-architecture`) should read `GLOSSARY.md` (if it exists) for vocabulary and
  check `docs/adr/` in the area they're touching, before proposing names or designs.
- Only the `domain-modeling` skill actively writes to `GLOSSARY.md` or proposes new ADRs. Other
  skills consume it, they don't edit it.
