# Plugin Development Workflows

Step-by-step procedures for creating, converting, validating, and distributing Claude Code plugins.

---

## Which Workflow?

```
Plugin exists?
├─ No → Workflow 1: Create New Plugin
└─ Yes
   └─ Is it already a plugin (has .claude-plugin/plugin.json)?
      ├─ No → Workflow 2: Convert to Plugin
      └─ Yes
         └─ Workflow 3: Validate/Improve
```

---

## Workflow 1: Creating a New Plugin from Scratch

### Step 1: Interview Requirements

Gather these details before creating any files:
- **Plugin purpose** — What does it do? What problem does it solve?
- **Plugin name** — Lowercase-hyphen format (becomes `/plugin-name:skill-name`)
- **Components** — Skills, agents, hooks, MCP/LSP servers?
- **Distribution scope** — Personal, team, or marketplace?

### Step 2: Create Directory Structure

```bash
mkdir -p my-plugin/.claude-plugin
mkdir -p my-plugin/skills
mkdir -p my-plugin/agents
mkdir -p my-plugin/commands
```

Or use the init script:
```bash
python scripts/init_plugin.py my-plugin --components skills,agents
```

### Step 3: Create plugin.json Manifest

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "description": "[Action]. [Brief description of purpose and capabilities]. [Components/scope].",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

**Validation:**
- `name`: lowercase-hyphen, 1-64 chars, no spaces
- `description`: 1-1024 chars, include specific trigger phrases
- `author`: Must be object `{"name": "..."}`, not string
- See `references/plugin-json-schema.md` for optional fields

### Step 4: Add Components

**4a. Agent Skills** (recommended)

Create `skills/skill-name/SKILL.md`:

```yaml
---
name: skill-name
description: Use when [trigger context]
allowed-tools: Read Write
---

# Skill Name

Instructions here...
```

**4b. Custom Agents** (for complex workflows)

Create `agents/agent-name.md`:

```yaml
---
description: What this agent specializes in
capabilities: ["task1", "task2"]
---

# Agent Name

Detailed description of agent role and when Claude should invoke it.
```

**4c. Hooks** (for event handlers)

Create `hooks/hooks.json` — see `references/hooks.md` for events and patterns.

**4d. MCP Servers** (for external service integration)

Create `.mcp.json` — see `references/mcp-servers.md`.

**4e. LSP Servers** (for language intelligence)

Create `.lsp.json` — see `references/lsp-servers.md`.

### Step 5: Validate

```bash
claude plugin validate /path/to/my-plugin
```

Checks: valid JSON, required fields, component paths, no structural errors.

### Step 6: Manual Structure Review

- [ ] `.claude-plugin/plugin.json` exists and is valid JSON
- [ ] `name` and `description` fields present
- [ ] Plugin name is lowercase-hyphen
- [ ] Description includes specific trigger phrases
- [ ] All component directories follow Claude Code conventions (one level deep)
- [ ] All packaged skills have `allowed-tools` in frontmatter

### Step 7: Test Locally

```bash
claude --plugin-dir /path/to/my-plugin
```

Verify components load and activate correctly.

### Step 8: Deploy

**Personal/local:**
```bash
cp -r my-plugin ~/.claude/skills/
```

**Project-specific (shared via git):**
```bash
cp -r my-plugin .claude/skills/
```

**Team/marketplace:** See `references/marketplace-reference.md`.

---

## Workflow 2: Converting an Existing Project to a Plugin

### Step 1: Identify Existing Components

Audit the project for:
- **Scripts/commands** → will become `skills/` or `commands/`
- **Multi-step processes** → will become `agents/`
- **Automation (on-save, on-commit)** → will become `hooks/hooks.json`
- **External APIs/databases** → will become `.mcp.json` or `.lsp.json`

### Step 2: Create Plugin Structure

```bash
mkdir -p my-plugin/.claude-plugin
mkdir -p my-plugin/skills
mkdir -p my-plugin/agents
mkdir -p my-plugin/commands
```

### Step 3: Write plugin.json Manifest

```json
{
  "name": "my-plugin",
  "description": "What the project does. Use when [contexts]. Includes [component list].",
  "version": "1.0.0",
  "author": { "name": "Author Name" }
}
```

### Step 4: Migrate Components

**Migrate to Agent Skills:**
1. Identify reusable Claude capabilities
2. Create `skills/skill-name/SKILL.md` with frontmatter (name, description, allowed-tools)
3. Move implementation to body

**Migrate to agents:**
1. Identify multi-step complex processes
2. Create `agents/agent-name.md` (flat file) with description + capabilities
3. Move workflow instructions to body

**Migrate hooks:**
1. Extract automation rules from project config
2. Create `hooks/hooks.json` mapping to Claude Code events (see `references/hooks.md`)

**Migrate external services:**
1. Extract API integrations
2. Create `.mcp.json` with server configurations

### Step 5: Update Component Metadata

**For each skill:**
- [ ] Frontmatter: name, description, allowed-tools
- [ ] Description includes trigger contexts
- [ ] Body <500 lines

**For each agent:**
- [ ] Frontmatter: description, capabilities array
- [ ] Workflow instructions are clear and procedural

### Step 6: Validate and Test

```bash
claude plugin validate /path/to/my-plugin
claude --plugin-dir /path/to/my-plugin   # verify activation
```

---

## Workflow 3: Validating or Improving Existing Plugins

### Step 1: Automated Scan (Optional but Recommended)

Use the scan script for a structured JSON report before manual validation:

```bash
bash scripts/scan-plugin.sh /path/to/plugin /tmp/plugin-scan.json
```

The scanner is **read-only** — it never modifies files. Output has three categories:
- `errors`: Critical issues blocking installation (must fix first)
- `warnings`: Best-practice violations (should fix)
- `decisions_needed`: Items requiring user choice (files to delete, permissions, etc.)

**Process errors first** — do not proceed to warnings until errors are resolved.

**Present decisions via AskUserQuestion:**

Non-standard files:
```
"Found non-standard files in .claude-plugin/. What should we do?"
Options: Delete all | Review each | Keep as-is
```

Script permissions:
```
"Script '[filename]' is not executable. Fix permissions?"
Options: Make executable (Recommended) | Leave as-is
```

Security warnings:
```
"Script '[filename]' contains potential secrets. Review and remove?"
Options: Review now | Already cleaned | Keep as-is
```

After approvals, show exact commands before executing:
```bash
rm -rf /path/to/.claude-plugin/MANIFEST.md
chmod +x /path/to/scripts/deploy.sh
```

Re-scan after changes to verify issues are resolved.

### Step 2: Run `claude plugin validate`

```bash
claude plugin validate /path/to/plugin
```

Identifies: invalid JSON, missing required fields, broken component paths, structural errors.

### Step 3: Manifest Validation

Check `.claude-plugin/plugin.json`:
- [ ] File exists, valid JSON
- [ ] `name`: lowercase-hyphen, 1-64 chars
- [ ] `description`: 1-1024 chars, includes trigger phrases
- [ ] `author` is an object, not a string

**Common issues:**
- Description too vague: "A plugin for processing" → won't activate reliably
- Invalid JSON: Use `jq .` to validate

### Step 4: Directory Structure Validation

- [ ] `.claude-plugin/plugin.json` at plugin root
- [ ] `skills/`, `agents/`, `commands/`, `hooks/` at plugin root (NOT inside `.claude-plugin/`)
- [ ] No deeply nested directories — keep one level deep

### Step 5: Component Metadata Validation

**Skills (`skills/*/SKILL.md`):**
- [ ] `name`, `description`, `allowed-tools` in frontmatter
- [ ] Description includes trigger contexts
- [ ] Body <500 lines

**Agents (`agents/*.md`):**
- [ ] `description` and `capabilities` array in frontmatter
- [ ] Clear workflow instructions in body

**Hooks (`hooks/hooks.json`):**
- [ ] Valid JSON, event names match Claude Code events
- [ ] Command references point to actual files

### Step 6: Activation Signal Review

**Good description:**
- Specific action verbs: "Review code", "Process PDFs"
- Clear purpose statement
- Component scope: "Includes validate, report, and export commands"

**Poor description:**
- "A plugin for code operations" — too vague, won't activate reliably

### Step 7: Improvement Priority

1. **Critical:** Invalid manifest JSON, missing name/description, wrong directory structure
2. **High:** Vague descriptions, missing component metadata, wrong event names
3. **Medium:** Unclear instructions, inconsistent naming
4. **Low:** Documentation improvements, token efficiency

### Step 8: Re-validate

```bash
claude plugin validate /path/to/plugin
```

---

## Development Workflow (Iterative)

### Version Bumping

Update version in **both** locations when making changes:
1. `.claude-plugin/plugin.json`
2. `.claude-plugin/marketplace.json` (matching plugin entry)

Or use the atomic bump script:
```bash
python scripts/bump_version.py patch   # or: major | minor | patch
```

**Semantic versioning:**
- **Major**: Breaking changes
- **Minor**: New features, refactoring
- **Patch**: Bug fixes, docs only

### Local Testing (Iterative Cycle)

After each change:
```bash
# Re-install to pick up changes
/plugin uninstall plugin-name@marketplace-name
/plugin install plugin-name@marketplace-name
# Restart Claude Code — caching requires restart for changes to take effect
```

Or use `--plugin-dir` for faster iteration (no install/uninstall needed):
```bash
claude --plugin-dir /path/to/plugin
```

### Publishing

```bash
# Commit with conventional commits
git commit -m "feat: add new skill"
git commit -m "fix: correct plugin manifest"

# Push and tag
git push origin main
git tag v1.2.0 && git push origin --tags
```

**GitHub-hosted marketplace — users install via:**
```bash
/plugin marketplace add owner/repo
/plugin install plugin-name@marketplace-name
```

**Local marketplace:**
```bash
/plugin marketplace add /path/to/marketplace
```

---

## Common Plugin Patterns

### Framework Plugin

Guidance for a specific framework (React, Vue, etc.):

```
plugins/framework-name/
├── .claude-plugin/plugin.json
├── skills/
│   └── framework-name/
│       ├── SKILL.md
│       └── references/
├── commands/
│   └── prime/
│       ├── components.md
│       └── framework.md
└── README.md
```

### Utility Plugin

Tools and utilities:

```
plugins/utility-name/
├── .claude-plugin/plugin.json
├── commands/
│   ├── action1.md
│   └── action2.md
└── README.md
```

### Domain Plugin

Domain-specific knowledge:

```
plugins/domain-name/
├── .claude-plugin/plugin.json
├── skills/
│   └── domain-name/
│       ├── SKILL.md
│       ├── references/
│       └── scripts/
└── README.md
```

---

## Common Mistakes

| Category | Wrong | Right |
|----------|-------|-------|
| Directory placement | `my-plugin/.claude-plugin/skills/` | `my-plugin/skills/` (plugin root) |
| Description | "A plugin for code" | "Review code for best practices. Includes validate and report skills." |
| Author field | `"author": "John Doe"` | `"author": {"name": "John Doe"}` |
| Source paths | `"source": "plugins/my-plugin"` | `"source": "./plugins/my-plugin"` |
| Nested commands | `commands/v1/latest/validate.md` | `commands/validate.md` |
| Skipping JSON check | (assume it's valid) | `jq . .claude-plugin/plugin.json` |
| Missing allowed-tools | No frontmatter field | `allowed-tools: Read Write Bash` |
