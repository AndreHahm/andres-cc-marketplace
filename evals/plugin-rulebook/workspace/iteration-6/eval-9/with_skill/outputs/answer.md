# R35 (Standard Sections Required) check

Skill headings present: Quick Start, When to Use This Skill, Testing & Validation. There is no `references/` directory.

**Missing required section**
- `## When NOT to Use` is missing. R35 requires it on every skill ("Always"). This is the only R35 finding. R35 is [REQUIRED, default: on], so it is a FAIL until the section is added.

**Reference Guide: not a problem**
- `## Reference Guide` is required only when the skill has a `references/` directory. This skill has none, so its absence is fine. The Fix note says so explicitly.

**"When to Use This Skill" wording: not a problem**
- Headings are matched by substance, not exact wording. `## When to Use This Skill` satisfies `## When to Use`. The accepted patterns come from `assets/settings.json -> rules.R35_standard_sections_required.config.required_sections`.
- `## Quick Start` is present and satisfied.

**Testing & Validation: not checked by R35**
- R35 deliberately does not check it, to avoid reporting one missing heading twice. Its presence or absence has no effect on R35. The heading is present here. R29 is what enforces it, and R29 would fail a SKILL.md that lacked it.

**Fix:** add a `## When NOT to Use` section. R35 applies because the skill is newly created (forward-looking scope).
