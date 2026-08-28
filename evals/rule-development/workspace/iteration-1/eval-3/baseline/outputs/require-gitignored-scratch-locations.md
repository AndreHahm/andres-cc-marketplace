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
override supplied), a CLI tool invoked with no explicit output-directory flag (e.g. a bare `pytest`
run), or a script that hardcodes a relative output path such as `./tmp/` instead of pointing at the
session scratchpad — each lands wherever the current working directory happens to be — usually the repo
root — unless the code or its caller explicitly points it elsewhere. A hardcoded `./tmp/`-style path is
especially easy to miss because it looks like a scratch directory by name alone, but a bare relative
path with no gitignore entry and no scratchpad redirection is exactly the failure mode this rule exists
to catch — the name "tmp" doesn't make it safe.

## Why

Three separate real occurrences across two sessions, none caught until the working tree was inspected
after the fact:

1. `pytest-cache-files-<random-suffix>/` (2026-08-14) — three separate directories left at repo root
   across multiple `uv run pytest` invocations. `pytest`'s own default cache location chose the spot, not
   this repo's own tooling — nothing in the test run itself pointed it at a gitignored directory.
2. `.codex-review-instructions/` (2026-08-14) — created at repo root by `dispatch_reviewers()`'s own
   default `instructions_dir = repo / ".codex-review-instructions"` parameter in
   `scripts/marketplace_ci/review.py`, surfaced the moment a local `pytest` run exercised that code path.
3. `./tmp/` — a script hardcoded a relative `./tmp/` output directory instead of writing to the session
   scratchpad. Because the path is relative, it resolves wherever the script happens to be invoked from
   (typically the repo root), landing untracked scratch content in a shippable location exactly like the
   two occurrences above, despite looking innocuous under a name that reads as "obviously temporary."

All three had to be manually flagged and left for the user to delete by hand, rather than being caught
structurally before they existed. This generalizes CLAUDE.md's existing "No Scratch Files at Repo Root"
guidance — which only covers Claude's own `Write` tool calls — to the broader failure mode CLAUDE.md
doesn't reach: a script's or tool's own hardcoded or default working directory, chosen independently of
any `Write` call Claude makes.
