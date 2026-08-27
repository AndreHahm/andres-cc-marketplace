# Cherry-pick "retry logic" — ambiguous match, next step

**Simulated exercise — no real `gh`/`git` calls made.** This describes exactly what I would do.

## What happened

The request was a feature-name-only cherry-pick ("cherry-pick the feature 'retry logic'"), which
`git-worktrees`' "Resolving a Cherry-Pick Commit List" section classifies as **Path 1: by
feature/skill name alone**. Path 1's procedure is:

1. Search `git log --all --oneline --grep="<feature>"` and
   `gh pr list --search "<feature>" --state merged` for candidates.
2. **If more than one plausible match turns up (or none at all), stop and ask the user to narrow it
   down (a PR number or SHA range) — never guess which one they mean.**

Both searches came back with two different, unrelated merged PRs that each plausibly match the name
"retry logic":

- **PR #40** — "add retry logic to the HTTP client"
- **PR #61** — "retry logic for the queue worker"

These are not duplicates or the same change reaching two branches — they're two genuinely different
features that happen to share a generic name. There is no way to tell from the name alone which one
the user meant, or whether they actually want both.

## Decision: don't pick one, don't cherry-pick both — ask

I do **not**:
- Silently pick one PR because it looks "more likely" (e.g. lower number, alphabetically first, or
  matching some assumed context) — that's exactly the guessing Path 1 explicitly forbids.
- Cherry-pick from both PRs on the assumption "retry logic" might mean either/all of it — that would
  apply an unrelated feature (queue-worker retry logic, or HTTP-client retry logic) the user never
  asked for, which is a bigger mistake than doing nothing. `resolving-merge-conflicts`/cherry-pick
  execution assumes a *confirmed, correct* list going in; fabricating a "combined" list to cover both
  possibilities isn't a confirmed list, it's a guess dressed up as coverage.

Instead, per Path 1's explicit stop condition ("more than one plausible match... stop and ask the
user to narrow it down (a PR number or SHA range) rather than guessing which one they mean"), I stop
and ask the user directly. Concretely, I would surface something like:

> Two different, unrelated merged PRs both plausibly match "retry logic":
> - **PR #40** — add retry logic to the HTTP client
> - **PR #61** — retry logic for the queue worker
>
> Which one did you mean — or do you want both cherry-picked? Please confirm a PR number (or give me
> a specific SHA range) so I resolve the exact commit list from GitHub's own record instead of
> guessing.

This is an `AskUserQuestion`-style clarification, not a further round of speculative searching.

## What happens after the user answers

Once the user names a PR number (say #40), the request converts to **Path 2: by PR number**, and I
would resolve the *authoritative* commit list from GitHub's own record — `gh pr view 40 --json
commits` (or `gh api repos/{owner}/{repo}/pulls/40/commits`) — never a hand-typed or remembered list
reconstructed from the earlier `git log`/`gh pr list` search output. If the user says "both," I'd
repeat that same PR-number resolution independently for #40 and #61, producing two separate resolved
commit lists.

Either way, before any `git cherry-pick` runs, the resolved list(s) get shown back to the user for
confirmation — the skill is explicit that all three resolution paths "converge on one resolved commit
list — show it back to the user for confirmation before any `git cherry-pick` runs." Only after that
confirmation would Strategy C's actual cherry-pick execution (`git cherry-pick <commit>` per commit,
or `--no-commit` if squashing/reviewing first) proceed.

## Summary

| Question | Answer |
|---|---|
| Pick one arbitrarily? | No — guessing is explicitly disallowed by Path 1. |
| Cherry-pick from both without asking? | No — would apply an unrequested feature; not a confirmed list. |
| What instead? | Stop, present both candidates with their PR numbers/descriptions, and ask the user to pick one, name both, or give a SHA range. |
| Next step once answered | Resolve the authoritative commit list via `gh pr view <N> --json commits` (Path 2), confirm it with the user, then cherry-pick. |
