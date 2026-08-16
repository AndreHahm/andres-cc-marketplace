# Canonical findings envelope

This is codex-kit's canonical findings envelope — every reviewer dispatched through `codex-review-bridge` returns exactly this shape, with no partial/reviewer-specific variants. The schema itself (`ENVELOPE_SCHEMA` in `scripts/bridge-invoke.mjs`) is also directly imported by `codex-windows-guardrails`' `scripts/guarded-dispatch.mjs` for its own `danger-full-access` dispatch path — a change to this shape affects that consumer too, not only callers going through this bridge's own CLI.

```json
{
  "contract_version": "1",
  "dispatch": { "id": "audit-...-001", "reviewer": "security-reviewer", "backend": "codex", "target_paths": ["plugins/example/skills/example/SKILL.md"] },
  "provenance": { "provider": "openai", "model": "reported-model-id", "cli_version": "reported-cli-version", "execution_profile": "container-read-only" },
  "findings": [
    { "id": "M1", "severity": "major", "axis": "reviewer-defined-axis", "location": "plugins/example/skills/example/SKILL.md:42",
      "components": ["plugins/example/skills/other-example/SKILL.md"],
      "evidence": "Concise observed evidence", "finding": "What is wrong and why it matters", "fix": "Specific recommended remediation", "confidence": "high" },
    { "id": "M2", "severity": "major", "axis": "reviewer-defined-axis", "location": "plugins/example/skills/example/SKILL.md:7",
      "components": null,
      "evidence": "Concise observed evidence", "finding": "A single-file finding, showing components explicitly null", "fix": "Specific recommended remediation", "confidence": "medium" }
  ],
  "verdict": "pass",
  "inspection_limits": []
}
```

## Field semantics

**This describes the contract a conforming reviewer must satisfy — not every field below is mechanically checked before an envelope reaches the caller today.** `references/semantic-validation.md`'s own "Currently implemented" vs. "Not yet implemented" split is the single canonical, authoritative list of which fields `bridge-invoke.mjs`'s `semanticallyValidate` actually enforces right now — not restated here, so this file and that one can't drift out of sync with each other.

- `contract_version` — lets callers reject unknown shapes.
- `dispatch.id` — ties output to exactly one invocation and scratch directory.
- `reviewer` / `target_paths` — must match the caller's request.
- `backend` + `provenance` — makes mixed-backend reports auditable.
- `severity` — restricted to `critical` / `major` / `minor`.
- `axis` — schema-typed only (a plain string; `ENVELOPE_SCHEMA` carries no enum/allowlist for it). **This bridge does not enforce an allowlist of valid axis values** — an earlier draft of this contract promised one ("from the reviewer's own allowlist"), but no caller has ever actually defined or passed one, and `semanticallyValidate` never checks it against anything (see `references/semantic-validation.md`'s "Not yet implemented" list — the same correction already made for `reviewerType` in `SKILL.md`'s Inputs section applies here). If a caller needs to restrict which axis values are acceptable, it must validate `axis` itself after the envelope returns.
- `location` — must resolve to an in-scope path and, if a line is given, an existing line.
- `components` (nullable, not merely optional-by-omission — see below) — for a finding that is inherently about a relationship between multiple files (a dependency cycle, a bidirectional coupling, a cross-file consistency/mirror mismatch), lists every other component involved, in addition to `location`'s single primary citation — never as a replacement for it. Each entry is validated the same way as `location` (must resolve to an in-scope, existing path). A reviewer that has nothing to add here sends `null`, not an omitted key.
- `evidence` — what was observed, not just a conclusion.
- `fix` — preserves the remediation value existing reviewers already provide.
- `confidence` — `high` / `medium` / `low`; informs reporting, does not alter scoring.
- `verdict` — must follow the reviewer's own deterministic pass/fail rule.
- `inspection_limits` — discloses skipped files, unreadable inputs, or other fidelity reductions.

Counts are always derived from accepted `findings` — Codex never provides an authoritative aggregate count.

## Why `components` is `["array", "null"]`, not simply absent from `required`

`bridge-invoke.mjs` enforces the envelope via `codex exec --output-schema`, which runs under OpenAI's strict structured-output mode when `additionalProperties: false` is set — that mode requires every key listed in `properties` to also appear in `required`; a key can only be made optional by allowing it to be `null` while still requiring its presence. Every `findings[]` field in `ENVELOPE_SCHEMA` is therefore listed in `required`, and `components` is the one nullable field among them. This was found the hard way: an earlier version of this fix added `components` to `properties` without adding it to `required`, which OpenAI's API rejected outright (`invalid_json_schema`, "Missing 'components'") for every dispatched reviewer, not just the ones the field was meant to fix.
