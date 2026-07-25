# Post-Fix Validation and Evidence-Gated Editing

## Post-Fix Validation (seven phases)

Run after applying fixes, before calling `skill-reviewer` again. Catches structural regressions that `skill-reviewer` may not surface.

1. **File Inventory** — List all files: `SKILL.md`, `references/`, `scripts/`, `assets/`
2. **Read All** — Load complete skill content (frontmatter, body, all referenced files)
3. **Frontmatter Check** — Verify required fields: `name`, `description`; check name is kebab-case, ≤64 chars, no reserved words
4. **Body Content** — Check: <500 lines? 80% rule applied? Clear procedural instructions in imperative form?
5. **References** — Verify links resolve and no reference→reference chain violation was introduced by the fix (see `issue-categorization.md`'s Major Issues list for the definition)
6. **Tool Scoping** — Verify no undeclared-tool violation was introduced by the fix (see `issue-categorization.md`'s Major Issues list); also check for unused declared tools (Minor). Principle of least privilege applied?
7. **Testing** — Does the description include trigger phrases? Will Claude recognize real requests?

Run only the phases relevant to the fixes applied. If fixes were frontmatter-only, skip phases 4–7.

## Evidence-Gated Editing (optional — for failure-driven loops)

Apply when the loop is triggered by observed skill failures rather than quality issues alone. An edit ships only when it demonstrably beats the version already in use.

**Gate — run every revision:**

1. Assemble a held-out check set (3–8 tasks, including the triggering failure). Keep it fixed for before/after comparability.
2. Score both the current version and the proposed fix.
3. Accept only if the fix strictly beats the current on the triggering criterion with no regression on other criteria. Ties → reject.

Cap at ~4 distinct changes per revision. Rank by: (1) systematic impact, (2) fills a real gap, (3) generalizable principle, (4) actionability.
