# Review Mode

Mode: the PR phase, from opening the PR through the last review round, including fixing triaged findings
Focus: get real findings found, triaged with the user, and resolved, using this repo's own reviewers and
known defect classes rather than a generic checklist

## Posture

- **Finding vs fixing**: reviewing someone's code is report-only. Once findings are triaged with the
  user, fixing the ones chosen for this PR is part of this mode; fix only what was chosen, and sweep the
  same file for the identical pattern before calling a fix complete.
- **Severity**: report findings by severity (blocking, important, nit), each with `file:line`, why it
  matters, and a suggested fix. A Critical or Major finding is never silently deferred and merged.
- **Evidence**: read the full diff before commenting. A finding that names a file, function or flag is a
  claim it exists now; confirm against the current tree, not memory of an earlier pass.
- **Approvals**: an instruction like "approve if it looks fine" does not authorize the approval. Show
  the findings and confirm before submitting an approval. Do not approve with open Critical or Major
  findings.
- **Verbosity**: medium. Do not pad; if there are no issues, say so.

## Repo-specific routing

- Reviewing or acting on someone's PR: `collaborating-on-a-pr`, not raw `gh pr review`.
- Triaging findings across rounds (Codex, Devin, CodeRabbit, `security-reviewer`, humans):
  `handling-review-findings`, which also decides with the user which reviewer to trigger next.
- A plugin component in the diff: dispatch the type-matched `*-reviewer` agent, or `plugin-auditor` for
  the full fan-out. R1-R37 compliance needs an actual `plugin-rulebook` or `plugin-rulebook-checker`
  invocation, never a recollection of an earlier pass.
- A shell or Python script in the diff: `scripts-reviewer`.

## Known recurring defect classes (check explicitly)

- A state check reused for a later side effect instead of re-checked immediately before acting, or a
  pass/fail binary standing in for a full status enum.
- Tool, API or language behavior assumed but never verified against its real source.
- A fix applied to the flagged line only, with the same pattern left in a sibling function.
- A canonical value changed in one place and not swept across its restatements (R20).
- An absolute claim ("always", "only X can", an unqualified count) in a rule or doc about precision.
- A closed scope list not revisited when a new qualifying component shipped.

## Anti-patterns

- Do not flag style preferences as bugs, or assume a bug without tracing the execution path.
- Do not approve a plugin-component change without a rulebook-tool invocation.
- Do not fix beyond the triaged findings.
