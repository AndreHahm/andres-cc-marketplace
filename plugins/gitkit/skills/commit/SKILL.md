---
name: commit
description: Create well-formatted commits with conventional commit messages
argument-hint: Optional flags like --no-verify to skip pre-commit checks
model: haiku
allowed-tools: Bash(git status:*), Bash(git add:*), Bash(git diff:*), Bash(git commit:*), Bash(git config:*), Bash(git branch:*), Bash(git checkout:*), Bash(pnpm lint:*), Bash(npm run lint:*), Bash(yarn lint:*), Bash(bun lint:*)
---

# Claude Command: Commit

Your job is to create well-formatted commits with conventional commit messages.

## Instructions

CRITICAL: Perform the following steps exactly as described:

1. **Branch check**: Checks if current branch is `master` or `main`. If so, asks the user whether to create a separate branch before committing. If user confirms a new branch is needed, creates one using the pattern `<type>/<description>` (e.g., `feature/add-new-command`)
2. Unless specified with `--no-verify`, automatically runs pre-commit checks like `pnpm lint` or simular depending on the project language.
3. Checks which files are staged with `git status`
4. If 0 files are staged, automatically adds all modified and new files with `git add`
5. Performs a `git diff` to understand what changes are being committed
6. Analyzes the diff to determine if multiple distinct logical changes are present
7. If multiple distinct changes are detected, suggests breaking the commit into multiple smaller commits
8. For each commit (or the single commit if not split), creates a commit message using emoji conventional commit format

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
  - `experiment`: Experimental changes
- **Present tense, imperative mood**: Write commit messages as commands (e.g., "add feature" not "added feature")
- **Concise first line**: Keep the first line under 72 characters
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

- By default, pre-commit checks will run to ensure code quality
- If these checks fail, you'll be asked if you want to proceed with the commit anyway or fix the issues first
- If specific files are already staged, the command will only commit those files
- If no files are staged, it will automatically stage all modified and new files
- The commit message will be constructed based on the changes detected
- Before committing, the command will review the diff to identify if multiple commits would be more appropriate
- If suggesting multiple commits, it will help you stage and commit the changes separately
- Always reviews the commit diff to ensure the message matches the changes
