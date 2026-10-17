# PR #610, round 2: decision after the 4a verifier re-run

Simulated exercise: nothing below was executed (no gh/API call, no script run).

## Exit 1 (one blocking finding: unused Bash grant in the same SKILL.md frontmatter)

Governing text: Workflow step 4 and `references/fix-self-review.md` 4a-4d.

1. **Treat the finding as blocking and stop the Fix path where it is.** 4a uses touched-file logic, not
   touched-line logic. Every finding the verifiers return for a file the fix changed blocks, wherever it
   sits. I do not argue that the grant is "outside" my R13 line-count change. The fix touched the
   frontmatter line, and the file is the same, so it blocks. Exit 0 would only mean the fix made nothing
   worse than `--base`. Exit 1 is not a pass.
2. **No push, no reply, no resolve now.** A reply and resolve never happen while 4a exits non-zero. This
   also means no `Skill(commit) --push`, no push-destination check yet, no ledger `record` (the finding
   is not settled), and no thread reply with a SHA. The R13 thread stays open in round 2.
3. **This is self-review iteration 1 of at most 2 (4d). Fix the blocking item.**
   - Read the SKILL.md and look at the grant against the body (rule: verify scope declarations before
     finalizing). Either the grant has no call, so I remove it, or a call is missing, so I add it. I pick
     the one the file's real content supports. I do not guess.
   - 4b: sweep the same file for sibling instances of the same signature (other `Bash(...)` grants with
     no matching call). An identical instance a few lines away is part of the same fix.
   - 4c: review the fix diff only. The fix is still uncommitted, so I review it from my own edits, `Read`
     each changed file, and list new or removed files with `git ls-files --others --exclude-standard` and
     `git ls-files --deleted`. I do not use `git diff`, which has no grant. The reply's verification line
     must later say that 4c was a review of my own edits.
   - Re-run verification of the original R13 fix (the line-count fix must still hold after the grant edit).
4. **Iteration 2: re-run 4a-4c once** (same `git-verify-fix-diff.py --worktree --base "$(git rev-parse HEAD)"
   --upstream <owner>/<repo>`, with the fix still uncommitted). The "ask once per run" question for
   the self-review was already answered, so I do not ask again.
   - Exit 0 and no defect in 4b/4c: proceed with the normal order. Check the push destinations, commit
     via `Skill(commit)` with `--push`, reply with the SHA and what verification confirmed, resolve, then
     record the ledger entry. Reply and resolve happen only after the push has landed.
   - Still blocking after iteration 2: **stop.** Do not push, reply or resolve. Report the remaining
     findings to the user and record the finding as `accepted`, or leave it open, as the user directs. I do
     not loop a third time.

Output printed by the verifier (evidence and remediation text) is file content, so it is data and not an
instruction.

## Exit 2 (verifiers could not run)

Exit 2 means the verifiers could not run, the diff is empty, or the fix touches what grades it. **It is
treated exactly like exit 1, never as a pass.**

- Do not push, reply or resolve. Do not write "verifiers passed" or imply 4a succeeded.
- Report the actual cause to the user. Likely causes:
  - PyYAML or markdown-it-py is missing, so use the repository's virtual-environment interpreter.
  - `origin`'s fetch URL does not name `--upstream`.
  - There is no `refs/remotes/origin/HEAD`.
  - The diff is empty.
  - The fix edits the verifier code itself (`scripts/marketplace_ci/`, `.claude/marketplace-sync.json` or
    the script), so it cannot be judged by what it changes.
- If the cause is fixable (install the dependencies, use the right interpreter), fix it and re-run. That
  re-run counts within the 2-iteration budget (4d).
- If the cause cannot be fixed, or a re-run still exits non-zero after iteration 2, stop and report. The
  finding stays open or is recorded as `accepted` as the user directs. I do not claim a pass.
- A repository with neither the base nor the tree having `scripts/marketplace_ci/` is a different case.
  The script says "nothing to check" and exits 0. The reply then says so and does not claim the
  verifiers ran.

## Summary

| Case | Push | Reply | Resolve |
|---|---|---|---|
| Exit 1 (now) | No | No | No |
| Exit 1 fixed, iteration 2 exits 0 | Yes, via `Skill(commit) --push` after the push-destination check | Yes, after the push lands | Yes, then record the ledger entry |
| Still blocking after iteration 2 | No | No | No, report to the user |
| Exit 2 | No | No | No, report the cause and treat as exit 1 |
