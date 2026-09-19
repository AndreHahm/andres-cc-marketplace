# Advanced GitHub Actions Triggers

**Last Updated:** May 2026

## Overview

This guide covers advanced trigger patterns for GitHub Actions workflows beyond the basic `push`, `pull_request`, and `schedule` triggers. These patterns enable workflow orchestration, external integrations, ChatOps, and complex automation scenarios.

## Table of Contents

1. [Workflow Orchestration](#workflow-orchestration)
2. [External Integration](#external-integration)
3. [ChatOps Patterns](#chatops-patterns)
4. [Deployment Triggers](#deployment-triggers)
5. [Advanced Path Filtering](#advanced-path-filtering)
6. [Security Patterns](#security-patterns)
7. [GitHub Services Integration](#github-services-integration)
8. [Best Practices](#best-practices)

---

## Workflow Orchestration

### workflow_run Trigger

The `workflow_run` trigger allows you to chain workflows together, running one workflow after another completes. This is the **recommended pattern** for handling external pull requests securely.

#### Basic Syntax

```yaml
name: Deploy Application

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main, staging]
```

#### Trigger Types

- `requested` - Workflow run was requested
- `in_progress` - Workflow run is currently running
- `completed` - Workflow run has finished (success, failure, or cancelled)

#### Use Cases

**1. Deployment After CI Success**

```yaml
# deploy.yml - Separate deployment workflow
on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: Download build artifacts from CI
        uses: actions/download-artifact@c850b930e6ba138125429b7e5c93fc707a7f8427 # v4.1.4
        with:
          name: build-artifacts
          run-id: ${{ github.event.workflow_run.id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
      - name: Report deployed commit
        env:
          HEAD_SHA: ${{ github.event.workflow_run.head_sha }}
        run: echo "Deploying commit $HEAD_SHA"
```

See `examples/triggers/workflow-orchestration.yml` (+ its 3 companion files, `-security-scan.yml`/`-deploy.yml`/`-performance-test.yml`) for the complete, runnable workflow-chaining example — one workflow definition per file, since GitHub Actions doesn't support multiple workflows in a single file, chained together via `workflow_run`.

**2. Security Scanning for External PRs**

```yaml
# security-scan.yml - Runs after CI for external PRs
name: Security Scan

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

permissions:
  security-events: write
  contents: read

jobs:
  scan:
    # Only scan if CI passed and it was a PR
    if: github.event.workflow_run.conclusion == 'success' && github.event.workflow_run.event == 'pull_request'
    runs-on: ubuntu-latest

    steps:
      - name: Checkout PR code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ github.event.workflow_run.head_sha }}

      - name: Run security scan  # scanning without exposing secrets to the PR
        run: npm audit --audit-level=high
```

#### Accessing Workflow Run Information

```yaml
steps:
  - name: Get workflow run details
    env:
      RUN_NAME: ${{ github.event.workflow_run.name }}
      RUN_CONCLUSION: ${{ github.event.workflow_run.conclusion }}
      RUN_HEAD_SHA: ${{ github.event.workflow_run.head_sha }}
      RUN_HEAD_BRANCH: ${{ github.event.workflow_run.head_branch }}
      RUN_ID: ${{ github.event.workflow_run.id }}
      RUN_EVENT: ${{ github.event.workflow_run.event }}
    run: |
      echo "Workflow: $RUN_NAME"
      echo "Conclusion: $RUN_CONCLUSION"
      echo "Head SHA: $RUN_HEAD_SHA"
      echo "Head Branch: $RUN_HEAD_BRANCH"
      echo "Run ID: $RUN_ID"
      echo "Event: $RUN_EVENT"
```

#### Security Benefits

✅ **Safer than `pull_request_target`** for external PRs:
- Runs with workflow file from target branch (not PR)
- No access to PR code by default
- Secrets are safe from malicious PRs
- Must explicitly checkout PR code if needed

---

## External Integration

### repository_dispatch Trigger

The `repository_dispatch` trigger allows external systems to trigger workflows via the GitHub API. This enables integration with webhooks, custom dashboards, monitoring systems, and other external tools.

#### Basic Syntax

```yaml
name: Handle External Event

on:
  repository_dispatch:
    types: [deploy-prod, deploy-staging, run-migration, rebuild-cache]
```

#### Event Types

Event types are custom strings you define. Common patterns:
- `deploy-<environment>` - Deployment triggers
- `run-<task>` - Task execution
- `notify-<event>` - Notification handling

#### Triggering via API

**Using curl:**

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{
    "event_type": "deploy-prod",
    "client_payload": {
      "version": "v1.2.3",
      "requestor": "monitoring-system",
      "environment": "production",
      "rollback": false
    }
  }'
```

**Using Python:**

```python
import requests

def trigger_deployment(repo, token, version, environment):
    url = f"https://api.github.com/repos/{repo}/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "event_type": f"deploy-{environment}",
        "client_payload": {
            "version": version,
            "requestor": "api",
            "environment": environment
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 204
```

**Using Node.js (Octokit):**

```javascript
const { Octokit } = require("@octokit/rest");

const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

await octokit.repos.createDispatchEvent({
  owner: "OWNER",
  repo: "REPO",
  event_type: "deploy-prod",
  client_payload: {
    version: "v1.2.3",
    requestor: "api",
    environment: "production"
  }
});
```

#### Handling Dispatch Events

```yaml
on:
  repository_dispatch:
    types: [deploy-prod, deploy-staging, deploy-dev]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout specific version
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ github.event.client_payload.version }}
      - name: Report deployment target
        env:
          DEPLOY_ENV: ${{ github.event.client_payload.environment }}
        run: echo "Deploying to $DEPLOY_ENV"
```

See `examples/triggers/repository-dispatch.yml` for the complete, runnable version (payload parsing, output-passing between steps, and full deployment job).

#### Use Cases

**1. Webhook Integration**

Trigger workflows from external monitoring/alerting systems:

```yaml
on:
  repository_dispatch:
    types: [incident-detected, performance-degradation]

jobs:
  handle-alert:
    runs-on: ubuntu-latest
    steps:
      - name: Process alert
        env:
          SEVERITY: ${{ github.event.client_payload.severity }}
          MESSAGE: ${{ github.event.client_payload.message }}
        run: |
          echo "Alert received: $MESSAGE (Severity: $SEVERITY)"

          if [[ "$SEVERITY" == "critical" ]]; then
            # Trigger emergency procedures
            echo "Initiating critical incident response"
          fi
```

**2. Manual Trigger from Dashboard**

Custom deployment dashboard that triggers GitHub Actions:

```yaml
on:
  repository_dispatch:
    types: [dashboard-deploy]

jobs:
  deploy:
    runs-on: ubuntu-latest

    environment:
      name: ${{ github.event.client_payload.environment }}

    steps:
      - name: Validate payload
        env:
          DEPLOY_VERSION: ${{ github.event.client_payload.version }}
          DEPLOY_APPROVER: ${{ github.event.client_payload.approver }}
        run: |
          # Required fields: version, approver
          if [[ -z "$DEPLOY_VERSION" || -z "$DEPLOY_APPROVER" ]]; then
            echo "Error: version and approver are required"
            exit 1
          fi

      - name: Deploy
        env:
          DEPLOY_VERSION: ${{ github.event.client_payload.version }}
          DEPLOY_APPROVER: ${{ github.event.client_payload.approver }}
        run: |
          echo "Deploying version $DEPLOY_VERSION"
          echo "Approved by: $DEPLOY_APPROVER"
```

**3. Cross-Repository Triggers**

Trigger workflow in repo A from repo B:

```yaml
# In Repository A
on:
  repository_dispatch:
    types: [dependency-updated]

jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - name: Rebuild with new dependency
        env:
          DEPENDENCY_NAME: ${{ github.event.client_payload.dependency }}
          DEPENDENCY_VERSION: ${{ github.event.client_payload.version }}
        run: |
          echo "Dependency $DEPENDENCY_NAME updated to $DEPENDENCY_VERSION"
          # Rebuild logic
```

#### Security Considerations

🔒 **Token Security:**
- Use a Personal Access Token (PAT) or GitHub App token
- Minimum required scope: `repo` (for private repos) or `public_repo` (for public repos)
- Store token in secrets, never in code
- Rotate tokens regularly

🔒 **Payload Validation:**
- Always validate `client_payload` fields
- Sanitize user input to prevent injection
- Use allowlists for critical fields

```yaml
- name: Validate environment
  env:
    ENV: ${{ github.event.client_payload.environment }}
  run: |
    # Only allow specific environments
    if [[ ! "$ENV" =~ ^(dev|staging|production)$ ]]; then
      echo "Error: Invalid environment: $ENV"
      exit 1
    fi
```

---

## ChatOps Patterns

### issue_comment Trigger

The `issue_comment` trigger allows you to implement ChatOps - executing workflows via commands in issue or PR comments.

#### Basic Syntax

```yaml
name: ChatOps Commands

on:
  issue_comment:
    types: [created, edited]
```

#### Comment Types

- `created` - New comment posted
- `edited` - Comment was edited
- `deleted` - Comment was deleted (rarely used)

#### Implementing ChatOps Commands

**Minimal shape** (security check, parse command, act):

```yaml
on:
  issue_comment:
    types: [created]

jobs:
  deploy:
    # Security checks (CRITICAL!)
    if: |
      github.event.issue.pull_request &&
      startsWith(github.event.comment.body, '/deploy') &&
      contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.comment.author_association)
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      deployments: write
    steps:
      - name: Parse deploy command
        id: parse
        env:
          COMMENT_BODY: ${{ github.event.comment.body }}
        run: |
          ENV=$(echo "$COMMENT_BODY" | grep -oP '/deploy\s+\K\w+' || echo 'staging')
          echo "environment=$ENV" >> $GITHUB_OUTPUT
      - name: Report deployment target
        env:
          DEPLOY_ENV: ${{ steps.parse.outputs.environment }}
        run: echo "Deploying to $DEPLOY_ENV"
```

See `examples/triggers/chatops-commands.yml` for the complete, runnable 7-step example (comment reaction,
PR-branch resolution, checkout, deploy, success/failure result comments).

#### Common ChatOps Commands

**1. /deploy [environment]**
```yaml
startsWith(github.event.comment.body, '/deploy')
```

**2. /run-tests [suite]**
```yaml
startsWith(github.event.comment.body, '/run-tests')
```

**3. /benchmark**
```yaml
contains(github.event.comment.body, '/benchmark')
```

**4. /approve**
```yaml
github.event.comment.body == '/approve'
```

#### Permission Checking

**Author Association Levels:**

- `OWNER` - Repository owner
- `MEMBER` - Organization member
- `COLLABORATOR` - Repository collaborator
- `CONTRIBUTOR` - Has contributed to repo
- `FIRST_TIME_CONTRIBUTOR` - First contribution
- `FIRST_TIMER` - First time interacting
- `NONE` - No association

**Check permissions:**

```yaml
# Only owners and members
if: contains(fromJSON('["OWNER", "MEMBER"]'), github.event.comment.author_association)

# More permissive
if: contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"]'), github.event.comment.author_association)
```

**Advanced permission check with team membership:**

```yaml
steps:
  - name: Check team membership
    uses: actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea # v7.0.1
    with:
      script: |
        const teams = ['deployment-team', 'admin-team'];
        const user = context.payload.comment.user.login;

        let authorized = false;
        for (const team of teams) {
          try {
            await github.rest.teams.getMembershipForUserInOrg({
              org: context.repo.owner,
              team_slug: team,
              username: user
            });
            authorized = true;
            break;
          } catch (error) {
            // User not in this team
          }
        }

        if (!authorized) {
          core.setFailed(`User ${user} not authorized`);
        }
```

#### Security Best Practices for ChatOps

🔒 **Always validate:**
1. Command is from a PR: `github.event.issue.pull_request`
2. User has permissions: `github.event.comment.author_association`
3. Command format is valid
4. Arguments are sanitized

🔒 **Never:**
- Execute arbitrary code from comments
- Use comment content in shell commands without validation
- Trust external PR authors for sensitive operations

🔒 **Use environment variables:**

```yaml
# BAD - Command injection risk
- run: echo ${{ github.event.comment.body }}

# GOOD - Safe
- env:
    COMMENT: ${{ github.event.comment.body }}
  run: echo "$COMMENT"
```

---

## Deployment Triggers

### deployment and deployment_status

These triggers integrate with GitHub's deployment API.

#### deployment Trigger

```yaml
name: Handle Deployment

on:
  deployment:

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Get deployment info
        env:
          DEPLOY_ENVIRONMENT: ${{ github.event.deployment.environment }}
          DEPLOY_REF: ${{ github.event.deployment.ref }}
          DEPLOY_TASK: ${{ github.event.deployment.task }}
          DEPLOY_PAYLOAD: ${{ toJSON(github.event.deployment.payload) }}
        run: |
          echo "Environment: $DEPLOY_ENVIRONMENT"
          echo "Ref: $DEPLOY_REF"
          echo "Task: $DEPLOY_TASK"
          echo "Payload: $DEPLOY_PAYLOAD"
```

#### deployment_status Trigger

```yaml
name: Post-Deployment Actions

on:
  deployment_status:

jobs:
  notify:
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest

    steps:
      - name: Send notification
        env:
          DEPLOY_ENVIRONMENT: ${{ github.event.deployment.environment }}
        run: |
          echo "Deployment to $DEPLOY_ENVIRONMENT succeeded"
          # Send Slack/email notification
```

---

## Advanced Path Filtering

### Complex Path Patterns

```yaml
on:
  push:
    paths:
      # Include specific paths
      - 'src/**'
      - 'lib/**/*.js'

      # Exclude paths (ignore)
      - '!src/**/*.md'
      - '!src/**/*.test.js'
      - '!**/__tests__/**'

      # Only specific file types
      - '**.py'
      - '**.yaml'
      - '**.yml'
```

### Path Filters with Multiple Triggers

```yaml
on:
  pull_request:
    paths:
      - 'backend/**'
  push:
    branches: [main]
    paths:
      - 'backend/**'
```

### Monorepo Path Filtering

```yaml
on:
  pull_request:
    paths:
      - 'packages/frontend/**'
      - 'packages/shared/**'
      - '!packages/**/README.md'
      - '!packages/**/*.test.*'
```

---

## Security Patterns

### pull_request vs pull_request_target

| Trigger | Context | Secrets | Use Case | Risk Level |
|---------|---------|---------|----------|------------|
| `pull_request` | PR branch | ❌ No access | Standard PR validation | ✅ Safe |
| `pull_request_target` | Target branch | ✅ Full access | Write to PR from fork | ⚠️ High risk |
| `workflow_run` | Target branch | ✅ Full access | Post-CI for external PRs | ✅ Safe (if used correctly) |

### Safe Patterns

**✅ Standard PR validation:**

```yaml
on:
  pull_request:
    branches: [main]

# Safe: No secrets exposed, runs PR code in isolation
```

**✅ Post-CI processing with workflow_run:**

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

# Safe: Runs after CI, has secrets, but uses target branch code
```

**⚠️ Dangerous: pull_request_target**

```yaml
on:
  pull_request_target:
    branches: [main]

# DANGEROUS: External PRs can access secrets!
# Only use if you explicitly checkout target branch code
```

### Securing pull_request_target

If you must use `pull_request_target`:

```yaml
on:
  pull_request_target:

jobs:
  comment:
    runs-on: ubuntu-latest

    steps:
      # SAFE: Don't checkout PR code
      - name: Comment on PR
        uses: actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea # v7.0.1
        with:
          script: |
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Thanks for your contribution!'
            });

      # UNSAFE: Never do this!
      # - uses: actions/checkout@v4
      #   with:
      #     ref: ${{ github.event.pull_request.head.sha }}
```

---

## GitHub Services Integration

### check_run and check_suite

```yaml
on:
  check_run:
    types: [created, rerequested, completed]

on:
  check_suite:
    types: [completed, requested]
```

### status

```yaml
on:
  status:

jobs:
  handle-status:
    runs-on: ubuntu-latest
    steps:
      - name: Check status
        env:
          EVENT_STATE: ${{ github.event.state }}
          EVENT_CONTEXT: ${{ github.event.context }}
        run: |
          echo "State: $EVENT_STATE"
          echo "Context: $EVENT_CONTEXT"
```

### package

```yaml
on:
  package:
    types: [published, updated]
```

---

## Best Practices

### 1. Choose the Right Trigger

| Scenario | Recommended Trigger |
|----------|-------------------|
| Standard PR validation | `pull_request` |
| External PR with secrets | `workflow_run` after `pull_request` |
| Deploy after CI | `workflow_run` |
| Manual dashboard trigger | `repository_dispatch` |
| ChatOps commands | `issue_comment` |
| Scheduled cleanup | `schedule` |
| External webhook | `repository_dispatch` |

### 2. Security Checklist

- [ ] Validate user permissions
- [ ] Sanitize all inputs
- [ ] Use environment variables, not direct interpolation
- [ ] Never trust external PR code with secrets
- [ ] Use `workflow_run` instead of `pull_request_target` when possible
- [ ] Implement allowlists for critical operations
- [ ] Log all security-sensitive actions

### 3. Performance Optimization

- Use `workflow_run` to separate slow jobs from fast CI
- Filter triggers with `paths` to avoid unnecessary runs
- Use `concurrency` to cancel outdated runs
- Implement conditional job execution

### 4. Debugging

**Check trigger details:**

```yaml
- name: Debug trigger info
  env:
    EVENT_NAME: ${{ github.event_name }}
    EVENT_JSON: ${{ toJSON(github.event) }}
  run: |
    echo "Event name: $EVENT_NAME"
    echo "Event: $EVENT_JSON"
```

**Test repository_dispatch locally:**

```bash
# Set token
export GITHUB_TOKEN="your_token"

# Trigger workflow
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{"event_type":"test","client_payload":{"debug":true}}'
```

---

## Example Workflows

See the `examples/triggers/` directory for complete working examples:

- `workflow-orchestration.yml` (+ 3 companion files) - CI → Deploy workflow chaining
- `repository-dispatch.yml` - External API triggers
- `chatops-commands.yml` - Full ChatOps implementation

---

## Resources

- [GitHub Actions Events Documentation](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Security Hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [GitHub API - Repository Dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
