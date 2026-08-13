# Finding-ID Fix Contract

Shared by `skill-development`, `agent-development`, `command-development`, `hook-development`,
`rule-development`, and `skill-improver-loop` — the contract each honors when a caller (e.g.
`plugin-lifecycle-downstream`'s Phase 4/6/8 fix batches) supplies a bounded finding-ID list to
act on, instead of an open-ended "improve this" request. This file is the single owner of the
contract's shape; each dev skill's own SKILL.md links here rather than restating it, so a
future change to the contract lands once, not six times.

## Input

- `finding_ids`: a bounded list of finding IDs, `<source>:<local-id>` per
  `plugin-rulebook/references/evidence-schema.md`, never an implicit "fix everything you
  notice while you're in there."
- Each ID's originating Finding (`severity`, `scope`/`location`, `fix` suggestion) supplied by
  the caller — under this contract, the dev skill does not re-derive findings from scratch.

## Behavior

- Touch only the file(s) named by the supplied finding IDs' `scope`/`location` — no unrelated
  cleanup, no drive-by fixes outside the named set, even when something else nearby looks
  wrong.
- For each ID, apply the smallest fix that resolves it, per the dev skill's own existing
  authoring standards — this contract changes *what's in scope*, not *how a fix is authored*.
- **Never mark a fix verified.** That stays the originating checker's job — the
  validator/reviewer/test that produced the finding rechecks live files, per
  `plugin-lifecycle-downstream`'s Core Contract point 3 ("The component that applies a fix
  does not verify its own work"). Hand control back to the caller once fixes are applied;
  don't re-invoke the checker yourself to declare success.

## Output

Return, per finding ID:

```yaml
finding_id: <source>:<local-id>
status: applied | deferred | failed
files_changed: [<path>, ...]
note: <why deferred/failed, or null>
```

Plus an overall `changed_files` list (the union across every applied ID) for the caller's own
commit/re-check step.

## When This Contract Does Not Apply

A direct, open-ended user request — "improve this skill," "add a section for X," "fix the
tool scoping on this agent" — is unaffected. This contract only activates when the caller
supplies a bounded finding-ID list explicitly; it is an additional invocation shape, not a
replacement for each dev skill's normal direct-use behavior.

## `skill-improver-loop`'s Additional Rules

- Its own bounded attempt count (previously a hardcoded 3-cycle limit) comes from the scope
  manifest's `max_fix_attempts` field when invoked under this contract, not its own default.
- It is **one of two** valid fix paths for a skill-type finding — `skill-development` used
  directly is the other. It is never the *only* path for a skill-type finding, and it is
  never a valid path for any other component type (agent/command/hook/rule findings always go
  through their own matching dev skill directly, never through this loop).
