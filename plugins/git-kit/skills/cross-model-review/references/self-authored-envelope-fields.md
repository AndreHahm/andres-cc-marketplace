# Fields Claude must self-author in its own findings envelope

Extracted from SKILL.md's Phase 1 per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the pointer and the two fields it names inline
(`dispatch.reviewer`, `dispatch.backend`); this file holds the rest.

`plugins/codex-kit/skills/codex-review-bridge/references/envelope-schema.md` documents the canonical
envelope shape — `contract_version`, `dispatch.{id,reviewer,backend,target_paths}`,
`provenance.{provider,model,cli_version,execution_profile}`, `findings[]`, `verdict`,
`inspection_limits` — but every field there is written from the perspective of `bridge-invoke.mjs`,
which fills `dispatch`/`provenance` programmatically for a real Codex dispatch. Claude's own native
pass never goes through that script, so nothing fills those fields automatically; each must be set by
hand when writing `$RUN/claude_fresh_eyes.json` (and `$RUN/claude_challenger.json` in Phase 2, with a
different `dispatch.id`/`dispatch.reviewer`):

- `contract_version: "1"` — matches the schema's own example; lets a future consumer reject an
  unknown shape.
- `dispatch.id` — follow the same pattern Codex's own dispatch-id uses:
  `cross-model-review-$(date +%s)-fresh-eyes-claude` (respectively `-challenger-claude` in Phase 2).
- `dispatch.target_paths: $TARGET_PATHS` — Claude's own native pass isn't scoped to
  `--target-paths` the way Codex's dispatch is (it reviews the full `"${DIFF[@]}"`), but the field
  still needs a value for the envelope to be well-formed; use the same eligible list Codex received.
- `provenance: {provider: "anthropic", model: "<this session's own model>", cli_version: null,
  execution_profile: "native"}` — self-reported, since there's no CLI wrapper to report it on
  Claude's behalf. `cli_version` has no equivalent for a native session; leave it `null` rather than
  inventing a value.

None of these fields are validated against `bridge-invoke.mjs`'s strict JSON schema the way Codex's
returned envelope is — Claude's own envelope is consumed only internally, by this skill's own Phase 2
cross-examination and Phase 3 merge/rank logic — but setting them explicitly still matters: without
them, someone following this skill by hand has no stated value to fall back on, and an envelope
missing required fields is not the "exact canonical shape" the schema actually specifies.
