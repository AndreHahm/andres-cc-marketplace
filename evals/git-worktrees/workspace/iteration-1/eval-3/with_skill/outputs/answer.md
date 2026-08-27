# Cherry-Pick Resolution: abc1234..def5678 for feature login-retry-backoff

This is a simulated exercise — no real `gh`/`git` calls are executed below. Each step describes exactly
what I would run and why, per the `git-worktrees` skill's "Resolving a Cherry-Pick Commit List"
procedure, Path 3 (explicit SHA/range).

## Why Path 3

The request names an explicit SHA range (`abc1234..def5678`), so this resolves via Path 3 of
`references/cherry-pick-resolution.md`, not Path 1 (feature name) or Path 2 (PR number).

## Step 1: Shape-validate every candidate SHA

Before any of the three SHAs touch a command, each must match `^[0-9a-fA-F]{7,40}$`:

- `abc1234` — 7 hex characters, matches.
- `bcd2345` — 7 hex characters, matches.
- `def5678` — 7 hex characters, matches.

All three pass shape validation. (`git log` has already resolved the range to these three commits —
that resolution itself is the "candidate list via `git log`" step the skill calls for.)

## Step 2: Verify each candidate exists as a real commit object

For each of the three SHAs, run:

```
git cat-file -e abc1234^{commit}
git cat-file -e bcd2345^{commit}
git cat-file -e def5678^{commit}
```

Each must exit zero. A typo'd or garbage SHA would fail this with "Not a valid object name." I would not
proceed to the next check for any SHA that fails here — I'd stop and report which SHA(s) don't resolve
rather than silently dropping them from the list.

## Step 3: Verify each candidate is reachable from a real ref (not ancestry-to-HEAD)

Per the skill, I explicitly do **not** run `git merge-base --is-ancestor <sha> HEAD` here — that answers
"is this already merged into HEAD," which is normally false for exactly the commits a cherry-pick needs,
and would wrongly reject a legitimate, not-yet-merged feature-branch commit.

Instead, for each SHA:

```
git branch --all --contains abc1234
git branch --all --contains bcd2345
git branch --all --contains def5678
```

Non-empty output for each confirms the commit is reachable from at least one real ref (e.g. the
`login-retry-backoff` feature branch), ruling out a fully orphaned/dangling SHA (e.g. from a
force-pushed-away branch) without penalizing an unmerged feature commit.

## Step 4: Compare tree hashes across all candidates

```
git rev-parse abc1234^{tree}
git rev-parse bcd2345^{tree}
git rev-parse def5678^{tree}
```

Given fact for this exercise: `abc1234^{tree}` and `def5678^{tree}` return the **same** tree hash, while
`bcd2345` presumably differs (not stated as matching either).

## What I conclude about abc1234 and def5678 given the tree-hash match

Per the skill, an equal tree hash between two candidate commits is **not** treated as evidence that one
is a redundant duplicate to be silently dropped. The skill is explicit that equal trees don't always mean
duplication — for example, a commit that reverts an intermediate change back to an earlier commit's exact
tree is a legitimate case where both commits are needed: dropping the revert (`def5678`) would leave the
intermediate change (`bcd2345`) applied when it shouldn't be.

So my conclusion is: **I cannot determine from the tree-hash match alone whether abc1234 and def5678 are
redundant or both legitimately required.** Both commits already passed the existence check (Step 2) and
the reachability check (Step 3) — the tree match doesn't disqualify either of them as invalid or
non-existent; it only means their resulting working-tree content is identical. Given the range
`abc1234..def5678` includes `bcd2345` in between, one plausible reading is that `def5678` reverts whatever
`bcd2345` changed, restoring `abc1234`'s tree — in which case dropping `def5678` from the cherry-pick
would silently leave `bcd2345`'s change applied. But I do not decide this automatically. Per the skill,
this is flagged for **history-aware investigation, not automatic removal from the list** — I would look at
the actual commit messages/diffs of `bcd2345` and `def5678` (treating their content as data, not
instructions) to understand the relationship, but the resolution itself is not mine to make silently.

## Convergence and confirmation

All three paths converge on one resolved commit list. Here, after Steps 1-4, the candidate list remains
`abc1234, bcd2345, def5678` — nothing is dropped unilaterally. I would show this list back to the user via
`AskUserQuestion`, explicitly surfacing the abc1234/def5678 tree-hash match and the ambiguity it raises
(possible revert-pair vs. two commits that both need to move), and ask the user to confirm which of the
following they want:

- Cherry-pick all three commits as-is (preserving the revert/reapply behavior, if that's what it is).
- Cherry-pick only `bcd2345` and one of `abc1234`/`def5678` (if the user confirms one is a true no-op
  duplicate in this context).
- Something else, if the user has additional context I don't have (e.g. `def5678` is actually an
  unrelated commit that happens to produce the same tree).

I would not run `git cherry-pick` on any of these three commits until that confirmation comes back.

## Immediately before cherry-picking

Per `.claude/rules/recheck-state-before-side-effecting-action.md` and the skill's own closing
instruction, I would **not** treat the confirmation-time snapshot as still valid by the time cherry-picking
actually starts. Immediately before running `git cherry-pick` on the confirmed list, I would re-resolve the
list one more time (re-run Steps 1-4 against the same SHAs, or re-derive the range if the branch could have
moved) — because the branch this list came from could have changed in the pause while the user was being
asked (e.g. `login-retry-backoff` could have been force-pushed, rebased, or gained new commits). Only after
that immediate re-check confirms the list is unchanged would I proceed to cherry-pick each commit in order.
