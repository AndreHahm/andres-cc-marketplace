# R24 — Allowed Programming Languages: Full Detail

Full whitelist, banned list, exempt tags, and worked violation examples for R24, referenced from `SKILL.md`'s Active Rules section.

Only Python, Bash, and JavaScript/TypeScript may be used as programming/scripting languages anywhere in the plugin. The whitelist is closed: any language not on it is banned by default-deny, not just the languages named explicitly.

**Scope:** Standalone script files in any `scripts/` directory (any component), and fenced code blocks in SKILL.md, agent files, command files, hook config, rule files, `references/`, `examples/`, and `workflows/` that are tagged with a general-purpose programming/scripting language identifier.

**Whitelist** (configurable in `settings.json → rules.R24_allowed_programming_languages.config.whitelist_extensions` / `.whitelist_language_tags`):
- **Python** — `.py` files; fenced blocks tagged `python`/`py`
- **Bash** — `.sh` files; fenced blocks tagged `bash`/`sh`/`shell`
- **JavaScript/TypeScript** — `.js`/`.mjs`/`.cjs`/`.jsx`/`.ts`/`.tsx` files; fenced blocks tagged `javascript`/`js`/`jsx`/`typescript`/`ts`/`tsx`

**Banned — explicit:** **Ruby** — `.rb` files; fenced blocks tagged `ruby`/`rb`. Named explicitly in `config.banned` even though the closed whitelist already implies the same result, so a reader scanning `settings.json` sees the prohibition without having to infer it from an absence.

**Banned — everything else:** Any other script-file extension or fenced-block language tag denoting a general-purpose programming/scripting language (e.g. `.go`, `.rs`, `.java`, `.php`, `.pl`, `.lua`, `.ps1`, `.swift`, `.kt`) is a REQUIRED violation by the same default-deny — nothing needs to be added to `config.banned` for it to be rejected.

**Exempt (not governed by this rule):** data/markup/config formats and illustrative-output tags are not "programming languages" for this rule's purposes: `yaml`, `yml`, `json`, `toml`, `ini`, `xml`, `html`, `css`, `markdown`, `md`, `text`, `plaintext`, `console`, `output`, `diff`, `http` (configurable in `config.exempt_tags`). An untagged fenced block (` ``` ` with no language identifier) cannot be classified — treat as Advisory/Unknown, not a violation.

**Violations:**
- A `.rb` script file — banned language (Ruby, explicit), REQUIRED (this rule's first real violation, `skill-tester/scripts/aggregate_benchmark.rb`, was ported to Python and removed)
- A fenced code block tagged ` ```go ` presenting an executable script — banned by default-deny, REQUIRED

**Fix:** Rewrite the script or embedded example in Python, Bash, or JavaScript/TypeScript. Language choice is a policy decision, not a size tradeoff — unlike R18, this rule has no exception-recording escape hatch; a maintainer who wants to keep a non-whitelisted language must change `config.whitelist_extensions`/`config.whitelist_language_tags` explicitly rather than annotate around the finding.
