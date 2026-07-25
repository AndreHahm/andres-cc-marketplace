# Size Limits

> **Rulebook override:** When `plugin-rulebook` is present (`**/plugin-rulebook/SKILL.md` found), load `<plugin-rulebook-dir>/references/size-rules.md` and apply its tiered thresholds from `<plugin-rulebook-dir>/assets/settings.json`. The values below are fallback defaults used only when `plugin-rulebook` is not found.

## Fallback Defaults (no plugin-rulebook present)

| Element | Limit | Action if Exceeded |
|---------|-------|--------------------|
| SKILL.md total | 500 lines | Extract content to `references/` |
| Inline code block | 30 lines | Extract to `scripts/` file and replace with pointer |
| `description` | min 80, max 1024 chars | Expand toward 80 if shorter; trim toward 1024 if longer |
| `when_to_use` | max 512 chars | Trim |
| combined (`description` + `when_to_use`) | min 80, max 1536 chars | Trim — this is the hard cap enforced by the skill listing |

## When plugin-rulebook Is Present

Apply the tiered severity from `<plugin-rulebook-dir>/references/size-rules.md` with thresholds from `assets/settings.json`:

- **R13 (line count):** Weak Warning >100, Soft Warning >300, Warning >490, Critical >500
- **R18 (code block):** Weak Warning >10, Warning >20, Critical >30
- **R21 (description size):** `description` — Critical <20, Warning 20–79, OK 80–1018, Warning 1019–1024, Critical >1024; `when_to_use` — OK ≤506, Warning 507–512, Critical >512; combined — OK ≤1524, Warning 1525–1536, Critical >1536

Only Critical findings block completion. Weak Warnings and Warnings are advisory.
