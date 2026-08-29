# Candidate Pattern Format

Each candidate produced by Phase 3 mirrors `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s own per-PR
pattern structure, so a candidate accepted by `managing-review-learnings` can be appended into the
document with no reshaping. A candidate is a *proposal* — nothing in this format implies it has been
added to the document yet.

## Fields

```markdown
### Candidate: <short pattern name>

**Source PR:** #<number> — <PR title>
**Reviewer(s):** <one or more `reviewer` logins from the cited `pr_review_fetcher.py` record(s), each
paired with its own `submitted_at` date (UTC, `YYYY-MM-DD`) — e.g. `coderabbitai[bot] (2026-08-17),
chatgpt-codex-connector[bot] (2026-08-19)`. When the same finding was raised more than once (a repeat
across separate review rounds, not just separate reviewers), list each occurrence's own date rather than
collapsing to one — the distinct dates are what shows it recurred across rounds. Both fields already
live on every record `pr_review_fetcher.py` returns — never a new fetch or tool grant to populate this.>
**Review round(s):** <the source PR's own total review-round count — the number of distinct
review-level records (`kind: "review"`, deduped by `review_id`) `pr_review_fetcher.py` returned for
*this PR as a whole*, one round per formal review submission (Codex/CodeRabbit/Devin/a human each
submitting one review is one round). This is a PR-wide count, not scoped to just the record(s) that
raised this specific candidate — `managing-review-learnings`' own document header
(`references/doc-update-conventions.md`'s `(<reviewer(s)>, <round count> rounds, <date>)` format)
needs the PR's overall round count regardless of which round first surfaced any one finding. Not the
same as counting individual inline comments, which can span multiple rounds or cluster within one.>
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
schema exists yet for this. Use `pr_review_fetcher.py`'s own `source_url` field directly for each cited
record — it's GitHub's real `html_url` for that review/comment/issue-comment, so this URL never needs
hand-reconstructing from a bare `review_id`/`comment_id`.>
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
**Reviewer(s):** chatgpt-codex-connector[bot] (2026-08-12)
**Review round(s):** 1
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
