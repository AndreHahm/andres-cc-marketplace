# GitHub API Mechanics

- [Replying to an inline PR review comment](#replying-to-an-inline-pr-review-comment)
- [Resolving a review thread](#resolving-a-review-thread)
- [Leaving a thread unresolved on purpose](#leaving-a-thread-unresolved-on-purpose)
- [Posting a review-trigger comment](#posting-a-review-trigger-comment)
- [Fetching all reviewers together](#fetching-all-reviewers-together)
- [Issue traceability payload](#issue-traceability-payload)
- [Issue-filing convention](#issue-filing-convention)
- [Scratchpad path](#scratchpad-path)

## Replying to an inline PR review comment

**The `gh-pr-review` marker (SKILL.md's Workflow / GitHub API Mechanics) goes immediately before this
reply call, same as the `resolveReviewThread` mutation below** — `guard-raw-pr-review.sh` hard-blocks
this endpoint without one. If a fresh marker isn't written right before it, the call is denied.

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies -f body="..."
```

The shorter, more-intuitive-looking `repos/{owner}/{repo}/pulls/comments/{comment_id}/replies` (no
`pull_number` segment) 404s — live-verified against this repository's own use of this endpoint. Always
include `pull_number`.

For a long or multi-line reply body, write it to a scratchpad file first rather than inline shell
quoting — avoids shell-escaping failures on backtick- or quote-heavy finding text:

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies \
  -f body="$(cat "<scratchpad-path>/reply.txt")" --silent
```

**`-f`/`--raw-field` never interprets a leading `@`.** Only `-F`/`--field` reads `@<path>` as a file
reference (`gh api --help`: `-F, --field key=value` — "use `@<path>` or `@-` to read value from file or
stdin"; `-f, --raw-field key=value` carries no such behavior). `-f body=@<path>` silently posts the
literal string `@<path>` as the comment body — no error, no file read. Use the `$(cat ...)` form above
with `-f`, or switch to `-F body=@<path>` — never `-f body=@<path>`.

## Resolving a review thread

There is no REST endpoint for this at all. It requires GitHub's GraphQL API — first a `reviewThreads`
query on the PR to obtain the thread's opaque node `id`, then the `resolveReviewThread` mutation keyed
by that `id`. Both calls go through `gh api graphql -f query=...`. `gh api` has no `-R`/`--repo` flag
(SKILL.md's Workflow step 1) — if `$ARGUMENTS` named a PR outside the current checkout's repository,
scope the `reviewThreads` query with explicit `owner`/`name` GraphQL variables (`-F owner=... -F
name=...`, exactly as the query below already does) rather than an env-var-prefixed (`GH_REPO=...`)
invocation, whose interaction with this skill's own `Bash(gh api graphql:*)` grant has not been
verified. The `resolveReviewThread` mutation needs no repo scoping at all — it's keyed entirely by the
thread's global node `id` resolved from that query.

The complete, executable `reviewThreads` query — a bare `reviewThreads(...) { ... }` fragment with no
`query`/variable declaration or `repository(owner:...) { pullRequest(number:...) { ... } }` wrapper is
**not** a submittable GraphQL document (`gh api --help`'s own GraphQL example shows the same
`repository(owner: $owner, name: $name)` wrapper for exactly this reason); this is the full shape,
live-verified against this skill's own use this session. Includes the field that bridges a thread node
back to the REST `comment_id` the reply endpoint above requires, and pagination via `pageInfo`/
`endCursor` — a single `first: 50` page silently misses any thread beyond the 50th on a PR with more
review threads than that, so loop on `hasNextPage` rather than treating one page as the complete set:

```
gh api graphql -F owner="{owner}" -F name="{repo}" -F number={pull_number} -f cursor=null -f query='
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          path
          line
          comments(first: 1) {
            nodes { databaseId body author { login } }
          }
        }
      }
    }
  }
}
'
```

Pass `$cursor` as a GraphQL variable (`null` on the first call, then each response's `pageInfo.endCursor`
on the next — set via `-f cursor="<endCursor>"`, not `-f cursor=null`, once a next page exists), and keep
querying while `pageInfo.hasNextPage` is `true` before treating the accumulated thread list as complete.
`-F owner=`/`-F name=`/`-F number=` are typed GraphQL variables (`gh api`'s `-F` flag), distinct from
`-f query=`'s plain string; get `{owner}`/`{repo}` the same way the REST endpoints above do.

`comments.nodes[0].databaseId` is the REST `comment_id` — the missing link between the GraphQL thread
list and the REST reply endpoint above.

**The `gh-pr-review` marker (SKILL.md's Workflow / GitHub API Mechanics) goes immediately before
*every* `gh api graphql` call here, including this `reviewThreads` lookup, not just the
`resolveReviewThread` mutation below.** An earlier revision of this guard carved out an exception for a
"verifiably read-only" lookup, matched by checking the command string for `reviewThreads` with no
`mutation` keyword — that carve-out was removed after three independent reviewers found four different
ways to defeat a substring match against a raw shell command (indirection via `=@file`/`$(cmd)`/
backtick/`--input`, a plain shell variable holding the query, and adjacent-quote string concatenation
splitting the literal word "mutation" across a quote boundary so it never appears contiguously) — see
`guard-raw-pr-review.sh`'s own header comment for the full history. The guard now denies every
`gh api graphql` call unconditionally absent a fresh marker, so the lookup needs one too. Since a marker
is single-use and consumed on the very next `Bash`/`PowerShell` call regardless of whether that call
matches, if the lookup and the mutation happen as two separate `Bash` calls, write the marker again
immediately before each one — a marker written once before the lookup is already consumed by the time
the mutation call runs.

Resolving one thread:

```
gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } } }' -f id="$tid"
```

Batch resolution — several threads in one shot beats N separate calls (Bash-tool syntax, POSIX `for`;
this repo's agent shell is PowerShell-primary, but the `Bash` tool is a separate, always-available
surface for exactly this kind of POSIX scripting):

```
for tid in PRRT_xxx PRRT_yyy; do
  gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } } }' -f id="$tid"
done
```

## Leaving a thread unresolved on purpose

For a deferred (exception-filed, budget-exhausted-and-filed, or declined) finding, reply with the
tracking-issue link (or the decline acknowledgment) and state explicitly that the thread is being left
open until the issue is addressed — then simply never call `resolveReviewThread` for it. This is the
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
and getting posted under the next reviewer's marker instead) — then post with `--body-file`:

```
# trigger-<name>.txt content:
<trigger text>

<!-- handling-review-findings-trigger:<batch-id> -->
```

```
gh pr comment <number> -R "<owner>/<repo>" --body-file "<scratchpad-path>/trigger-<name>.txt"
```

`--body-file` is a real, confirmed flag on `gh pr comment` specifically (`gh pr comment --help`: `-F,
--body-file file   Read body text from file`) — not assumed from its presence on other `gh` subcommands
like `gh issue create`.

Posting one comment per selected reviewer is fine; there's no requirement to combine multiple
reviewers' trigger strings into a single comment, and combining them risks one reviewer's connector
misparsing text meant for another.

**The `gh-pr-review` marker goes immediately before this call too**, same as the reply/resolve calls
above — one fresh marker per `gh pr comment` call, never one marker reused across several reviewers'
posts, since the marker is consumed by the next `Bash`/`PowerShell` call regardless of match. Unlike
those two, this call needed no *logic* change to `guard-raw-pr-review.sh` itself — that hook's `gh pr
comment` branch already matches any `gh pr comment` invocation unconditionally, regardless of the
comment body, so the existing guard already covers this new call site for the shapes it can see. Only
this skill's own `allowed-tools` frontmatter needed the addition (`Bash(gh pr comment:*)`), since the
skill had never posted a top-level comment before this redesign — only inline replies via the
`.../replies` endpoint above. This coverage isn't unconditional, though: `guard-raw-pr-review.sh`'s own
header comment discloses residual bypass shapes (command-substitution/backtick/quote-prefix
indirection, and invocation via a script file the hook never inspects) that apply to every branch in
that file, including this one — nothing about this new call site closes or reopens those, they're a
pre-existing property of the guard itself.

## Fetching all reviewers together

Pull every reviewer's inline comments in one call and triage as one batch, rather than per-tool —
consistent with "the round counter is per-PR, not per-reviewer". Paginate — a PR with enough inline
comments to span multiple API pages otherwise silently loses later pages from dedup and triage:

```
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments --paginate
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
