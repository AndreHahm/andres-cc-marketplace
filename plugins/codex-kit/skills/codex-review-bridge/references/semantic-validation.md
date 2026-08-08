# Semantic validation (deterministic, runs before a response is returned)

Schema conformance is necessary but not sufficient — a structurally valid response can still cite a nonexistent file, escape scope, contradict its own verdict, or fabricate evidence.

Checks, in order:

1. `contract_version` is supported.
2. `dispatch.id`, `reviewer`, `backend`, `target_paths` match the request.
3. Every cited path is normalized, remains inside the allowed target scope, and exists on disk.
4. Every cited line number is valid for the current file (file has at least that many lines).
5. Finding IDs are unique.
6. `axis` and `severity` belong to the reviewer's allowed values (caller-supplied allowlist).
7. `verdict` follows the reviewer's own deterministic pass/fail rule (e.g. "FAIL if any critical/major finding exists").
8. No undeclared inspection limit that would invalidate the review (e.g. Codex silently skipped a target file without disclosing it in `inspection_limits`).

Any failed check returns a `semantic_validation_failure` typed failure (see `typed-failures.md`) rather than passing the finding through. This validation does not prove the model's reasoning was correct — it only proves the response is internally consistent and grounded in files that actually exist. Paired evaluation (comparing this bridge's output against a Claude-native reviewer on the same target) is what supplies the empirical quality check this deterministic pass cannot.
