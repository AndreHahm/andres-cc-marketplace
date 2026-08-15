# Semantic validation (deterministic, runs before a response is returned)

Schema conformance is necessary but not sufficient — a structurally valid response can still cite a nonexistent file, escape scope, contradict its own verdict, or fabricate evidence.

## Currently implemented (in `scripts/bridge-invoke.mjs`'s `semanticallyValidate`)

1. `dispatch.id` and `dispatch.reviewer` match the request (`backend`/`target_paths` are not yet cross-checked).
2. Every cited path is normalized, remains inside the allowed target scope, and exists on disk.
3. Finding IDs are unique.

Any failed check returns a `semantic_validation_failure` typed failure rather than passing the finding through.

## Not yet implemented

These were part of the original design and are known gaps, not currently tracked by any issue or checklist — not currently enforced:

- `contract_version` support check.
- Full `dispatch.backend`/`dispatch.target_paths` cross-check (only `id`/`reviewer` are checked today).
- Cited line-number validity (only the path portion of `location` is checked; the line number is not verified against the file's actual line count).
- `axis`/`severity` against the reviewer's own allowlist (currently only schema-typed, not allowlist-checked).
- `verdict` following the reviewer's own deterministic pass/fail rule.
- Undeclared-inspection-limit detection.

This validation does not prove the model's reasoning was correct — even once complete, it only proves the response is internally consistent and grounded in files that actually exist. Paired evaluation (comparing this bridge's output against a Claude-native reviewer on the same target) is what supplies the empirical quality check this deterministic pass cannot.
