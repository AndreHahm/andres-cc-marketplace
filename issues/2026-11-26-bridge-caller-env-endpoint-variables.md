## Summary
The Codex dispatch from workmanagement-kit's bridge caller (and git-kit's codex-kit locator) still passes endpoint, proxy, certificate and other `CODEX_*` variables to the child, and its scratch directory follows `TMPDIR`/`TMP`/`TEMP`.

## Environment
- **Product/Service**: `workmanagement-kit` (`plugins/workmanagement-kit/scripts/wmgt_bridge_caller.py`) and `git-kit` (`plugins/git-kit/scripts/git-review-codex-kit.py`)
- **Region/Version**: branch `feat/workmanagement-kit-pr-link-classify-guard` at eee9ca2d4152df773be8110b49146ae2af13105e
- **Browser/OS**: all; `ComSpec` only on Windows

## Reproduction Steps
Found by review and by reading the code; not reproduced at runtime.

1. Set `OPENAI_BASE_URL`, `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY` or `SSL_CERT_FILE`/`SSL_CERT_DIR` in the environment the caller inherits (for example through settings a project supplies).
2. Run a classify or intake dispatch through `wmgt_bridge_caller.py`.
3. The child Node process, and the Codex CLI it starts, receive those values unchanged.
4. Separately, `tempfile.mkdtemp()` writes the instruction file under whatever `TMPDIR`/`TMP`/`TEMP` names.

## Expected Behavior
- Variables that choose Codex's API endpoint, proxy or trusted certificates, and other `CODEX_*` variables, are dropped, pinned, or checked like `CODEX_HOME` before the dispatch.
- The scratch directory is created in a trusted temp location and checked to lie outside the repository and every target path.
- git-kit's `git-review-codex-kit.py` (line 94, which drops only `GIT_*` and `NODE_*`) gets the same treatment as the bridge caller.

## Actual Behavior
- PR #913 made the bridge caller drop `LD_*`, `DYLD_*`, `GLIBC_TUNABLES`, `BASH_ENV` and `ENV`, and refuse a `CODEX_HOME` that is relative or inside the repository under review. Everything listed above still reaches the child, as the caller's docstring now states.
- With an endpoint or proxy variable set by a project the user trusts to set variables, Codex could send the account's credentials or the reviewed text to a host the user did not choose.

## Error Details
~~~
None (no runtime error; a trust-boundary gap)
~~~

## Visual Evidence
None.

## Impact
**Medium** - needs a project that can set environment variables for the session; the effect is credential or content exposure, not code execution.

## Additional Context
- Found in PR #913 (head eee9ca2d4152df773be8110b49146ae2af13105e).
- Sources: the CI Codex delta review's `skill-reviewer` finding on `wmgt_bridge_caller.py:336` (Minor, `mkdtemp` follows the temp variables, fingerprint `d838b43874fc6935e3c04e630c9b9a11`, line not in the PR's diff), and a `security-reviewer` pass on the PR's environment fix, which named the endpoint, proxy, certificate and `CODEX_*` variables and `ComSpec`.
- An explicit environment allowlist was considered and declined for PR #913 as a larger change with more risk of breaking Codex.
