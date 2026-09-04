# Validation Rules Reference

Complete validation checks for Claude Code plugins.

## Structure Validation

### Required Structure

```
plugin-name/
├── .claude-plugin/          # MUST exist
│   └── plugin.json          # MUST exist (only required file)
├── skills/                  # MUST be at plugin root (not in .claude-plugin/)
├── commands/                # If present, must be at plugin root
├── agents/                  # If present, must be at plugin root
└── README.md                # RECOMMENDED
```

### Common Errors

**Error**: Component directory in `.claude-plugin/`
```
✗ skills/ found in .claude-plugin/ (should be at plugin root)
FIX: mv plugin/.claude-plugin/skills plugin/skills
```

**Error**: Missing `.claude-plugin/` directory
```
✗ .claude-plugin/ directory missing
FIX: mkdir -p plugin/.claude-plugin
```

**Error**: Missing `plugin.json`
```
✗ .claude-plugin/plugin.json missing (REQUIRED)
FIX: Create plugin.json with at minimum: {"name": "plugin-name"}
```

## Manifest Validation

### JSON Syntax

**Error**: Invalid JSON
```
✗ Invalid JSON syntax: Unexpected token ','
FIX: Remove trailing commas, check quotes, validate with JSON linter
```

**Error**: Trailing comma
```json
{
  "name": "my-plugin",
  "version": "1.0.0",  // ← Remove this comma
}
```

### Required Fields

**Error**: Missing `name` field
```
✗ Missing required field: 'name'
FIX: Add "name": "your-plugin-name"
```

### Field Format

**Name Format**:
```
✗ Plugin name 'My_Plugin' should be kebab-case
FIX: Change to 'my-plugin' (lowercase with hyphens)
```

**Version Format**:
```
✗ Version '1.2' should follow semver (e.g., 1.0.0)
FIX: Use format MAJOR.MINOR.PATCH (e.g., '1.2.0')
```

### Path Validation

**Absolute Paths**:
```
✗ Field 'skills' has absolute path: /Users/me/skills
FIX: Use relative path: ./skills
```

**Missing `./` prefix**:
```
⚠ Path should start with './' (currently: skills)
FIX: Change 'skills' to './skills/'
```

## Component Validation

### Skills

**Missing SKILL.md**:
```
✗ Skill 'my-skill' missing SKILL.md file
FIX: Create skills/my-skill/SKILL.md
```

**Missing Frontmatter**:
```
✗ Skill 'my-skill' missing YAML frontmatter
FIX: Add frontmatter at top of SKILL.md:
---
name: my-skill
description: What it does
allowed-tools: Read, Write, Bash
---
```

**Incomplete Frontmatter**:
```
✗ Skill 'my-skill' has incomplete frontmatter (missing closing ---)
FIX: Ensure frontmatter has opening and closing --- markers
```

### Commands

**Missing Frontmatter** (warning):
```
⚠ Command 'deploy.md' missing YAML frontmatter (recommended)
FIX: Add frontmatter with name and description
```

### Agents

**Valid Structure**:
- Markdown files in `agents/` directory
- Descriptive content about agent capabilities

## 2025 Schema Compliance

### Required: allowed-tools Field

**Error**: Missing `allowed-tools`
```
✗ Skill 'my-skill' missing 'allowed-tools' field (2025 schema)
FIX: Add to SKILL.md frontmatter:
---
name: my-skill
description: What it does
allowed-tools: Read, Write, Bash
---
```

### Common Tool Sets

**Read-only analysis**:
```yaml
allowed-tools: Read, Grep, Glob
```

**File editing**:
```yaml
allowed-tools: Read, Write, Edit
```

**Automation**:
```yaml
allowed-tools: Read, Write, Bash
```

**Research**:
```yaml
allowed-tools: Read, WebSearch, WebFetch
```

**Full access**:
```yaml
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch
```

## Validation Workflow

### Pre-Publishing Checklist

- [ ] Run `python scripts/validate_plugin.py plugin/`
- [ ] 0 errors reported
- [ ] Fix all warnings (recommended)
- [ ] README.md exists and is complete
- [ ] All skills have `allowed-tools` field
- [ ] Version number appropriate
- [ ] Test local installation

### Validation Command

```bash
# Full validation
python scripts/validate_plugin.py my-plugin/

# Verbose output
python scripts/validate_plugin.py my-plugin/ --verbose

# Specific check
python scripts/validate_plugin.py my-plugin/ --check structure
python scripts/validate_plugin.py my-plugin/ --check manifests
python scripts/validate_plugin.py my-plugin/ --check components
python scripts/validate_plugin.py my-plugin/ --check 2025
```

### Exit Codes

- `0`: All validation passed, plugin ready
- `1`: Errors found, fix before publishing
- `2`: Script execution error

## Quick Fixes

### Add allowed-tools to Existing Skills

1. Open `SKILL.md`
2. Find YAML frontmatter (between `---` markers)
3. Add line: `allowed-tools: Read, Write, Bash`
4. Save file

### Convert Underscore Names to Kebab-Case

```bash
# In plugin.json
# Change: "my_plugin" → "my-plugin"
# Change: "My_Plugin" → "my-plugin"
```

### Fix Trailing Commas in JSON

```bash
# Remove commas before closing braces or brackets
# Before: "license": "MIT",
# After:  "license": "MIT"
```

### Move Component Directories

```bash
# If skills in wrong location:
mv plugin/.claude-plugin/skills plugin/skills

# If commands in wrong location:
mv plugin/.claude-plugin/commands plugin/commands
```

## Migration Guide: 2025 Schema

### For Existing Plugins

1. **Identify Skills Without allowed-tools**:
```bash
python scripts/validate_plugin.py plugin/ --check 2025
```

2. **Add allowed-tools to Each Skill**:
   - Determine which tools skill uses
   - Add field to frontmatter
   - Validate again

3. **Common Tools by Skill Type**:
   - Analysis skills: `Read, Grep, Glob`
   - Editor skills: `Read, Write, Edit`
   - Automation: `Read, Write, Bash`
   - Research: `Read, WebSearch, WebFetch`

4. **Re-validate**:
```bash
python scripts/validate_plugin.py plugin/ --check 2025
```

## Resources

- **Official Schema**: [anthropic.com/schemas/plugin.json](https://anthropic.com/schemas/plugin.json)
- **Generate Manifest**: `python scripts/generate_manifest.py plugin/`
- **Validate Plugin**: `python scripts/validate_plugin.py plugin/`
- **Package Skills**: `python scripts/package_skills.py source/ plugin/ --validate`
