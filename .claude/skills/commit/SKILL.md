---
name: commit
description: >-
  Create well-formatted git commits with conventional commit messages — staging review, sensitive-file
  detection, and message confirmation before running `git commit`. Use when committing changes, running
  `/commit`, asked to "commit this", "create a commit", "commit and push", or amending the last commit
  with `--amend`. Shapes and executes a single commit's message; for deciding whether to split a diff
  into multiple commits, see standalone-commits instead.
argument-hint: Optional flags (--no-verify, --amend, --push) followed by an optional commit message
model: haiku
allowed-tools: Bash(git status:*), Bash(git add:*), Bash(git restore --staged:*), Bash(git diff:*), Bash(git commit:*), Bash(git branch:*), Bash(git checkout:*), Bash(git push -u origin:*), Bash(git push origin:*), Bash(git ls-files:*), Bash(gh pr view:*), Bash(pnpm lint:*), Bash(npm run lint:*), Bash(yarn lint:*), Bash(bun lint:*), Bash(uv run python -m scripts.marketplace_ci:*), Bash(uv run ruff format:*), Bash(uv run ruff check:*), Bash(uv run ty check:*), Bash(${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh:*), Bash(${CLAUDE_PLUGIN_ROOT}/scripts/scan-staged-files.sh:*), Read, Skill(git-kit:create-pr)
---

# Claude Command: Commit

Your job is to create well-formatted commits with conventional commit messages.

## When to Use

Creating a commit for currently staged (or about-to-be-staged) changes — conventional commit message
formatting, sensitive-file scanning, staging confirmation, and optional push/PR follow-through. Triggers:
`/commit`, "commit this", "commit and push", "amend the last commit", or any request to turn staged/
unstaged changes into a properly formatted commit.

## When NOT to Use

- **Deciding whether to split a diff into multiple commits, ordering multi-file changes into
  dependency-ordered waves, or picking which of several pending changes to stage first** — that's
  `standalone-commits`'s job (run the `standalone-commits` skill). `commit` only shapes and executes
  the message for whatever is already staged; step 11 below is a lightweight "multiple concerns?"
  signal, not the actual splitting procedure.
- **Creating a fresh branch before any changes exist** — that's `starting-work`
  (run the `starting-work` skill), which also handles the worktree-vs-branch choice and main-sync that
  step 3 below doesn't. Step 3's branch check stays as a fallback for someone already mid-edit on
  `main`/`master`; it isn't a substitute for deliberately starting new work through `starting-work`.

## Flags

Parse `$ARGUMENTS` for these flags (each may appear alone or combined with the others, in any order,
optionally followed by a commit message to use instead of generating one):

| Flag | Effect |
|------|--------|
| `--no-verify` | Skip pre-commit checks (lint) |
| `--amend` | Amend the last commit instead of creating a new one |
| `--push` | Push to remote after a successful commit — except when `commit` was invoked as a nested dependency from `create-pr`'s Pre-flight Checks with instructions not to push, where step 16 skips entirely regardless of this flag (see step 16 below) |

## Settings

Staging, commit confirmation, and message-length targets are read from a settings file, resolved in this order:

1. `.claude/git-kit.local.json` in the project root, if it exists (gitignored, user-local — create it with `/create-git-kit-local-json`, which seeds it from the defaults below).
2. For any field that file doesn't set (or if it doesn't exist at all), fall back to the git-tracked defaults at `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json` (shared across git-kit skills, not commit-specific).

| Setting | Default | Meaning |
|---|---|---|
| `commit_confirm_before_commit` | `true` | Show the generated message and ask before running `git commit` |
| `commit_auto_stage` | `false` | When nothing is staged, ask what to stage instead of auto-staging everything |
| `commit_first_line_soft_limit` | `50` | Recommended max length for the first line |
| `commit_first_line_hard_limit` | `72` | Hard max length for the first line |
| `commit_body_max_lines` | `5` | Recommended max lines for the body, when one is included |
| `commit_auto_push` | `false` | After a successful commit, push without asking |
| `push_auto_pr` | `false` | After a successful push (via `--push` or `commit_auto_push`), create a PR without asking (if none is already open) |

**Security note:** `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, and `push_auto_pr` all weaken safety or trigger further automation when enabled, so they're only honored from `.claude/git-kit.local.json` when that file is untracked by git (see Instructions step 2). A copy committed into the repo — whether accidentally or by an attacker — can never silently disable the confirmation gate, enable auto-staging, or trigger unattended pushes/PR creation; the skill falls back to the git-tracked `git-kit.settings.json` defaults for those fields instead.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Read settings**: Read the git-tracked defaults from `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json` (`enabled`, `commit_confirm_before_commit`, `commit_auto_stage`, `commit_first_line_soft_limit`, `commit_first_line_hard_limit`, `commit_body_max_lines`, `commit_auto_push`, `push_auto_pr`). Then check for `.claude/git-kit.local.json` in the project root — if it exists and its own `enabled` isn't `false`, its fields override the corresponding default for any field it sets.
2. **Trust check (security)**: If `.claude/git-kit.local.json` exists and set `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, or `push_auto_pr`, check whether the file is tracked by git: `git ls-files --error-unmatch .claude/git-kit.local.json`. A git-tracked copy could have been committed by anyone with repo write access — including an attacker aiming to silently weaken safety gates for the next person who runs `/commit`. So if the file IS tracked (command exits 0), discard its values for those four fields and use the `git-kit.settings.json` defaults instead, regardless of what the local file says. Only an untracked (genuinely local, gitignored) `.claude/git-kit.local.json` may override any of these gates. The length-limit and `pr_merge_type`/`merge_auto_delete_branch`-style fields aren't security-relevant and may be honored either way, tracked or not.
3. **Branch check**: Checks if current branch is `master` or `main`. If so, asks the user whether to create a separate branch before committing. If user confirms a new branch is needed, run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-branch-create commit` immediately before creating the branch — this writes the marker git-kit's branch-creation guard requires; it must be written right before `git checkout -b`, not earlier. Then create the branch using the pattern `<type>/<description>` (e.g., `feature/add-new-command`). This is a fallback for someone already mid-edit on `main`/`master` — if no changes exist yet, point at the `starting-work` skill instead, which also syncs `main` and asks about a worktree.
4. Unless specified with `--no-verify`, automatically runs pre-commit checks depending on the project
   language. For a project-wide tool that doesn't need to know what's staged yet (`pnpm lint`/
   `npm run lint`/`yarn lint`/`bun lint` or similar, depending on what the project's own tooling —
   lockfile, config — indicates), run it here. **This repository's own Python/`ruff` check is
   staged-file-aware and runs later, at step 7.5, once staging is actually settled** — see that step
   rather than duplicating it here.
5. Checks which files are staged with `git status`
6. **Staging**: If 0 files are staged — when `commit_auto_stage` is `true`, stage everything with `git add -A`; otherwise show the unstaged files and ask the user what to stage (or whether `git add -A` is appropriate). **Never auto-stage without confirmation unless `commit_auto_stage` is explicitly enabled.**
7. **Check for sensitive files** among the now-staged files: run
   `"${CLAUDE_PLUGIN_ROOT}/scripts/scan-staged-files.sh"` with the staged file list to check them against
   the fixed sensitive-filename patterns (`.env`/`.env.*`, `*secret*`/`*credential*`/`*.key`/`*.pem`,
   `*password*`/`*token*`, SSH/cloud private keys `id_rsa`/`id_ed25519`/`id_ecdsa`/`id_dsa`/
   `service-account.json`/`*.p12`/`*.pfx`/`*.jks`, and credential config files `.npmrc`/`.pgpass`/
   `.netrc`). If any are flagged, warn the user and unstage them (`git restore --staged <file>`) before
   continuing.

   **Limitation:** this check matches staged *filenames* only — it does not inspect staged diff content
   for embedded credential-shaped strings (API keys, tokens) in a file whose name doesn't match one of
   these patterns. A key pasted into an otherwise-unflagged file's content is not caught by this step.
7.5. **Lint/format/type-check staged Python files** (this repository only, unless `--no-verify` was
   given — a no-op if no staged path ends in `.py`): mirrors CI's own "Python quality" gate
   (`docs/ci.md`: `ruff format --check`, `ruff check`, `ty check`) as closely as a local pre-commit step
   can:
   - **Skip any staged `.py` path that's only partially staged** — check `git diff --name-only -- <path>`
     (the *unstaged* diff) for each staged `.py` path first; if it's non-empty, that file has unstaged
     hunks alongside its staged ones. `ruff format`/`ruff check --fix` operate on the whole working-tree
     file, not just the staged content, and a blanket `git add <path>` afterward would silently pull the
     unstaged hunks into this commit too — overriding the user's own deliberate staging choice (a
     `AGENTS.md`/`CLAUDE.md` "Surgical Changes" violation, not just a style nit). Report each skipped file
     by name so it's never a silent gap; auto-fix only the remaining fully-staged `.py` paths.
   - For each fully-staged `.py` path: run `uv run ruff format <path>` then
     `uv run ruff check --fix <path>` — auto-fixing formatting and auto-fixable lint violations in place —
     then re-stage it (`git add <path>`) so the commit captures the fixed content. Runs before step 8 so
     that if a fixed file is also a canonical mirror source, step 8's sync picks up the corrected content,
     not the pre-fix version. Report which files, if any, were modified by the auto-fix.
   - Run `uv run ty check <staged .py paths>` (including any skipped-from-autofix partially-staged ones —
     `ty` only reads, it never risks clobbering unstaged content) — type errors aren't auto-fixable, so
     this only checks.
   - If either `ruff check` or `ty check` still reports a violation, surface it and ask (mirroring step
     10's pattern) whether to proceed anyway or stop and fix manually — never silently commit code that
     still fails either check.
   - If `ruff`/`ty`/`uv` aren't available, warn once and continue rather than blocking the commit.
   This step exists because a ruff-format violation reached `main` and needed a reactive follow-up fix
   (`1f4baa0`) — it's what should have caught that locally before the first commit.
8. **Marketplace CI targeted repair** (this repository only — a no-op if `scripts/marketplace_ci/` and
   `.claude/marketplace-sync.json` don't exist): if any staged file is a canonical `plugins/<name>/...`
   source for a registered plugin mirror, or a registered `.claude/skills/<name>/...`/
   `.claude/agents/<name>.md` export source, run
   `uv run python -m scripts.marketplace_ci sync-plugin-mirrors` and
   `uv run python -m scripts.marketplace_ci convert-codex-exports` — never hand-edit a generated
   `.claude`/`.agents`/`.codex` destination directly. Then run `git status --porcelain` again and stage
   only the generated files whose canonical source is among the paths already staged in this commit;
   leave any other file those commands happened to repair (drift unrelated to this commit) on disk,
   unstaged. Finally run `uv run python -m scripts.marketplace_ci check-all --staged` — **this runs even
   under `--no-verify`**, since `--no-verify` only skips `pnpm lint`-style checks (step 4), not marketplace
   parity. If it fails, report the specific mismatch and stop; do not commit an inconsistent mirror/export.
9. Performs a `git diff --cached` to understand what changes are being committed
10. **Test-behavior-change check**: scan the staged diff for any `skills/*/SKILL.md`, `skills/*/references/*.md`, or `agents/*.md` change that alters guidance or instructions — per `.claude/rules/require-tests-for-behavior-changes.md`'s definition (a change to what a component actually does when followed on some input; excludes deterministic script/code logic changes and prose fixes that only restore already-intended behavior). If any staged file matches, ask via `AskUserQuestion`: "This looks like it changes skill/agent behavior. Has it been tested?" with options covering the mechanisms in `require-tests-for-behavior-changes.md` (a `skill-tester` eval run, the Testing & Validation checklist, the trigger-phrase smoke check), plus "No — commit anyway" and "No — stop, let me test first". This ask is mandatory whenever the diff matches — never skip it silently — but the answer, including "commit anyway", is the user's call. On "stop, let me test first", halt here without committing.
11. **Check whether this is a single logical change**: scan the diff for signs of multiple unrelated
    concerns (different top-level directories/domains touched, a mix of feature/fix/refactor/docs
    changes, or unrelated file types changed together). This is a lightweight signal, not a splitting
    procedure — see step 12.
12. If step 11 finds signs of multiple concerns, tell the user and point them to
    the `standalone-commits` skill for the actual splitting/ordering/wave-planning logic
    (dependency-ordered waves, acceptance checks, staging workflow) instead of re-deriving a split
    here. Continue `commit`'s own flow only for the single commit currently staged (or whatever subset
    the user chooses to keep in this commit).
13. Creates a commit message for the currently staged changes using conventional commit format (no emoji — see Best Practices). Include a body when the reason isn't obvious from the diff alone (recommended, not required — see Best Practices). **Before presenting the message in step 14, count the body's own line count against `commit_body_max_lines` (default 5) and cut it to that limit if over — this check applies regardless of how large or multi-part the underlying diff is, and regardless of how detailed a summary of the same change was already given in this conversation; a large multi-fix batch still gets a WHY-only body, never an itemized per-file changelog.** Include a footer trailer only when it applies: a `BREAKING CHANGE:` trailer when the subject uses `!`, a `Refs:`/`Closes:` trailer when the conversation named a specific issue this commit relates to or resolves, and a `Related-PR:` trailer when the conversation named a specific related PR. Don't ask the user for footer content on every commit — only include a trailer when there's a concrete breaking change, issue, or PR already in view (see Commit Message Footer below).
14. **Confirm before committing**: when `commit_confirm_before_commit` is `true` (the default), use AskUserQuestion to show the generated commit message and ask the user to proceed; only run `git commit` after confirmation. When `false`, commit directly. **Immediately before running `git commit`** (right after confirmation, or right before committing directly when confirmation is off), run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-commit commit` — this writes the marker git-kit's commit-guard hook requires; it must be written right before the commit, not earlier in this run, since the hook only accepts a marker up to 60 seconds old.
15. **Amend**: if `--amend` was given, run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-commit commit` immediately before running it, then use `git commit --amend` instead of a plain commit. Before amending, check with `git status` whether the branch is ahead of its remote and warn if the target commit was already pushed.
**Steps 16 and 17's numbers below are cited externally** — `plugins/git-kit/skills/create-pr/SKILL.md` names them by number in its own Pre-flight Checks instructions to `commit`. If either step is ever renumbered, update `create-pr`'s citations in the same change.
16. **Push**: skip this step entirely if `commit` was invoked as a nested dependency from `create-pr`'s own Pre-flight Checks (i.e. this run's instructions say not to push on this run's behalf) — this applies even when `--push` was given or `commit_auto_push` is `true`, and the push-confirmation `AskUserQuestion` below is not asked at all in that case, not merely answered on the caller's behalf; `create-pr`'s own Pre-flight step 4 mandatory review gate has not run yet at this point, and pushing here would let the branch reach the remote before that gate ever sees it. **State plainly in this run's output that the push was suppressed for this nested invocation** — a `--push` flag or `commit_auto_push: true` that silently produced no push would otherwise read as a dropped instruction rather than a deliberate gate. Otherwise: push after a successful commit when `--push` was given (explicit override, always pushes regardless of setting), or when `commit_auto_push` is `true`. Otherwise, when `commit_auto_push` is `false` and no `--push` flag was given, ask via `AskUserQuestion` whether to push. If push fails because there's no upstream, suggest `git push -u origin <branch>`.
17. **Auto-PR**: skip this step entirely if `commit` was invoked as a nested dependency from `create-pr`'s own Pre-flight Checks (i.e. this run's instructions say to skip Auto-PR) — `create-pr` is about to create the PR itself right after this run returns, so running this step too would create a duplicate PR or nest `create-pr` inside itself. For a `create-pr`-nested invocation specifically, this is always passed together with step 16's push-skip instruction, never independently — a different caller may pass only this Auto-PR-skip instruction without also skipping step 16's push (see `plugins/analysis-kit/skills/running-a-full-retrospective/references/phase-5-fix-execution.md` for one such caller), so don't assume the two are coupled outside the `create-pr` case. Otherwise, after a successful push (from step 16), check `gh pr view --json number` for the current branch. If a PR is already open, skip this step entirely. Otherwise: when `push_auto_pr` is `true`, invoke `Skill(git-kit:create-pr)` directly; when `false`, ask via `AskUserQuestion` whether to create one now, and invoke `Skill(git-kit:create-pr)` only on yes.
18. **Show the result**: commit hash, files changed, insertions/deletions, and push status (if a push happened)

## Best Practices for Commits

- **Verify before committing**: Ensure code is linted, builds correctly, and documentation is updated
- **Atomic commits**: Each commit should contain related changes that serve a single purpose
- **Split large changes**: If changes touch multiple concerns, split them into separate commits (see `standalone-commits` for the actual splitting/ordering procedure)
- **Conventional commit format**: Use the format `<type>(scope): <description>` where type is one of:
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation changes
  - `style`: Code style changes (formatting, etc)
  - `refactor`: Code changes that neither fix bugs nor add features
  - `perf`: Performance improvements
  - `test`: Adding or fixing tests
  - `chore`: Changes to the build process, tools, etc.
  - `ci`: CI/CD changes
  - `experiment`: Experimental changes
- **Breaking changes**: Add `!` before the colon, e.g. `feat!:` or `refactor(api)!:`
- **Present tense, imperative mood**: Write commit messages as commands (e.g., "add feature" not "added feature")
- **Concise first line**: Aim for `commit_first_line_soft_limit` characters (default 50), hard limit `commit_first_line_hard_limit` (default 72)
- **Body (recommended, not required)**: explain WHY the change was made, not WHAT changed (the diff already shows that). Up to `commit_body_max_lines` lines (default 5). A one-line subject is fine when the diff is genuinely self-explanatory — don't pad a body onto a change that doesn't need one.
- **Audience**: describe the change in terms any repo reader understands — never a local-machine-specific path, a symptom as it appeared in one session's terminal, or context ("fixed the issue from my last session") that means nothing outside this one environment.
- **Footer (optional)**: see Commit Message Footer below for the trailer format (breaking changes, related issues, related PRs)
- **Emoji**: Do not use emoji in commit messages

## Commit Message Footer

Add a footer — a blank line after the subject/body, then one or more trailer lines — only when it applies. Never fabricate a trailer with no real content behind it.

| Trailer | When to include | Format |
|---|---|---|
| `BREAKING CHANGE:` | The subject uses `!` (e.g. `feat!:`) | `BREAKING CHANGE: <what breaks, and migration guidance>` |
| `Refs:` | The commit relates to an issue without resolving it | `Refs: #<issue-number>` |
| `Closes:` | The commit resolves an issue (GitHub auto-closes it on merge to the default branch) | `Closes: #<issue-number>` |
| `Related-PR:` | The commit depends on, supersedes, or otherwise relates to another PR | `Related-PR: #<pr-number>` |

Multiple trailers can appear together, one per line. Only include a trailer when the conversation already named a specific issue, PR, or breaking-change detail — don't ask the user to supply one just to fill out the section.

## Examples

Good commit messages (first line only):
- feat: implement business logic for transaction validation
- feat: add input validation for user registration form
- feat: improve form accessibility for screen readers
- fix: strengthen authentication password requirements
- fix: resolve failing CI pipeline tests
- fix: address minor styling inconsistency in header
- fix: patch critical security vulnerability in auth flow
- fix: remove deprecated legacy code
- docs: update API documentation with new endpoints
- refactor: simplify error handling logic in parser
- chore: improve developer tooling setup process
- style: reorganize component structure for better readability

Commit with a body and footer:

```
fix(auth)!: require re-authentication after password change

Sessions issued before a password change stayed valid indefinitely,
so a compromised session survived the one action meant to kill it.

BREAKING CHANGE: existing sessions are invalidated on password change;
clients must handle a 401 and re-prompt for login.
Closes: #482
```

For splitting a diff into multiple commits — ordering, wave-planning, deciding what's reviewable on its
own — see the `standalone-commits` skill; that skill owns the full procedure and worked examples.

## Branch Naming Convention

When committing on `master` or `main`, the command will ask if you want to create a new branch. If yes, it creates a branch following this pattern:

```
<type>/<description>
```

**Components:**
- `<type>`: The commit type (feature, fix, docs, refactor, perf, test, chore, etc.)
- `<description>`: A kebab-case description of the change (e.g., `add-user-auth`, `fix-login-bug`)

**Examples:**
- `feature/add-new-command`
- `fix/resolve-memory-leak`
- `docs/update-api-docs`
- `refactor/simplify-error-handling`
- `chore/update-dependencies`

**Workflow:**
1. Command detects you're on `master` or `main`
2. Command searches for another branch
3. If another branch exists, it will ask if you want to create a new branch or use the existing one
3.1 AskUserQuestion: "You're on the main branch. Do you want to switch to branch <branch-name>?"
3.2 If "Yes": Switches to the existing branch and proceeds with commit on current branch
3.3 If "No": AskUserQuestion: "Do you want to create a separate branch?"
3.4 If "No": Stop the process
3.5 If "Yes": Analyzes your changes to determine the type, asks for a brief description, creates the branch, and proceeds with commit
4. If another branch does not exist, it will ask if you want to create a new branch
4.1 AskUserQuestion: "You're on the main branch. Do you want to create a separate branch?"
4.2 If "No": Stop the process
4.3 If "Yes": Analyzes your changes to determine the type, asks for a brief description, creates the branch, and proceeds with commit

## Important Notes

- By default, pre-commit checks will run to ensure code quality (skip with `--no-verify`)
- If these checks fail, you'll be asked if you want to proceed with the commit anyway or fix the issues first
- If specific files are already staged, the command will only commit those files
- If no files are staged, you'll be asked what to stage — nothing is auto-staged unless `commit_auto_stage: true` is set (via `.claude/git-kit.local.json` or the git-tracked `git-kit.settings.json` defaults)
- Staged files matching sensitive patterns (`.env`, `*secret*`, `*.key`, `*.pem`, `*password*`, `*token*`, SSH/cloud keys, `.npmrc`/`.pgpass`/`.netrc`) are flagged and unstaged automatically
- In this repository, a staged `.py` file is auto-formatted and auto-fixed with `ruff format`/`ruff check --fix` (re-staged afterward) and type-checked with `ty check` (blocking, not auto-fixed) — unless `--no-verify` was given
- In this repository, staging a canonical `plugins/<name>/...` or registered `.claude/skills|agents/...`
  source runs the marketplace-CI sync/export CLI and stages only the resulting generated counterparts —
  never a hand-edit of `.claude`/`.agents`/`.codex`. This parity check always runs, even under
  `--no-verify` (which only skips lint-style checks)
- The commit message will be constructed based on the changes detected
- Before committing, the command signals when the diff shows signs of multiple unrelated concerns and
  points you to `standalone-commits` for the actual split — it doesn't perform the split itself
- Always reviews the commit diff to ensure the message matches the changes
- You'll be asked to confirm the generated message before the commit runs, unless `commit_confirm_before_commit: false` is set — but that setting (along with `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true`) is only honored from `.claude/git-kit.local.json` when it isn't tracked by git; a git-tracked copy can never silently weaken any of these gates, and the skill falls back to the safe defaults in `git-kit.settings.json` instead
- `--amend` warns before rewriting an already-pushed commit; `--push` pushes after a successful commit (an explicit override that always pushes) and suggests `git push -u origin <branch>` if there's no upstream; without `--push`, a push still happens automatically if `commit_auto_push: true`, otherwise you're asked — **except when `commit` was invoked as a nested dependency from `create-pr`'s Pre-flight Checks with instructions not to push, where step 16 skips entirely and `--push`/`commit_auto_push` are not honored for this run; that suppression is reported in this run's output** (see step 16)
- After a push, if no PR is already open for the branch, a PR gets created automatically when `push_auto_pr: true`, otherwise you're asked whether to create one

## Testing & Validation

**Verify this skill does NOT activate on:**
- "split this diff into separate commits" / "break this up into multiple commits" / "how should I order
  these changes into waves" → these route to `standalone-commits`, not `commit`; step 11's "multiple
  concerns?" signal exists to catch this mid-flow (a diff that looks split-worthy once already staged),
  not to make `commit` a second entry point for a request to split in the first place

**Verified live, 2026-08-11:** `commit` was invoked for real (`Skill(commit)`, not a raw `git commit`) roughly 5 times across that session's fix-batch commits, including the final commit of that session's second fix batch (`2160f56`) — the test-behavior-change check (now step 10, renumbered from step 9 by step 8's later targeted-repair insertion) fired correctly on every behavior-changing commit in that run. That live run confirmed the check fires and gates correctly in real use; it did not walk each item below individually, so the checkboxes stay unchecked pending a full manual pass — re-run this checklist (and check off what it confirms) after the next behavior-changing invocation, rather than treating this date as a permanent guarantee:

- [ ] The staged-diff scan actually fires — a change to `skills/*/SKILL.md`, `skills/*/references/*.md`, or `agents/*.md` content triggers the `AskUserQuestion`; an unrelated change (docs, scripts, config) does not
- [ ] The `AskUserQuestion` presents the options as written in step 10's prose (the testing-mechanism choices, plus "commit anyway" and "stop, test first")
- [ ] Step 10 sits correctly in sequence — fires after step 9's `git diff --cached`, before step 11's multiple-change analysis, without disrupting the flow
- [ ] Step 10's ask and step 14's separate confirm-before-commit ask don't read as a confusing back-to-back double prompt when both fire in the same run
- [ ] "Stop, test first" actually halts before any commit runs
- [ ] Step 11's "multiple concerns?" signal fires without `commit` attempting to perform the split itself — step 12 always redirects to the `standalone-commits` skill rather than re-deriving a split
- [ ] Generated commit messages never contain a local-machine-specific path, terminal-session symptom description, or session context — only content a reader of the shared repo history would understand
- [ ] A request to commit while on `main`/`master` with nothing staged yet points at `starting-work`; step 3's own branch-creation fallback only fires for someone already mid-edit
- [ ] When invoked as a nested dependency from `create-pr`'s Pre-flight Checks (told not to push on that run's behalf), step 16 always skips entirely — including its own push-confirmation `AskUserQuestion`, which is never asked and then overridden — regardless of `--push` or `commit_auto_push`; step 17's Auto-PR skip always applies together with it in that same case, never independently
- [ ] Step 7.5 always checks `git diff --name-only -- <path>` per staged `.py` path before auto-fixing it
      — a non-empty result always skips that file's auto-fix rather than risking a blanket `git add`
      pulling unstaged hunks into the commit (found by Codex's automated PR review, 2026-08-16: the
      original version had no such check)
- [ ] A skipped partially-staged file is always reported by name, never silently dropped — and is still
      included in the `ty check` pass, which only reads

**Step 7.5 (lint/format/type-check staged Python files) — verified live, 2026-08-16:** ran
`uv run ruff format`/`uv run ruff check --fix`/`uv run ty check` against two newly-written scripts
(`remap-handoff-shas.py`, `check-pr-title.py`) in this repository. `ruff format` reformatted both files on
the first pass; `ruff check` flagged 2 non-auto-fixable `E501` (line-too-long) violations, fixed manually
and reconfirmed clean; `ty check` separately caught 2 real issues `ruff` didn't (an unused blanket
`# type: ignore`, and `sys.stdout.reconfigure`/`sys.stderr.reconfigure` not resolving on the `TextIO`
union type) — confirming `ty check`'s inclusion catches a real class of error `ruff` alone misses. All
three checks passed clean after fixes.

**Step 8 (marketplace CI targeted repair) — verified via `tests/marketplace_ci/test_hooks.py`'s
`check_staged_parity` coverage (deterministic, not blind A/B — see rationale below), 2026-08-13:**
- [x] Staging a canonical `plugins/<name>/...` change without staging its generated `.claude` mirror
      counterpart is correctly flagged as a parity failure, even when the mirror file's *working-tree*
      content already happens to match (`test_unstaged_repair_does_not_satisfy_staged_parity`)
- [x] Staging both the canonical source and a byte-identical generated counterpart passes
      (`test_staged_mirror_matching_content_satisfies_parity`)
- [x] A staged generated counterpart with stale/wrong content fails
      (`test_staged_mirror_with_wrong_content_fails_parity`)
- [x] An unrelated staged change (no registered canonical path touched) does not trigger the check
      (`test_unrelated_staged_change_does_not_trigger_parity_check`)
- [x] The same coverage holds for converted agent exports (`.claude/agents/<name>.md` →
      `.codex/agents/<name>.toml`), not just plain-copy skill mirrors
- [ ] Live invocation: a real `commit` run against a deliberately drifted canonical file, confirming step 8
      actually repairs and stages the right subset in this repository (not yet exercised end-to-end;
      Task 12's rollout PR is the first real opportunity)

A `skill-tester` blind-comparison eval is the heavier alternative `require-tests-for-behavior-changes.md` names first, but `commit` is a `model: haiku`, heavily interactive skill built around several `AskUserQuestion` steps — an awkward fit for blind A/B comparison. This checklist, plus `check_staged_parity`'s own deterministic test suite for step 8's actual repair logic, is the pragmatic mechanism the rule explicitly permits instead ("a documented Testing & Validation section... concrete scenarios, pass/fail criteria").
