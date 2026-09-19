# Modern GitHub Actions Features Reference

This reference covers validation of modern GitHub Actions features including reusable workflows, attestations, OIDC authentication, and more.

**Staleness note:** limits, claims, and dates below reflect this file's last content update (November
2025). If that looks old relative to today, verify current values via `WebSearch` before treating this
file as current.

## Reusable Workflows

### Validation Points
- `workflow_call` trigger configuration
- Required and optional inputs with correct types
- Secrets declaration and usage
- Outputs definition

### Example

**Size exception:** this block is already trimmed to the minimum needed to show the full
`workflow_call` contract in one place (inputs, secrets, and outputs together) — splitting it further
would separate parts of a single contract that only make sense read together.

```yaml
# Reusable workflow (.github/workflows/reusable-deploy.yml)
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      deploy-token:
        required: true
    outputs:
      deployment-url:
        value: ${{ jobs.deploy.outputs.url }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - id: deploy
        run: echo "url=https://example.com" >> $GITHUB_OUTPUT
```

### Common Errors
- Incorrect input types (string, number, boolean)
- Missing required secrets
- Invalid output references

### Workflow Limits (November 2025)

GitHub Actions increased reusable workflow limits:
- **Nested workflows**: Up to 10 levels (previously 4)
- **Total workflows per run**: Up to 50 workflows (previously 20)

This enables complex workflow compositions and better code reuse.

---

## SBOM and Build Provenance Attestations

### Validation Points
- Correct permissions (`id-token: write`, `attestations: write`)
- Valid artifact paths
- Proper attestation action usage

### Example

```yaml
permissions:
  id-token: write
  contents: read
  attestations: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - run: syft ./src -o spdx-json > sbom.spdx.json

      - uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6  # v4.2.2
        with:
          subject-path: 'dist/*.tar.gz'
          sbom-path: 'sbom.spdx.json'

      - uses: actions/attest-build-provenance@977bb373ede98d70efdf65b84cb5f73e068dcc2a  # v3.0.0
        with:
          subject-path: 'dist/*.tar.gz'
```

### Common Errors
- Missing required permissions
- Invalid subject-path glob patterns
- Incorrect SBOM format

---

## OIDC Authentication

### Validation Points
- Correct permissions (`id-token: write`)
- Valid audience claims
- Proper OIDC provider configuration
- Token claim validation in receiving systems

### Available Token Claims (November 2025)

| Claim | Description |
|-------|-------------|
| `repository` | Repository name |
| `ref` | Git ref (branch/tag) |
| `sha` | Commit SHA |
| `workflow` | Workflow name |
| `run_id` | Workflow run ID |
| `run_attempt` | Attempt number |
| `check_run_id` | **NEW** - Specific check run ID for the job |
| `actor` | User who triggered the workflow |
| `environment` | Deployment environment (if applicable) |

### Example: AWS OIDC

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@7474bc4690e29a8392af63c5b98e7449536d5c3a  # v4.3.1
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1

      - name: Deploy to AWS
        run: aws s3 sync ./build s3://my-bucket/
```

### AWS IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:sub": "repo:org/repo:ref:refs/heads/main",
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

---

## Deployment Environments

### Validation Points
- Environment name configuration
- Protection rules compatibility
- Required reviewers setup
- Environment variables and secrets scope

### Example

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - run: ./deploy.sh staging

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment:
      name: production
      url: https://prod.example.com
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - run: ./deploy.sh production
```

### Common Errors
- Undefined environment names
- Missing URL for environment tracking
- Incorrect environment variable scope

---

## Job Summaries

### Validation Points
- Correct usage of `$GITHUB_STEP_SUMMARY`
- Valid Markdown formatting
- Proper escaping of dynamic content

### Example

```yaml
steps:
  - name: Run tests
    id: tests
    run: |
      # Run tests and capture results
      npm test 2>&1 | tee test-output.txt
      PASSED=$(grep -c "PASS" test-output.txt || echo 0)
      FAILED=$(grep -c "FAIL" test-output.txt || echo 0)
      echo "passed=$PASSED" >> $GITHUB_OUTPUT
      echo "failed=$FAILED" >> $GITHUB_OUTPUT

  - name: Generate summary
    run: |
      echo "## Test Results" >> $GITHUB_STEP_SUMMARY
      echo "" >> $GITHUB_STEP_SUMMARY
      echo "| Status | Count |" >> $GITHUB_STEP_SUMMARY
      echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
      echo "| Passed | ${{ steps.tests.outputs.passed }} |" >> $GITHUB_STEP_SUMMARY
      echo "| Failed | ${{ steps.tests.outputs.failed }} |" >> $GITHUB_STEP_SUMMARY
```

**Note:** Job summaries are runtime features - actionlint validates script syntax but not summary content.

---

## Container Jobs

### Validation Points
- Valid container image references
- Correct volume mounts
- Environment variable configuration
- Service container networking

### Example

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: node:24
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - run: npm ci
      - env:
          DATABASE_URL: postgres://postgres:postgres@postgres:5432/testdb
        run: npm test
```

A container job can define multiple `services:` entries the same way (each reachable by its service
name as hostname, e.g. `redis:6379`), and a service's `options:` can add health-check flags
(`--health-cmd`/`--health-interval`/etc.) — omitted above to keep the example focused on the
container-to-service networking pattern itself.

### Common Errors
- Invalid image tags
- Incorrect volume mount syntax
- Service container networking issues
- Missing health checks for services

---

## Matrix Strategies

### Validation Points
- Matrix values must be arrays
- Valid matrix variable references
- Proper include/exclude syntax

### Example

**Size exception:** this block is already trimmed to the minimum needed to show `exclude:`/`include:`
together with a base matrix — either alone wouldn't demonstrate the interaction this section documents.

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [20, 22, 24]
        exclude:
          - os: macos-latest
            node: 20
        include:
          - os: ubuntu-latest
            node: 24
            experimental: true
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - uses: actions/setup-node@6044e13b5dc448c55e2357c09f80417699197238  # v6.2.0
        with:
          node-version: ${{ matrix.node }}
      - run: npm test
```

---

## Concurrency Control

### Validation Points
- Valid concurrency group names
- Proper cancel-in-progress usage

### Example

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - run: npm ci && npm run build
```

This prevents redundant runs while protecting main branch runs from cancellation.