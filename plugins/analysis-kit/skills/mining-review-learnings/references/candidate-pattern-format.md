# Candidate Pattern Format

Each candidate produced by Phase 3 mirrors `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s own per-PR
pattern structure, so a candidate accepted by `managing-review-learnings` can be appended into the
document with no reshaping. A candidate is a *proposal* — nothing in this format implies it has been
added to the document yet.

## Fields

```markdown
### Candidate: <short pattern name>

**Source PR:** #<number> — <PR title>
**session-transcript:** available | unavailable
**What happened:** <1-3 sentences, matching the document's own "What happened" framing>
**Assumed vs. actual** (when applicable — omit for findings that aren't a tool/API/language-behavior
mismatch):

| Assumed | Actual |
|---|---|
| <what was assumed to be true> | <what is actually true> |

**Rule:** <the generalizable rule this finding implies, in the document's own imperative style>
**Evidence:** <comment URL(s) from the fetched review history, and the transcript locator when
`session-transcript: available` — the raw source, not a metadata block; no formal evidence-metadata
schema exists yet for this>
**Cross-check:** <only when session-transcript is available — does the transcript's own account agree
with the review comment's stated root cause? Note agreement or divergence explicitly.>
```

## Excluded candidates

Every finding Phase 3 considered but didn't promote to a candidate is still listed, under its own
`### Excluded: <short description>` heading with a one-line reason (already cited for this exact
finding, doesn't generalize beyond this PR, content comparison was ambiguous and judged not new — state
which). An excluded finding is never silently dropped from the report.

## Example

```markdown
### Candidate: gh api pagination silently drops earlier page's true result under jq -e

**Source PR:** #49 — fix(codex-review-recovery): stuck-check retry mechanics
**session-transcript:** unavailable
**What happened:** An instruction assumed `jq -e 'any(...)'` over `--paginate` output matches if any
page matched. In fact `jq -e`'s exit status reflects only the last value it emitted — an earlier page's
`true` result is silently overridden by a later page's `false`.
**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| `jq -e 'any(...)'` over paginated output matches if any page matched | Exit status reflects only the last emitted value; an earlier `true` can be silently overridden |

**Rule:** When piping paginated `gh api` output through `jq -e`, aggregate across all pages before the
`-e` exit-status check, never rely on the last page's own exit code alone.
**Evidence:** [PR #49, review comment](https://github.com/<owner>/<repo>/pull/49#discussion_r<id>)
**Cross-check:** N/A — no session transcript found in the PR's merge window.
```
