# Decision: PR #610 round 2, self-review verifier results

## Exit 1 case (one blocking finding)

The finding is a Bash grant in the SKILL.md frontmatter, on a line my fix touched, that has no matching call in the body. My own fix introduced or left it, so it is mine to resolve before anything leaves my machine.

Steps, in order:
1. Read the reported line and the SKILL.md body. Confirm the finding is real: is the grant unused, or is the call present under a different form the verifier cannot match?
2. If the grant is unused, remove it (or narrow it) in the working tree. If a matching call really is needed, restore the call instead. Keep the change minimal and limited to the fix's scope.
3. Re-run the R13 line-count check to confirm the original Major finding is still resolved, and any other verification I ran earlier.
4. Re-run the self-review verifier (4a). Repeat until it exits 0. If the finding is a false positive, do not suppress it silently. Record the reason and tell the user.
5. Mirror check: this repo keeps `plugins/` and `.claude/` byte-identical, so apply the same edit to the mirror copy and confirm they match.
6. Only then commit (through the commit skill).

## Push, reply, resolve

None of these now. The fix is uncommitted and the verifier is failing, so nothing is pushed, no reply is posted to the review thread, and the thread is not resolved. Reply and resolve come after the fix is committed and pushed, and the reply should cite the pushed commit SHA. Resolving earlier would claim a fix that is not yet clean or visible to the reviewer.

## Exit 2 case ("Verifiers could not run")

Exit 2 is not a pass and not a finding. It means the check did not happen, so I treat it as unverified, not clean.
1. Do not proceed to commit, push, reply or resolve on the strength of it.
2. Find out why the verifiers could not run (missing tool, bad arguments, wrong cwd or mirror path) and fix the environment or invocation. Do not edit the fix to work around it.
3. Re-run until it gives exit 0 (clean) or exit 1 (real findings, handled as above).
4. If it still cannot run, stop and tell the user that self-review is unverified, rather than pushing as if it passed.
