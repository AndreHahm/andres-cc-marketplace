CONFIRMATION: I did not read any file under `plugins/git-kit/skills/cross-model-review/`, `.claude/skills/cross-model-review/`, or `plugins/codex-kit/` in this repository, and I did not run `git log`/`git diff`/`git show` (or any other command) against this repo's real history. Everything below is reasoned generically from the task description and general knowledge of how a diff-reviewing tool with a "Preflight" stage typically has to be built — it is analysis/inference, not a report of verified file contents.

# Walkthrough: self-modifying prompt file during Preflight

## Restating the scenario

- There's a skill, "cross-model-review," whose job (per its name and the task description) is to hand a diff — the set of changes on a branch that's about to become a PR — to a *different* model for review ("cross-model").
- The skill has a "Preflight" stage, which by convention in this kind of tool is the setup phase that runs before the actual review call: resolving the base branch (`$BASE`), computing the diff, and assembling whatever context/instructions get sent to the reviewing model.
- One of the assets a Preflight stage for a prompt-driven review tool almost certainly needs is the review *prompt itself* — here, `plugins/git-kit/skills/cross-model-review/prompts/review.md`, described as containing (among other things) a "fresh-eyes persona" for the reviewing model.
- The twist: the diff being reviewed in this run **is itself a change to that exact prompt file** — it adds a line to the fresh-eyes persona. So the artifact Preflight needs to load (the reviewer's own instructions) is *also* one of the files under review.
- Further twist: this is the skill's own first commit, not yet merged — so the file `prompts/review.md` doesn't exist at all on `$BASE`, only in the working tree / on the feature branch.

## Step 1 — Why this matters at all: a self-reference problem

Any tool that (a) reads a prompt/config file from the repo to construct its own instructions, and (b) is being asked to review a diff that can touch arbitrary files in that same repo, has a structural hazard: the diff under review can rewrite the reviewer's own instructions. This is the same class of problem as a compiler whose source is compiled by itself, or a linter whose own config is part of the changeset it's linting.

For a review tool specifically, this hazard has a security/integrity flavor, not just a cosmetic one: if Preflight naively reads the prompt file from the current working tree (i.e., "whatever is checked out right now, diff included"), then a malicious or careless diff could alter the reviewer persona to something that suppresses criticism, before the reviewer ever runs. A Preflight stage that's been designed with this in mind would therefore want to pin the reviewer's instructions to a *trusted, pre-diff* copy of the prompt — i.e., the version that existed on `$BASE`, before the branch's changes — rather than blindly using the working tree's version.

That's the crux of "where this matters": it's not merely that the diff happens to touch a file the skill also reads — it's that the file it reads is the one thing standing between "the reviewer's instructions are trustworthy" and "the diff can rewrite its own reviewer." A careful Preflight has to make a deliberate choice here, and that choice is almost certainly implemented as an explicit step (something like "load base-branch copy of the review prompt, not working-tree copy") rather than an implicit side effect of just `cat`-ing a file off disk.

## Step 2 — What command most plausibly resolves it

Given that framing, the natural, idiomatic way to fetch a specific file's content *as of a specific ref* in git — without checking that ref out, without touching the working tree — is:

```
git show <BASE>:plugins/git-kit/skills/cross-model-review/prompts/review.md
```

(or the equivalent plumbing form, `git cat-file -p <BASE>:path/to/file`). This is the standard idiom for "give me file X's content on commit/branch Y" and is what I'd expect a Preflight step describing itself as something like "load the trusted review prompt from the base branch" to actually invoke. `$BASE` here is whatever ref the skill has already resolved as the PR's target/base (e.g., `origin/main`, or a merge-base commit) — presumably established by an earlier Preflight step before this one runs, since you need to know `$BASE` before you can ask git for a file's content on it.

The reason this specific command shape matters for the failure question below: `git show <ref>:<path>` requires that `<path>` exist as a blob in the tree at `<ref>`. It is not a "diff-aware" or "fall back gracefully" operation by default — it's a direct tree lookup.

## Step 3 — What happens when the file doesn't exist on `$BASE`

This is exactly the situation described: `prompts/review.md` (or at least this particular file) was introduced on the feature branch and has never been merged into `$BASE`. So the tree at `$BASE` has no blob at that path.

Running `git show $BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md` against a `$BASE` where that path doesn't exist fails outright:

- Exit code: non-zero (git's conventional 128 for this class of fatal error).
- Stderr message along the lines of:
  `fatal: path 'plugins/git-kit/skills/cross-model-review/prompts/review.md' does not exist in '<BASE>'`

Critically, this is a *different* failure mode from "the file exists on both sides but its content differs" (which is the normal, expected case a self-modifying-prompt guard is built for). Here there is no old copy to fall back to at all — the file is wholly new on the branch. Any Preflight logic that assumes "fetch base copy, and if it differs from working tree, warn or use base" implicitly assumes the base copy *exists*. A first-commit/not-yet-merged scenario breaks that assumption at the lookup step, before any diffing or warning logic even gets a chance to run.

## Step 4 — Downstream consequences of that failure

Two broad ways this plays out, depending on how defensively Preflight was written (I'm speculating here since I haven't read the actual implementation):

1. **Unhandled / propagated failure.** If the `git show $BASE:...` call's non-zero exit isn't specifically caught and interpreted, the Preflight step aborts, and depending on how the skill is orchestrated (shell script with `set -e`, or an agent step that treats a failed shell command as a hard stop), the entire skill invocation could fail before ever reaching the actual cross-model review call. From a user's point of view this would look like the skill just breaking on its own PR, with a git error message that doesn't obviously explain "you're trying to review the skill's own first commit."

2. **Handled fallback (the more robust design).** A Preflight step that anticipated this exact bootstrapping case would catch the specific "path does not exist at ref" failure and treat it as equivalent to "there is no trusted base version to protect, because this content is brand new" — and fall back to using the working-tree version of `review.md` (i.e., the version with the diff already applied) as the reviewer's own instructions, likely with a note/warning surfaced that the self-referential safeguard couldn't apply this run because the file is new. This is the sensible behavior for exactly the case named in the task: a skill's own first, not-yet-merged commit, where "protect against the diff altering pre-existing trusted instructions" doesn't apply because there *is* no pre-existing version to protect.

Since I have not inspected the actual `SKILL.md`/Preflight implementation (per the constraint on this task), I can't say with certainty which of these two behaviors the real skill exhibits — only that the second is the behavior a careful implementation would want, and the first is the generic failure mode you get if that specific edge case wasn't special-cased.

## Summary

- **Where it matters:** the Preflight step that loads the review prompt (`prompts/review.md`) to build the reviewing model's persona/instructions — specifically the moment it has to decide whether to trust the working-tree copy (which the diff under review can alter) or pin to a pre-diff, base-branch copy, given that this run's diff modifies that very file.
- **What command resolves it:** a git ref:path lookup — `git show $BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md` (or the `git cat-file -p` equivalent) — to fetch the trusted, pre-change version of the prompt without touching the working tree.
- **What happens on failure (file absent on `$BASE`):** the lookup fails fatally — non-zero exit, `fatal: path '...' does not exist in '<BASE>'` — because this is the skill's first commit and the file has never existed on `$BASE` at all, not merely differed. Without explicit handling of that specific failure, Preflight (and thus the whole skill run) would abort before reaching the review call; a defensively-written Preflight would instead treat "path does not exist at base" as "nothing to protect against — fall back to the working-tree copy" and proceed using the new prompt content (the one that already includes the added fresh-eyes-persona line).
