I carry on with development-to-pr and do not re-invoke linear-github-lifecycle: it dispatched this skill, and the "When NOT to Use" entry exempts that case. I run only this phase.

Next, step 1: read ENG-205's outcome and title via linear-work-management, its git-github-evidence via linear-github-linking, and the policy profile via repository-gates. Then step 2: search for an existing PR via linear-github-linking before committing, confirming an Adoptable match or resolving a conflict with the user.

- Existing PR: verify checkout, then git-kit:cross-model-review (BASE=HEAD), then git-kit:commit with its push.
- No PR: git-kit:commit without push/Auto-PR, then, after confirmation, git-kit:create-pr.

Then read back, confirm gates, record evidence, and return control to linear-github-lifecycle, which owns review and merge.
