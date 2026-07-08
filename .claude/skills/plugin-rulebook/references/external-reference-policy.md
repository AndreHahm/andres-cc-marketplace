# External Reference Policy (R23)

Checks that every reference to an external company, GitHub organization, marketplace, plugin, skill, or repository is either explicitly whitelisted, explicitly blacklisted, resolvable and unclassified (advisory), or broken (critical, regardless of classification).

**Config is split across two files.** `assets/settings.json`'s `rules.R23_external_reference_policy.config` ships with `whitelist`/`blacklist`/`excluded_paths` empty — those three fields are inherently repo-specific and live instead in `{REPO_ROOT}/.claude/plugin-rulebook.config.json`, merged on top at load time. Every step below that reads `config.whitelist`/`config.blacklist`/`config.excluded_paths` means "the merged values," not just what's in `assets/settings.json`. See `plugin-rulebook/SKILL.md`'s "Repo-Specific Configuration" section for the full load procedure.

## Background: what counts as an "external reference"

A reference is external if it points outside the plugin/project being reviewed, to:
- A **domain** or URL (`github.com/...`, a marketplace site, a company homepage)
- A **GitHub organization or repository** (`owner/repo` shorthand, or a full URL)
- A **plugin name** — including namespaced mentions like `acme-tools:skill-reviewer` (the `acme-tools` prefix names the source plugin)
- A **skill or agent name** that isn't defined anywhere in the current plugin/project
- A **marketplace name** (e.g. `claude-code-marketplace`)
- A **company or organization name** mentioned in prose (e.g. an `author` field, a "based on X's approach" note)

Internal references — a plugin's own components referencing each other by name, or standard Claude Code platform names (`Claude`, `Anthropic`, official tool names) — are not external references and are out of scope for this rule.

**Also out of scope: illustrative examples.** A plugin/org/marketplace name used purely to illustrate a concept in prose — e.g. this very file's own `acme-tools:skill-reviewer` example above, or a trigger description saying "after adapting a pattern from a plugin like `acme-tools`" — is not a reference requiring classification. Only a genuine dependency, citation, or leftover mention (something the reader could actually follow or that was actually copied from) counts. Note this exception is orthogonal to whitelist/blacklist status — even a blacklisted name used purely as an illustrative placeholder wouldn't be flagged, though using a live blacklisted name for illustration is confusing in practice, which is why this file now uses the neutral placeholder `acme-tools` instead of a name that carries real classification weight.

## Detection Procedure

0. **Skip excluded paths entirely.** Before extracting anything, check the target file's path against `config.excluded_paths` (exact relative-path matches, relative to the plugin root). A match means this file is **out of scope for R23 entirely** — not classified, not reported, not even as an informational note. Use this for files whose whole purpose is to catalog third-party names/domains as functional content (a trusted-domain allowlist, a credential-signature reference) rather than incidentally mention them — classifying every entry in such a file would be noise, not signal.

1. **Extract candidate references** from the target file: URLs, `owner/repo` patterns, `<namespace>:<component>` patterns, `mcpServers` entries, `author`/`homepage`-style frontmatter fields, and prose mentions of a plugin/marketplace/company name (capitalized proper nouns adjacent to words like "plugin," "marketplace," "repo," "skill from," "adapted from").

2. **Check for a `marketplace.json`** anywhere in the repository (`Glob("**/marketplace.json")`). If found, read its plugin list and add every listed plugin name to the effective whitelist for this check — this is `config.auto_allow_marketplace_json_entries`.

3. **Classify each candidate** against the merged config (`assets/settings.json`'s defaults with `{REPO_ROOT}/.claude/plugin-rulebook.config.json`'s overrides applied, per the note above):
   - Matches `config.whitelist` (or the marketplace auto-allow list) → **Whitelisted**, no finding
   - Matches `config.blacklist` → **Blacklisted**, Critical
   - Matches neither → **Unknown**, Advisory
   - Whitelist/blacklist entries support a trailing `/*` wildcard (e.g. `github.com/anthropics/*` matches any repo under that org)

4. **Check resolvability independently of classification.** A reference can be whitelisted and still broken (e.g. a whitelisted repo that was renamed or deleted):
   - A `owner/repo` or full URL reference — verify it's at least well-formed (valid GitHub org/repo shape); this rule does not perform live network requests, so "broken" here means structurally invalid or self-evidently stale (e.g. referencing a plugin name that used to exist in this project but was renamed/removed, verifiable via Glob) rather than a live HTTP check
   - A `<namespace>:<component>` reference to another *local* plugin — Glob for that plugin's actual component file; if it doesn't resolve, this is **Broken**, Critical, regardless of whitelist/blacklist status

## Worked Examples

**OK — whitelisted:**
```yaml
config:
  whitelist: ["github.com/anthropics/*", "claude-code-marketplace"]
```
A reference to `github.com/anthropics/claude-code` → Whitelisted, no finding.

**Critical — blacklisted:**
```yaml
config:
  blacklist: ["some-abandoned-fork/plugin-dev"]
```
A reference to `some-abandoned-fork/plugin-dev` → Blacklisted, Critical — must be removed or replaced.

**Advisory — unknown:**
A prose mention of `"adapted from the acme-tools plugin's skill-reviewer"` where `acme-tools` appears in neither list → Unknown, Advisory. Flag for the maintainer to decide: whitelist it (the reference is intentional and should stay) or blacklist it (clean it up) — R23 does not guess which.

**Critical — blacklisted, real example:**
```yaml
config:
  blacklist: ["rcc", "daymade", "daymade-docs", "daymade-skills"]
```
A prose mention of `"mirroring the rcc plugin's live check_hooks_json behavior"` → Blacklisted, Critical — must be removed or replaced, even though the mention is factually accurate provenance, because the maintainer has decided this plugin should not carry forward-referencing mentions of `rcc`.

**Critical — broken:**
A reference `acme-tools:hook-reviewer` where no `acme-tools` plugin/agent resolves anywhere in the project → Broken, Critical, independent of whether `acme-tools` itself is whitelisted or blacklisted.

**Critical — marketplace auto-allow doesn't cover a non-listed plugin:**
A `marketplace.json` lists plugins `a`, `b`, `c`. A reference to plugin `d` (not in that list) is **not** auto-allowed by this rule — it falls through to the normal whitelist/blacklist/unknown classification.

**Out of scope — excluded path:**
```yaml
config:
  excluded_paths: ["skills/skill-security/references/api-whitelist.md"]
```
`api-whitelist.md` catalogs dozens of third-party domains (`*.amazonaws.com`, `api.openai.com`, etc.) as functional security-policy content, not incidental mentions. With this path excluded, none of those domains are extracted, classified, or reported at all — the file is skipped in Step 0, before extraction.
