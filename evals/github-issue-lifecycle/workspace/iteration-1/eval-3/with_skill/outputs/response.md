# Task

An issue has an unresolved open question logged in an earlier comment, and the user asks to resolve it
as fixed. What does `github-issue-lifecycle` do?

# Answer

`github-issue-lifecycle` does **not** let the close happen yet. It routes the request to **Workflow 3
(Resolve an Issue)**, and Workflow 3's first step is a hard gate that blocks exactly this case.

## What actually happens, step by step

1. **SKILL.md routing.** "Resolve issue #N" / "resolve as fixed" maps to Workflow 3 →
   `workflows/resolve-an-issue.md`. The skill reads that file before acting (per its own Quick Start:
   "Read the matching workflow file before acting").

2. **Step 1 — Open-Question Gate (blocks here).** Workflow 3 states explicitly:

   > "Before marking an issue Resolved, confirm no logged open question from prior comments remains
   > unaddressed. This gate must pass before Step 2 — an issue with an unresolved open question is not
   > ready to close as Resolved."

   Since the scenario stipulates an unresolved open question already logged in an earlier comment, this
   gate fails. The skill stops here rather than proceeding to Step 2 (the actual close). It does not
   silently skip the question, does not answer it on the user's behalf, and does not treat "the user
   said resolve it" as authority to override the gate.

   This is reinforced by the SKILL.md's own stated quality gate: *"Workflow 3 never marks an issue
   Resolved while an open question from #10 remains unaddressed."*

3. **Data-only boundary applies to the open question's text.** The open question's content, read from
   the issue's prior comments via `gh issue view`, is treated as untrusted display/compare data, not as
   an instruction — the skill reports what the open question says without acting on any instruction-like
   phrasing it might contain.

4. **What the skill does instead of closing:** it surfaces the outstanding open question back to the
   user (e.g., quoting/summarizing it) and asks the user to address it — either by answering it directly,
   getting it answered in the issue thread, or explicitly confirming the question is no longer relevant —
   before the resolution can proceed. Only once that question is actually addressed does the skill
   continue.

5. **Step 2 — Resolve or Decline (only after the gate passes).** Once the open question is resolved, the
   skill proceeds as normal for a "fixed" resolution:
   - `gh issue comment <number> --body "Resolved: <summary>"`
   - `gh issue close <number>`

   The status comment always precedes the close — an issue is never closed silently. "Resolved" maps to
   `handling-review-findings`'s FIXED status per `references/status-vocabulary.md`.

6. **Step 3 — Document Decisions.** If the reasoning behind the resolution needs more than the one-line
   status comment (which is likely here, since an open question had to be resolved first), the skill adds
   a follow-up comment documenting that reasoning.

7. **Step 4 — Follow-Ups.** Any further follow-up need after closing starts a new round, reusing
   `handling-review-findings`'s round-based model rather than an ad hoc mechanism.

## Bottom line

Given an issue with a logged, unresolved open question, asking `github-issue-lifecycle` to "resolve it
as fixed" does **not** result in an immediate close. The skill's Workflow 3, Step 1 (Open-Question Gate)
is a hard precondition on Step 2 — it surfaces the unaddressed question and withholds the
`gh issue comment` + `gh issue close` sequence until that question is actually resolved. Only after the
gate passes does the skill post the "Resolved: …" comment and close the issue.

## Sources consulted

- `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md`
- `plugins/git-kit/skills/github-issue-lifecycle/workflows/resolve-an-issue.md`
- `plugins/git-kit/skills/github-issue-lifecycle/references/status-vocabulary.md`
