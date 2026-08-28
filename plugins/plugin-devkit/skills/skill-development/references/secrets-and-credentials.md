# Preventing Secret Leaks in Claude Code Skills

Secrets are credentials that grant access to systems: API keys, passwords, tokens, SSH keys, and connection strings. They're dangerous in skills because they can be accidentally committed to git, loaded into Claude's context, or exposed in logs. This guide covers detection, prevention, and safe handling patterns.

## Table of Contents

- [What Are Secrets](#what-are-secrets)
- [Why Secrets in Skills Are Dangerous](#why-secrets-in-skills-are-dangerous)
- [Detection Patterns](#detection-patterns)
- [Good vs Bad Patterns](#good-vs-bad-patterns)
- [Handling Secrets in Skills](#handling-secrets-in-skills)
- [Git Safety](#git-safety)
- [Testing Without Exposing Secrets](#testing-without-exposing-secrets)
- [Validation Checklist](#validation-checklist)
- [References & Tools](#references--tools)

## What Are Secrets

Secrets are ANY credentials that grant access to systems or data:

- **API Keys:** GitHub tokens, AWS keys, OpenAI keys, Stripe keys
- **Passwords:** Database passwords, SSH passphrases, service account passwords
- **Tokens:** OAuth refresh tokens, JWT tokens, session tokens, authorization headers
- **Connection Strings:** `postgres://user:password@host/db` (embedded credentials)
- **Private Keys:** SSH private keys, TLS certificates, encryption keys
- **Certificates:** Client certificates, self-signed certs with embedded secrets
- **Application Secrets:** Django SECRET_KEY, encryption salts, signing keys

**The rule:** If revealing it compromises security or access, it's a secret. Treat it like one.

## Why Secrets in Skills Are Dangerous

### 1. Git History Exposure
Once committed to git, secrets persist in history forever. Even deleting the file doesn't remove it from `git log`. Attackers searching GitHub for exposed credentials find them automatically.

**Risk:** Any secret you commit can be found and exploited, even if you delete it immediately.

### 2. Context Loading into Claude
When Claude loads your skill, if secrets are in the source code, they're loaded into Claude's context window. If Claude is compromised or logs are accessed, secrets leak.

**Risk:** Secrets in SKILL.md, scripts, or reference files are visible to Claude.

### 3. Compliance Violations
Organizations with SOC 2, HIPAA, PCI DSS, or GDPR compliance cannot store secrets in code. Audits will find violations. Fines and certification loss follow.

**Risk:** Hardcoded secrets = audit failure = compliance violation = penalties.

### 4. Attack Vectors
- GitHub scanning: Attackers automatically scan repos for exposed credentials
- Accidental sharing: Sharing skill code for feedback accidentally exposes secrets
- Log files: If scripts log environment variables or API responses, secrets are logged
- Backup systems: If skills are backed up without care, secrets are backed up

**Risk:** Multiple ways for secrets to leak once they're in the codebase.

## Detection Patterns

### Pattern Matching
Common secret-shaped variable names and value formats that should trigger alerts:

| Variable name | Example value shape |
|---|---|
| `API_KEY` | `sk-` prefix followed by random characters |
| `PASSWORD` | a plaintext password string |
| `SECRET_TOKEN` | `ghp_` prefix (GitHub) followed by random characters |
| `CREDENTIALS` | a JSON blob with `username`/`password` fields |
| `DATABASE_URL` | a connection string with embedded `user:password@host` |
| `AWS_SECRET_ACCESS_KEY` | a long random string |
| `GITHUB_TOKEN` | `ghp_` prefix followed by random characters |

### File Patterns to Never Commit
- `.env` or `.env.local` — Local environment configuration
- `.env.*.local` — Environment-specific secrets
- `credentials.json` — Service account credentials (Google, AWS)
- `secrets.yml` or `secrets.yaml` — YAML secrets files
- `.aws/credentials` — AWS credential files
- `.ssh/id_*` — SSH private keys
- `.git/config` — Git config with embedded credentials
- `*.pem`, `*.key`, `*.p12` — Certificate and key files

### Git Scanning Tools

**Use these tools to detect secrets BEFORE committing:**

- **git-secrets** — GitHub's official tool for preventing secret commits
- **truffleHog** — Searches git history for high-entropy strings and known patterns
- **gitleaks** — Scans repos for secrets using regex patterns and entropy detection
- **GitHub Secret Scanning** — GitHub's built-in scanning for known secret types

## Good vs Bad Patterns

### Pattern 1: API Key Handling

❌ **BAD: Hardcoded API key**
```python
# scripts/fetch_data.py
SERVICE_CREDENTIAL = "sk-proj-EXAMPLE1"

def fetch_from_service():
    headers = {"Authorization": f"Bearer {SERVICE_CREDENTIAL}"}
    response = requests.get("https://api.service.com/data", headers=headers)
    return response.json()
```

✅ **GOOD: Environment variable + validation**
```python
# scripts/fetch_data.py
import os
import sys

def fetch_from_service():
    credential = os.getenv("API_KEY")
    if not credential:
        print("ERROR: API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {credential}"}
    response = requests.get("https://api.service.com/data", headers=headers)
    return response.json()
```

**Prerequisites section in SKILL.md:**
```
- Environment variable: `API_KEY` (get from https://dashboard.service.com/api-keys)
```

---

### Pattern 2: Database Connection String

❌ **BAD: Hardcoded credentials**
```python
# scripts/migrate.py
DB_URL = "postgres://admin:SecurePass123@db.example.com:5432/myapp"

def run_migration():
    engine = create_engine(DB_URL)
    # migration logic
```

✅ **GOOD: Environment variable with validation**
```python
# scripts/migrate.py
import os
import sys

def run_migration():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Format: postgres://user:password@host/db", file=sys.stderr)
        sys.exit(1)

    if "@" not in db_url:
        print("ERROR: DATABASE_URL missing credentials", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(db_url)
    # migration logic
```

**SKILL.md Prerequisites:**
```
- `DATABASE_URL` environment variable: postgres://user:password@host/db
- Retrieve from https://console.example.com/databases/connection-strings
```

---

### Pattern 3: .env File Handling

❌ **BAD: .env file in git**
```bash
# Committed to repo (BAD!)
# .env
SERVICE_CREDENTIAL=sk-abc123
DB_AUTH_VALUE=MyPassword
STRIPE_CREDENTIAL=sk_live_51234567890
```

✅ **GOOD: .env template, .gitignore protection**
```bash
# .env.example (committed to repo - no real secrets!)
SERVICE_CREDENTIAL=YOUR_SERVICE_CREDENTIAL_HERE
DB_AUTH_VALUE=YOUR_DB_AUTH_VALUE_HERE
STRIPE_CREDENTIAL=YOUR_STRIPE_CREDENTIAL_HERE
```

```bash
# .gitignore (prevents .env from being committed)
.env
.env.local
.env.*.local
```

**SKILL.md Prerequisites:**
```
1. Copy .env.example to .env: `cp .env.example .env`
2. Edit .env and fill in actual values from your service
3. Run validation: `bash scripts/validate-env.sh`
```

---

### Pattern 4: Documentation Examples

❌ **BAD: Real secrets in examples**

A "## Example Usage" section in SKILL.md showing a working `curl` command against
`https://api.github.com/user`, with a real personal access token spelled out as the request's
Bearer credential — copy-pasteable, but now a leaked credential sitting in your docs.

✅ **GOOD: Placeholder examples**

The same `curl` command, but with the Bearer credential replaced by an obvious placeholder
(e.g. `YOUR_GITHUB_TOKEN`) instead of a real value:

Set `YOUR_GITHUB_TOKEN` to your personal access token from https://github.com/settings/tokens

---

### Pattern 5: Git Remote URLs

❌ **BAD: Credentials in git config**
```bash
# .git/config (credentials embedded in URL)
[remote "origin"]
    url = https://user:password@github.com/org/repo.git
```

✅ **GOOD: SSH or credential helper**
```bash
# .git/config (credentials via SSH)
[remote "origin"]
    url = git@github.com:org/repo.git
```

Or use git credential helper:
```bash
git config credential.helper store
# Then git will prompt once and cache credentials securely
```

---

### Pattern 6: Bash Scripts with Tokens

❌ **BAD: Token hardcoded in script**
```bash
#!/bin/bash
# scripts/deploy.sh
RELEASE_CREDENTIAL="dt_abc123def456"

# Sent as the request's Bearer credential to https://deploy.service.com/release below --
# hardcoded here, so it ships with the script wherever it goes.
```

✅ **GOOD: Token from environment with validation**
```bash
#!/bin/bash
# scripts/deploy.sh

: "${DEPLOY_TOKEN:?ERROR: DEPLOY_TOKEN env var not set}"

# Sent as the request's Bearer credential to https://deploy.service.com/release below,
# read from the already-validated environment variable instead of a hardcoded value.
```

**SKILL.md:**
```
- `DEPLOY_TOKEN` environment variable (get from https://service.com/settings/tokens)
```

## Handling Secrets in Skills

### 1. Use Environment Variables

Store all secrets in environment variables. Never hardcode them.

**In Python:**
```python
import os

credential = os.getenv("API_KEY")
if not credential:
    raise ValueError("API_KEY environment variable not set")
```

**In Bash:**
```bash
: "${API_KEY:?ERROR: API_KEY env var not set}"
```

### 2. Validate They're Set

Check that required environment variables are present before running. Fail fast with clear error messages.

```python
required_vars = ["API_KEY", "DATABASE_URL"]
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)
```

### 3. Provide Clear Error Messages

When a secret is missing, tell Claude exactly what to do:

```python
credential = os.getenv("API_KEY")
if not credential:
    print("ERROR: API_KEY not set", file=sys.stderr)
    print("Get it from: https://dashboard.service.com/api-keys", file=sys.stderr)
    sys.exit(1)
```

### 4. Never Bundle Secrets

Secrets should NEVER be in:
- SKILL.md body or frontmatter
- Any reference file
- Scripts or source code
- Comments or documentation

### 5. Document Credential Sources

In the Prerequisites section, tell Claude where to get each secret:

```markdown
## Prerequisites

- Environment variables (required):
  - `GITHUB_TOKEN`: Personal access token from https://github.com/settings/tokens (create with 'repo' scope)
  - `DATABASE_URL`: Connection string from your database provider
  - `API_KEY`: From https://dashboard.service.com/api-keys

Set them before running:
```bash
export GITHUB_TOKEN=your_token_here
export DATABASE_URL=postgres://user:password@host/db
export API_KEY=sk_live_1234567890abcdef
```

Then validate:
```bash
bash scripts/validate-env.sh
```
```

## Git Safety

### Pre-Commit Hooks

Use git hooks to prevent secrets from being committed.

**Install git-secrets (GitHub's official tool):**
```bash
brew install git-secrets  # macOS
# or
apt-get install git-secrets  # Linux

# Configure for your repo
cd /path/to/skill/repo
git secrets --install
git secrets --register-aws
```

**Or create a manual hook:**

Create `.git/hooks/pre-commit` (executable):
```bash
#!/bin/bash

# Check for common secret patterns
patterns=(
    "api_key\s*=\s*['\"]?[a-zA-Z0-9_-]{20,}['\"]?"
    "password\s*=\s*['\"].*['\"]"
    "secret\s*=\s*['\"].*['\"]"
    "token\s*=\s*['\"]?ghp_[a-zA-Z0-9_]{36,255}['\"]?"
    "AWS_SECRET_ACCESS_KEY"
)

for pattern in "${patterns[@]}"; do
    if git diff --cached | grep -E "$pattern"; then
        echo "ERROR: Possible secret detected in staged changes"
        echo "Pattern: $pattern"
        exit 1
    fi
done

exit 0
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### .gitignore Patterns

Add to `.gitignore` to prevent secret files from being committed:

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — a security-relevant complete pattern set; trimming risks silently dropping a real credential-file pattern from the recommendation.

```gitignore
# Environment files with secrets
.env
.env.local
.env.*.local
.env.production
.env.staging

# Credential files
credentials.json
secrets.yml
secrets.yaml
~/.aws/credentials
~/.ssh/id_*

# Certificate and key files
*.pem
*.key
*.p12
*.pfx

# Application-specific
.api_key
API_KEY.txt
```

### If Secrets Are Already Committed

If you accidentally commit a secret, you must remediate immediately:

**1. Rotate the credential** — The compromised credential is now unsafe. Rotate it immediately in the service (revoke old token, generate new one).

**2. Remove from git history** — Use **BFG Repo-Cleaner** (faster than git filter-branch):

```bash
bfg --delete-files API_KEY.txt
bfg --replace-text passwords.txt  # passwords.txt contains: old_password==>new_password
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**3. Force push** (if you own the repo):
```bash
git push --force-with-lease
```

**4. Notify users** — If the repo is shared, alert all users to pull the cleaned history.

**References:**
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Git docs: git-filter-branch](https://git-scm.com/docs/git-filter-branch)

## Testing Without Exposing Secrets

### 1. Use Mock Credentials

In tests, use placeholder credentials that won't work in production:

```python
# tests/test_api.py
import os
import pytest

@pytest.fixture
def mock_credentials(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_key_do_not_use")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    yield

def test_fetch_data(mock_credentials):
    # Test runs with mock credentials
    # Won't actually call the real API
    assert fetch_from_service() is not None
```

### 2. Separate Test and Production Configs

```python
# config.py
import os

ENV = os.getenv("ENV", "development")

if ENV == "production":
    API_URL = "https://api.production.com"
else:
    API_URL = "https://api.staging.com"
```

### 3. Use CI/CD Secret Management

In GitHub Actions, use encrypted secrets:

```yaml
# .github/workflows/test.yml
env:
  API_KEY: ${{ secrets.API_KEY }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: bash scripts/validate-env.sh && python -m pytest
```

### 4. Validation Script Template

Create `scripts/validate-env.sh` to check that required credentials exist:

```bash
#!/bin/bash

echo "Validating environment setup..."

REQUIRED_VARS=("API_KEY" "DATABASE_URL" "GITHUB_TOKEN")
MISSING=()

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        MISSING+=("$var")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "ERROR: Missing environment variables: ${MISSING[*]}"
    echo "Set them with: export VAR_NAME=value"
    exit 1
fi

# Optional: validate format
if ! [[ $API_KEY =~ ^sk_ ]]; then
    echo "ERROR: API_KEY doesn't look like a valid key (should start with 'sk_')"
    exit 1
fi

echo "✓ Environment validation passed"
exit 0
```

## Validation Checklist

Use this checklist when creating or reviewing skills to ensure no secrets are exposed:

- [ ] **No hardcoded secrets in SKILL.md** — body, frontmatter, or examples
- [ ] **No hardcoded credentials in scripts/** — all secrets from environment variables
- [ ] **No .env files in repo** — only `.env.example` with placeholders
- [ ] **No credential files** — no credentials.json, secrets.yml, or similar
- [ ] **Environment variables documented** — Prerequisites section lists all required env vars
- [ ] **Validation script present** — scripts/validate-env.sh or equivalent
- [ ] **Examples use placeholders** — code examples use `YOUR_API_KEY_HERE`, not real keys
- [ ] **Error messages are clear** — when secrets missing, tell Claude exactly what to do
- [ ] **Git history clean** — use `git log -p` to verify no secrets in history
- [ ] **No forgotten files** — check `.git/config`, local config, credentials helpers
- [ ] **No secrets in comments** — even commented-out code can expose secrets
- [ ] **Tool scoping reviewed** — if Bash access granted, validate it can't leak secrets

## References & Tools

### Security Tools

- **git-secrets** — GitHub's official tool to prevent secret commits
  [github.com/awslabs/git-secrets](https://github.com/awslabs/git-secrets)

- **truffleHog** — Searches git history for secrets with high confidence
  [github.com/trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog)

- **gitleaks** — Scans repos against 140+ secret patterns
  [github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)

### Service-Specific Resources

- **GitHub Token Security** — [docs.github.com: keeping your account and data secure](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
- **AWS Credential Security** — [docs.aws.amazon.com: credential types](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html)
- **OAuth Best Practices** — [RFC 6749 section 3.2.1](https://tools.ietf.org/html/rfc6749#section-3.2.1)

### Compliance & Standards

- **OWASP: Secrets Management** — [cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- **CWE-798: Hardcoded Credentials** — [cwe.mitre.org](https://cwe.mitre.org/data/definitions/798.html)
