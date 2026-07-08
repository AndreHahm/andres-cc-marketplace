# /diff-explainer

## Workflow

### Phase 1 — Detect Input Mode

Classify the input into exactly one mode:

```text
github_pr_diff
git_ref_to_main_diff
local_to_branch_diff
local_file_to_branch_diff
file_to_file_diff
unknown
```

Use this decision order:

1. If `file_a` and `file_b` are provided → `file_to_file_diff`.
2. Else if `file` is provided → `local_file_to_branch_diff`.
3. Else if PR URL or PR number is provided → `github_pr_diff`.
4. Else if `commit` or `branch` is provided → `git_ref_to_main_diff`.
5. Else → `local_to_branch_diff`.

If multiple modes are possible, choose the most specific mode.

### Phase 2 — Resolve Comparison Pair

Identify:

```text
base
target
comparison_type
diff_command
context_command
```

#### Scenario 1 — PR vs Main

If only PR number or PR URL is provided:

1. Detect repository remote.
2. Resolve PR metadata.
3. Identify PR base branch.
4. Identify PR head branch.
5. Compare PR head against PR base.

Preferred commands:

```bash
gh pr view <PR> --json number,title,baseRefName,headRefName,headRepositoryOwner,author,state,mergeable,url
gh pr diff <PR>
```

Fallback commands:

```bash
git fetch origin
git diff origin/main...HEAD
```

If the PR base is not `main`, use the actual PR base and say so.

#### Scenario 2 — Git Diff to Main

If a commit, branch, or PR ref is provided:

```bash
git fetch origin
git diff origin/main...<ref>
```

If `base_branch` is provided:

```bash
git fetch origin
git diff origin/<base_branch>...<ref>
```

For a single commit:

```bash
git show --stat <commit>
git show --find-renames <commit>
```

If the user asks for cumulative branch diff, use triple-dot comparison:

```bash
git diff origin/main...<branch>
```

If the user asks for direct endpoint difference, use two-dot comparison:

```bash
git diff origin/main..<branch>
```

Default to triple-dot for branch and PR explanations because it reflects changes introduced by the branch relative to the merge base.

#### Scenario 3 — Local Diff to Branch

If no PR, commit, branch, or file pair is provided:

1. Detect active branch.
2. Use `base_branch` if provided, otherwise compare against the active branch’s upstream or `main`.

Useful commands:

```bash
git branch --show-current
git status --short
git diff
git diff --staged
git diff origin/main...HEAD
```

Default behavior:

- If there are unstaged changes, explain unstaged local diff.
- If `scope=staged`, explain staged diff.
- If no local changes exist, compare active branch to `origin/main`.
- If `base_branch` is provided, compare local working tree or active branch to that base.

#### Scenario 4 — Local File Diff to Branch

If `file` is provided:

```bash
git diff origin/main -- <file>
```

If `base_branch` is provided:

```bash
git diff origin/<base_branch> -- <file>
```

Also collect file context when helpful:

```bash
git status --short -- <file>
git log --oneline -- <file> -5
```

If the file is untracked, explain that no branch baseline exists and treat it as a new file.

#### Scenario 5 — File-to-File Diff

If `file_a` and `file_b` are provided:

```bash
diff -u <file_a> <file_b>
```

If available, prefer a syntax-aware or word-level diff for Markdown or code:

```bash
git diff --no-index --word-diff <file_a> <file_b>
git diff --no-index --stat <file_a> <file_b>
```

This mode is independent of Git repository state.

### Phase 3 — Gather Diff Metadata

Before explaining content, collect overview metadata:

```bash
git diff --stat
git diff --name-status
git diff --summary
```

For PRs:

```bash
gh pr view <PR> --json title,body,labels,baseRefName,headRefName,author,files,commits
```

For commits:

```bash
git show --stat <commit>
git show --name-status <commit>
```

Extract:

```text
files changed
added files
deleted files
renamed files
modified files
binary files
lines added/deleted
config files changed
test files changed
docs changed
dependency files changed
migration files changed
security-sensitive files changed
```

### Phase 4 — Classify Change Types

Classify each changed file and each major hunk.

Possible change types:

```text
feature
bugfix
refactor
test
documentation
configuration
dependency
migration
security
performance
observability
build
ci
formatting
deletion
rename
generated
unknown
```

Use file paths and content signals:

| Signal | Likely Type |
|---|---|
| `test`, `spec`, `__tests__` | test |
| `README`, `docs`, `.md` | documentation |
| `package.json`, `lock`, `requirements`, `pyproject`, `pom.xml` | dependency/build |
| `.github/workflows`, `ci`, `pipeline` | ci |
| `Dockerfile`, `compose`, `helm`, `terraform` | infrastructure/config |
| `auth`, `token`, `permission`, `role`, `jwt`, `crypto` | security-sensitive |
| `migration`, `schema` | migration |
| logging, metrics, traces | observability |

### Phase 5 — Explain the Diff by Intent

For each meaningful change group, explain:

```text
What changed
Why it likely changed
What behavior or contract changed
What files or areas are involved
What risk or review focus exists
```

Use this structure:

```markdown
### <Change Group>

**What changed:**  
...

**Why this likely exists:**  
...

**Developer impact:**  
...

**Review focus:**  
...
```

Keep explanations tied to evidence from the diff.

### Phase 6 — Distinguish Facts from Inferences

Use explicit labels:

```markdown
**Observed:** The route now validates `userId` before querying the database.

**Likely intent:** This appears to prevent invalid IDs from reaching the data layer.

**Unclear:** The diff does not show whether this is covered by tests.
```

Rules:

- “Observed” must be directly visible in the diff.
- “Likely intent” must be supported by the surrounding change.
- “Unclear” must be used when context is missing.
- Do not present assumptions as facts.

### Phase 7 — Explain Structural vs Behavioral Changes

Separate:

```text
behavioral changes
API/contract changes
data model changes
control-flow changes
error-handling changes
test changes
documentation changes
style/formatting changes
```

This prevents small formatting changes from hiding behavior changes.

### Phase 8 — Identify Risk and Review Focus

Highlight changes that deserve careful review.

Risk categories:

```text
security
data loss
backward compatibility
migration
performance
race condition
dependency risk
configuration drift
silent failure
test gap
public API change
auth/authz behavior
```

For each risk, include:

```text
risk level: low | medium | high
why it matters
where to look
suggested verification
```

### Phase 9 — Explain Missing or Surprising Changes

Look for mismatch patterns:

- implementation changed but tests did not
- behavior changed but docs did not
- dependency changed but lockfile did not
- public API changed but migration or compatibility note missing
- config changed without environment documentation
- security-sensitive code changed without security tests
- deleted code without replacement
- renamed files without import updates visible
- generated files changed without source changes

Report these as:

```markdown
## Notable Absences

- Tests were not changed even though authentication behavior changed.
- Documentation was not updated despite a new public option.
```

Do not overstate. Use “may need review” when appropriate.

### Phase 10 — Produce Human-Friendly Summary

Start with a concise summary:

```markdown
## Diff Explanation

**Short version:**  
This diff appears to ...

**Main reason for the changes:**  
...

**Most important files:**  
...

**Main review focus:**  
...
```

Then provide grouped explanations.

### Phase 11 — Optional Command Appendix

If `include_commands=yes`, include the commands used or recommended.

```markdown
## Commands Used / Recommended

```bash
...
```
```

If commands could not be executed, include recommended commands instead.

### Phase 12 — Self-Review

Before finalizing, verify:

```text
[ ] The comparison pair is clear.
[ ] The explanation distinguishes observed facts from inferred intent.
[ ] Major behavior changes are described.
[ ] Risk-bearing changes are highlighted.
[ ] Tests/docs/config/dependencies are mentioned when relevant.
[ ] Missing or surprising related changes are noted.
[ ] File paths and symbols are preserved.
[ ] The explanation is understandable to a human developer.
[ ] The output does not claim unsupported intent.
```
