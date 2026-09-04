# PR #150, Round 3: Triage Decision

## (1) Commit Label / Description

**Recommended commit message:**

```
docs: file review finding as separate issue

Add issue draft documenting Minor finding from round 3 review:
inconsistent list formatting in README.md changelog section.

This change defers the formatting fix to a separate issue rather
than addressing it in this PR.
```

**Rationale:**
- The commit adds no actual fix to the PR's deliverable (README.md remains unchanged)
- The commit only documents and formalizes the decision to defer a Minor finding
- The commit message should make this deferral decision explicit and transparent
- This avoids ambiguity — a reader seeing the commit hash in the PR can understand that the change is meta (filing an issue) rather than substantive (fixing code)

**Alternative, shorter:**

```
docs: add issue draft for review finding #X
```

Either is valid; the first is more explicit about what decision was made.

---

## (2) Does This Commit Open a New Review Round?

**Answer: Ambiguous; depends on team policy and review automation.**

**Analysis:**

| Factor | Assessment |
|--------|-----------|
| **HEAD SHA changed?** | Yes — adding a commit always changes HEAD. This may trigger automated CI or review-request re-fires in some GitHub workflows. |
| **Deliverable changed?** | No — README.md (the file containing the actual finding) remains unfixed. Only a metadata file (`issues/...md`) was added. |
| **Finding addressed?** | No — the Minor formatting issue itself was not fixed, only documented/deferred. |
| **Policy dependency?** | High — whether a new round is needed depends on whether the team considers deferring findings *without* fixing them sufficient, or whether all findings (especially in the PR's scope) must be addressed before merge. |

**Three reasonable interpretations:**

1. **"Any HEAD change triggers review"** — If the repo's GitHub Actions or review automation fires on every new commit to a PR, then yes, a new round window opens automatically. This is common and requires no explicit decision.

2. **"New round only if deliverable changed"** — If the review process is scoped to the PR's stated deliverable (README.md fixes, code changes, etc.), and this commit only adds documentation *about* a deferred finding without changing the deliverable, then technically no new round is strictly needed. The deliverable is unchanged.

3. **"New round depends on finding severity"** — If the team has a policy like "defer Minor findings to issues automatically, but Critical/Major must be fixed this PR," then a decision to file this Minor separately *without* fixing it may not require a new review round, as long as the issue draft makes the deferral explicit.

**Recommendation:**

- **Assume a new round *may* open** due to the HEAD SHA change and standard CI automation.
- **Do not assume a new round is *unnecessary* without explicit team policy** on handling deferred findings.
- **Be transparent in the commit message** that this is a deferral decision (as suggested above), so reviewers understand the intent if they do re-review.
- **If the team's policy explicitly allows deferring Minor findings to separate issues**, document that in a comment on the PR or the issue draft itself.

---

## Summary

| Question | Answer |
|----------|--------|
| How to label this commit? | `docs: file review finding as separate issue` — make the deferral decision explicit. |
| Does it open a new round? | Possibly/probably, due to HEAD SHA change and CI automation. Not guaranteed to require a full substantive review, but re-review automation may fire. Recommend documenting the decision in the commit message to clarify intent. |
