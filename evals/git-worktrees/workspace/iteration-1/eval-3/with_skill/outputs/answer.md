# Cherry-Pick Verification: `abc1234..def5678` for `login-retry-backoff`

**Simulated exercise — no `gh`/`git` commands are actually run.** Everything below is a description
of the commands I would run and why, per `git-worktrees`' "Resolving a Cherry-Pick Commit List"
section, Path 3 (explicit SHA/range).

## Why Path 3 applies

The request names an explicit SHA range (`abc1234..def5678`), not a feature-name search (Path 1) or
a PR number (Path 2). Path 3 requires resolving the candidate list via `git log`, then verifying it
before trusting it — never cherry-picking straight off a hand-typed or `git log`-resolved range.

## Step 1 — Resolve the candidate list

`git log --oneline abc1234..def5678` (or `abc1234^..def5678` if `abc1234` itself should be
included) resolves to three commits, as given:

```
abc1234
bcd2345
def5678
```

This list is provisional — it becomes the "resolved" list only after the verification steps below,
and even then only after the user confirms it.

## Step 2 — Reachability check on every candidate

For **each** of the three SHAs individually:

```
git merge-base --is-ancestor abc1234 HEAD
git merge-base --is-ancestor bcd2345 HEAD
git merge-base --is-ancestor def5678 HEAD
```

(substituting the actual target branch for `HEAD` if cherry-picking onto something other than the
current branch). This confirms each SHA is a real, reachable commit on the branch it's supposed to
come from — a typo'd or wrong-branch SHA fails this check instead of silently being cherry-picked.
I would not proceed past this step if any of the three failed.

I'd also use this same command (or `git branch --contains <sha>` / `git log --all --oneline
<sha>` grepped against the target branch's own history) to check whether **any of the three is
already an ancestor of the branch I'm cherry-picking onto** — i.e., already merged/applied under this
exact SHA. That's a distinct question from the tree-hash check in Step 3: this one is about SHA
identity, not content identity.

## Step 3 — Tree-hash comparison across all three candidates

```
git rev-parse abc1234^{tree}
git rev-parse bcd2345^{tree}
git rev-parse def5678^{tree}
```

**Given fact for this exercise:** `abc1234^{tree}` and `def5678^{tree}` return the same tree hash;
`bcd2345`'s tree is (by elimination) different from both.

## Step 4 — Follow-up diagnostics triggered by the tree-hash match

A tree-hash match between two *different* commit SHAs means their resulting working-tree content is
byte-identical, even though they're distinct commits (different parents/metadata/message). Per the
skill's own guidance, this is "a sign one of them is a no-op duplicate, not a distinct change that
still needs applying" — but it doesn't by itself say *which* one is redundant or *why*. Before
concluding anything, I would additionally run:

- `git diff abc1234 def5678` — expected to return empty, confirming the tree match isn't a hash
  collision artifact.
- `git show bcd2345 --stat` and `git diff abc1234 bcd2345` — to see what content change `bcd2345`
  actually introduces relative to `abc1234`.
- `git diff bcd2345 def5678` — to see whether `def5678` *reverts* exactly what `bcd2345` introduced
  (which is what a tree match on the endpoints would imply if `bcd2345`'s change is undone by the
  time you reach `def5678`), versus `def5678` being an unrelated, coincidentally-identical rebase
  replay of `abc1234`.
- `git show --stat` / `git log -1 --format='%an %ad %s'` on `abc1234` and `def5678` individually —
  comparing author, date, and message helps distinguish "genuine revert commit" from "rebase-replay
  duplicate of already-upstream content" from "accidental empty/no-op commit."
- Cross-check whether the *content* of `abc1234` (its tree) already exists reachable from the target
  branch under a **different** SHA (e.g., via `git log --all` search for that tree, or knowing it was
  previously cherry-picked/rebased in) — this is the "redundant, already-merged rebase-replay commit"
  case the skill explicitly calls out.

## Conclusion on `abc1234` and `def5678`

Given only the stated fact (identical tree hash, different commit SHAs), I can draw this much with
confidence, and no more:

- **`abc1234` and `def5678` produce the same final working-tree state.** Cherry-picking both is
  redundant from a content standpoint — applying both to the target branch would not net out to the
  full three-commit range's apparent intent unless one of two things is true, which Step 4's
  diagnostics are needed to distinguish:
  1. **`def5678` reverts `bcd2345`'s change**, meaning the net effect of the whole `abc1234..def5678`
     range is *zero* — the feature range as given nets out to no actual change at all. That's a red
     flag on the range boundaries themselves (wrong end SHA, an accidental revert commit swept into
     the range, or the user meant a different/earlier tip than `def5678`).
  2. **`def5678` is a rebase-replay duplicate** whose content already matches `abc1234` for reasons
     unrelated to `bcd2345` (e.g., `abc1234`'s content already landed upstream under a different SHA,
     and `def5678` is a re-application of that same state) — in which case one of the two endpoint
     commits is the actual no-op and should be dropped from the cherry-pick list, while `bcd2345`
     (whose tree differs) is very likely the one commit in the range that carries real, needed
     content.

- **I would not silently decide between these two readings, and I would not silently drop either SHA
  from the list.** The skill is explicit that "two different commits with the same tree hash produce
  the same working-tree result — a sign one of them is a no-op duplicate, not a distinct change that
  still needs applying," but determining *which* one is the duplicate (or whether the whole range's
  intent is broken) requires the Step 4 content inspection, and even after that inspection this is
  exactly the kind of resolved-list ambiguity the skill requires surfacing to the user rather than
  guessing.

## What I would present back to the user (before any cherry-pick runs)

A resolved-list confirmation, explicitly flagging the anomaly, roughly:

> Range `abc1234..def5678` resolves to three commits: `abc1234`, `bcd2345`, `def5678`. All three are
> reachable/valid. However, `abc1234` and `def5678` have identical tree hashes despite being
> different commits — meaning they produce the same working-tree result. This usually means one of
> them is redundant (e.g., `def5678` reverts `bcd2345`'s change, or `def5678`/`abc1234` duplicates
> content already present elsewhere). Before I cherry-pick anything, can you confirm: should I
> cherry-pick all three commits as-is, skip one of `abc1234`/`def5678` as redundant, or is the range
> itself wrong (e.g., a different intended tip)?

No `git cherry-pick` would run — for any of the three SHAs — until the user answers this and the
list is explicitly reconfirmed, per the skill's closing instruction that "all three paths converge on
one resolved commit list — show it back to the user for confirmation before any `git cherry-pick`
runs."
