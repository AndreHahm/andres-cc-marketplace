# commit Testing Checklist

The full Testing & Validation checklist for `commit` and its verification history, extracted from SKILL.md
to keep SKILL.md under R13's line budget (R30). SKILL.md keeps the key pass criteria inline. The boxes stay
unchecked deliberately: none of the dry-run batteries was a real `git`/`gh` execution against a live PR.

**Verified live, 2026-08-11:** `commit` was invoked for real (`Skill(commit)`, not a raw `git commit`) roughly 5 times across that session's fix-batch commits, including the final commit of that session's second fix batch (`2160f56`) — the test-behavior-change check (now step 10, renumbered from step 9 by step 8's later targeted-repair insertion) fired correctly on every behavior-changing commit in that run. That live run confirmed the check fires and gates correctly in real use; it did not walk each item below individually, so the checkboxes stay unchecked pending a full manual pass — re-run this checklist (and check off what it confirms) after the next behavior-changing invocation, rather than treating this date as a permanent guarantee:

- [ ] The staged-diff scan actually fires — a change to `skills/*/SKILL.md`, `skills/*/references/*.md`, or `agents/*.md` content triggers the `AskUserQuestion`; an unrelated change (docs, scripts, config) does not
- [ ] The `AskUserQuestion` presents the options as written in step 10's prose (the testing-mechanism choices, plus "commit anyway" and "stop, test first")
- [ ] Step 10 sits correctly in sequence — fires after step 9's `git diff --cached`, before step 11's multiple-change analysis, without disrupting the flow
- [ ] Step 10's ask and step 14's separate confirm-before-commit ask don't read as a confusing back-to-back double prompt when both fire in the same run
- [ ] "Stop, test first" actually halts before any commit runs
- [ ] Step 11's "multiple concerns?" signal fires without `commit` attempting to perform the split itself — step 12 always redirects to the `standalone-commits` skill rather than re-deriving a split
- [ ] Generated commit messages never contain a local-machine-specific path, terminal-session symptom description, or session context — only content a reader of the shared repo history would understand
- [ ] Generated commit messages never contain a literal bot-trigger mention (e.g. `@codex review`,
      `@codex full review`), even when the diff itself is about a bot's own trigger-phrase syntax
      (e.g. adding `@codex full review` recognition to a workflow) — the phrase is described in
      prose instead of reproduced literally; an ordinary `@username`/`@team` mention notifying a
      human collaborator is not affected by this check
- [ ] A request to commit while on `main`/`master` with nothing staged yet points at `starting-work`; step 3's own branch-creation fallback only fires for someone already mid-edit
- [ ] When invoked as a nested dependency from `create-pr`'s Pre-flight Checks (told not to push on that run's behalf), step 16 always skips entirely — including its own push-confirmation `AskUserQuestion`, which is never asked and then overridden — regardless of `--push` or `commit_auto_push`; step 17's Auto-PR skip always applies together with it in that same case, never independently
- [ ] Step 6's staging never composes a `git add <filename>` string from a working-tree filename —
      partial-staging always goes through `git-stage-selected-files.sh --list` and then
      `git-stage-selected-files.sh <index...>`, passing only plain digits back, never the filename itself
- [ ] `git-stage-selected-files.sh` is committed with the executable bit set (`100755`, not `100644`) —
      on a fresh POSIX checkout, a non-executable script invoked by direct path (as step 6 does)
      fails with `Permission denied` (exit 126) before the user ever sees the candidate list (found
      by Codex's automated PR review, 2026-08-28: this repo's `core.fileMode=false` default let the
      original commit ship non-executable without any local signal, since the working-tree file
      still showed as executable regardless of what mode git actually recorded)
- [ ] Staging by index always resolves against the exact snapshot `--list` produced, never a fresh
      re-scan of `git status` at staging time — a working-tree change between the two calls must
      never silently resolve the same index to a different file (found independently by this
      session's own pre-push `cross-model-review` and by CodeRabbit's automated PR review,
      2026-08-28)
- [ ] `--list` enumerates an untracked directory's individual files, never the directory as one
      collapsed candidate — selecting one numbered entry must never silently stage more than the
      one file it displayed (found by Codex's automated PR review, 2026-08-28: `--untracked-files=all`
      is required, since the default collapses a wholly-untracked directory to one `?? dirname/` entry)
- [ ] Step 16 always pushes with `git push origin HEAD` (`git push -u origin HEAD` when there's no
      upstream) — never a branch name typed or interpolated into the push command, including one
      freshly resolved via `git rev-parse` immediately beforehand
- [ ] Step 13.5 fires before step 14's confirm ask, is a no-op without `.commitlintrc.cjs`/
      `.github/commitlint-tools/package.json`, and is skipped under `--no-verify` (same as step 7.5)
- [ ] Exit 2 (pnpm missing or toolchain install failed) is always an infrastructure skip — reported
      plainly, proceeds like a clean pass — never routed through exit 1's revise-or-ask branch
- [ ] `git-lint-commit-message.sh` is committed with the executable bit set (`100755`) — this repo's
      `core.fileMode=false` silently downgraded it to `100644` on first `git add` once (caught here
      before commit; see `git-stage-selected-files.sh`'s own 2026-08-28 incident above)
- [ ] A body/footer line over 100 characters (exit 1) is rewrapped and re-checked once; a non-wrapping
      rule (e.g. `type-enum`, `subject-case`) surfaces the exact rule name and asks instead
- [ ] The config/manifest/lockfile the check runs against always come from `origin/<default-branch>`,
      never the checked-out working tree — the install itself lives under `.git/`, never touching the
      repo's own tracked `.github/commitlint-tools/package.json`/`pnpm-lock.yaml` as a side effect
- [ ] Step 7.5's `git-lint-staged-python.sh` always positively confirms full-staging via `git status
      --porcelain` per staged `.py` path before auto-fixing it — a path that isn't confirmed fully
      staged always skips that file's auto-fix rather than risking a blanket `git add` pulling unstaged
      hunks into the commit (found by Codex's automated PR review, 2026-08-16: the original version had
      no such check; the script-based rewrite closed a follow-on command-injection finding from a later
      `security-reviewer` pass on the same step)
- [ ] A skipped partially-staged file is always reported by name, never silently dropped — and is still
      included in the `ty check` pass, which only reads
- [ ] Step 16.5 only ever fires when `--bypass-codex-review "<reason>"` was given AND step 16 actually pushed — never on a nested `create-pr`-suppressed run, never when the user declined to push, never with an empty/missing reason
- [ ] Step 16.5(b) finding no open PR always defers to step 17 rather than attempting to attest against nothing — and step 17 always forwards the deferred flag+reason verbatim to whichever `Skill(create-pr)` call it goes on to make
- [ ] If step 17 never ends up creating a PR (one was already open, or the user declined), a deferred step-16.5 bypass request is always reported as having had no effect this run — never silently dropped
- [ ] Step 16.5(c-g)'s shared protocol (step 4) always re-applies (remove then re-add) the label when it's already present on the PR from a prior round, rather than a plain `--add-label` that GitHub silently no-ops and never re-triggers `publish` — this is the primary case this step exists for
- [ ] Step 16.5(c-g)'s shared protocol never interpolates the reason text directly into a shell string — the reason is written to a file via `Write` and read back with `jq -n --rawfile`, and only ever after the bot-trigger-mention check (step 1) passes
- [ ] Step 16.5(c-g)'s shared protocol never polls for the re-triggered check's completion — it reports the attestation was posted and returns, unlike `merge-pr`'s own version of this protocol
- [ ] Step 16.5(c-g)'s shared protocol finding insufficient actor permission always stops before marker construction/posting/labeling — never posts a comment or touches the label — and reports that the push already succeeded and only the attestation was skipped, never that the whole run failed

  All 7 boxes above stay unchecked deliberately, the same convention the 2026-08-11 entry states for the earlier test-behavior-change checklist: the 2026-09-21 dry-run eval battery (`evals/commit/`, 36/36 assertions across 8 scenarios, see `references/staging-fix-verification-log.md`'s own "Step 16.5" entry) confirmed each scenario's documented procedure is correct, but none of it was a real `git`/`gh` execution against a live PR — check these off only after a live invocation.
