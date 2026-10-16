# Decision: PR #610, round 2, verifier re-run results

Source: `SKILL.md` Workflow step 4 and `references/fix-self-review.md` 4a-4e.

## Exit 1 (one blocking finding)

The blocking finding is a Bash grant in the same SKILL.md frontmatter, on a line my fix touched, with no matching call. It is on a touched line, so it is in the fix's lane. It is not an `outside_lane` item.

This is self-review iteration 1. In order:

1. Do not push, do not commit with `--push`, do not reply and do not resolve. A blocking finding on a touched line stops all of these. A reply and resolve never happens while 4a-4c show a new blocking finding on a line the fix touched.
2. Fix the blocking item. Either remove the unused Bash grant or add the missing matching call. Choose the one that is correct for the skill. This follows `verify-scope-declarations-before-finalizing`: the grant list and the calls must agree.
3. Sweep siblings (4b). Grep the rest of the same SKILL.md and component for the same anti-pattern: other grants with no matching call, and other calls with no grant.
4. Review the fix diff only (4c). Use `git diff`, not the whole PR. Check that the fix did not introduce a new edge case next to the one it closes.
5. Re-run the verifier (4a) on the still-uncommitted state: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-verify-fix-diff.py" --worktree --base "$(git rev-parse HEAD)"`. This is iteration 2, which is the last one allowed.
   - If it exits 0: self-review is done. The reply must not claim more than the verifier did. Then continue with the push-destination check (every `git remote get-url --push --all origin` line must equal the PR head repository), `Skill(commit) --push`, and the reply with SHA and the verification line. Resolve the thread only after the push has landed. Record the disposition in the ledger (4e) with `git-review-ledger.py record`.
   - If it still shows a blocking finding after iteration 2: stop. Do not loop a third time. Do not push, reply or resolve. Report the remaining findings to the user, and record the finding as `accepted` or leave it open, as the user directs. Ask via `AskUserQuestion`.

Any `outside_lane` findings are reported to the user, not fixed in this fix.

## Push, reply, resolve now?

No. Not now, and not on the strength of the passing verification alone. The earlier verification passed, but self-review is a second hard gate before the push, reply and resolve. The thread stays open in round 2 until the exit-1 item is fixed and the re-run is clean.

## Exit 2 ("Verifiers could not run")

Treat it exactly like exit 1. It is never a pass. Do not push, reply or resolve. It also counts as a blocking result for the 2-iteration budget.

- Report the failure to the user plainly. Do not claim the verifiers ran.
- Retry once at most if the cause is fixable, for example a wrong `--base`, a missing path, or a dirty state I can correct. That retry uses the iteration budget.
- If it still exits 2, stop and report to the user. They decide whether it is `accepted` or left open.

This is different from the "nothing to check" message. A repo with no `scripts/marketplace_ci/` exits 0 with that message, and the reply's verification line says so instead of claiming the verifiers ran.
