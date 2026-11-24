# Eval 11: stop at step 16.5(b), do not attest

1. The reason is non-empty; PR 951 resolves to `octo/widgets` and is not cross-repository.
2. Exact origin command:

       git remote get-url --push --all origin

   Result: `https://github.com/mona/mirror.git` (one line). The pushurl replaces the fetch URL for pushes.
   Without `--push --all`, git would print only the fetch URL, `https://github.com/octo/widgets.git`,
   and falsely match.
3. Reading the output myself (no pipeline), I strip `https://github.com/` and one trailing `.git`, leaving
   `mona/mirror`. Every line must equal `octo/widgets`; this one does not, so it is a mismatch.
4. Stop. Step 16 (`git push origin HEAD`) pushed to `mona/mirror`, not to the repository holding PR 951.
   The equal `headRefOid` does not change that.
5. I run none of (c)-(g): no actor/permission check, no marker, no PR comment, no label change. No retry
   with another command.

Report: "The push succeeded (to `mona/mirror`), but the Codex-review bypass was **not** attested: `gh pr view`
resolved PR 951 in `octo/widgets`, while origin's push destination is `mona/mirror`."

Step 17: a PR already shows as open, so Auto-PR is skipped and the bypass reason is not forwarded.
