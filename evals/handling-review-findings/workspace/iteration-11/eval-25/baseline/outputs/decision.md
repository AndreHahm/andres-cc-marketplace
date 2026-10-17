# PR #610 round 2: decision

## Exit 1 case (one blocking finding: orphan Bash grant on a line my fix touched)

1. Treat it as a real defect in my own uncommitted fix. Do not dismiss it, do not commit around it, and do not argue the verifier down.
2. Look at the flagged frontmatter line. Decide whether the grant is truly unused.
   - If the fix touched that line, the grant is my responsibility. Either the fix removed the call the grant covered, or the line count trim moved things.
   - If unused: remove the grant (or restore the call if the fix wrongly deleted it).
   - If the verifier is wrong (a call exists in a form it cannot match): record why, and only then proceed. Never silently override.
3. Re-check the original Major finding: R13 line count on `plugins/demo-kit/skills/demo/SKILL.md` still passes after the extra edit.
4. Sweep sibling occurrences: check the rest of that frontmatter for other grants without a matching call.
5. Mirror check: if `.claude/skills/demo/` mirrors this skill, apply the identical edit there.
6. Re-run the verifier. Loop until it exits 0. Re-run the original verification too.
7. Only then commit (via the commit skill) the fix, including the grant correction.

## Push, reply, resolve now?

No. Nothing is pushed, no reply is posted and no thread is resolved while the verifier is at exit 1. The fix is uncommitted and not yet verified clean. Replying "fixed" would claim something not yet true. After the verifier exits 0 and the commit exists, push, then reply to the finding with the commit SHA and resolve it. Doing this after the push means the reply points at something the reviewer can see.

## Exit 2 ("Verifiers could not run")

Exit 2 is not a pass and not a finding. It means no verification happened.
- Do not treat it as clean, and do not proceed to push, reply or resolve on it.
- Diagnose why the verifiers could not run (missing interpreter, bad path, environment error, mirror root, script not executable) and fix the cause. Re-run.
- If it cannot be made to run, stop and report this to the user with the error. Offer options (fix the environment, do a manual check, or proceed knowingly with the gap disclosed). Do not decide this silently.
- Until the verifier gives exit 0 (or the user explicitly accepts the gap), the fix stays unpushed and the finding unreplied and unresolved.
