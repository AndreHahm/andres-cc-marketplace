# Canonical findings envelope

This is codex-kit's canonical findings envelope — every reviewer dispatched through `codex-review-bridge` returns exactly this shape, with no partial/reviewer-specific variants.

```json
{
  "contract_version": "1",
  "dispatch": { "id": "audit-...-001", "reviewer": "security-reviewer", "backend": "codex", "target_paths": ["plugins/example/skills/example/SKILL.md"] },
  "provenance": { "provider": "openai", "model": "reported-model-id", "cli_version": "reported-cli-version", "execution_profile": "container-read-only" },
  "findings": [
    { "id": "M1", "severity": "major", "axis": "reviewer-defined-axis", "location": "plugins/example/skills/example/SKILL.md:42",
      "evidence": "Concise observed evidence", "finding": "What is wrong and why it matters", "fix": "Specific recommended remediation", "confidence": "high" }
  ],
  "verdict": "pass",
  "inspection_limits": []
}
```

## Field semantics

**This describes the contract a conforming reviewer must satisfy — not every field below is mechanically checked before an envelope reaches the caller today.** See `references/semantic-validation.md`'s own "Currently implemented" vs. "Not yet implemented" split for exactly which of these are enforced by `bridge-invoke.mjs`'s `semanticallyValidate` right now (as of this writing: `dispatch.id`/`reviewer` match, in-scope-and-on-disk `location` path, and unique finding IDs — `target_paths` cross-checking, `location`'s line-number validity, `axis`/`severity` allowlist-checking, and `verdict`'s pass/fail-rule consistency are not yet enforced).

- `contract_version` — lets callers reject unknown shapes.
- `dispatch.id` — ties output to exactly one invocation and scratch directory.
- `reviewer` / `target_paths` — must match the caller's request.
- `backend` + `provenance` — makes mixed-backend reports auditable.
- `severity` — restricted to `critical` / `major` / `minor`.
- `axis` — from the reviewer's own allowlist (caller-supplied, not invented by the bridge).
- `location` — must resolve to an in-scope path and, if a line is given, an existing line.
- `evidence` — what was observed, not just a conclusion.
- `fix` — preserves the remediation value existing reviewers already provide.
- `confidence` — `high` / `medium` / `low`; informs reporting, does not alter scoring.
- `verdict` — must follow the reviewer's own deterministic pass/fail rule.
- `inspection_limits` — discloses skipped files, unreadable inputs, or other fidelity reductions.

Counts are always derived from accepted `findings` — Codex never provides an authoritative aggregate count.
