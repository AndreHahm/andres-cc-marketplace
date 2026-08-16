# External Reference Policy (R23)

Checks that every reference to an external company, GitHub organization, marketplace, plugin, skill, or repository is either explicitly whitelisted, explicitly blacklisted, resolvable and unclassified (advisory), or broken (critical, regardless of classification).

**Config is split across two files.** `assets/settings.json`'s `rules.R23_external_reference_policy.config` ships with `whitelist`/`blacklist`/`excluded_paths` empty — those three fields are inherently repo-specific and live instead in `{REPO_ROOT}/.claude/plugin-rulebook.config.json`, merged on top at load time. Every step below that reads `config.whitelist`/`config.blacklist`/`config.excluded_paths` means "the merged values," not just what's in `assets/settings.json`. See `plugin-rulebook/SKILL.md`'s "Repo-Specific Configuration" section for the full load procedure.

**Disclosure, not silent application.** A committed `{REPO_ROOT}/.claude/plugin-rulebook.config.json` can turn off a finding permanently for everyone who runs this rule — no different in effect from a safety-weakening override, even though the file is git-tracked rather than a local/gitignored one. The compliance report (`SKILL.md`'s Compliance Check Procedure) must enumerate every `whitelist`/`blacklist`/`excluded_paths` entry actually applied from that file, plus every marketplace-auto-allow entry actually applied from step 2 below, each tagged with its source file — never merged into the report silently as if they were this plugin's own portable defaults.

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

2. **Locate marketplace.json auto-allow candidates, excluding the plugin under review's own tree.** If `config.auto_allow_marketplace_json_entries` is `false`, skip this step entirely (the auto-allow candidate set is empty; the compliance report's disclosure line reads `disabled`, not `none`). Otherwise: `Glob("**/marketplace.json")` across the repo, then drop any match that resolves inside **the plugin root that owns the target component** — not the component's own directory, since a `marketplace.json` never lives inside an individual skill/agent folder in practice (the real, conventional location is `<plugin-root>/.claude-plugin/marketplace.json`, or a repo-root `.claude-plugin/marketplace.json` for the marketplace's own manifest). Resolve "the plugin root that owns the target component" as: for a directory-based component (a skill), walk up from the component directory to the nearest ancestor containing `.claude-plugin/plugin.json`; for a file-based component (an agent, command, or hook script), same walk-up from the file's containing directory; for a whole-plugin audit, the plugin root itself. **If this boundary cannot be resolved confidently** (no `.claude-plugin/plugin.json` found within a reasonable number of ancestor levels, or a path-comparison outcome that isn't clearly inside-vs-outside), **fail closed: treat every `marketplace.json` found as excluded** rather than silently keeping the original, wider Glob result — a component under audit must never be able to whitelist its own name by shipping a `marketplace.json` at any level of its own plugin. Compare paths fully-resolved (realpath, following symlinks/junctions) and case-insensitively on a case-insensitive filesystem. For each surviving `marketplace.json`, read its plugin list; this is the auto-allow candidate set. Record which file(s) contributed which names, and which file(s) were found-but-excluded (with why) — the compliance report must disclose both (see `SKILL.md`'s Compliance Check Procedure).

3. **Classify each candidate against the merged config, blacklist first:**
   - Matches `config.blacklist` → **Blacklisted**, Critical — checked *before* whitelist/auto-allow, so a blacklisted name is never silently cleared by also appearing in a `marketplace.json`'s auto-allow candidate set from step 2
   - Matches `config.whitelist`, or the surviving marketplace auto-allow candidate set from step 2 → **Whitelisted**, no finding
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
  blacklist: ["some-abandoned-fork/plugin-devkit"]
```
A reference to `some-abandoned-fork/plugin-devkit` → Blacklisted, Critical — must be removed or replaced.

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

**Critical — a component under review cannot self-whitelist a blacklisted name:**
```yaml
config:
  blacklist: ["some-abandoned-fork/plugin-devkit"]
```
The plugin that owns the component under review ships its own `<plugin-root>/.claude-plugin/marketplace.json` listing `some-abandoned-fork/plugin-devkit`. Step 2 drops that `marketplace.json` from the auto-allow candidate set because it resolves inside the owning plugin root (not merely the individual component's own directory, which a marketplace manifest never lives inside in practice) — the reference still classifies as **Blacklisted**, Critical, exactly as if the `marketplace.json` didn't exist. (Before this ordering/sourcing fix, the marketplace auto-allow list was built from every `marketplace.json` in the repo with no such exclusion, and whitelist/auto-allow was classified before blacklist — together, a plugin could clear its own blacklisted reference silently via a manifest that no per-component boundary would ever have caught.)

**Out of scope — excluded path:**
```yaml
config:
  excluded_paths: ["skills/skill-security/references/api-whitelist.md"]
```
`api-whitelist.md` catalogs dozens of third-party domains (`*.amazonaws.com`, `api.openai.com`, etc.) as functional security-policy content, not incidental mentions. With this path excluded, none of those domains are extracted, classified, or reported at all — the file is skipped in Step 0, before extraction.
