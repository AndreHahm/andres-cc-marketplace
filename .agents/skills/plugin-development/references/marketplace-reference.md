# Marketplace Reference

Covers `marketplace.json` schema, distribution methods, team setup, versioning, and publishing.

---

## marketplace.json Schema

**File location:** `.claude-plugin/marketplace.json`

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string (kebab-case) | Marketplace identifier |
| `owner` | **object** | Maintainer info — MUST be `{"name": "..."}`, not a string |
| `plugins` | array | List of plugin entries (can be empty `[]`) |

```json
{
  "name": "company-approved-plugins",
  "owner": {
    "name": "Engineering Team",
    "email": "engineering@company.com"
  },
  "plugins": []
}
```

### Optional Marketplace Fields

| Field | Type | Description |
|-------|------|-------------|
| `$schema` | string | Schema URL for IDE validation |
| `version` | string | Marketplace version |
| `description` | string | Marketplace purpose |
| `metadata.pluginRoot` | string | Base path for relative plugin sources |

### Plugin Entry Fields

**Required per entry:**
- `name` (string): Plugin identifier (kebab-case, must match plugin.json)
- `source` (string | object): Plugin location — paths MUST start with `./`

**Optional per entry:**
- `description`, `version`, `author` (object), `homepage`, `repository`, `license`
- `keywords` (array), `category`, `tags`
- `commands`, `agents`, `hooks`, `mcpServers`: Custom path overrides
- `strict` (boolean): Require plugin.json in folder

### Source Specifications

```json
// Relative path (paths MUST start with ./)
{ "name": "my-plugin", "source": "./" }
{ "name": "my-plugin", "source": "./plugins/my-plugin" }

// GitHub repository
{ "name": "my-plugin", "source": { "source": "github", "repo": "owner/repo" } }

// Git URL
{ "name": "my-plugin", "source": { "source": "url", "url": "https://gitlab.com/team/plugin.git" } }
```

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `owner: expected object, received string` | `owner` is a string | Use `"owner": {"name": "..."}` |
| `plugins: expected array, received undefined` | Missing `plugins` field | Add `"plugins": []` |
| `plugins.0.source: Invalid input` | Source path missing `./` | Use `"source": "./"` not `"source": ""` |

### Categories

Standard values for `category`: `development`, `productivity`, `security`, `learning`, `utilities`

### Complete Example

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — deliberately shows two plugin entries with different `source` shapes (local path vs. GitHub) side by side; splitting would lose that comparison.

```json
{
  "$schema": "https://anthropic.com/schemas/marketplace.json",
  "name": "company-approved-plugins",
  "version": "1.0.0",
  "description": "Approved plugins for Company engineering",
  "owner": {
    "name": "Engineering Team",
    "email": "engineering@company.com"
  },
  "metadata": { "pluginRoot": "./plugins" },
  "plugins": [
    {
      "name": "deployment-tools",
      "description": "Automated deployment and rollback",
      "version": "2.1.0",
      "author": { "name": "DevOps Team", "email": "devops@company.com" },
      "source": "./plugins/deployment-tools",
      "category": "development",
      "keywords": ["deployment", "ci-cd"],
      "license": "MIT"
    },
    {
      "name": "security-scanner",
      "description": "Security analysis and vulnerability detection",
      "source": { "source": "github", "repo": "company/security-scanner" },
      "category": "security"
    }
  ]
}
```

---

## Distribution Methods

### Method 1: Direct Installation (Simple)

For small teams or quick sharing:

```bash
claude plugin install https://github.com/your-org/my-plugin
```

**When to use:** Small teams (<10 people), internal tools, testing before wider distribution.

### Method 2: Team Marketplace (Recommended)

Central repository for organization-wide discovery and installation:

```bash
claude plugin marketplace configure https://github.com/your-org/plugin-marketplace
```

**When to use:** Multiple plugins across teams, versioned releases, self-service installation.

**Auto-configure via `settings.json`:**
```json
{
  "extraKnownMarketplaces": [
    { "source": { "source": "github", "repo": "company/marketplace" } }
  ]
}
```

### Method 3: Public Marketplace (Community)

Requires: comprehensive README, clear description, capacity to maintain.

---

## Team Marketplace Setup

### Step 1: Create Marketplace Repository

```bash
mkdir plugin-marketplace && cd plugin-marketplace && git init
```

### Step 2: Marketplace Structure

```
plugin-marketplace/
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest (required)
│   └── marketplace.json         # Marketplace manifest (required)
├── README.md
├── plugins/
│   ├── code-reviewer/
│   ├── pdf-processor/
│   └── test-runner/
└── CONTRIBUTING.md
```

### Step 3: Create marketplace.json

The file MUST be at `.claude-plugin/marketplace.json` for `claude plugin marketplace add` to work.

Single-plugin (self-contained repo):
```json
{
  "name": "dev-flow",
  "owner": { "name": "full-stack-biz" },
  "plugins": [
    {
      "name": "dev-flow",
      "source": "./",
      "description": "Development workflow tools"
    }
  ]
}
```

Multi-plugin repo:
```json
{
  "name": "company-tools",
  "owner": { "name": "DevTools Team", "email": "devtools@company.com" },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting",
      "version": "2.1.0"
    },
    {
      "name": "deployment-tools",
      "source": { "source": "github", "repo": "company/deploy-plugin" },
      "description": "Deployment automation"
    }
  ]
}
```

### Step 4: Configure Team Access

**GitHub:**
```bash
claude plugin marketplace configure https://github.com/your-org/plugin-marketplace
```

**GitLab / Self-Hosted:**
```bash
claude plugin marketplace configure https://gitlab.company.com/teams/plugin-marketplace
```

---

## Versioning and Releases

Use semantic versioning: `MAJOR.MINOR.PATCH`
- `1.0.0` → Initial release
- `1.1.0` → New feature (minor bump)
- `1.1.1` → Bug fix (patch bump)
- `2.0.0` → Breaking changes (major bump)

**Release checklist:**
- [ ] Update `version` in `.claude-plugin/plugin.json`
- [ ] Update `version` in marketplace `plugins` entry
- [ ] Test all plugin components locally
- [ ] Create CHANGELOG entry
- [ ] Tag release: `git tag v1.2.0 && git push origin --tags`

---

## Team Workflow

**For team members:**
```bash
claude plugin discover          # See available plugins
claude plugin install code-reviewer
claude plugin update            # Update all plugins
```

**For maintainers:**
1. Make changes and test with `--plugin-dir`
2. Bump version in plugin.json
3. Commit, push, tag release: `git tag v1.2.0 && git push origin --tags`

---

## Best Practices

- No hardcoded secrets — use environment variables
- Validate user input in all commands
- Keep plugins up-to-date with Claude Code API changes
- Document changes in CHANGELOG
- For public plugins: write comprehensive README, set up GitHub Issues, add CONTRIBUTING guide

---

## Troubleshooting

**Plugin not appearing in marketplace:**
- Verify plugin is listed in `plugins` array in marketplace.json
- Check `.claude-plugin/plugin.json` exists and is valid JSON
- Try: `claude plugin discover`

**Installation fails:**
- Verify marketplace URL is correct and accessible
- Check network connectivity
- Try installing from direct URL: `claude plugin install https://github.com/your-org/plugin-marketplace/tree/main/plugins/my-plugin`

**Version conflicts:**
- Pin versions during onboarding: `claude plugin install code-reviewer@1.2.0`
- Communicate breaking changes before major bumps

---

## Publishing to Public Marketplaces

**Preparation checklist:**
- [ ] Comprehensive README with examples
- [ ] CONTRIBUTING guide
- [ ] Issue templates for bug reports
- [ ] License file (MIT, Apache 2.0, etc.)
- [ ] CHANGELOG with version history
- [ ] Tested with multiple Claude Code versions
