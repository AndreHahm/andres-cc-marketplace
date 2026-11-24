# Eval 44: step 7(a), PR 946, REBASE
Command:

```
gh api repos/octo/widgets/pulls/946/commits --paginate --jq '.[] | select((.parents | length) > 1) | .sha' | wc -l
```

**What it reports:** `0` on stdout. Page 1 selected nothing and page 2 failed, so `wc -l` counts no lines. The pipeline's exit status is `wc`'s, 0, not gh's 1. The only trace of the failure is gh's HTTP 502 message on stderr.

**What the text says:** "If the count is zero, proceed with `REBASE` as configured". 7(a) has no rule for a failed request (7(c) has one, for the squash count only), so read literally it goes on to 7(b) and a rebase merge.

**What I do:** I do not treat this `0` as a count, since the 502 is visible on stderr and page 2 was never read. This is my judgment, not a rule in 7(a). I re-run the command once. If it works, I use its count: zero goes on to 7(b); non-zero gets the merge-or-squash `AskUserQuestion`. If it fails again, I stop, report that the merge-commit count could not be determined, and neither write the marker nor merge.

If a merge commit were missed anyway, GitHub would reject the rebase and 7(d)'s fallback would ask for another strategy; it never retries silently.
