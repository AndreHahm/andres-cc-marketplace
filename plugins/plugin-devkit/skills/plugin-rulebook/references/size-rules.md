# Size Rules (R13 + R18 + R21)

Tiered quality thresholds for SKILL.md line count (R13/C1), inline code block size (R18/C2), and skill description size (R21).

## Configuration

Thresholds are read from `assets/settings.json`. To customize, edit the `config.thresholds` block under `R13_skillmd_line_limit` and `R18_code_block_line_limit`, or the `config` block under `R21_skill_description_size`, in that file.

---

## R13 / C1 — SKILL.md Line Count

Thresholds from `assets/settings.json → rules.R13_skillmd_line_limit.config.thresholds`:

| Lines | Severity | Label | Required Action |
|-------|----------|-------|-----------------|
| ≤ 100 | — | OK | None |
| > 100 | ⚪ Weak Warning | Note it | Record as informational; no fix required |
| > 300 | 🟡 Soft Warning | Plan extraction | Recommend planning extraction soon; do not block |
| > 490 | ⚠️ Warning | Fix recommended | Recommend moving content to `references/`; do not block |
| > 500 | ❌ Critical | Hard stop | Must move content to `references/` before proceeding |

**Severity behavior:**
- **Weak Warning** — record as polish item; never block the workflow; never require a fix
- **Soft Warning** — record as a planning note; recommend scheduling extraction; never block
- **Warning** — flag as Major issue with specific recommendation; do not block
- **Critical** — flag as Critical issue; block completion; require resolution before sign-off

---

## R18 / C2 — Inline Code Block Size

Thresholds from `assets/settings.json → rules.R18_code_block_line_limit.config.thresholds`:

| Block Lines | Severity | Label | Required Action |
|-------------|----------|-------|-----------------|
| ≤ 10 | — | OK | None |
| > 10 | ⚪ Weak Warning | Consider extraction | Suggest extracting; no fix required |
| > 20 | ⚠️ Warning | Extraction recommended | Recommend extracting to `scripts/` or `references/`; do not block |
| > 30 | ❌ Critical | Hard stop | Must extract before proceeding |

**Extraction target:** Runnable code → `scripts/<name>.<ext>`. Templates, config examples, non-executable content → `references/<topic>.md`. Replace the original block with a 1–2-line pointer.

**Before extracting, check whether extraction actually removes the violation:** if the block's content is a complete, coherent worked example (a full YAML frontmatter block, a full config file, a full script) whose entire pedagogical value is showing the whole thing at once, moving it into a new `references/<topic>.md` often just re-wraps the same content in another fenced block inside that new file — the identical R18 violation, relocated rather than fixed. Ask first: "would the destination file need to show this content in a fence of the same size to serve its own purpose?" If yes, extraction is not a real fix — use the **R18 exception (recorded)** pattern instead: add a one-line note directly above the block explaining that it is an intentional whole-example illustration where splitting would destroy pedagogical value, and leave the block in place. Reserve extraction for blocks that can be restructured into a genuinely standalone file with independent, non-nested fences (e.g. frontmatter as its own small block, each example as its own separate fence) — not for a block that would just be re-wrapped whole.

---

## R21 — Skill Description Size

Thresholds from `assets/settings.json → rules.R21_skill_description_size.config`:

| `description` length | Severity | Label |
|---|---|---|
| < 20 | ❌ Critical | Far too short — Claude has no basis to select the skill |
| 20–79 | ⚠️ Warning | Below the 80-char recommended minimum |
| 80–1018 | — | OK |
| 1019–1024 | ⚠️ Warning | Approaching the 1024-char hard max |
| > 1024 | ❌ Critical | Exceeds the hard max |

| `when_to_use` length (if present) | Severity | Label |
|---|---|---|
| ≤ 506 | — | OK |
| 507–512 | ⚠️ Warning | Approaching the 512-char max |
| > 512 | ❌ Critical | Exceeds the max |

| combined (`description` + `when_to_use`) length | Severity | Label |
|---|---|---|
| ≤ 1524 | — | OK |
| 1525–1536 | ⚠️ Warning | Approaching the 1536-char listing cap |
| > 1536 | ❌ Critical | Exceeds the listing cap |

**Severity behavior:**
- **Warning** — flag with the specific metric and value; recommend trimming or expanding toward the target band; do not block
- **Critical** — flag as Critical issue; block completion; require resolution before sign-off
- Overall severity for the component = the most severe tier triggered across the three metrics above

---

## How to Apply

1. Read `assets/settings.json` — load thresholds from R13, R18, and R21 config blocks
2. Count total lines in `SKILL.md`; compare against R13 thresholds
3. Find all fenced code blocks (``` delimiters); count lines in each; compare against R18 thresholds
4. Read the frontmatter `description` and `when_to_use` (if present) values; compute their individual lengths and their combined length; compare each against the R21 thresholds
5. Assign severity per the tables above
6. Only Critical findings block completion; Weak Warnings and Warnings are advisory
