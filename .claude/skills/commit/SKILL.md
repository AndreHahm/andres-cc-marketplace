---
name: commit
description: Create well-formatted commits with conventional commit messages
argument-hint: Optional flags (--no-verify, --amend, --push) followed by an optional commit message
model: haiku
allowed-tools: Bash(git status:*), Bash(git add:*), Bash(git restore --staged:*), Bash(git diff:*), Bash(git commit:*), Bash(git config:*), Bash(git branch:*), Bash(git checkout:*), Bash(git push:*), Bash(git ls-files:*), Bash(gh pr view:*), Bash(pnpm lint:*), Bash(npm run lint:*), Bash(yarn lint:*), Bash(bun lint:*), Read, Skill(git-kit:create-pr)
---

# Claude Command: Commit

Your job is to create well-formatted commits with conventional commit messages.

## Flags

| Flag | Effect |
|------|--------|
| `--no-verify` | Skip pre-commit checks (lint) |
| `--amend` | Amend the last commit instead of creating a new one |
| `--push` | Push to remote after a successful commit |

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
| `commit_auto_push` | `false` | After a successful commit, push without asking |
| `push_auto_pr` | `false` | After a successful push (via `--push` or `commit_auto_push`), create a PR without asking (if none is already open) |

**Security note:** `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, and `push_auto_pr` all weaken safety or trigger further automation when enabled, so they're only honored from `.claude/git-kit.local.json` when that file is untracked by git (see Instructions step 2). A copy committed into the repo — whether accidentally or by an attacker — can never silently disable the confirmation gate, enable auto-staging, or trigger unattended pushes/PR creation; the skill falls back to the git-tracked `git-kit.settings.json` defaults for those fields instead.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Read settings**: Read the git-tracked defaults from `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json` (`enabled`, `commit_confirm_before_commit`, `commit_auto_stage`, `commit_first_line_soft_limit`, `commit_first_line_hard_limit`, `commit_auto_push`, `push_auto_pr`). Then check for `.claude/git-kit.local.json` in the project root — if it exists and its own `enabled` isn't `false`, its fields override the corresponding default for any field it sets.
2. **Trust check (security)**: If `.claude/git-kit.local.json` exists and set `commit_confirm_before_commit`, `commit_auto_stage`, `commit_auto_push`, or `push_auto_pr`, check whether the file is tracked by git: `git ls-files --error-unmatch .claude/git-kit.local.json`. A git-tracked copy could have been committed by anyone with repo write access — including an attacker aiming to silently weaken safety gates for the next person who runs `/commit`. So if the file IS tracked (command exits 0), discard its values for those four fields and use the `git-kit.settings.json` defaults instead, regardless of what the local file says. Only an untracked (genuinely local, gitignored) `.claude/git-kit.local.json` may override any of these gates. The length-limit and `pr_merge_type`/`merge_auto_delete_branch`-style fields aren't security-relevant and may be honored either way, tracked or not.
3. **Branch check**: Checks if current branch is `master` or `main`. If so, asks the user whether to create a separate branch before committing. If user confirms a new branch is needed, creates one using the pattern `<type>/<description>` (e.g., `feature/add-new-command`)
4. Unless specified with `--no-verify`, automatically runs pre-commit checks like `pnpm lint` or similar depending on the project language.
5. Checks which files are staged with `git status`
6. **Staging**: If 0 files are staged — when `commit_auto_stage` is `true`, stage everything with `git add -A`; otherwise show the unstaged files and ask the user what to stage (or whether `git add -A` is appropriate). **Never auto-stage without confirmation unless `commit_auto_stage` is explicitly enabled.**
7. **Check for sensitive files** among the now-staged files. **NEVER commit:**
   - `.env`, `.env.*` files
   - `*secret*`, `*credential*`, `*.key`, `*.pem`
   - `*password*`, `*token*` files
   - SSH/cloud private keys: `id_rsa`, `id_ed25519`, `id_ecdsa`, `id_dsa`, `service-account.json`, `*.p12`, `*.pfx`, `*.jks`
   - Credential config files: `.npmrc`, `.pgpass`, `.netrc`

   If any are detected, warn the user and unstage them (`git restore --staged <file>`) before continuing.
8. Performs a `git diff --cached` to understand what changes are being committed
9. **Test-behavior-change check**: scan the staged diff for any `skills/*/SKILL.md`, `skills/*/references/*.md`, or `agents/*.md` change that alters guidance or instructions — per `.claude/rules/require-tests-for-behavior-changes.md`'s definition (a change to what a component actually does when followed on some input; excludes deterministic script/code logic changes and prose fixes that only restore already-intended behavior). If any staged file matches, ask via `AskUserQuestion`: "This looks like it changes skill/agent behavior. Has it been tested?" with options covering the mechanisms in `require-tests-for-behavior-changes.md` (a `skill-tester` eval run, the Testing & Validation checklist, the trigger-phrase smoke check), plus "No — commit anyway" and "No — stop, let me test first". This ask is mandatory whenever the diff matches — never skip it silently — but the answer, including "commit anyway", is the user's call. On "stop, let me test first", halt here without committing.
10. Analyzes the diff to determine if multiple distinct logical changes are present
11. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller commits
12. For each commit (or the single commit if not split), creates a commit message using conventional commit format (no emoji — see Best Practices)
13. **Confirm before committing**: when `commit_confirm_before_commit` is `true` (the default), use AskUserQuestion to show the generated commit message and ask the user to proceed; only run `git commit` after confirmation. When `false`, commit directly.
14. **Amend**: if `--amend` was given, use `git commit --amend` instead of a plain commit. Before amending, check with `git status` whether the branch is ahead of its remote and warn if the target commit was already pushed.
15. **Push**: push after a successful commit when `--push` was given (explicit override, always pushes regardless of setting), or when `commit_auto_push` is `true`. Otherwise, when `commit_auto_push` is `false` and no `--push` flag was given, ask via `AskUserQuestion` whether to push. If push fails because there's no upstream, suggest `git push -u origin <branch>`.
16. **Auto-PR**: skip this step entirely if `commit` was invoked as a nested dependency from `create-pr`'s own pre-flight check (i.e. this run's instructions say to skip Auto-PR) — `create-pr` is about to create the PR itself right after this run returns, so running this step too would create a duplicate PR or nest `create-pr` inside itself. Otherwise, after a successful push (from step 15, either path), check `gh pr view --json number` for the current branch. If a PR is already open, skip this step entirely. Otherwise: when `push_auto_pr` is `true`, invoke `Skill(git-kit:create-pr)` directly; when `false`, ask via `AskUserQuestion` whether to create one now, and invoke `Skill(git-kit:create-pr)` only on yes.
17. **Show the result**: commit hash, files changed, insertions/deletions, and push status (if a push happened)

## Best Practices for Commits

- **Verify before committing**: Ensure code is linted, builds correctly, and documentation is updated
- **Atomic commits**: Each commit should contain related changes that serve a single purpose
- **Split large changes**: If changes touch multiple concerns, split them into separate commits
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
- **Body (optional)**: 1-2 lines max, explaining WHY the change was made, not WHAT changed (the diff already shows that)
- **Emoji**: Do not use emoji in commit messages

## Guidelines for Splitting Commits

When analyzing the diff, consider splitting commits based on these criteria:

1. **Different concerns**: Changes to unrelated parts of the codebase
2. **Different types of changes**: Mixing features, fixes, refactoring, etc.
3. **File patterns**: Changes to different types of files (e.g., source code vs documentation)
4. **Logical grouping**: Changes that would be easier to understand or review separately
5. **Size**: Very large changes that would be clearer if broken down

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

Example of splitting commits:
- First commit: feat: add new solc version type definitions
- Second commit: docs: update documentation for new solc versions
- Third commit: chore: update package.json dependencies
- Fourth commit: feat: add type definitions for new API endpoints
- Fifth commit: feat: improve concurrency handling in worker threads
- Sixth commit: fix: resolve linting issues in new code
- Seventh commit: test: add unit tests for new solc version features
- Eighth commit: fix: update dependencies with security vulnerabilities

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
- The commit message will be constructed based on the changes detected
- Before committing, the command will review the diff to identify if multiple commits would be more appropriate
- If suggesting multiple commits, it will help you stage and commit the changes separately
- Always reviews the commit diff to ensure the message matches the changes
- You'll be asked to confirm the generated message before the commit runs, unless `commit_confirm_before_commit: false` is set — but that setting (along with `commit_auto_stage: true`, `commit_auto_push: true`, and `push_auto_pr: true`) is only honored from `.claude/git-kit.local.json` when it isn't tracked by git; a git-tracked copy can never silently weaken any of these gates, and the skill falls back to the safe defaults in `git-kit.settings.json` instead
- `--amend` warns before rewriting an already-pushed commit; `--push` pushes after a successful commit (an explicit override that always pushes) and suggests `git push -u origin <branch>` if there's no upstream; without `--push`, a push still happens automatically if `commit_auto_push: true`, otherwise you're asked
- After a push, if no PR is already open for the branch, a PR gets created automatically when `push_auto_pr: true`, otherwise you're asked whether to create one
