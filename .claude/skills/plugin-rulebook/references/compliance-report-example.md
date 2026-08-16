# Compliance Report Example

Worked example of the Compliance Check Procedure's step 7 output shape (`SKILL.md`'s "Compliance Check
Procedure" section), extracted here to keep `SKILL.md` itself under its own R13 line-budget threshold.

```
📋 Rulebook Compliance: <component-name> (<type>)
Path: <resolved-absolute-path> [R19: no duplicates found]
Settings: assets/settings.json [loaded]
Repo overrides applied (.claude/plugin-rulebook.config.json): whitelist +["acme-tools"], blacklist +["rcc"]
Marketplace auto-allow applied: none found
Rules checked: N enabled / 27 total

PASS    R1 R2 R4 R5 R6 R8 R9 R10 R14 R19
ADVISORY R7 — emoji in heading "## 🚀 Quick Start" (SKILL.md:14) [SUGGESTED]
FAIL    R3 — references/patterns.de.md exists but references/patterns.md missing [REQUIRED]

Status: FAIL — 1 blocking violation
Scope: structure/naming/formatting/frontmatter only — does not check script or code
correctness (encodings, shell logic, mojibake). Run `scripts-reviewer` separately for that.
```

**Repo overrides / marketplace auto-allow lines:** always present, never omitted, so a reader can't mistake
"the line is missing" for "nothing was applied." The marketplace auto-allow line distinguishes three
distinct outcomes, not just applied-vs-not — collapsing them to a single "none" hides the
security-relevant middle case:
- `none found` — no `marketplace.json` anywhere in the repo (the example above)
- `disabled` — `config.auto_allow_marketplace_json_entries` is `false`; step 2 was skipped entirely
- `applied: <plugin>/.claude-plugin/marketplace.json → ["a", "b"]` plus, on a separate line if any were
  found but dropped, `excluded (inside plugin under review): <path>` — a found-but-excluded manifest is
  the security-relevant event and must stay visible, never folded into "none"

When something *was* applied, name the source file and the exact entries contributed — never just "some
overrides were applied."
