# check-prefixes / check-all fail on gitignored __pycache__ files after any local pytest run

## Summary
The R33 prefix check enumerates plugin files with a filesystem walk, so gitignored bytecode caches count as plugin files and are reported as prefix violations. Running the repo's own tests makes the local `check-all` fail until the caches are deleted.

## Environment
- **Product/Service**: `scripts/marketplace_ci` (`check-prefixes`, `check-all`), `scripts/marketplace_ci/prefix_check.py`
- **Region/Version**: Python 3.13 (`cpython-313` bytecode), repository state on 2026-10-01

## Reproduction Steps
1. On a clean tree with no `__pycache__` directories under `plugins/`, run `uv run python -m scripts.marketplace_ci check-all`. It exits 0.
2. Run `uv run pytest plugins/analysis-kit/tests -q` (137 passed). `plugins/analysis-kit/tests` and `plugins/session-kit/tests` are in `pyproject.toml`'s pytest `testpaths`, and the root tests also import plugin scripts. This creates `plugins/analysis-kit/scripts/__pycache__/*.cpython-313.pyc`.
3. Run `uv run python -m scripts.marketplace_ci check-prefixes`, then `check-all` again.

## Expected Behavior
Gitignored bytecode caches are never treated as plugin files. `check-prefixes` and `check-all` still exit 0 after a normal test run.

## Actual Behavior
`check-prefixes` exits 1 and `check-all` exits 1. One line is printed per cache file, with the same message as a real violation.

## Error Details
~~~
[prefixes] analysis-kit: plugins/analysis-kit/scripts/__pycache__/anls_critical_path_analyzer.cpython-313.pyc - basename does not start with plugin 'analysis-kit''s registered prefix/domain_prefix ('anls-' or 'analysis-')
~~~

## Visual Evidence
None.

## Impact
**Medium-High** - A workaround exists (delete the caches), but it affects every contributor after a normal test run. Priority set to `p: high` at the maintainer's request.

## Additional Context
- **Same pattern elsewhere:** earlier in the same session, files under plugin-devkit's `scripts/inventory_common/__pycache__/` and session-kit's `scripts/__pycache__/` were flagged identically. Any plugin with Python scripts that a test run imports is affected, not only analysis-kit.
- **Why it happens:** the files are ignored by `.gitignore` line 4 (`__pycache__/`), confirmed with `git check-ignore`. `scripts/marketplace_ci/prefix_check.py` walks with `root.rglob("*", recurse_symlinks=False)` and `path.is_file()` (around lines 413-417), with no tracked-files filter and no skip for `__pycache__` or `.pyc`.
- **Workaround:** `find plugins -name __pycache__ -type d -prune -exec rm -rf {} +`
- **Suggested directions, not decided:** restrict the walk to tracked files (`git ls-files`), or skip `__pycache__` directories and `.pyc` files.
- **Precedent:** the #446 change added the same kind of skip to the mirror walk (`scripts/marketplace_ci/sync_plan.py`, `_is_bytecode_cache`) after hitting this.
- **Scope notes:** the commit-time lint step is not involved, because it only looks at staged files and ignored caches never reach it. Whether CI is affected is not verified; a fresh checkout has no caches.
- Related: #446, #440 (other `prefix_check` hardening).
