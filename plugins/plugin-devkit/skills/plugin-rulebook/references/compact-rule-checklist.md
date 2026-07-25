# Compact Rule Checklist

Mechanical pattern → violation → severity reference for all 22 currently-enabled rules (R1-R10, R13, R14,
R17-R26; R11/R12/R15/R16 disabled per `assets/settings.json`). No narrative rationale, examples, or
"why enable" content — read `SKILL.md` instead for that. Kept in sync with `assets/settings.json` and
`SKILL.md`'s own Active Rules section; any threshold shown here must match those two files exactly (R20).

**Tier key:** `M` = mechanical (pattern/threshold match, safe for a faster model per this rule's own
documented risk profile) · `J` = judgment-heavy (requires contextual reasoning — always run at full
model quality regardless of dispatch mode).

| Rule | Severity | Tier | Scope | Violation pattern | Fix |
|---|---|---|---|---|---|
| R1 Language: English Only | REQUIRED | M | SKILL.md, agent/command files, hook config, rule files, references/*.md | Non-English text in frontmatter or body (exception: locale-specific user-facing output strings) | Translate to English |
| R2 Reference Files: English Primary Required | REQUIRED | M | references/ dirs | A `references/<topic>.<lang>.md` variant exists with no English `references/<topic>.md` | Create the English primary first |
| R3 Reference Files: Optional Multilingual Variants | OPTIONAL | M | references/ dirs | Variant lang code not in `settings.json → languages.additional` (default de/zh/fr/es/ja/pt), or variant content diverges from English primary | Use a valid lang code; sync content |
| R4 Naming: Kebab-Case Only | REQUIRED | M | `name` field, directory names, reference filenames | Pattern `^[a-z][a-z0-9-]+[a-z0-9]$` violated (camelCase/underscore/uppercase); < 3 or > `naming.max_length` (64) chars; contains `anthropic`/`claude` | Rename to kebab-case; remove forbidden word |
| R5 Frontmatter: No Non-Standard Fields | REQUIRED | M | SKILL.md, agent files | `version` present (command-only); `AskUserQuestion` in `allowed-tools` (not a tool). ADVISORY only: `hooks`/`mcpServers`/`permissionMode` in agent files (schema-accepted, not honored) | Remove the field; for agent-file ADVISORY, flag not block |
| R6 Tool Scoping: Least Privilege | REQUIRED | M | any `allowed-tools` field + body | Bare `Bash`/`Bash(*)`/`Bash(sh:*)`/`Bash(bash:*)`/`Bash(cmd:*)`/`Bash(powershell:*)`; a tool used in body but absent from `allowed-tools`; a tool declared but never used (over-permission, still REQUIRED to flag per least-privilege) | Scope to named tool/script; add/remove tool declaration |
| R7 Formatting: No Emoji in Structural Elements | SUGGESTED | M | headings, frontmatter, step labels | Emoji in a heading/frontmatter/procedural label (sample output and illustrative examples are exempt) | Remove emoji from structural element |
| R8 Frontmatter: Multiline Description Syntax | REQUIRED | M | `description` field | > 80 chars not using `>-` block scalar. Command files only, ADVISORY: 61-80 chars (truncates in `/help`) | Convert to `>-` block scalar |
| R9 Security: No Hardcoded Credentials | REQUIRED | M | all files incl. scripts/assets/config | API key/token/password/secret present (placeholder values like `YOUR_API_KEY_HERE`/`$API_KEY` exempt) | Remove; replace with placeholder |
| R10 Reference File Naming: Descriptive and Specific | REQUIRED | M | references/ filenames | Generic name (`reference.md`/`guide.md`/`config.md`/`docs.md`/`info.md`); topic portion > 40 chars; unrecognized abbreviation | Rename descriptively |
| R13 SKILL.md Line Count | REQUIRED (tiered) | M | SKILL.md | ≤100 OK · >100 Weak Warning (info) · >300 Soft Warning · >490 Warning · >500 Critical (blocking) | Move content to references/ |
| R14 References: One Level Deep | REQUIRED | M | references/ dirs | Any subdirectory inside `references/` | Flatten to `references/<name>.md`; or extract to a new skill |
| R17 Formatting: No Bare URLs | SUGGESTED | M | body prose | Bare URL not in `[text](url)` form (code blocks and example placeholders exempt) | Convert to named-reference syntax |
| R18 Inline Code Block Size | REQUIRED (tiered) | M | any fenced code block | ≤10 OK · >10 Weak Warning (info) · >20 Warning · >30 Critical (blocking). 3+ Weak-Warning blocks → one consolidated ADVISORY | Extract to `scripts/`/`references/` |
| R19 Canonical Path Resolution | REQUIRED | J | any named component | Component name resolves to 2+ directories with differing content; report omits the resolved absolute path. Exception: `.claude/` ↔ plugin in-development mirror (must verify identical, not flag) | Report resolved path; disambiguate/resync if duplicates differ |
| R20 Duplicate Fact Sweep | REQUIRED | J | whole plugin tree | A canonical value (enum/threshold/forbidden-field list) changed but a sibling file still states the old value | Grep tree for old value; update every occurrence or record intentional divergence |
| R21 Skill Description Size | REQUIRED (tiered) | M | SKILL.md frontmatter only | `description`: <20 Critical, 20-79 Warning, 1019-1024 Warning, >1024 Critical · `when_to_use`: 507-512 Warning, >512 Critical · combined: 1525-1536 Warning, >1536 Critical | Trim/expand to band; move detail to body |
| R22 Argument Frontmatter Consistency | REQUIRED (tiered) | M | SKILL.md + commands/*.md | Body accepts args but `argument-hint`/`arguments` empty → Warning · position/name beyond declared → Critical (missing) · declared slot never referenced → Critical (stale) · declared order ≠ body consumption order → Critical (wrong position). Positional placeholders are 0-based (`$0` = first arg) | Correct argument-hint/body mismatch |
| R23 External Reference Policy | REQUIRED (tiered) | J | SKILL.md, agent/command files, hook config, rule files, references/scripts/examples/workflows | Whitelisted → OK · Blacklisted → Critical · Unknown → Advisory · Broken (doesn't resolve) → Critical. Merge repo override `{REPO_ROOT}/.claude/plugin-rulebook.config.json` first. Illustrative-example mentions exempt | Classify explicitly whitelist/blacklist; fix broken reference |
| R24 Allowed Programming Languages | REQUIRED | M | scripts/ files, fenced code blocks | Any language/extension outside Python/Bash/JS-TS whitelist (closed allowlist, default-deny); Ruby explicitly banned | Rewrite in Python/Bash/JS/TS |
| R25 Unplanned-Overhead Disclosure | REQUIRED | J | SKILL.md/agent files documenting a quick/fast/bounded phase | Actual execution deviated from documented scope (retry, detour, fallback) with no plain-language disclosure | Add explicit disclosure instruction |
| R26 Expensive-Action Opt-In | REQUIRED | J | SKILL.md/agent files with per-item nested-call or whole-surface-rescan steps | An expensive action (per-item LLM/subprocess fan-out, whole-plugin re-verification, multi-agent dispatch) not gated behind an explicit `AskUserQuestion` | Add opt-in gate before the expensive step |

## R19/R20 Procedure Reminder (always full-quality, never skipped in Fast path)

1. Resolve the canonical absolute path of the target component first. If it resolves to 2+ directories, compare contents — halt and FAIL before continuing if they differ (except the documented `.claude/` mirror exception).
2. When a canonical value in this check touches something else's stated fact (an enum, a threshold), grep the plugin tree for the previous value before closing out — this is R20's job regardless of which mode dispatched this check.

## R18 Consolidation Rule

When 3 or more code blocks in the same component exceed the 10-line weak-warning threshold, emit one consolidated ADVISORY ("N blocks exceed 10 lines; consider extracting the largest (M lines)") rather than one entry per block.
