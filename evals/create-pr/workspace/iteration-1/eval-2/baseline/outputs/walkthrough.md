# Baseline Dry-Run Walkthrough — create a PR for `feat/example-widget`

Context: on branch `feat/example-widget`, everything committed and pushed, no PR open, no issue
mentioned. This is a narration only — no Bash/git/gh/Skill/Agent tool calls were actually made.
Answers are based on standard git/GitHub CLI knowledge only (no specialized skill/methodology
assumed available).

---

## Part A — "create a PR for this" (no flags)

Steps I would narrate:
1. Confirm the branch is pushed and up to date with its remote (`git status`, `git rev-parse
   @{u}` conceptually) — already stated as true.
2. Run `gh pr create` (interactively or with `--title`/`--body`/`--fill`), optionally choosing
   draft vs. ready.
3. `gh pr create` opens the PR against the configured base branch.

**Does any independent/adversarial review of the diff happen before anything is pushed or the PR
is opened?**

With plain git + the standard `gh` CLI, no. Neither `git push` nor `gh pr create` runs any
automated adversarial/cross-model review step as part of its own execution — that's not a
capability either tool has natively. The only way a review would happen automatically is if the
repository's CI (GitHub Actions or similar) is configured to run one on `pull_request` or `push`
events — and that would happen server-side, *after* the push/PR-open, not before. Nothing in
plain git/gh blocks or gates the push/PR-creation on a review completing first.

**Does the manual review already run five minutes ago count, or does it need to happen again?**

Under plain git/gh semantics there is no formal "review gate" object that tracks whether a review
happened, so there's nothing to satisfy or re-satisfy — the question is somewhat moot in this
baseline flow. Practically: if a human (or the assistant, unprompted) eyeballed the diff five
minutes ago and nothing has changed since (no new commits), that manual look is still valid
information for the person deciding whether to open the PR — but it isn't recorded or enforced
anywhere by git/gh, so nothing in the tooling "remembers" it or requires it to be repeated. If any
new commits landed in between, the earlier review would no longer cover the current diff and
should be treated as stale.

---

## Part B — `create a PR for this, with --bypass-cross-model-review "already reviewed manually, low-risk docs change"`

`--bypass-cross-model-review` is not a flag that exists on the standard `gh pr create` command (or
on plain `git` push/commit tooling). Using it as shown would be passed straight to `gh`, which
would reject it as an unrecognized flag — something like:

```
unknown flag: --bypass-cross-model-review
```

**What changes?** Nothing behavioral — the command simply fails at argument-parsing time before
doing anything. No push happens as a result of this flag (push may have already happened
separately, per the scenario's premise that everything is already pushed), and no PR is created by
this invocation.

**Is anything posted to GitHub because of this flag?** No. The command errors out before `gh`
makes any API call, so nothing is posted, created, or modified on GitHub as a result of supplying
this flag.

---

## Part C — `create a PR for this, with --bypass-cross-model-review ""` (empty reason)

Same outcome as Part B, for the same reason: this flag isn't part of the standard `gh`/git
tooling, so the CLI would reject it as unrecognized before ever inspecting the value passed to it.
Whether the string argument is `"already reviewed manually, low-risk docs change"` or an empty
string `""` makes no difference — the failure happens at the flag-recognition stage, before any
argument value is evaluated. No PR is opened and nothing is posted to GitHub in this case either.

---

## Part D — Back in Part A's scenario: a review finding requires editing a file after the fact

Suppose (hypothetically, since Part A's baseline flow doesn't itself run a review) some review
step surfaces one finding, the user says to fix it, and the fix means editing a tracked file in
the working tree. At that point the diff has changed since anything last checked whether the tree
was clean.

**What happens between that edit and the eventual `git push`?**

Under standard git behavior:
- The edit is **not committed automatically**. `Edit`/file-write operations only change the
  working tree; git never auto-stages or auto-commits on its own.
- Running `git status` at this point would show the file as modified (unstaged), and `git push`
  would still only push whatever is already committed — the uncommitted fix would **not** be
  included in that push at all until it's staged and committed first.
- Standard/careful practice at this point is to stop and surface the uncommitted change rather
  than silently commit it: run `git status`/`git diff` to show what changed, propose a commit
  message, and ask the user to confirm before running `git add` + `git commit`. Only after an
  explicit commit would `git push` actually carry the fix to the remote.
- If `git push` were run before committing the fix, the fix would simply be absent from what's
  pushed — the remote branch and any open PR would still reflect the pre-fix diff, silently out of
  sync with the local working tree, until a commit + push happens.

So the short answer: the edit is left uncommitted by default; it requires an explicit `git add`
and `git commit` (with the user's confirmation on the message, as a matter of good practice) before
it would ever reach `git push` — it is not committed automatically, and nothing in plain git/gh
would silently fold it into a push that already happened or is about to happen.
