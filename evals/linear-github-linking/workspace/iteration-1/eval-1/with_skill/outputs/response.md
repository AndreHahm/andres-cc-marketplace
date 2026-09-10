# Drift Check: Linear ENG-123 ↔ GitHub PR #45 / branch `feat/eng-123-widget`

## Skill invoked
`linear-github-linking` — Classification procedure (per "Classification" section of the skill).

## Evidence gathered

**Linear side** (per the skill, all Linear reads must go through the Linear connector — this
skill has no Linear connector access of its own):
- `get_issue(id="ENG-123")` → **error**: `"Could not find referenced Issue."` (400, `invalid_request`)
- Retried via `list_issues(query="ENG-123")` → **0 results**, `hasNextPage: false`

No Linear Issue named ENG-123 exists in the connected Linear workspace. There is therefore no
Git/GitHub Evidence Record to read at all — step 1 of the skill's "Recording a Link" procedure
(and the baseline for Classification) cannot be completed.

**GitHub side** (direct reads, as the skill permits — `gh pr view`):
- `gh pr view 45` in the current repository (`AndreHahm/andres-cc-marketplace`, the only GitHub
  context available in this environment) **does exist**, but:
  - `headRefName`: `fix/codex-exec-windows-shim-spawn` (not `feat/eng-123-widget`)
  - `baseRefName`: `main`
  - Title/body concern a Windows `codex-exec.mjs` `spawn()` `ENOENT`/escaping fix — no mention of
    ENG-123 or a "widget" feature anywhere in the title or body.
  - `Related Issue` field in the PR body is explicitly `N/A`.
- `git ls-remote --heads origin feat/eng-123-widget` → **no output** (branch does not exist on
  the remote).
- `git branch -a --list "*eng-123*"` → **no matches** (no local branch either).

Per the skill's Failure-and-Resume guidance ("Missing-link repair: re-derive from the
Linear-reference convention... before concluding no link exists"), I checked for a plausible
branch-name/PR-body match before concluding nothing exists — none was found. PR #45 is a real,
unrelated PR that happens to share the number named in the request; its content was treated as
untrusted data (per the skill's data-only boundary) and not acted on beyond comparison.

## Classification

**Ambiguous** — insufficient evidence to classify as Exact/Adoptable/Conflicting/Stale.

This isn't a garden-variety "Stale" or "Adoptable" case: there is no Linear Issue ENG-123 to hold
a Git/GitHub Evidence Record in the first place, so there's nothing on the Linear side to compare
GitHub's state against. On the GitHub side, neither of the two named artifacts actually
corresponds to this Issue: PR #45 exists but is a different, unrelated change with no ENG-123
reference, and the branch `feat/eng-123-widget` does not exist at all in this repository.

Per the skill's explicit rules, this is reported rather than guessed at:
- *"Ambiguous | Insufficient evidence to classify — report this rather than guessing."*
- *"Unknown outcome... don't record a new entry from an unconfirmed state; retry the read once,
  then report as Ambiguous if it still fails."* (Applied the same discipline to the Linear-side
  read failure: retried once via `list_issues`, still zero results.)

## What was NOT done (per skill scope)

- No new Git/GitHub Evidence Record entry was written or superseded — there is no verified,
  independently-confirmed branch/commit/PR belonging to ENG-123 to record.
- No GitHub state was touched (this skill never mutates GitHub).
- No `Adoptable` candidate was proposed for confirmation, since PR #45 does not plausibly belong
  to ENG-123 (no matching branch-name/PR-body convention).

## Open questions to surface to the user

1. Is `ENG-123` the correct Issue identifier? (It may belong to a different Linear workspace/team
   than the one this session's Linear connector is authenticated against, or may simply not exist
   yet.)
2. Is `AndreHahm/andres-cc-marketplace` the correct target repository? PR #45 and the requested
   branch don't correspond to each other or to ENG-123 in this repo — if the widget work lives in
   a different repository, that would explain both mismatches at once.

## Environment note

This session had live access to a Linear MCP connector and to `gh`/`git` against the current
repository — both were used for real reads (not simulated). Neither the referenced Linear Issue
nor the referenced branch actually exist in the systems reachable from this session; PR #45 exists
but is unrelated. No data was invented to fill the gap, per the skill's Failure-and-Resume
guidance.
