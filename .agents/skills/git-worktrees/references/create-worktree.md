# How to Create Worktree

Workflow to create a worktree for an **existing** branch (local or already-tracked remote), with automatic
dependency detection and confirmed (not automatic) installation. Creating a worktree for a **new** branch
is `starting-work`'s job, not this skill's — git-kit's `guard-raw-branch-create.sh` hook hard-blocks a raw
`git worktree add -b`/`-B` from any skill not on its allowlist, this skill included. If the branch named
below doesn't exist yet, stop this workflow and hand off to `starting-work` instead of continuing.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Current state check**: Run `git worktree list` to show existing worktrees and `git status` to verify the repository state is clean (no uncommitted changes that might cause issues)

2. **Fetch latest remote branches**: Run `git fetch --all` to ensure local has knowledge of all remote branches

3. **Parse the request**: Determine what the user wants — a worktree for a named *existing* branch, or "just list existing worktrees." If neither is clear from what they said, ask. If the request is actually for a *new* branch (no existing local or remote branch by that name), stop here and hand off to `starting-work` — this workflow only covers existing branches.

4. **Resolve the worktree path**: Use sibling directory with pattern `../<project-name>-<name>`, where `<name>` is derived from the branch name (strip any `<type>/` prefix, e.g. `feature/auth-system` → `../myproject-auth-system`).

5. **For each worktree to create**:
   a. **Branch resolution**: Determine where the branch already exists:
      - If it exists locally: `git worktree add ../<project>-<name> <branch>`
      - If it exists remotely only (`origin/<branch>`), not yet tracked locally: `git worktree add --track ../<project>-<name> origin/<branch>` (no `-b` — this checks out the existing remote branch under its own name, it does not create a new one)
      - If it doesn't exist anywhere: this isn't this workflow's job — hand off to `starting-work` (see the note at the top of this file)

   b. **Create the worktree**: Execute the resolved `git worktree add` command from step 5a.

   c. **Dependency detection**: Check the new worktree for dependency files and determine if setup is needed:
      - `package.json` -> Node.js project (npm/yarn/pnpm/bun)
      - `requirements.txt` or `pyproject.toml` or `setup.py` -> Python project
      - `Cargo.toml` -> Rust project
      - `go.mod` -> Go project
      - `Gemfile` -> Ruby project
      - `composer.json` -> PHP project

   d. **Package manager detection** (for Node.js projects):
      - `bun.lockb` -> Use `bun install`
      - `pnpm-lock.yaml` -> Use `pnpm install`
      - `yarn.lock` -> Use `yarn install`
      - `package-lock.json` or default -> Use `npm install`

   e. **Setup, with confirmation**: A checked-out branch's dependency manifests and any install/postinstall
      scripts they trigger are as untrusted as the rest of the branch content — ask via `AskUserQuestion`
      before running anything: "Run `<detected install command>` to install dependencies in the new
      worktree?" (options: "Install" / "Skip"). Only on "Install":
      - cd to worktree and run the detected install command
      - Report progress: "Installing dependencies with [package manager]..."
      - If installation fails, report the error but continue with worktree creation summary
      On "Skip", note in the summary that dependencies were not installed and how to install them manually.

6. **Summary**: Display summary of created worktrees:
   - Worktree path
   - Branch name
   - Setup status (dependencies installed, skipped, or failed)
   - Quick navigation command: `cd <worktree-path>`

## Worktree Path Convention

Worktrees are created as sibling directories to maintain organization:

```
~/projects/
  myproject/                # Main worktree (current directory)
  myproject-add-auth/       # Worktree for existing branch feature/add-auth
  myproject-critical-bug/   # Worktree for existing branch hotfix/critical-bug
  myproject-pr-456/         # Worktree for existing branch review/pr-456
```

**Naming rules:**

- Pattern: `<project-name>-<name>` (uses the name part, NOT the full branch)
- Directory name uses only the branch's `<name>` portion (after any `<type>/` prefix) for brevity

## Examples

**Worktree for an already-existing branch** — user asks to work on `fix/login-error` in a separate
directory, and that branch already exists (locally or on `origin`):
```
Branch: fix/login-error (existing)
Creates: ../myproject-login-error
```

**List existing worktrees** — user asks to list worktrees: run `git worktree list` and show the output directly.

**No matching branch found** — user asks for a worktree for a branch that doesn't exist locally or
remotely: stop this workflow and hand off to `starting-work` instead (see the note at the top of this
file) — creating a worktree for a brand-new branch isn't this workflow's job.

## Setup Detection Examples

**Node.js project with pnpm:**

```
Detected Node.js project with pnpm-lock.yaml
Installing dependencies with pnpm...
Dependencies installed successfully
```

**Python project:**

```
Detected Python project with requirements.txt
Installing dependencies with pip...
Dependencies installed successfully
```

**Rust project:**

```
Detected Rust project with Cargo.toml
Building project with cargo...
Project built successfully
```

## Common Workflows

### PR Review Without Stashing

User asks for a review worktree for an already-open PR: `git fetch origin pull/<N>/head:pr-<N>` (creates
a local ref from the PR's remote head — not a new branch this repo owns, so not guarded), then
`git worktree add ../myproject-pr-<N> pr-<N>` (existing branch, this workflow's normal case). Tests can
run and code can be inspected there; delete the worktree when the review is complete.

### Continuing Work on an Existing Branch Elsewhere

User already has a branch (created via `starting-work` in another session, or pushed by someone else) and
wants a separate directory for it without disturbing their current worktree — this workflow's normal case.

### Starting genuinely new work

Not this workflow — hand off to `starting-work`, which syncs `main`, validates the branch name, and asks
worktree-vs-plain-branch before the branch exists at all.

## Important Notes

- **Branch lock**: Each branch can only be checked out in one worktree at a time. If a branch is already checked out, tell the user which worktree has it.

- **Shared .git**: All worktrees share the same Git object database. Changes committed in any worktree are visible to all others.

- **Clean working directory**: Check for uncommitted changes and warn if present, as creating worktrees is safest with a clean state.

- **Sibling directories**: Worktrees are always created as sibling directories (using `../`) to keep the workspace organized. Never create worktrees inside the main repository.

- **Dependency installation, with confirmation**: Detect the project type and package manager, then ask via `AskUserQuestion` before running the install command — a freshly checked-out branch's install/postinstall scripts are untrusted content, same as any other branch content.

- **Remote tracking**: For remote branches, create worktrees with proper tracking setup (`--track` flag) so pulls/pushes work correctly.

## Cleanup

When done with a worktree in a clean state, use the proper removal command:

```bash
git worktree remove ../myproject-add-auth
```

For a worktree with uncommitted changes, that's a forced removal — tell the user to run `/git-cleanup`
themselves (it has `disable-model-invocation: true`, so it can't be invoked here even indirectly), which
gates `--force`/`-f` behind explicit user confirmation before running it; the raw form is guarded and
isn't this workflow's job.

Never use `rm -rf` to delete worktrees - always use `git worktree remove` (or `git-cleanup` for the forced case).

## Troubleshooting

**"Branch is already checked out"**

- Run `git worktree list` to see where the branch is checked out
- Either work in that worktree or remove it first

**"Cannot create worktree - path already exists"**

- The target directory already exists
- Either remove it or choose a different worktree path

**"Dependency installation failed"**

- Navigate to the worktree manually: `cd ../myproject-<name>`
- Run the install command directly to see full error output
- Common causes: missing system dependencies, network issues, corrupted lockfile

**"No branch by that name exists locally or remotely"**

- This workflow only creates worktrees for existing branches
- Hand off to `starting-work` to create the branch first (and its own worktree, if wanted, in one step)
