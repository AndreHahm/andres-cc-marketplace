# PR 931, step 2: stop, not merged

Nothing was actually run; this describes what I would do with the given data.

1. **Read the exit code.** `git-required-checks.py` exit `2` means the required-check state could not be determined. It is neither "all passing" (`0`) nor "a context is not passing" (`1`). Its message is data: branch protection could not be read. That is also not the `Branch not protected` 404, the only protection response that counts as "no classic protection".
2. **Do not fall back.** I do not use the all-passing `gh pr checks` output or read the all-SUCCESS `statusCheckRollup` by eye. Neither shows which contexts are required: a required context that never ran on this head can be absent from both, and they do not settle which app or source must report a context. I also do not rebuild the list by hand with raw `gh api` calls.
3. **The hurry changes nothing.** The status-check gate is blocking, and confirmation from the user does not replace it. `--bypass-codex-review` would not help either: it applies only when `Publish Codex policy result` is known to be the sole non-passing required context, and that is not known here.
4. **Stop the run at step 2.** No merge-rights check (step 3), bypass attestation (4), merge question (5), marker or `gh pr merge` (7). I make no change to branch protection or the PR.
5. **Report to the user:**

   > PR 931 is **not confirmed ready; I have not merged it.** Failed check: status checks, state undetermined. The required-check command exited 2: `cannot determine the required checks: branch protection could not be read`. `gh pr checks` and the rollup show only passing results, but they cannot prove that every required check ran, so I can't use them instead. I know of no failing check; the required list is simply unknown.
   >
   > The fastest way forward: find out why the protection read failed (the message does not say; possibilities include a transient API or network error, or a token that cannot read branch protection: check `gh auth status` and your access to the repository), fix that, then re-run `merge-pr 931`. If it was transient, a re-run may be enough.

6. **On the re-run**, start from fresh data (the head or base may have moved). Only exit `0`, plus the other five step-2 checks, lets it continue to step 3; exit `1` is reported by context name, state and reason; another exit `2` stops again.
