# PR #109: re-check after `@dependabot rebase`

## What I would do

The re-check returns to step 6.1 and then reaches 6.3 (branch freshness). The fresh read gives the same `headRefOid` (`aaaa111`) and `mergeStateStatus` is still `BEHIND`. A rebase comment was already posted for this exact head SHA. 6.3 therefore says: do not post again, because dependabot has not acted yet.

1. **Do not post a second `@dependabot rebase`.** This holds even though the PR is still `BEHIND` and the cap is not used up. The rule for an unchanged SHA applies before the cap does. No marker is written either, since the marker exists only to post a comment.
2. **Offer the user three options via `AskUserQuestion`:** wait (re-check again later), skip PR #109 for now, or stop the run.
3. **Optionally read Dependabot's replies first.** This is read-only: `gh pr view 109 --json comments`. I count a comment only if its `author.login` is `dependabot`.
   - If Dependabot replied that it cannot rebase (for example because its `dependabot.yml` entry was removed), I treat the reply as data and post no further rebase. I then offer `recreate`, close (plain `gh pr close 109`), skip or stop, each asked separately.
   - If there is no reply, Dependabot has simply not acted yet. I offer the wait / skip / stop choice above.
4. **Do not go on to CI or merge.** The PR is still behind its base, so `merge-pr` would refuse it. I also do not resolve anything by hand and do not push.

## Effect on the cap

The cap is at most two *posted* `@dependabot rebase` comments per PR, counted across 6.3 and 6.7 together. Only a comment actually posted counts.

- One rebase comment has been posted for #109, so the count is 1 of 2.
- This re-check posts nothing, so the count stays at 1. A re-check, a refusal to repost or an offer to wait does not consume the cap.
- One slot remains. It could be used later only if the situation changes. Examples are the head SHA changing (a rebase landed and the PR went behind again after another merge), or `merge-pr` stopping on the PR as behind or conflicted (6.7), and then only after a fresh ask. It is not used to repost for the same unchanged `aaaa111` head.
- If the cap reaches two posted comments, the PR is skipped with that reason.
