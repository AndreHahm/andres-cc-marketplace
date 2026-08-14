# Require Gitignored Scratch Locations

## When this applies

Any temporary, test-run, or cache file or directory that a script, test suite, CI step, build tool, or
Claude's own tool calls create as a side effect of running — not content meant to ship as part of the
repo's tracked history. Applies to any shippable/tracked location this repo has, not only the repo root:
a plugin's own directory is just as much a shippable location as the root is.

## Rule

Never let temporary, cache, or scratch content land in a shippable location. Route it to a gitignored
location instead:

- **Claude's own scratch writes** (a `Write`/`Bash` call that needs somewhere to put intermediate
  output): the session scratchpad directory — already covered by CLAUDE.md's "No Scratch Files at Repo
  Root" guidance, which this rule doesn't duplicate.
- **Code, scripts, or test fixtures that need a working/output directory**: an existing gitignored
  convention this repo already uses (`.temp/`, `.draft/`, or a tool's own conventional cache directory,
  as long as it's covered by `.gitignore`) — or a fresh gitignored directory if none of those fit, added
  to `.gitignore` in the same change that introduces the code using it, not after the fact.

Watch specifically for a default that silently resolves to a shippable location: a bare relative path in
a script's own default (e.g. a function parameter like `instructions_dir = repo / ".foo"` with no
override supplied), or a CLI tool invoked with no explicit output-directory flag (e.g. a bare `pytest`
run), lands wherever the current working directory happens to be — usually the repo root — unless the
code or its caller explicitly points it elsewhere.

## Why

Two separate real occurrences in one session (2026-08-14), neither caught until the working tree was
inspected after the fact:

1. `pytest-cache-files-<random-suffix>/` — three separate directories left at repo root across multiple
   `uv run pytest` invocations. `pytest`'s own default cache location chose the spot, not this repo's own
   tooling — nothing in the test run itself pointed it at a gitignored directory.
2. `.codex-review-instructions/` — created at repo root by `dispatch_reviewers()`'s own default
   `instructions_dir = repo / ".codex-review-instructions"` parameter in
   `scripts/marketplace_ci/review.py`, surfaced the moment a local `pytest` run exercised that code path.

Both had to be manually flagged mid-session and left for the user to delete by hand, rather than being
caught structurally before they existed. This generalizes CLAUDE.md's existing "No Scratch Files at Repo
Root" guidance — which only covers Claude's own `Write` tool calls — to the broader failure mode CLAUDE.md
doesn't reach: a script's or tool's own hardcoded or default working directory, chosen independently of
any `Write` call Claude makes.
