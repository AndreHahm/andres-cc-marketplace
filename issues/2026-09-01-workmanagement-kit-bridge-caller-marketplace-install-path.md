## Summary
`bridge_caller.py` assumes a source-checkout monorepo layout and cannot locate its own `codex-kit` dependency (or its own repo root) when `workmanagement-kit` is installed standalone via the Claude Code plugin marketplace mechanism

## Environment
- **Product/Service**: `workmanagement-kit` plugin (`plugins/workmanagement-kit/scripts/bridge_caller.py`)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Install `workmanagement-kit` as a standalone plugin (not as part of a checkout of this monorepo) via Claude Code's plugin marketplace mechanism, into a consumer project.
2. Invoke `bridge_caller.py` with no `--repo-root` given.
3. `Path(__file__).resolve().parent.parent` (`plugin_root`) resolves to somewhere under the Claude plugin cache, which has no ancestor `.git` directory.
4. `repo_root_from(plugin_root)` raises `ValueError: could not resolve repo root from <plugin cache path>` (the documented typed-failure path, not a crash — see PR #278's fix for the earlier `SystemExit` bug).
5. Even if `--repo-root <consumer-project-root>` is passed explicitly to work around step 4, `bridge_script` is still computed as `<repo_root>/plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` — an ordinary consumer project does not contain a `plugins/codex-kit/` directory even when the `codex-kit` dependency is installed separately via the same marketplace mechanism.

## Expected Behavior
The bridge-caller should be able to locate (a) the host/consumer project it's operating against, and (b) its installed `codex-kit` dependency (specifically `bridge-invoke.mjs`), as two independent locations — neither assumed to be a subdirectory of the other, regardless of whether `workmanagement-kit` and `codex-kit` are installed from this monorepo (development) or from the marketplace as two independently-installed plugins (a real consumer install).

## Actual Behavior
`bridge_caller.py`'s design (both `repo_root_from`'s `.git`-ancestor search and `bridge_script`'s hardcoded `<root>/plugins/codex-kit/...` path) only works when both plugins live under the same monorepo checkout — exactly this repository's own current layout, and the only layout this PR's own live testing exercised.

## Error Details
~~~
ValueError: could not resolve repo root from <plugin-cache-path>
~~~
(or, with `--repo-root` supplied to work around that): `FileNotFoundError: <repo_root>/plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`

## Visual Evidence
N/A

## Impact
**Medium** — doesn't block this repo's own live use (confirmed working end-to-end in PR #278), but blocks the plugin's own documented "install this plugin as usual" story for any installation outside this monorepo. `codex-review-bridge`'s live dispatch path is entirely unavailable to a standalone `workmanagement-kit` install until this is resolved.

## Additional Context
- **Found in PR #278** (`feat(workmanagement-kit): wire live Notion/Linear connector + bridge-caller`), automated review round 1 — independently flagged by two reviewers:
  - Codex, P1, https://github.com/AndreHahm/andres-cc-marketplace/pull/278#discussion_r3903828831 (head SHA `c5cbd8f6847e29523f9cec2b6febe0a069ec91d7` at the time of the finding)
  - Devin, `BUG_pr-review-job-3b89a37b2b694092ad3a283b999e18a8_0001`, https://github.com/AndreHahm/andres-cc-marketplace/pull/278#discussion_r3903911049
- PR #278 itself, at head SHA `b4ae5b7c2dbc2a45f31f422d7452720398fd97ca`, fixed 5 other real bugs the same review round found in `bridge_caller.py`, but deliberately left this one for a separate issue — it's a design question (how a plugin should discover a sibling dependency plugin's own install location under Claude Code's actual plugin-install mechanism), not a quick fix, and out of that PR's own stated scope (wiring this repo's own installation).
- A related, narrower security note from the same review round (Devin, `SEC_pr-review-job-3b89a37b2b694092ad3a283b999e18a8_0001`, https://github.com/AndreHahm/andres-cc-marketplace/pull/278#discussion_r3903912287) was declined as not currently reachable — no untrusted caller is wired to `--repo-root` today — but whoever designs the fix for this issue should account for that trust boundary: if a future integration point lets another component supply `--repo-root`, it must not be allowed to point at an attacker-controlled location that would then get executed as `bridge-invoke.mjs`.
- Relevant file: `plugins/workmanagement-kit/scripts/bridge_caller.py` (`repo_root_from`, and the `bridge_script` path composition inside `dispatch()`).
