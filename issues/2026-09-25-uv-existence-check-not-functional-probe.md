## Summary
Repo-wide `uv`-tier interpreter-fallback checks use `command -v uv` (existence-only) before
unconditionally `exec`ing into it, so a present-but-broken `uv` fails the whole hook instead of
falling through to `python3`/`python`

## Environment
- **Product/Service**: `plugin-devkit`'s hook interpreter-fallback convention (`hooks/rulebook-check.sh`,
  `security-precommit-check.sh`, `r25-overhead-disclosure-check.sh`, `r26-expensive-action-check.sh`,
  and any other `uv`-tier hook repo-wide)
- **Region/Version**: n/a

## Reproduction Steps
1. Create a PATH shim named `uv` that exits nonzero (simulating a broken or sandboxed/snap-confined
   install): `printf '#!/bin/sh\nexit 1\n' > $TMPBIN/uv && chmod +x $TMPBIN/uv`.
2. Run any hook still using the existence-only check (e.g. `plugins/plugin-devkit/hooks/rulebook-check.sh`)
   with that shim first on `PATH`.
3. Observe: `command -v uv` succeeds (the shim exists and is executable), so the script commits to
   `exec uv run ...`/`uv run ...` — which then fails, since `exec` irrevocably replaces the shell
   process once it successfully launches a program. The script never falls through to `python3`/`python`,
   even though those are available and would work.
4. Confirmed live for the *fixed* pattern (see Additional Context): the same shim correctly falls
   through to `python3` once the check adds `&& uv --version >/dev/null 2>&1`.

## Expected Behavior
A `uv` that exists on `PATH` but fails when actually invoked should be treated as unavailable, falling
through to the next tier (`python3`, then `python`) — the same graceful-degradation goal issues
#358/#359 already established for "no interpreter found at all."

## Actual Behavior
`command -v uv` only confirms a binary named `uv` exists on `PATH` — it says nothing about whether
invoking it actually succeeds. Every hook using this check as its sole `uv`-tier gate is vulnerable to
this exact failure mode.

## Impact
**Low-Medium** — only triggers when `uv` exists on `PATH` but is broken, sandboxed, or otherwise
non-functional (not the common case), but when it does trigger, the affected hook fails completely
instead of gracefully falling through to a working interpreter tier — exactly the failure mode the
#358/#359 fix was meant to close, one level deeper (existence vs. actually-working).

## Additional Context
Found live during a `cross-model-review` pass on the PR fixing #358/#359: Codex's own sandboxed review
environment hit this exact failure — its installed `uv` (via snap) exists on `PATH` but fails at
runtime due to snap confinement restrictions, while `python3` was available and would have worked.

**Already fixed in the #358/#359 PR** (scoped only to files that PR touched — using a functional probe
`command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1` before committing to the `uv` tier via
`exec`):
- `plugins/context-kit/hooks/hooks.json` (all 4 entries)
- `plugins/plugin-devkit/skills/marketplace-development/hooks/post_edit_validate.sh` and
  `post_edit_sync_check.sh`
- `hook-development`'s `references/patterns-and-templates.md` (Pattern 11) and the new rule
  `plugins/plugin-devkit/rules/require-python-hook-interpreter-fallback.md`

**Not yet fixed** (still existence-only, out of scope for that PR):
- `plugins/plugin-devkit/hooks/rulebook-check.sh`
- `plugins/plugin-devkit/hooks/security-precommit-check.sh`
- `plugins/plugin-devkit/hooks/r25-overhead-disclosure-check.sh`
- `plugins/plugin-devkit/hooks/r26-expensive-action-check.sh`
- any other `uv`-tier hook elsewhere in the repo not enumerated here — needs a full repo-wide grep for
  `command -v uv` immediately followed by an unconditional `exec`/pipe with no functional probe.

Suggested fix direction (not mandated): repo-wide grep for `command -v uv >/dev/null 2>&1` not
immediately followed by a functional probe (`uv --version` or similar) across `hooks/*.sh`,
`hooks.json` command strings, and skill-frontmatter `hooks:` blocks; add the same
`&& uv --version >/dev/null 2>&1` probe used in the already-fixed files.

Suggested labels: `t: bug`, `s: triage`, `a: ai-setup`, and an appropriate `p:` tier per
`docs/github-label-taxonomy.md` (likely `p: low` or `p: medium`).
