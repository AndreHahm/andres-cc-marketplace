# PR #610, round 2: fix self-review result (simulated, nothing executed)

## Exit-1 case (one blocking finding: unused Bash grant in demo SKILL.md frontmatter)

Governing text: `references/fix-self-review.md` 4a-4d.

1. Treat the finding as blocking. The verifiers use touched-file logic, not touched-line logic: every
   finding for a file the fix changed blocks, wherever it sits. The finding is on a line my fix touched
   anyway, but I would not wave it off as "outside my diff" even if it were not. This counts as
   iteration 1 of the 2-iteration budget (4d).
2. Do not push, reply or resolve. A non-zero 4a exit stops all three. The fix stays uncommitted.
3. Fix the finding in the same working tree. Either remove the unused `Bash(...)` grant, or, if the call
   is meant to exist, add the matching call. The choice depends on what the SKILL.md actually needs.
   Removing the grant is the likelier case, because the line-count fix probably dropped the call.
4. Do 4b, the sibling sweep. Grep the rest of the same SKILL.md for other grants without a matching
   call, which is the same anti-pattern. Fix any found as part of the same fix.
5. Do 4c. Review my own edits, because the fix is uncommitted. Use the old and new text, `Read` each
   changed file, and run `git ls-files --others --exclude-standard` and `git ls-files --deleted`. The
   check is whether the grant change created a new edge case next to the line-count fix. The reply's
   verification line must say 4c was a review of my own edits.
6. Re-run 4a, with `--worktree` and the same `--base`, as iteration 2. Re-run verification of the
   original R13 fix as well, since the SKILL.md changed again.
   - Exit 0: continue the normal Fix path. Check the push destinations, commit via `Skill(commit)` with
     `--push`, wait until the push has landed, then reply with the SHA and a verification line (and say
     4c was a review of my own edits). Then resolve the thread and record the disposition in the
     ledger (4e).
   - Still blocking after iteration 2: stop. Do not loop a third time and do not push, reply or
     resolve. Report the remaining findings to the user, and record the finding as `accepted` or leave
     it open, as the user directs.

## Push, reply or resolve now?

No. Not while 4a exits non-zero (1 or 2), or 4b/4c show a defect in the fix. The finding stays open in
round 2, with no ledger entry until it is settled. Reply-with-SHA also needs a landed push, so replying
or resolving off an unpushed or unverified fix is excluded twice over.

## Exit-2 case ("Verifiers could not run")

Treat it exactly like exit 1: never as a pass, and never as "no findings".
- Do not push, reply or resolve. Do not write "verifiers passed" in any reply.
- Find the cause from the script's message. Possible causes: PyYAML or markdown-it-py is missing (use the
  repository's virtual environment interpreter), `origin`'s fetch URL is not the PR's base repository
  (`--upstream`), no `refs/remotes/origin/HEAD`, an empty diff, or the fix edits what grades it
  (`scripts/marketplace_ci/`, `.claude/marketplace-sync.json` or the script itself).
- If the cause is an environment problem I can correct, correct it and re-run 4a. That counts toward the
  2-iteration budget if it leads to a blocking result. If it cannot be corrected, or the fix edits the
  grading code, report that to the user ("could not be judged by the verifiers") rather than claiming a
  pass. Leave the finding open until the user directs otherwise.
- Only if the script says "nothing to check" (neither base nor tree has `scripts/marketplace_ci/`) is it
  an exit-0 case, not exit 2. The reply must then say so, not claim the verifiers ran.

Note: even an exit 0 is not the CI verdict. A size tier already over its limit before the fix and not
worse after it passes here, and CI can still block.
