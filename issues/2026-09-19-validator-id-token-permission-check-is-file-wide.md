## Summary
`github-actions-validator`'s `check_security_policies()` (in `scripts/validate_workflow.py`) checks
whether a workflow declares `id-token: write` for OIDC-integrated actions by searching the **entire
file's text**, not the specific job that uses the OIDC action — so a job that uses an OIDC action gets a
false "compliant" result whenever ANY other unrelated job in the same file happens to declare
`id-token: write` at its own job level.

## Environment
- **Product/Service**: `plugins/github-actions-kit/skills/github-actions-validator/scripts/validate_workflow.py`, `check_security_policies()`, the `OIDC_ACTION_RE` check (around line 340)
- **Region/Version**: this repo, found during PR #355's code review (CodeRabbit), branch `feat/devops-kit`

## Reproduction Steps
1. Create a workflow with two jobs: `job-a` uses an OIDC-integrated action (e.g.
   `aws-actions/configure-aws-credentials@...`) but declares no `permissions:` block of its own; `job-b`
   is unrelated and declares `permissions: { id-token: write }` at its own job level.
2. Run `validate_workflow.py --policy-checks` against the file.
3. Observe no warning is emitted for `job-a`, even though `job-a`'s own effective permissions do not
   include `id-token: write`.

## Expected Behavior
The check should warn when a specific job that uses an OIDC-integrated action does not have
`id-token: write` in its own *effective* permission set.

## Actual Behavior
The current code is:
```python
if OIDC_ACTION_RE.search(text) and not re.search(r"id-token:\s*write", text, re.IGNORECASE):
    log_warn(
        f"{file} uses an OIDC-related action but does not declare "
        "id-token: write in permissions."
    )
```
`text` is the whole file's contents, so `re.search(r"id-token:\s*write", text, ...)` matches if
`id-token: write` appears *anywhere* in the file — including inside a different job's own
`permissions:` block, or even inside a `workflow_call`'s declared `secrets`/inputs section. Any job in
the file that happens to declare it "covers" every other job's OIDC-action usage, whether or not that
other job actually has the permission.

This is wrong because of how GitHub Actions permissions scoping actually works: a job-level
`permissions:` block **replaces**, not merges with, the workflow-level `permissions:` block. So a job's
true effective permission set is either (a) its own job-level `permissions:` block if present, or (b)
the workflow-level `permissions:` block if the job declares none, or (c) the (increasingly restrictive)
GitHub default otherwise. A file-wide substring search cannot express any of that per-job resolution.

## Impact
**Medium.** This is a security-hardening advisory check (doesn't fail the run, `check_security_policies`
always returns 0), so it doesn't block anything — but it can give false confidence: a job that's
genuinely missing `id-token: write` for its OIDC action gets silently marked compliant purely because an
unrelated job elsewhere in the same file has its own, unrelated `id-token: write`. Multi-job workflow
files (common in this plugin's own examples, e.g. `examples/valid-ci.yml`) are exactly the shape where
this false negative can occur.

## Suggested Fix (not prescriptive)
Parse the workflow's job boundaries and each job's own `permissions:` block (plus the workflow-level
`permissions:` block for jobs that declare none), compute each OIDC-using job's actual effective
permission set per GitHub's replace-not-merge model, and warn per-job rather than per-file. This requires
real per-job YAML/structure parsing (job start markers, indentation-scoped `permissions:` block
detection) rather than the current single `re.search` over the whole file's text — genuinely more
involved than the other, mechanically-scoped findings fixed alongside this issue in the same PR review
round, so it was deferred rather than attempted inline.

## Additional Context
Found in PR #355's review (CodeRabbit) and deferred as too large to fix in that review round, alongside
several smaller, independently-scoped findings (an `act` fallback exit-code bug, an untrusted-context
injection-regex gap, and a Windows path-separator bug) that were fixed directly in that same PR. This
finding was intentionally left for a dedicated follow-up rather than folded into that fix set.

## Review Finding Source
- **PR:** https://github.com/AndreHahm/andres-cc-marketplace/pull/355
- **Head SHA at time of finding:** `78f8f4194862fc45eaea081dc24c020f458b7520`
- **Review:** https://github.com/AndreHahm/andres-cc-marketplace/pull/355#pullrequestreview-5254985343
- **Reviewer:** coderabbitai (CodeRabbit)
- **Stated severity:** Major ("🏗️ Heavy lift" / too large to fix in this review round)
