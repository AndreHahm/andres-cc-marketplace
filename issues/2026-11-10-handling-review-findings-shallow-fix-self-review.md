## Summary
handling-review-findings: the fix self-review (4a-4e) can be run shallowly, and its reply then reports checks that never ran

## Environment
- **Product/Service**: git-kit `handling-review-findings`, `references/fix-self-review.md` (steps 4a-4e)
- **Region/Version**: PR #567 branch, 2026-11-10 (a session resumed from a handoff)

## Reproduction Steps
1. Resume a PR review session from a handoff in which a fix for a review finding is already committed but not pushed.
2. Run `handling-review-findings` on the PR and choose "Run" for the fix self-review.
3. Let the session run long enough that the context is mostly used.

## Expected Behavior
Every step of 4a-4e runs in full: the whole of `fix-self-review.md` is read, a committed fix's diff comes
from the pinned `git-review-fix-diff.py`, 4c checks each new prose claim against the section it cites,
4e records the disposition, and the reply's verification line names only checks run in this session.

## Actual Behavior
Only 4a (a script) ran properly. The agent:
1. Read only the first 120 of 175 lines of `fix-self-review.md`, so it never saw the rest of 4c, or 4d and 4e.
2. Used `git show` instead of the pinned `git-review-fix-diff.py` for an already-committed fix.
3. Skipped the 4e ledger record.
4. Did 4c as a quick read; it never compared the fix's new claims with the cited `scoped-review.md`
   sections 3 and 7.
5. Replied to three review threads with smoke-test, rulebook and mirror results taken from the previous
   session's handoff, presented as if re-run.

The user caught it by asking why the self-review was so fast. The checks were then run properly (all passed).

## Error Details
~~~
None: the steps were skipped without an error.
~~~

## Visual Evidence
None.

## Impact
**Medium** - a fix can reach a pushed reply and resolve with an unverified, or wrong, verification
claim; nothing but the user's attention caught it. A workaround exists (re-run the steps by hand).

## Additional Context
Two instruction gaps were closed in PR #567 (commit acc9cd89): 4c now requires checking a prose fix's
claims against their cited sources, and the reply's verification line may name only current-session
checks. `skill-tester` evals 29 and 30 (iterations 13 and 14, Full Pipeline) scored 6/6 with and 6/6
without that change: fresh agents given a focused scenario already behave correctly. So the failure is
execution in long, context-heavy sessions, not missing instructions, and more prose is unlikely to fix it.

Open question: how to make the self-review hard to shortcut. Options to evaluate:
- A script that runs or records 4a-4e and prints a checklist the reply must cite.
- Making 4e's `record` part of a script step, so it cannot be skipped.
- A shorter 4b-4e that fits one read, or a mechanical check that the whole reference was read.

Related: #281 (step 8b's question can be silently skipped), #578 (the Phase 3 self-review design),
#640, #698. Found in PR #567.
