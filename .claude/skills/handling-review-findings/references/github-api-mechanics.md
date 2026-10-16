# GitHub API Mechanics

- [The wrapper script](#the-wrapper-script)
- [Replying to an inline PR review comment](#replying-to-an-inline-pr-review-comment)
- [Resolving a review thread](#resolving-a-review-thread)
- [Leaving a thread unresolved on purpose](#leaving-a-thread-unresolved-on-purpose)
- [Posting a review-trigger comment](#posting-a-review-trigger-comment)
- [Fetching all reviewers together](#fetching-all-reviewers-together)
- [Issue traceability payload](#issue-traceability-payload)
- [Issue-filing convention](#issue-filing-convention)
- [Scratchpad path](#scratchpad-path)

## The wrapper script

This skill reaches GitHub's REST comment endpoints, GraphQL and top-level PR comments only through
`${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py` (SKILL.md's GitHub API Mechanics). It runs one fixed `gh` call per
subcommand, validates every argument, and embeds the only two GraphQL documents this skill sends, so
the skill needs no broad `gh api graphql` or `gh pr comment` grant. Run it as:

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" <subcommand> [flags]
```

In this repo's own sessions `CLAUDE_PLUGIN_ROOT` is empty; substitute the `.claude/` mirror per
`.claude/rules/resolve-plugin-root-to-claude-mirror.md`. `<owner>`/`<repo>`/`<pr>` below are the real
resolved values from Workflow step 1, never `-R`.

| Subcommand | Flags | Marker |
|---|---|---|
| `threads` | `--owner --repo --pr [--cursor]` | yes |
| `resolve` | `--thread-id` | yes |
| `reply` | `--owner --repo --pr --comment-id --body-file` | yes |
| `trigger-comment` | `--owner --repo --pr --body-file` | yes |
| `issue-create` | `--owner --repo --title --body-file` | yes |
| `list-comments` | `--owner --repo --pr` | no (read-only) |
| `whoami` | none | no (read-only) |
| `push-destinations` | none | no (read-only) |

**The marker.** Immediately before each marker-requiring call, in its own `Bash` call, run
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review-wrapper handling-review-findings`.
The script refuses without a fresh one (60 seconds) and deletes it on first use, so write one per call.
Use the `gh-pr-review-wrapper` type, never `gh-pr-review`: `git-guard-raw-pr-review.sh` deletes every
`gh-pr-review` marker on the next `Bash` call whether or not that call matches, so the script would
find nothing. A refusal prints the exact reason on stderr and exits 2; the call is never retried
without a new marker.

**`--body-file`** is never handed to `gh` as a path. The script refuses a path that is itself a symlink,
resolves it (so a symlinked directory cannot hide the real location), requires the result to sit below a
directory named `scratchpad` inside `<temp>/claude-<uid>` (the session scratchpad's location), opens it
without following a final symlink, requires a single-link regular file owned by you (a hard link to a
file elsewhere is refused), reads it itself (at most 256
KiB, valid UTF-8, non-empty, at most 65,536 characters, which is GitHub's comment limit) and passes the
content to `gh` on stdin. A file anywhere else — including an issue draft under the repo's `issues/` —
must first be copied into the scratchpad with `Write`. Other sessions' scratchpads of the same user stay
readable (residual). The script needs a POSIX platform and refuses elsewhere. It exits with `gh`'s own
status and does not print the body it sends.

`whoami` prints the authenticated login (used by `references/next-round-trigger.md`'s authorship
check). `push-destinations` prints each of `origin`'s push URLs as `owner/repo`, one per line (used by
Workflow step 4's push-destination check). `issue-create` files an issue in the named repo with
`--title` (1-256 characters, no control characters) and the body file, and prints the issue URL.

## Replying to an inline PR review comment

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" reply --owner <owner> --repo <repo> \
  --pr <pr> --comment-id <comment_id> --body-file "<scratchpad-path>/reply.txt"
```

Write the reply text to a scratchpad file first rather than inline shell quoting — this avoids
shell-escaping failures on backtick- or quote-heavy finding text. The script reads the file
itself and posts its content as the body, on stdin (`gh api`'s `-F body=@-`; a `-f` field would post
the literal string instead of the content, which the script never does). The endpoint it calls is
`repos/<owner>/<repo>/pulls/<pr>/comments/<comment_id>/replies`; the shorter form without the `<pr>`
segment 404s, so `--pr` is always required.

## Resolving a review thread

There is no REST endpoint for this. It takes GitHub's GraphQL API: first a `reviewThreads` query on the
PR to obtain the thread's opaque node `id`, then the `resolveReviewThread` mutation keyed by that `id`.
Both are subcommands of the script; the mutation needs no repo scoping because it is keyed by the
thread's global node `id`.

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" threads --owner <owner> --repo <repo> --pr <pr>
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" threads --owner <owner> --repo <repo> --pr <pr> \
  --cursor "<endCursor>"
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" resolve --thread-id "<thread id>"
```

`threads` returns one page of 50: each thread's `id`, `isResolved`, `path`, `line` and its first
comment's `databaseId`, body and author, plus `pageInfo { hasNextPage endCursor }`. A single page
silently misses any thread beyond the 50th, so keep calling with the previous response's `endCursor`
as `--cursor` while `hasNextPage` is `true` before treating the thread list as complete. The first
call (no `--cursor`) sends a typed GraphQL `null`; the script never sends the string `"null"`, which
was observed to return a silently truncated page with `hasNextPage: false` (issue #312).

`comments.nodes[0].databaseId` is the REST `comment_id` — the link between the GraphQL thread list and
the `reply` subcommand above.

Every `threads` and `resolve` call needs its own marker, including the read-only `threads` lookup. A
verifiably-read-only carve-out was tried in the guard and removed after three independent reviewers
found four ways to defeat a substring match on a raw command (see `git-guard-raw-pr-review.sh`'s header
comment); the script applies the same rule to its own GraphQL calls.

To resolve several threads, make one `resolve` call per thread, each in its own `Bash` call with a
fresh marker written just before it.

## Leaving a thread unresolved on purpose

For a deferred (exception-filed, budget-exhausted-and-filed, or declined) finding, reply with the
tracking-issue link (or the decline acknowledgment) and state explicitly that the thread is being left
open until the issue is addressed — then simply never call `resolve` for it. This is the
mechanical counterpart to `references/round-and-dedup-rules.md`'s "deferred findings don't get
resolved" rule.

## Posting a review-trigger comment

Workflow step 8 posts a plain **top-level** PR comment — not an inline reply, and not the same endpoint
as "Replying to an inline PR review comment" above. `<trigger text>` (a reviewer's
`default_review_trigger` or `full_review_trigger` from `review_findings_reviewers`, e.g.
`@codex review`, `@coderabbitai full review`, `/devin review`) is settings data, not something this
skill authored — it must pass Workflow step 8's three-step check (tracked-ness gate, then the
allowlist-regex and handle-token checks) *and* must never be inlined directly into the command line,
even after validating clean, since a value that happens to pass every check could still contain
characters a shell interprets.

**Every trigger comment's body also carries the batch marker**, `<!--
handling-review-findings-trigger:<batch-id> -->`, on its own line after a blank line following the
trigger text — a plain trigger-string match can't tell this skill's own post apart from
`codex-review-recovery`'s identical-looking retry comment, so the marker (plus the author-ownership
check in SKILL.md's Workflow step 8a) is what actually identifies a comment as this skill's own. The
`<batch-id>` generation rule and the full counting mechanism live in SKILL.md's Workflow step 8a/8d —
not restated here. Write each reviewer's validated string plus this marker to its **own** scratchpad
file — `trigger-<name>.txt`,
written immediately before that specific reviewer's post, never one shared filename reused across
reviewers (a shared name risks a stale prior reviewer's body surviving a failed or out-of-order write
and getting posted under the next reviewer's marker instead) — then post it:

```
# trigger-<name>.txt content:
<trigger text>

<!-- handling-review-findings-trigger:<batch-id> -->
```

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" trigger-comment --owner <owner> \
  --repo <repo> --pr <number> --body-file "<scratchpad-path>/trigger-<name>.txt"
```

Posting one comment per selected reviewer is fine; there's no requirement to combine multiple
reviewers' trigger strings into a single comment, and combining them risks one reviewer's connector
misparsing text meant for another. Write one fresh marker per `trigger-comment` call, never one reused
across several reviewers' posts. The script checks the file's type and size, not what the trigger text
says; Workflow step 8's own validation and confirmation are what bound that.

## Fetching all reviewers together

Pull every reviewer's inline comments in one call and triage as one batch, rather than per-tool —
consistent with "the round counter is per-PR, not per-reviewer". The subcommand paginates — a PR with
enough inline comments to span multiple API pages otherwise silently loses later pages from dedup and
triage:

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-api.py" list-comments --owner <owner> --repo <repo> --pr <pr>
```

## Issue traceability payload

Every issue filed from the Issue path (SKILL.md Workflow step 5) must include, beyond
`github-issue-creator`'s standard template fields:

- The PR URL.
- The head SHA the finding was raised against.
- The review thread/comment URL or ID.
- The reviewer that raised it (tool name, or human reviewer's handle).
- Its stated severity.

This is the payload a reader needs to act on the issue without re-opening the PR. Add it as its own
`## Review Finding Source` section in the drafted issue file, after `## Additional Context`.

## Issue-filing convention

Use a plain, non-closing reference in the PR body/comment — "Found in PR #N" — never
"Fixes #N"/"Closes #N". A merge must not auto-close a still-open, still-unaddressed issue.

## Scratchpad path

Any placeholder path above (e.g. `<scratchpad-path>/reply.txt`) means the session's actual scratchpad
directory — never a literal path to type as-is, and never a bare relative filename, which would
silently resolve to the current working directory instead (see CLAUDE.md's "No Scratch Files at Repo
Root" and `.claude/rules/require-gitignored-scratch-locations.md`).
