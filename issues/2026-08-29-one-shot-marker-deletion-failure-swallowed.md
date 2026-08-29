## Summary
A one-shot authorization marker's deletion step swallowed its own failure (`rm -f "$MARKER" || true`) — a genuine deletion failure (e.g. a read-only or permission-restricted `.git`) left the marker still valid and reusable, defeating the documented single-use guarantee, across all five of this plugin's guard scripts.

## Environment
- **Product/Service**: `git-kit` plugin — all five `hooks/scripts/guard-raw-*.sh` scripts
- **Region/Version**: this repo, found during PR #177 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Make `.git` (or the marker file's directory) read-only or otherwise permission-restricted, so `rm -f "$MARKER"` fails.
2. Trigger a guarded destructive operation with a valid marker present — `allowed` is set to `true` before the deletion attempt.
3. The `|| true` on the `rm -f` call swallows the deletion failure; execution proceeds as if the marker was successfully consumed.
4. Within the marker's 60-second TTL, trigger another matching destructive command — it's authorized again, with no fresh skill handshake, since the marker file is still present and still valid.

## Expected Behavior
A one-shot authorization marker's deletion/consumption step must be checked for success — a deny result should follow if deletion fails, rather than trusting an unconsumed marker.

## Actual Behavior
Protected operations could repeat within the TTL window without a fresh handshake whenever marker deletion failed for any reason, silently converting a single-use guarantee into a reusable one.

## Impact
[Severity: Critical, per Devin's own security classification] This directly undermines the security property the marker mechanism exists to provide — a single successful skill handshake could authorize multiple destructive operations under a filesystem-permission edge case. Fixed in `git-kit`'s PR #177 (commit `3d07969`): added `if ! rm -f "$MARKER"; then allowed=false; fi` (denying instead of trusting an unconsumed marker on genuine deletion failure) across all 5 guard scripts. Verified live via a fake-`rm`-override harness against each real shipped script (deny confirmed, no ERR-trap crash), plus the success path re-confirmed unaffected. Security-reviewed (Pass).

## Additional Context
Mined from PR #177's own review history (`chatgpt-codex-connector[bot]`, `devin-ai-integration[bot]`; 17 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #177` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/177#discussion_r3885664350
