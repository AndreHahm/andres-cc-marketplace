I did not Read/Grep/Glob any file under `plugins/git-kit/skills/cross-model-review/`, `.claude/skills/cross-model-review/`, or `plugins/codex-kit/`, and did not run `git log`/`git diff`/`git show` (or any other command) against this repository's actual history. Everything below is inferred generically from the task description, not from inspecting the real skill.

---

# Walkthrough: Preflight and the skill's own modified prompt file

## Caveat up front

I have not read the actual `cross-model-review` skill (that's off-limits for this exercise), so I don't know its exact phase names, variable names, or the literal shell/tool commands it issues. What follows is a reasoned, best-effort model of how a skill like this *would* need to behave, given:

- it's named "cross-model-review" and lives in `git-kit`, so its job is almost certainly to take the diff of a branch about to become a PR and hand it to a different model (plausibly via Codex, given the `codex-kit` plugin sitting alongside it) for an independent review;
- it ships a `prompts/review.md` file, which is almost certainly the template/persona text that gets assembled into the instructions sent to that other model — the task calls out a "fresh-eyes persona" inside it, which is a strong signal this file *is* the reviewer's system/persona prompt;
- a "Preflight" phase, by name, is where a skill like this would validate its environment and assemble everything it needs *before* actually dispatching the review — i.e., before the other model ever sees anything.

I'll flag every place I'm inferring rather than quoting, and note where I'm uncertain of exact syntax.

## 1. Why this scenario is special

Normally, `prompts/review.md` is just static skill content — it doesn't change from PR to PR, so Preflight can safely read it straight off disk (the working tree / `HEAD`) and use it as-is.

This case is different: the diff *being reviewed* is the diff that edits `prompts/review.md` itself, specifically the fresh-eyes persona. That creates a self-referential trust problem. If Preflight just does the naive thing — read the file off the current working tree — then the diff under review gets to rewrite the very instructions that govern how it's reviewed, in the same change that's being judged. A PR could, in principle, quietly soften or redirect the "fresh eyes" persona (e.g. tell the reviewing model to go easier, or to ignore certain classes of issues) and have that edited persona apply to reviewing itself. That's the kind of self-modifying-gate problem you'd want a careful Preflight to guard against, conceptually similar to why a security/permission gate shouldn't trust a file that the very change under review could have altered.

So the place this "matters" in Preflight is not diff computation in general — it's specifically the step where the skill decides *which version* of its own prompt/template files to load before building the instructions it will hand to the other model.

## 2. Where in Preflight this shows up

A reasonable Preflight sequence for a skill like this would look roughly like:

1. Confirm the reviewing tool/model is available (e.g. Codex CLI installed/authenticated).
2. Resolve `$BASE` — the branch/commit the PR is (or will be) merged into, e.g. `origin/main`, or a merge-base SHA computed from the current branch vs. the base branch.
3. Compute the diff range (`$BASE...HEAD` or similar) that will actually be sent for review.
4. **Load the skill's own review instructions/persona** (`prompts/review.md` and any sibling prompt files) to assemble what gets sent to the other model.
5. Dispatch the review with the assembled diff + instructions.

Step 4 is where this matters. If Preflight is written defensively, it will not simply read `prompts/review.md` off the working tree at this point — it will try to pin that file to the pre-diff baseline, i.e. the version of the file as it existed at `$BASE`, before the change under review was applied. That's the only way to guarantee the diff under review can't influence the criteria used to review it.

## 3. What command plausibly resolves it

The idiomatic way to read a specific path's content as of a specific ref, without touching the working tree, is `git show`:

```
git show $BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md
```

(`$BASE` here standing in for whatever ref Preflight resolved in step 2 above — could be a branch name like `origin/main`, or a merge-base SHA.)

I'm not certain this exact invocation is what the real skill uses — it could equally be done via a helper script, a `git diff --name-only` check combined with a conditional read, or something wrapped in the skill's own tooling rather than a raw `git show`. But `git show <ref>:<path>` is the standard, generically-correct way to ask "what did this file look like at this specific commit/ref," which is exactly what pinning the persona to the pre-diff baseline requires — so it's the most likely shape of the command even without confirming it directly.

## 4. What happens when that command fails because the file doesn't exist on `$BASE`

This is exactly the case described: the skill's *own first commit* introduces `prompts/review.md` (and the whole `cross-model-review` skill) and that commit hasn't merged yet, so `$BASE` — main, pre-merge — has no such path at all.

`git show <ref>:<path>` fails loudly in that situation. Git's behavior for a path that doesn't exist at the given ref is a non-zero exit (128) and a stderr message along the lines of:

```
fatal: path 'plugins/git-kit/skills/cross-model-review/prompts/review.md' does not exist in 'origin/main'
```

(Wording/exact phrasing may vary slightly by Git version, but "path does not exist in `<ref>`" plus a fatal/non-zero exit is the standard behavior for `git show ref:path` against a genuinely absent path — this isn't a guess about a specific skill's error handling, it's a property of `git show` itself.)

So whatever Preflight logic calls this command has to handle that failure explicitly — a bare `git show` failing here is an expected, first-run condition, not a corrupted repo or a bug. There are a few plausible ways a well-designed Preflight would handle it, in rough order of how likely I'd guess they are for a skill whose whole purpose is a trust-sensitive review gate:

- **Fall back to the working-tree/`HEAD` copy of the file, with the caveat surfaced.** If there is no baseline to pin against — because the file is brand-new on this branch — there is nothing to "protect" against self-modification; the only version of the persona that has ever existed *is* the one in this diff. In that case the sensible fallback is to use the current working-tree copy and (ideally) note in its output/log that no pre-diff baseline existed for this file, so a human reviewer knows the persona itself wasn't independently pinned this time.
- **Abort Preflight with an explicit error**, if the skill treats "can't establish a trusted baseline for my own review instructions" as a hard stop rather than something to silently work around. This would be the more conservative choice, especially for a security/trust-relevant gate — favoring "ask a human" over "guess and proceed."
- **Silently swallow the error and proceed with empty/default content** — this would be a bug if it happened, not a designed behavior, and I'd flag it as such if I saw it in the real code.

Without reading the actual skill I can't say which of these it actually implements, but given this repo's own stated conventions around gates that could be weakened by the very change they're gating (see the general principle that a new security/trust-relevant check should fail safe rather than fail open), the first or second option is far more likely than the third — and the task's framing ("this is the skill's own first, not-yet-merged commit") reads like it's specifically probing whether Preflight has a deliberate, non-crashing fallback for exactly this bootstrap case, rather than an unhandled `git show` failure propagating up as a raw script error.

## 5. Summary

- The self-referential risk (diff modifying the reviewer's own persona) surfaces in Preflight at the step where the skill loads its own `prompts/review.md` to build the instructions it hands to the other model — not at diff-computation or dispatch time.
- The mechanism that would resolve it is reading the file's pre-diff content via something like `git show $BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md`, rather than reading the working-tree copy directly — exact syntax not confirmed against the real skill.
- On the skill's own first commit, `$BASE` (pre-merge main) has no such path yet, so that command fails with a `fatal: path '...' does not exist in '<ref>'`-style error and non-zero exit — an expected bootstrap condition, not a corrupted-repo error.
- What the skill does next (fall back to `HEAD`/working tree with a caveat, abort with an explicit message, or something else) is implementation detail I can't confirm without reading the file, which is out of scope here; a fallback-to-working-tree-with-a-caveat or an explicit abort are the two behaviors that would make sense for a gate whose entire purpose is resisting exactly this kind of self-modification.
