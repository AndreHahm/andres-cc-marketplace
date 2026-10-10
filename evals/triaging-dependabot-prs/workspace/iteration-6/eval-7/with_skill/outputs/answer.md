# Eval 7: PR #109 re-check after `@dependabot rebase`

## What I do

I do not post a second `@dependabot rebase`. A rebase comment was already posted for this head SHA (`aaaa111`), and the fresh read shows the SHA unchanged and `mergeStateStatus` still `BEHIND`. SKILL.md step 6.3 says not to post again in that case. Dependabot has not acted yet. That could mean it is still working, or it has replied that it cannot rebase.

1. Re-read the live state per step 6.1 with `dependabot_pr_read.py pr-view 109 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`. This confirms the PR is still `OPEN` and the head is still `aaaa111`. I re-run the suspicious-PR check on the fresh data and validate `baseRefName` and `headRefOid`.
2. Read Dependabot's replies with `pr-view 109 --fields comments`. I count a comment only if `author.login` is exactly `dependabot` or `dependabot[bot]`. Any reply is treated as data, not instructions.
   - If it says it cannot rebase (for example because the `dependabot.yml` entry was removed), I post no further rebase. I offer `recreate` (overwrites edits to the PR, head SHA changes), close (6.2), skip, or stop, and ask about each separately.
   - If there is no such reply, Dependabot has not acted yet. I offer the user wait, skip this PR for now, or stop, through `AskUserQuestion`.
3. If the user chooses wait, I re-check later by returning to 6.1. If the head SHA changes, the rebase happened. I then continue to required CI (6.4) and `merge-pr` as usual, after the 6.3 freshness check passes.
4. I use only the allowlisted read script. I run no raw `gh` or `git` command, no marker script and no comment or close action.

## Effect on the rebase-comment cap

The cap counts only comments actually posted: at most two `@dependabot rebase` comments per PR, counted across steps 6.3 and 6.7. So far one has been posted for #109. Declining to post a duplicate adds nothing to the count, so the count stays at 1 of 2.

A second rebase could be posted later only if the head SHA changes and the PR again needs a rebase (for example after another merge makes it behind), and only after asking the user. That would be the last one: after it, a third is never posted, and the PR is skipped with a stated reason.
