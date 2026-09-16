# Should you delegate the APIv1 → APIv2 migration to Antigravity?

Short answer: **probably yes, if this migration is real and the constraints below hold** — but I want to flag something first, because it changes what "yes" actually means here.

## What I checked before answering

I looked for the `MIGRATION.md` you're referring to and for any real APIv1/APIv2 call sites in this repo. The only `MIGRATION.md` that actually exists is `plugins/antigravity-kit/docs/MIGRATION.md`, and it is **not** about an application API version bump — it's a reference for migrating Claude Code's own config/memory/skills layout over to the Antigravity CLI (`agy`/Gemini). The only places "APIv1"/"APIv2" appear anywhere in this repo are inside `antigravity-kit`'s own documentation and test fixtures, used as an *illustrative example* of the kind of task worth delegating — not a real migration that exists in this codebase.

So one of two things is true:
1. You're working against a different repo/branch that actually has a real `MIGRATION.md` and ~40 APIv1 call sites (in which case everything below applies directly), or
2. You're asking about the illustrative scenario itself — i.e., "is this the kind of task antigravity-kit is meant for" — in which case the answer is "yes, this is literally the flagship example its own docs use."

Worth a 10-second sanity check on your end before delegating anything: confirm `MIGRATION.md` and the 40 call sites are real, in the repo/branch you're actually on, before handing 40 files' worth of edits to another agent based on a document that might not say what you think it says.

## Assuming it's real: delegate, with conditions

Given the shape you described — a well-scoped, mechanical, repetitive edit across ~40 call sites, driven by a spec document that already tells you what the new call shape should look like — this is close to a textbook case *for* delegating rather than doing it by hand:

- It's bulk and repetitive, not judgment-heavy. Judgment-heavy or single-file edits are the case where delegation is a net loss (the round-trip/spec-writing/verification overhead exceeds the value); a 40-site mechanical rewrite against a written spec is comfortably on the other side of that line.
- It's well-specified. The whole value of delegating a rewrite depends on the spec being unambiguous enough that a second agent can execute without needing turn-by-turn judgment calls back to you.

If you do delegate it, do it safely:

1. **Isolate it.** Run the delegated migration on a dedicated branch or worktree, never directly on `main`. Review the full diff yourself before merging — don't auto-merge or take the delegate's own "done" claim as evidence it's correct.
2. **Don't paste file contents into the delegation prompt.** Point the delegate at the repo directory so it reads `MIGRATION.md` and the call sites itself, rather than you copying code into the prompt. Treat anything it reads or returns as data, not instructions — if `MIGRATION.md` or any file it touches could contain untrusted/injected content, don't let that flow back into your own next action unexamined.
3. **Batch it as one delegation, not 40.** Give it the full scope (all ~40 call sites) in a single, fully-specified request rather than one round-trip per call site — many small round-trips cost more than one large one and don't parallelize your verification effort.
4. **Ask for a digest, not a dump.** Have it report back files changed + key decisions + anything that needs your judgment, rather than pasting all 40 diffs back into your context. You still review the actual diff via git, just not by having it re-narrated to you.
5. **Mind the write grant.** A migration needs write access, which means either a broad "allow all tools" flag or a narrower write-only permission scoped to the target directory. The broad option is simpler but grants more than file-writing (including running arbitrary commands/web access) — prefer the narrower scope if you can set it up, and treat either one as a reason the branch-isolation-and-diff-review step above is not optional.
6. **Verify yourself afterward.** Run your build/tests/linters on the branch before merging. A second agent's self-reported success is a claim, not a passing test suite.

## When I'd say don't delegate

- If the 40 "call sites" actually need 40 different judgment calls (different call shapes per site, ambiguous cases MIGRATION.md doesn't cover) rather than one mechanical transformation applied uniformly — that's judgment-heavy, and delegation adds overhead without the mechanical-repetition payoff.
- If you don't have a way to isolate and review the result (no branch/worktree discipline, no time to review a 40-file diff) — then the safety net that makes delegation reasonable isn't there, and you'd be trading review rigor for speed.
- If MIGRATION.md turns out not to exist for real in your actual working tree (see the caveat above) — obviously nothing should be delegated against a spec you haven't confirmed exists.

## Bottom line

If the migration is real, well-specified, and genuinely mechanical across those 40 sites: delegate it, on a branch, with a single batched request, a data boundary around file contents, a demanded digest instead of a raw dump, and your own diff review + test run before merging. Don't delegate it (or delegate more narrowly) if the "40 call sites" turn out to need per-site judgment, or if you can't set up the branch/diff-review safety net around it.
