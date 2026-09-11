## Are the recorded gates still valid?

No — both recorded gates ("Python quality (ruff, ty, pytest)" and "Publish Codex policy result") are **invalid at the current HEAD** and need to be rerun before you merge.

Per `repository-gates`'s Invalidating Prior Evidence logic: gate evidence is bound to the exact SHA it covered. You supplied the recorded SHA (`a1b2c3d`) and your own git-kit read-back of the current HEAD (`e4f5a6b`) — those two values don't match, and this is a **new commit on the same branch**, not a rewrite. The rule for that case is explicit:

> A gate whose recorded SHA doesn't match the current SHA is invalid — report it as requiring a rerun, don't silently treat it as still passing.

That applies uniformly to both gates — there's no carve-out for "the commit was small" or "the commit didn't touch the checked code." The recorded evidence covered `a1b2c3d`; it says nothing about `e4f5a6b`. Since this repository's PR required checks are exactly these two ("Python quality (ruff, ty, pytest)" and "Publish Codex policy result"), the practical action is to let/ensure they re-run against `e4f5a6b` and get a fresh passing result recorded for that SHA before merge — the old passing result stays on record for `a1b2c3d`, but it doesn't carry forward.

One scoping note, for completeness: this assessment rests entirely on the two SHAs as you've reported them. `repository-gates` never independently determines "current HEAD" — it holds no `git rev-parse`/`git log` grant — so the validity call here is only as good as your own read-back being accurate and current at the moment you act on it.

## How would this differ under a force-push?

The end result — "the old evidence no longer covers HEAD, rerun before merging" — is the same either way. What changes is severity of *why*, and how the invalidation gets recorded:

- **New commit (your actual situation):** history is linear; `a1b2c3d` is still an ancestor of `e4f5a6b`. The gates just haven't run against the new tip yet. This is reported as "requires a rerun."
- **Force-push (rewritten history):** if `a1b2c3d` had instead been rewritten out of the branch's history entirely, **every** gate recorded against that old SHA is invalid — not just the two gates you named, but anything else recorded against it. The recording treatment is also different: the calling skill doesn't edit the old evidence entry in place. It appends a **new** `git-github-evidence` entry whose `supersedes` field names the invalidated old entry — the original entry is preserved as-is, never edited, per `FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record. So a force-push leaves an explicit audit trail (old entry → new entry that supersedes it), whereas a plain new commit is simply treated as "this SHA has no gate evidence yet."

Either way, nothing here lets you merge on the strength of the `a1b2c3d` evidence — rerun both required checks against `e4f5a6b` (or whatever HEAD is at merge time) first.
