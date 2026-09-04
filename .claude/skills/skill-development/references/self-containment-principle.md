# Bounded Scope Principle for Skills

## Core Principle

**Skills operate within bounded scope.** Skills follow Claude's progressive disclosure architecture: metadata is always available, full instructions load when triggered, and supporting resources load on-demand. Skills must not reference external content as requirements—all knowledge and data needed for execution must be bundled within the skill directory or accessed only through explicitly allowed tools.

**Why this matters:**
- **Reliability**: Skills work independently without external fetch dependencies; network calls only when explicitly designed
- **Reproducibility**: Same skill executes identically across time and environments
- **Portability**: Deploy anywhere without external setup or runtime configuration
- **Token efficiency**: Progressive loading means Claude only pays for content used
- **Boundary clarity**: Explicit separation between bundled content and optional external access

---

## What Bounded Scope Means

### Progressive Disclosure Architecture

Claude's skill loading follows three layers:

1. **Metadata Layer** (~100 tokens, always loaded): Skill frontmatter (name, description) in Claude's prompt
2. **Instruction Layer** (~1,500-5,000 tokens, triggered): Full SKILL.md body when skill is activated
3. **Resource Layer** (unlimited, on-demand): Supporting files loaded only when Claude determines they're needed

Bounded scope means operating within this architecture's allowed boundaries.

### ✅ Allowed: Bundled Content (No External Dependencies for Operation)

Everything required for skill operation should be included in the skill directory:

```
skill-name/
├── SKILL.md              # Instructions + metadata
├── scripts/              # Executable code
│   ├── process.py
│   └── validate.sh
├── references/           # Documentation, schemas, data
│   ├── api-guide.md
│   ├── schema.json
│   └── config-examples.md
└── assets/               # Output templates, files
    └── template.docx
```

**Examples of self-contained content:**
- ✅ JSON schemas bundled in `references/`
- ✅ Example data or test files in `references/`
- ✅ Configuration examples in `references/`
- ✅ Complete API documentation in `references/`
- ✅ Helper scripts in `scripts/`
- ✅ Output templates in `assets/`

### ❌ Forbidden: Content Dependencies on External URLs

**Skills must NOT require:**
- 🚫 External URLs as content sources (e.g., "see docs at https://...")
- 🚫 Downloading files to function (e.g., "install this library from...")
- 🚫 External configuration as setup (e.g., "get config from cloud storage")
- 🚫 Mandatory API keys/credentials from external services
- 🚫 Runtime dependencies on external services being available

**Examples to avoid (content dependencies):**
- ❌ "For full documentation, see https://api.example.com/docs" (should be in references/)
- ❌ "Download the latest schema from https://registry.example.com" (should be bundled)
- ❌ "This skill requires AWS credentials in ~/.aws/config" (should be optional or user-provided)

**Critical distinction:** This forbids REQUIRING external dependencies for operation. It does NOT forbid optional network calls when explicitly designed.

---

## When External Access is Allowed by Architecture

### Optional Network Calls (Via Explicitly Allowed Tools)

Network access is allowed **only when**:

1. **Declared in allowed-tools** — Explicitly listed in skill frontmatter (e.g., `Bash(curl:*)`, `Bash(gh:*)`)
2. **User-initiated** — Called only when user explicitly requests it or provides input
3. **Not mandatory for operation** — Skill works with reduced functionality if network unavailable
4. **From trusted sources** — Only internal APIs or official services (e.g., GitHub, npm registries)
5. **Documented clearly** — SKILL.md documents what external calls happen and why

**Allowed network patterns:**
- ✅ `allowed-tools: Bash(curl:*, gh:*)` with user asking "fetch GitHub data"
- ✅ `allowed-tools: Bash(curl:*)` with explicit network call in SKILL.md instructions
- ✅ Bundled `scripts/fetch.sh` that uses curl only when called

**Examples where network is acceptable:**
- ✅ GitHub helper skill: queries GitHub API on user request (with `allowed-tools: Bash(gh:*)`)
- ✅ Weather checker skill: fetches weather on user request (with `allowed-tools: Bash(curl:*)`)
- ✅ Log analyzer skill: fetches logs from company service on user request (documented, optional)

**Always document:**
```yaml
---
name: github-helper
allowed-tools: Bash(gh:*)
description: >-
  Query GitHub repositories and issues. Requires GitHub CLI and authentication.
  Network calls made only on request.
---
```

### Building on Other Skills

A skill can depend on another skill if:
1. **It's optional** — Skill works without it, but has enhanced features with it
2. **It's documented** — Clear in description and documentation which skill(s) it builds on
3. **It's internal to the system** — Both skills are deployed together

**Example:**
```yaml
# ✅ GOOD - skill-creator extends from skill ecosystem
description: >-
  Create and refine Claude Code skills following best practices.
  Use when building new skills, validating existing skills, or improving skill quality.
  Integrates with skill validation ecosystem.
```

---

## Implementation Guidelines

### 1. Use references/ for All Documentation

Instead of linking to external docs, include content in `references/`:

```markdown
# BAD
For database schema details, see https://company.wiki/schemas

# GOOD
For database schema details, see references/database-schema.md
```

If content is large (>10KB), create a separate reference file:
```
references/
├── quick-reference.md
├── database-schema.md
├── api-operations.md
└── troubleshooting.md
```

### 2. Include Example Data in references/

Provide sample files or data:

```
references/
├── example-config.json
├── sample-data.csv
└── test-cases.md
```

This lets Claude work with realistic examples without fetching external data.

### 3. Document Required External Tools

If the skill must call external services (rare), document clearly:

```yaml
---
name: github-helper
allowed-tools: Bash(curl:*)
description: >-
  Interact with GitHub repositories. Use when querying GitHub for
  repository info, creating issues, or pulling pull request data.
  Requires GitHub API access and curl.
---
```

In SKILL.md, document:
```markdown
## Prerequisites
- GitHub API token (set GITHUB_TOKEN env var)
- curl for API calls

## Network Dependencies
This skill makes HTTPS calls to api.github.com:
- GET /repos/{owner}/{repo} — Fetch repository details
- GET /repos/{owner}/{repo}/pulls — List pull requests

All calls use GitHub's public API.
```

### 4. Validate Self-Containment During Creation

Before deploying a skill:

- [ ] All referenced files exist in the skill directory
- [ ] No external URLs in SKILL.md (except in notes/sources)
- [ ] No required network calls (except where documented as core feature)
- [ ] All example data is bundled
- [ ] No external configuration required (except env vars for credentials)
- [ ] No mandatory tools beyond what's in `allowed-tools`

### 5. Anti-Patterns: Beware of These

❌ **Don't reference external wikis/docs:**
```markdown
For details, see https://internal.wiki/database
```
Instead, include the docs in `references/`

❌ **Don't require downloading external files:**
```python
# BAD - requires internet and setup
urllib.request.urlretrieve("https://...", "config.json")
```
Instead, bundle files in the skill or have user provide them

❌ **Don't make non-user-initiated network calls:**
```python
# BAD - auto-fetches without asking
schema = requests.get("https://api.example.com/schema").json()
```
Instead, bundle schema or ask user to provide it

❌ **Don't rely on environment-specific external services:**
```python
# BAD - breaks if service is down or unreachable
check_status = requests.get("https://status.example.com")
```
Instead, fail gracefully with clear error messages

---

## Bounded Scope Validation Checklist

When validating a skill against bounded scope requirements:

**Metadata Layer (Frontmatter):**
- [ ] `allowed-tools` explicitly lists any network access (e.g., `Bash(curl:*)`, `Bash(gh:*)`)
- [ ] Description clearly states external dependencies (if any)

**Instruction Layer (SKILL.md body):**
- [ ] No external URL references as content sources (except Sources/Acknowledgments)
- [ ] No "download from" or "see external docs at" instructions
- [ ] All required knowledge is in SKILL.md or references/

**Resource Layer (Supporting files):**
- [ ] All documentation referenced exists in references/
- [ ] All example data is bundled (sample files in references/)
- [ ] Scripts are self-contained (no automatic external downloads)
- [ ] No API keys or credentials stored in files (documented as user-provided)

**External Access (if applicable):**
- [ ] Network calls (curl, gh, etc.) explicitly documented in SKILL.md
- [ ] Network calls are optional, not required for operation
- [ ] Only user-initiated or explicitly triggered
- [ ] Fail gracefully if network unavailable

**Overall:**
- [ ] Skill works standalone after deployment
- [ ] No external setup or configuration required (except optional credentials)
- [ ] All required files exist in skill directory

---

## Why Bounded Scope Matters

**Without bounded scope, skills become fragile and opaque:**
- External docs get moved/deleted → skill fails silently
- Network dependencies introduce unpredictable failures
- Hidden setup requirements break deployment
- Skills scattered across external systems → hard to audit
- Token bloat from content that could be bundled

**With bounded scope:**
- **Predictable**: All content included; skill works identically everywhere
- **Efficient**: Progressive disclosure means Claude only loads needed content
- **Maintainable**: Updates to bundled content don't affect external systems
- **Transparent**: Explicit `allowed-tools` shows what external access exists
- **Reliable**: Optional network calls don't block skill operation
- **Auditable**: All knowledge and dependencies visible in skill directory

Bounded scope aligns with Claude's progressive disclosure architecture and creates skills that are reliable, transparent, and maintainable across deployment contexts.

---

## Grounding in Claude Architecture

This principle is built on Claude Code's official skill loading model:

1. **Metadata loading** - Frontmatter (`name`, `description`, `allowed-tools`) always available for discovery
2. **Progressive disclosure** - Full skill content loads only when relevant; supporting resources on-demand
3. **Allowed tools declaration** - `allowed-tools` frontmatter explicitly declares what external access is available
4. **Bundled resources** - All skill content lives in the skill directory (SKILL.md, references/, scripts/, assets/)

This creates a clear boundary:
- **Inside**: All content required for operation (bundled)
- **Outside**: Optional external resources (network calls via explicitly declared tools)

Skills respecting bounded scope work reliably across all Claude Code deployment contexts: local, project, user, and managed scopes.
