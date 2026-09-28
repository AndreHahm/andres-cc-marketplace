## Summary
`plan_plugin_sync`'s mode-only-drift detection uses a filesystem `stat()` check, which is unreliable on the same Windows platform issue #413 already fixed at the staging layer -- a mode-only, content-identical drift can go completely undetected there

## Environment
- **Product/Service**: `scripts/marketplace_ci/sync_plan.py` (`plan_plugin_sync`)
- **Region/Version**: n/a

## Reproduction Steps
1. On a native Windows checkout (`core.fileMode` forced off, `os.chmod()`/`os.stat()` can't represent a
   real POSIX execute bit), take a canonical plugin source file that's already mirrored into `.claude/`
   with byte-identical content on both sides.
2. Change only the source's executable bit (e.g. `git update-index --chmod=+x` with no content edit),
   with no other change to the file's bytes.
3. Run `plan_plugin_sync`.

## Expected Behavior
The plan should schedule an `update` action so the mirrored destination's executable bit can be
corrected (via the fix from issue #413/PR for #413, which forces the git-index mode in
`stage_generated_destinations`).

## Actual Behavior
`plan_plugin_sync` (`scripts/marketplace_ci/sync_plan.py:136`) only schedules an action for a
mode-only drift when `_is_executable(dest) == _is_executable(source)` is `False` -- and `_is_executable`
(`sync_plan.py:57-58`) is a filesystem `stat()` check: `stat.S_IMODE(path.stat().st_mode) & 0o111`. On
Windows, this is exactly the kind of check issue #413 already established is unreliable for a real
POSIX execute bit. If both sides report the same (likely constant/inaccurate) value on Windows, the
comparison at line 136 is silently satisfied and the `continue` at line 137 skips scheduling any action
at all -- so `stage_generated_destinations` (the function fixed for issue #413) never even runs for
this file, and the git-index-based fix never fires.

## Error Details
~~~
(no error/exception -- a silent planning gap, only reachable on native Windows with a
content-identical, executable-bit-only change to an already-mirrored file)
~~~

## Visual Evidence
N/A

## Impact
**Medium** -- narrower than issue #413's original trigger (a file *rename*, which always produces a
`create` action and is already fully fixed/verified by that issue's fix). This gap only affects a
content-identical, executable-bit-only change to an *already-mirrored* file -- plausible (e.g. a hook
script's executable bit fixed in a follow-up commit with no other edit) but not the originally reported
incident.

## Additional Context
Found by `cross-model-review` (Codex, high confidence) during the PR for issue #413, and independently
verified by reading `sync_plan.py:57-58` and `:134-137` directly. Deliberately left out of scope for
that PR: `sync_plan.py` is explicitly documented, in its own module docstring (see issue #351), as a
**pure, git-free planning layer** -- no `subprocess`/git calls. Fixing this properly likely means either
introducing git-index awareness into that layer (violating its documented architecture) or a larger
restructuring of how canonical-source/destination pairs are discovered independent of the plan's own
byte-content comparison. That's a bigger design question than a follow-up ticket should presume to
answer -- flagging for a maintainer to decide the right approach (e.g. a git-index-aware variant of the
mode-drift check, gated behind the same layer boundary sync.py's apply/staging functions already use;
or documenting this as an accepted, narrow limitation).
