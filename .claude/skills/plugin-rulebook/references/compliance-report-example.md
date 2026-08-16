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

PASS    R1 R4 R5 R6 R8 R9 R10 R14 R19
ADVISORY R7 — emoji in heading "## 🚀 Quick Start" (SKILL.md:14) [SUGGESTED]
FAIL    R2 — references/patterns.de.md exists but references/patterns.md missing [REQUIRED]

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

## Worked Example: R23 Blacklist-First, Self-Whitelisting Excluded

Concrete scenario exercising the blacklist-first classification order and the same-plugin
`marketplace.json` exclusion (`external-reference-policy.md`'s Detection Procedure steps 2-3) —
this is the check that would have caught the pre-fix self-whitelisting bypass, and stands in as
this rule's own documented test scenario per `require-tests-for-behavior-changes.md`'s
"Skill, most other cases" tier.

**Setup:**
```yaml
config:
  blacklist: ["some-abandoned-fork/plugin-devkit"]
```
The plugin under review ships its own `<plugin-root>/.claude-plugin/marketplace.json` listing
`some-abandoned-fork/plugin-devkit` (a self-authored attempt to whitelist that name via the
marketplace auto-allow path), and its `SKILL.md` body mentions
`"mirrors some-abandoned-fork/plugin-devkit's live check_hooks_json behavior"`.

**Expected outcome:**
1. Step 2 drops the plugin's own `marketplace.json` from the auto-allow candidate set — it resolves
   inside the owning plugin root under review, so it never reaches the whitelist/auto-allow set at all.
2. Step 3 checks `config.blacklist` first, regardless: `some-abandoned-fork/plugin-devkit` matches →
   **Blacklisted, Critical** — classified before whitelist/auto-allow is even consulted, so the
   dropped `marketplace.json` (had it survived step 2) could never have silently cleared this anyway.
3. Report line: `FAIL R23 — some-abandoned-fork/plugin-devkit (SKILL.md:N) [REQUIRED] — blacklisted,
   self-authored marketplace.json excluded (resolves inside plugin under review)`.

**What this catches:** the pre-fix ordering bug (whitelist/auto-allow classified *before* blacklist,
with no same-plugin exclusion) would have let the plugin's own `marketplace.json` silently clear this
exact reference — Whitelisted, no finding, on a name the maintainer had explicitly blacklisted.
