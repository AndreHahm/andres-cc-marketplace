---
name: gh-operations
description: >-
  Provides a GitHub operations command reference using gh CLI and GitHub API — listing, viewing, and
  editing pull requests; managing issues, repository settings, and GitHub Actions workflows; querying API
  endpoints; and handling GitHub workflows in enterprise or public GitHub environments. Use when
  listing/viewing/editing PRs, managing issues, or automating GitHub Actions/API calls. For creating a
  new PR use `create-pr` (template + pre-commit handling), for merging a PR use `merge-pr`
  (readiness + merge-rights checks), and for reviewer actions (approve/comment/request-changes) with
  CODEOWNERS context use `collaborating-on-a-pr` — this skill does not do any of the three; the `gh pr
  review`/`gh pr comment` examples below are raw reference material only, not a recommendation to run
  them standalone for a real review.
allowed-tools: Bash(gh pr:*), Bash(gh issue:*), Bash(gh repo view:*), Bash(gh repo clone:*), Bash(gh repo create:*), Bash(gh repo set-default:*), Bash(gh workflow:*), Bash(gh run:*), Bash(gh api:*), Bash(gh config:*)
---

# GitHub Operations

## Overview

This skill provides comprehensive guidance for GitHub operations using the `gh` CLI tool and GitHub REST/GraphQL APIs. Use this skill when performing any GitHub-related tasks including pull request management, issue tracking, repository operations, workflow automation, and API interactions.

## When to Use This Skill

This skill activates for tasks involving:
- Viewing and editing pull requests (not creating — see `create-pr`; not merging — see `merge-pr`; not a
  reviewer action with CODEOWNERS context — see `collaborating-on-a-pr`)
- Managing GitHub issues or repository settings
- Querying GitHub API endpoints (REST or GraphQL)
- Working with GitHub Actions workflows
- Performing bulk operations on repositories
- Integrating with GitHub Enterprise
- Automating GitHub operations via CLI or API

## Core Operations

### Pull Requests

**Not for:** creating a PR (→ `create-pr`), merging a PR (→ `merge-pr`), or a reviewer action —
approve/comment/request-changes with CODEOWNERS context (→ `collaborating-on-a-pr`).

```bash
# List and view PRs
gh pr list --state open
gh pr view 123

# Edit PR metadata (not a review action)
gh pr edit 123 --add-label needs-triage
```

See `references/pr-operations.md` for comprehensive PR workflows

**PR Title Convention (org-specific example, optional):** the `IN-1234:`/`NOLINEAR:` prefix below is a Linear-ticket-tracking convention from this skill's original source project — adopt it only if your project uses Linear; otherwise use your own project's PR title convention.
- With LINEAR ticket: `IN-1234: Descriptive title`
- Without LINEAR ticket: `NOLINEAR: Descriptive title`

### Issues

```bash
# Create and manage issues
gh issue create --title "Bug: Issue title" --body "Issue description"
gh issue list --state open --label bug
gh issue edit 456 --add-label "priority-high"
gh issue close 456
```

See `references/issue-operations.md` for detailed issue management

### Repositories

```bash
# View and manage repos
gh repo view --web
gh repo clone owner/repo
gh repo create my-new-repo --public
```

### Workflows

```bash
# Manage GitHub Actions
gh workflow list
gh workflow run workflow-name
gh run watch run-id
gh run download run-id
```

See `references/workflow-operations.md` for advanced workflow operations

### GitHub API

The `gh api` command provides direct access to GitHub REST API endpoints. Refer to `references/api-reference.md` for comprehensive API endpoint documentation.

**Basic API operations:**
```bash
# Get PR details via API
gh api repos/{owner}/{repo}/pulls/{pr_number}

# Add PR comment
gh api repos/{owner}/{repo}/issues/{pr_number}/comments \
  -f body="Comment text"

# List workflow runs
gh api repos/{owner}/{repo}/actions/runs
```

For complex queries requiring multiple related resources, use GraphQL. See `references/api-reference.md` for GraphQL examples.

## Authentication and Configuration

**The `gh auth` examples below are reference material only** — `allowed-tools` deliberately excludes
`gh auth` (credential/identity surface, same reasoning as excluding `gh secret`/`gh variable`/`gh repo
delete`), so this skill never runs them itself. Run them yourself outside this skill if needed.

```bash
# Login to GitHub (reference only — not run by this skill)
gh auth login

# Login to GitHub Enterprise (reference only — not run by this skill)
gh auth login --hostname github.enterprise.com

# Check authentication status (reference only — not run by this skill)
gh auth status

# Set default repository
gh repo set-default owner/repo

# Configure gh settings
gh config set editor vim
gh config set git_protocol ssh
gh config list
```

## Output Formats

Control output format for programmatic processing:

```bash
# JSON output
gh pr list --json number,title,state,author

# JSON with jq processing
gh pr list --json number,title | jq '.[] | select(.title | contains("bug"))'

# Template output
gh pr list --template '{{range .}}{{.number}}: {{.title}}{{"\n"}}{{end}}'
```

See `references/best-practices.md` for shell patterns and automation strategies

## Quick Reference

**Most Common Operations:**
```bash
# Create PR — see the create-pr skill (template + pre-commit handling)
gh pr list                                                  # List PRs
gh pr view 123                                              # View PR details
gh pr checks 123                                            # Check PR status
# Merge PR — see the merge-pr skill (checks readiness + rights first)
gh pr comment 123 --body "LGTM"                            # Comment on PR
gh issue create --title "Title" --body "Description"       # Create issue
gh workflow run workflow-name                               # Run workflow
gh repo view --web                                          # Open repo in browser
gh api repos/{owner}/{repo}/pulls/{pr_number}              # Direct API call
```

## Testing & Validation

**Verify this skill activates on:**
- "list open PRs" / "view PR 123" / "check PR status"
- "manage GitHub issues" / "create an issue for this bug"
- "run this GitHub Actions workflow" / "query the GitHub API for pull request details"

**Verify it does NOT activate on:**
- "create a PR" / "open a pull request" → `create-pr`
- "merge this PR" / "is this ready to merge" → `merge-pr`
- "review this PR" / "approve this PR" / "request changes on PR #42" → `collaborating-on-a-pr`

**Quality gates:**
- [ ] PR creation, merging, and reviewer-action requests are always redirected to `create-pr`, `merge-pr`,
      and `collaborating-on-a-pr` respectively — never handled directly from this skill's own reference
      material
- [ ] The `gh pr review`/`gh pr comment` examples in this skill are never run standalone as a real review
      action — they stay reference material only, per this skill's own description
- [ ] The LINEAR/`NOLINEAR:` PR title convention is always presented as an optional, org-specific example
      — never asserted as this project's actual convention
- [ ] `allowed-tools` stays scoped to its current narrowed grant (`gh pr`, `gh issue`, `gh repo`
      view/clone/create/set-default, `gh workflow`, `gh run`, `gh api`, `gh config`) — it never silently
      widens back to a blanket `Bash(gh:*)`, and never gains `gh secret`, `gh auth`, `gh repo delete`, or
      `gh variable`

## Resources

### references/pr-operations.md

Comprehensive pull request operations including:
- Detailed PR creation patterns (LINEAR integration, body from file, targeting branches)
- Viewing and filtering strategies
- Review workflows and approval patterns
- PR lifecycle management
- Bulk operations and automation examples

Load this reference when working with complex PR workflows or bulk operations.

### references/issue-operations.md

Detailed issue management examples including:
- Issue creation with labels and assignees
- Advanced filtering and search
- Issue lifecycle and state management
- Bulk operations on multiple issues
- Integration with PRs and projects

Load this reference when managing issues at scale or setting up issue workflows.

### references/workflow-operations.md

Advanced GitHub Actions workflow operations including:
- Workflow triggers and manual runs
- Run monitoring and debugging
- Artifact management
- Secrets and variables
- Performance optimization strategies

Load this reference when working with CI/CD workflows or debugging failed runs.

### references/best-practices.md

Shell scripting patterns and automation strategies including:
- Output formatting (JSON, templates, jq)
- Pagination and large result sets
- Error handling and retry logic
- Bulk operations and parallel execution
- Enterprise GitHub patterns
- Performance optimization

Load this reference when building automation scripts or handling enterprise deployments.

### references/api-reference.md

Contains comprehensive GitHub REST API endpoint documentation including:
- Complete API endpoint reference with examples
- Request/response formats
- Authentication patterns
- Rate limiting guidance
- Webhook configurations
- Advanced GraphQL query patterns

Load this reference when performing complex API operations or when needing detailed endpoint specifications.