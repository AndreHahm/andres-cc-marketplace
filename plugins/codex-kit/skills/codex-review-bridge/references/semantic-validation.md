# Semantic validation (deterministic, runs before a response is returned)

Schema conformance is necessary but not sufficient — a structurally valid response can still cite a nonexistent file, escape scope, contradict its own verdict, or fabricate evidence.

## Currently implemented (in `scripts/bridge-invoke.mjs`'s `semanticallyValidate`)

`semanticallyValidate` is exported and imported directly by `codex-windows-guardrails`'
`scripts/guarded-dispatch.mjs` for its own `danger-full-access` dispatch path (`isWithin`, which
`semanticallyValidate` depends on internally, is also exported but not separately imported by that
consumer — see `SKILL.md`'s "Public API beyond the CLI" for the full export/consumer breakdown) —
this list is authoritative for both, not only for callers going through this bridge's own CLI.

1. `dispatch.id` and `dispatch.reviewer` match the request (`backend`/`target_paths` are not yet cross-checked).
2. Every cited path is normalized, remains inside the allowed target scope, and exists on disk — this applies to `location` and, when present, to every entry in the optional `components[]` array (a multi-file finding's secondary citations get the same containment/existence check as its primary `location`).
3. Finding IDs are unique.

Any failed check returns a `semantic_validation_failure` typed failure rather than passing the finding through.

## Not yet implemented (open items, not decided against)

These were part of the original design. None is tracked by any issue or checklist outside this file,
and none is currently enforced — listed here as the single place a caller checks before assuming a
field is mechanically verified, per each item's own "why this doesn't block today" note:

- **`contract_version` support check** — not yet decided what a caller should do on a version
  mismatch (reject outright, or attempt best-effort parsing); no caller has ever emitted a
  non-`"1"` value, so there's nothing to test the check against yet.
- **Full `dispatch.backend`/`dispatch.target_paths` cross-check** — only `id`/`reviewer` are checked
  today; a mismatched `backend` or `target_paths` would currently pass through undetected, but no
  live caller has been observed sending one, so this hasn't blocked real usage yet.
- **Cited line-number validity** — only the path portion of `location` is checked; the line number
  itself is not verified against the file's actual line count. Low priority: a wrong line number is
  a findings-quality defect, not a trust-boundary or scope-escape risk the way an out-of-scope path
  would be.
- **`axis` against an allowlist** — not applicable as originally scoped: `SKILL.md`'s Inputs section
  and `references/envelope-schema.md`'s field semantics both now state plainly that no caller has
  ever defined an `axis` allowlist, so there is nothing yet to check `axis` against. This bullet
  stays here as a placeholder for if a caller ever does define one, not as a gap in current
  enforcement.
- **`verdict` following the reviewer's own deterministic pass/fail rule** — `verdict` is dropped,
  not modeled, by `plugin-auditor`'s Adapter (see `codex-backend.md`'s Adapter table) — the one
  known consumer of this envelope shape doesn't currently read `verdict` at all, so this check has
  no live consumer requiring it yet.
- **Undeclared-inspection-limit detection** — would require comparing `inspection_limits` against
  an independently-derived expected set (e.g. every file Codex was asked to look at but never cited);
  no such independent set is currently computed anywhere in this pipeline to compare against.
- **`--execution-profile`'s actual passed value threaded into `provenance.execution_profile`** — every
  non-`danger-full-access` value currently behaves identically at dispatch time (see `SKILL.md`'s
  Inputs section for `executionProfile`), so there is no behavioral difference for this field to
  currently disclose beyond what `provenance.isolation_strength` (`plugin-rulebook`'s
  `references/evidence-schema.md`) already carries.

This validation does not prove the model's reasoning was correct — even once complete, it only proves the response is internally consistent and grounded in files that actually exist. Paired evaluation (comparing this bridge's output against a Claude-native reviewer on the same target) is what supplies the empirical quality check this deterministic pass cannot.
