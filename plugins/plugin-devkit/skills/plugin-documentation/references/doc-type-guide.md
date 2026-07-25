# Doc Type Guide

Required sections and plugin-state source mapping for each doc type `plugin-documentation` authors. Read the row for the type in scope before writing — don't rely on general doc-writing intuition, since these baselines are chosen specifically to satisfy `human-doc-reviewer`'s own structural checks (for the six types it covers) or to stay internally consistent with them (for the five it doesn't).

## Reviewed by `human-doc-reviewer`

These six baselines are drawn directly from `human-doc-reviewer`'s own Step 2 structural-completeness checks — write to satisfy them, not a generic template, since that agent is what actually QAs the output.

### README.md

**Required:** one paragraph near the top stating what the plugin/project does; installation or setup instructions; a usage example; a link to CONTRIBUTING.md if one exists; a license mention.

**Source of truth:** `plugin.json`'s `name`/`description`/`license` fields for the opening paragraph and license line; the plugin's own install command convention (`/plugin install <name>@<marketplace>` or `cc --plugin-dir <path>` for local dev) for setup; one representative skill/agent/command's trigger phrase, drawn from its actual frontmatter `description`, for the usage example.

### CONTRIBUTING.md

**Required:** dev environment setup; how to propose a change (branch/PR flow); code-style or test requirements if any exist in the repo; a link back to README.md rather than re-describing setup if README already covers it.

**Source of truth:** any existing test/lint tooling actually present in the repo (e.g. a `pyproject.toml`, `package.json` scripts, a CI config) — state only what's actually configured, not a generic "run the tests" placeholder.

### CHANGELOG.md

**Required:** entries in a consistent format, each with a date or version. A file with only a placeholder header and no entries is acceptable to create (Minor, not Major, per `human-doc-reviewer`'s own severity framing) but should never be left that way indefinitely — the first real entry should land with the next meaningful change.

**Source of truth:** `git log` for the plugin's own directory tree, or the specific change that prompted this authoring pass if `git log` access isn't in scope for this invocation.

### INSTALLATION.md

**Required:** the actual content the filename promises — concrete install steps, not a redirect stub. If README.md already has a full installation section, INSTALLATION.md should either not exist (don't create a near-duplicate) or clearly cover something README doesn't (e.g. platform-specific instructions).

**Source of truth:** same as README's install section — `plugin.json`'s manifest, the install command convention.

### SECURITY.md

**Required:** actual reporting instructions (an email, an issue template, a security contact) — a title with no body is a `human-doc-reviewer` Major finding, treated the same as a "documented commitment never delivered."

**Source of truth:** ask the user for the actual reporting channel if not already stated anywhere in the repo — do not invent a contact address or process.

### CODE_OF_CONDUCT.md

**Required:** actual conduct expectations and an enforcement/reporting path — same "content the filename promises" bar as SECURITY.md.

**Source of truth:** ask the user for the actual content, or reuse a named standard (e.g. Contributor Covenant) — but only after using `AskUserQuestion` to confirm that standard is the intended baseline, don't silently adopt one.

## Not Yet Reviewed by `human-doc-reviewer`

For these five, no dedicated reviewer exists yet (see SKILL.md Gotchas). Follow the baseline below as the best available standard, but always state the reviewer gap explicitly when reporting.

### RELEASE_NOTES.md

**Required:** per-release entries describing user-visible changes (distinct from CHANGELOG.md's often more granular/technical log — if a plugin has both, RELEASE_NOTES.md should read as a curated summary, not a duplicate).

**Source of truth:** same as CHANGELOG.md — `git log`, or the specific change prompting this pass.

### ARCHITECTURE.md

**Required:** how the plugin's components relate — which skills delegate to which agents, what a request's path through the plugin looks like for the common case.

**Source of truth:** each component's own `description` and any explicit `Skill(...)`/`Agent(...)` cross-references found by `Grep`ping the plugin tree — never describe a delegation relationship that isn't actually present in a component's own instructions.

### THIRD_PARTY_NOTICES.md

**Required:** actual third-party dependencies and their licenses, if the plugin bundles any (a vendored script, an MCP server dependency, a bundled library).

**Source of truth:** a `requirements.txt`/`package.json`/`pyproject.toml` if present, or explicit vendored files found in the plugin tree — do not list a dependency that isn't actually bundled or declared.

### How-To guides (`HOWTO_<topic>.md` or `docs/how-to/<topic>.md`)

**Required:** a single concrete task from start to finish, written for someone who wants to accomplish that one thing, not a full reference.

**Source of truth:** the specific workflow the user names when requesting the guide, cross-checked against the actual component(s) involved so the steps match real behavior.

### QUICK_START.md

**Required:** the shortest path from "just installed" to "first successful use" — narrower than README's full overview, no more than the install step plus one working example.

**Source of truth:** same as README's usage example — one representative trigger phrase drawn from an actual component's frontmatter.
