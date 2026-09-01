## Summary
`gh api ... -f field="@path/to/file"` silently posts the literal string `@path/to/file` instead of the file's contents — only `-F`/`--field` supports the `@file` read convention, not `-f`/`--raw-field` — with no error or warning at call time

## Environment
- **Product/Service**: `gh` CLI (GitHub CLI), used throughout this repo's own skills (e.g. `handling-review-findings`, `create-pr`'s bypass-attestation step) for `gh api` calls that post comment/review bodies
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
1. Prepare a text file with some content, e.g. `echo "real content" > /tmp/reply.txt`.
2. Run `gh api repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies -f body="@/tmp/reply.txt"`.
3. The call succeeds (HTTP 201, valid comment ID returned) with no error or warning.
4. Fetch the posted comment back: `gh api repos/{owner}/{repo}/pulls/comments/{new_id} --jq '.body'`.
5. Observe the body is the literal string `@/tmp/reply.txt` — not the file's contents.

## Expected Behavior
Either: `-f`/`--raw-field` should support `@file` the same way `-F`/`--field` documents it does (consistency), or `gh api` should reject/warn on a raw-field value starting with `@` when the file exists, since a value that happens to start with a literal `@` character is a much rarer intent than "read from this file" (and `-F` already exists for that intent).

## Actual Behavior
`gh api --help` documents `@file`/`@-` support only under `-F, --field` ("use \"@<path>\" or \"@-\" to read value from file or stdin"), not under `-f, --raw-field` ("Add a string parameter in key=value format" — no `@file` mention at all). Using `-f` with a `@path` value is accepted at the CLI-parsing level with no error, and posts the literal string. This is a real, live-confirmed distinction between the two nearly-identically-named flags, not a hypothetical.

## Error Details
~~~
(no error at all -- the call succeeds with a normal 201 response and a real comment ID; the bug only becomes visible by reading the posted content back)
~~~

## Visual Evidence
N/A

## Impact
**Medium** — a real, live incident in this repo's own session use: 13 PR review-thread reply comments were posted with `@<scratchpad-file-path>` as their entire visible body instead of the intended explanation text (PR #278, comment IDs 3905797609, 3905797862, 3905798108, 3905798346, 3905798584, 3905798778, 3905799030, 3905811317, 3905811560, 3905811775, 3905812024, 3905812278, 3905812587), only caught because the user directly inspected the PR and reported it — the `gh api` call itself gave no signal anything was wrong. All 13 were later corrected via `PATCH .../pulls/comments/{id}` with `-f body="$(cat file)"` (command substitution, confirmed working) instead of the `@file` form.

## Additional Context
- Found live during a `handling-review-findings` triage session on PR #278 (this repo), 2026-09-01 — see that PR's own review-thread history for the original broken comments (now corrected).
- Root cause confirmed by reading `gh api --help` directly: the `@file`/`@-` read convention is documented only under `-F`/`--field`, never under `-f`/`--raw-field`.
- `.claude/rules/verify-tool-behavior-before-instructing.md` (this repo's own rule) exists specifically to catch this class of mistake — assuming a flag's behavior from a sibling flag's documented behavior, rather than checking the actual flag's own docs, is exactly the pattern that rule warns against. This incident is a fresh, concrete instance of it, worth adding to that rule's own table of prior instances if/when it's next revised.
- Relevant components: `handling-review-findings` (`references/github-api-mechanics.md`, which documents the reply/resolve command shapes other skills reuse) is the most likely place a fix belongs — either updating its own example commands to use `-F` instead of `-f` for any file-sourced body, or adding an explicit warning about this exact `-f`/`-F` distinction before its reply-posting instructions. `create-pr`'s bypass-attestation step (step 5d) also posts a `gh pr comment`/`gh api` body built via `jq -n --arg`, a different (and safe) construction method, but is worth a quick check for the same anti-pattern if any `-f ...@file` form ever gets introduced there.
