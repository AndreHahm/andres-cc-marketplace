## Summary
`agy-migrate.py` has ~15 methods flagged by Codacy for cyclomatic complexity well over the
repo's threshold (limit 8), several 3-6x over, plus a couple of method-length and
hardcoded-format-string style findings in the same file.

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `plugins/antigravity-kit/scripts/agy-migrate.py`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. Open Codacy's Static Code Analysis check on PR #337 (`https://app.codacy.com/gh/AndreHahm/andres-cc-marketplace/pull-requests/337`).
2. Review the "Complexity increasing per file" section for `plugins/antigravity-kit/scripts/agy-migrate.py` (1289 non-comment lines, new to this repo as part of the plugin transfer).

## Expected Behavior
Methods in a maintained script stay reasonably close to this repo's complexity/length
thresholds, so a future change can be reasoned about locally instead of tracing a
50-branch function.

## Actual Behavior
Codacy flags (cyclomatic complexity, limit 8 unless noted):
- `do_uninstall`: complexity 50, 93 lines (limit 50)
- `main`: complexity 35, 125 lines (limit 50)
- `unit_settings`: complexity 38, 109 lines (limit 50)
- `postprocess_staged`: complexity 31, 77 lines (limit 50)
- `collect_mcp`: complexity 23
- `unit_plugins`: complexity 20
- `unit_memory`: complexity 17, 60 lines (limit 50)
- `convert_hooks`: complexity 16
- `translate_mcp`: complexity 11
- `unit_mcp`, `translate_permission`, `existing_project_for`, `default_roots`,
  `split_frontmatter`, `unit_settings.fn`, `installed_plugins`, `convert_matcher`:
  complexity 9-10 each

Also two minor style findings worth folding into the same cleanup: hardcoded
`strftime` format strings at lines 176 and 286 (repeated date-format literals with
no shared constant).

## Impact
**Low-Medium** — maintainability/readability risk, not a functional bug. These are
pre-existing patterns carried over from the upstream fork, not new bugs introduced by
the transfer itself; the file works correctly today per the plugin's own 282+ passing
deterministic tests. Codacy's actual gate-failing threshold on PR #337 was a separate
"9 new security issues (5 max)" bandit count (subprocess partial-path / untrusted-input
/ except-pass findings), which was fixed directly in that PR — this issue only tracks
the complexity/method-length backlog, which was not.

## Additional Context
Discovered during a `handling-review-findings` triage pass on PR #337 (round 1: Codex +
CodeRabbit + Codacy). Not fixed in that PR: refactoring ~15 methods (several
multiple times over the complexity limit) without changing behavior is a substantial, coordinated
effort distinct from that round's scoped bug fixes, and needs its own dedicated pass with
its own test coverage rather than being rushed into an unrelated review-findings batch.
Found in PR #337.
