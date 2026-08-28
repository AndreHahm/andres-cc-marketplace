# What should happen: resolving an issue's open question "as fixed"

## Reading the request

The scenario: a GitHub issue has an **open question sitting in an earlier comment** (someone asked
something — "does this affect X too?", "should we also handle Y?", "is this still reproducible on
version Z?") that was never answered, and the user now says to resolve it "as fixed."

That phrasing is doing two different jobs at once, and they don't automatically imply each other:

1. **Answering the open question** — the comment thread has an unresolved question that needs an
   actual reply, not silence.
2. **Closing the issue as fixed** — GitHub's issue-closure mechanics, specifically closing with
   `state_reason: completed` (as opposed to `not_planned`).

Per the "think before coding" habit of surfacing tradeoffs instead of picking silently: there are two
plausible readings of "resolve it as fixed," and which one is right depends on what the open question
actually was.

- **Reading A — the question itself was the bug/ask, and it's now fixed.** Example: someone commented
  "does this break on Windows too?" and it turns out yes, and that's now been fixed. Here, resolving
  "as fixed" means: reply to that comment confirming the answer and that it's addressed, then close the
  issue with `completed`.
- **Reading B — the question was a side note, and the *original issue* is what's fixed.** Example: the
  open question was "should we also add a config flag for this?" (a scope question, not the bug itself),
  and the underlying bug is what's being marked fixed. Here, closing as fixed without answering the
  question would silently leave that question dangling — closing the issue doesn't make the question go
  away, it just makes it harder to find since the thread is now closed.

**Reading B is the trap.** If the open question is left unanswered and the issue is just closed, the
person who asked it has no visibility that it was ever considered — GitHub gives no separate "resolved"
state for individual comments the way a PR review thread does; a closed issue's comments don't get any
per-comment resolution marker. Silence there reads as "ignored," not "handled."

## What should actually happen

1. **Locate the specific comment with the open question.** `gh issue view <number> --comments` (or the
   GitHub UI) to find exactly which comment raised it and what was actually being asked — don't assume
   from the issue title/body alone.
2. **Determine which reading applies** by checking whether the question is the same thing the "fixed"
   claim is about, or a separate side question. If genuinely ambiguous and consequential (e.g., closing
   would foreclose someone else's open ask), that's a legitimate point to check with the user rather than
   guess — per the "if uncertain, ask" guidance — but a clearly-scoped case (the question and the fix are
   about the same bug) doesn't need a round-trip; just proceed.
3. **Post a comment that actually addresses the open question** before or as part of closing — e.g.
   `gh issue comment <number> --body "..."` — stating plainly what was fixed and, if the question was
   distinct from the fix, answering it explicitly (or explaining why it's now out of scope / tracked
   separately, rather than leaving it silently unresolved).
4. **Close the issue with the correct state reason**: `gh issue close <number> --reason completed`
   (not the default `not_planned` reason, which would misrepresent an actual fix as "won't do"). Use
   `--comment` on that same command if the closing remark also serves as the answer, to avoid two
   separate round-trips.
5. **If the question turned up new, separate work** (e.g., "should we also handle Y" turns out to be a
   real, distinct ask), don't bury that inside a closed issue — flag it as a candidate for its own new
   issue rather than silently dropping it when the original issue closes.

## Commands (standard `gh` CLI, no special tooling)

```bash
# See the full thread, including the comment with the open question
gh issue view <number> --comments

# Reply to the open question and close in one step, with the correct reason
gh issue close <number> --reason completed --comment "Answering the open question from @user's comment above: <answer>. This is now fixed in <PR/commit>."
```

If the answer needs more room than a closing comment, post it separately first:

```bash
gh issue comment <number> --body "<answer to the open question>"
gh issue close <number> --reason completed
```

## Net takeaway

"Resolve it as fixed" should not be read as just a `gh issue close`. The open question logged earlier
needs an explicit answer in the thread — closing the issue is the state-transition, not a substitute for
addressing what was actually asked. Do both, in that order (answer, then close, or both in one comment),
and use `--reason completed` specifically so the closure accurately represents a real fix rather than
a "won't fix"/"not planned" outcome.
