# workledger-kit

Keeps one deduplicated, approved open-item list and a navigable PR history for a repository. It
**collects and plans only**: every Linear or Notion write goes through `workmanagement-kit`'s
`plugin-integration-intake`, which asks for its own live approval each time, and GitHub is read through a
GET-only wrapper and never written to.

**Status: 1.0.0-alpha.1.** The collectors, dedup core, report assembler and config loader are built and
tested. Submitting to Linear and Notion is blocked until `workmanagement-kit`'s Wave 3a ships batch
submission, report page-content blocks, queries, updates and caller-reachable classification, so every
skill that would write runs in plan mode today (see `references/wlgr-kit-dependencies.md`).

## Skills

| Skill | What it does |
|---|---|
| `syncing-open-items` | The periodic review: collect from `.claude/output/` reports, open GitHub issues and pull-request follow-ups; annotate and dedup by an exact first-line `dedup_key`; plan per-source hash-bound batches; submit approved batches through intake |
| `open-item-digest` | Read-only, unattended digest of what is new since the last run, written as a dated markdown file in the working folder (no `Write` grant, no prompt) |
| `reporting-pr-history` | Dated PR history report (baseline, then deltas): timeline, PR-to-issue references, issues closed by merged PRs, follow-ups, per-plugin counts |
| `reporting-roadmap` | Dated roadmap snapshot from Linear Initiatives, Projects and Milestones (needs intake's query capability) |
| `onboarding-repositories` | Confirms (or attests) the human setup steps for a further repository, emits its label plan, and adds its local config entry after approval |

## Install and use

Install `workmanagement-kit` first (this plugin depends on it), then this plugin, for example with
`claude --plugin-dir plugins/workledger-kit` during local development. Run `syncing-open-items` for the
periodic review; it starts in plan mode.

## Configuration

Two JSON tiers:

- `workledger-kit.settings.json` (git-tracked defaults): `version`, `repos` (empty: a project onboards its own
  repository with `onboarding-repositories`), `digest.output_dir`, `intake_capabilities` (all off).
- `.claude/workledger-kit.local.json` (gitignored override per project). Only those keys are accepted;
  unknown keys are dropped with a warning.

A local file that is **tracked** by git cannot change `repos`, `digest` or `intake_capabilities`: the loader
refuses those fields with a warning, because a tracked copy could have been committed by anyone with repo
write access. Tracked-ness is decided case-insensitively, and a file under a submodule or another work tree counts as
tracked too, so a differently-cased or nested copy cannot slip past. That check proves the file is untracked,
not who wrote it, so a skill re-reads the config right before it submits. The repository-to-Linear-team mapping lives in `workmanagement-kit`, not here.

`digest.output_dir` is the plugin's one **working folder** (default `.temp/workledger-digest`): it must be
relative, inside the repository, free of symlinks and gitignored, and every script reads and writes only
plain file names inside it. Its files hold full issue, PR and report text; review or redact before sharing.

## Scripts

All in `scripts/`, with the `wlgr_` file prefix (Python 3.11+, no third-party dependencies). The scripts take
plain file names inside the working folder, never paths, and print counts, never collected text.

| Script | Purpose |
|---|---|
| `wlgr_collect.py` | Read-only collectors for reports, GitHub issues, pull requests and raw PR facts |
| `wlgr_open_items.py` | Annotate (dedup key, label mapping), folder counts and filter, classify against existing issues, apply the classification (drop duplicates), describe (propose issues), plan hash, chunking, digest state |
| `wlgr_pr_report.py` | Assemble the PR history report |
| `wlgr_digest.py` | Write the dated digest file (never overwrites) |
| `wlgr_config.py` | Load and validate config, enforce the trust boundary, resolve the working folder |
| `wlgr_paths.py` | Path-safety checks, no-follow file IO and PATH-only executable lookup shared by every script |
| `wlgr_gh_api_readonly.py` | GET-only `gh api` wrapper (plain REST paths only) |
| `wlgr_smoke_checks.py` | Shared structural smoke checks for the skills |

Tests: `python scripts/wlgr_test_core.py`, `python scripts/wlgr_test_collect.py`,
`python scripts/wlgr_test_pr_report.py`.

## Known limits

- Unresolved review threads are not collected (GraphQL is a POST; this plugin never writes to GitHub).
- Inferred PR links and ambiguous follow-ups need intake's classification capability; until then ambiguous
  items are shown as "needs your decision".
- Creating a repository's Linear labels is a manual step; intake has no label operation.
- `Write` is pre-approved, without a path scope, in `syncing-open-items`, `reporting-roadmap` and
  `onboarding-repositories`, so the trusted local config file is not protected against a prompt-injected run;
  a guard hook is a recorded follow-up (see `references/wlgr-kit-dependencies.md`).
- A skill's tool grants only pre-approve tools; they do not remove the session's others. The "no connector,
  no GitHub write" rule is backed by the scripts but is not mechanically enforced (see
  `references/wlgr-kit-dependencies.md`).

See `CONTRIBUTING.md` for the preferred language (Python) and the change process.
