# Policy and Trust

## Configuration

Resolution order: `.claude/codex-windows-guardrails.local.json` (gitignored, untracked) overrides
`assets/settings.json` (git-tracked default) field by field.

```json
{
  "windows_guardrails": {
    "enabled": false,
    "central_policy_version": "1"
  }
}
```

- Missing file, missing field, or unknown value → resolves to disabled *given today's shipped
  default of `enabled: false`* — the actual merge (`{...shipped, ...local}`) preserves whatever the
  shipped default says for any field the local override omits; it doesn't force `disabled`
  unconditionally. If the shipped default ever changed to `enabled: true`, an override that merely
  omits `enabled` would inherit that, not fall back to disabled.
- **Trust boundary:** `guarded-dispatch.mjs` runs `git ls-files --error-unmatch
  .claude/codex-windows-guardrails.local.json` internally (a subprocess call the script itself
  makes — this is not a separate model-facing tool grant, which is why `allowed-tools` only needs
  the one pinned script invocation). **Exact discriminator, since "non-zero means untracked" is the
  wrong inference and inverts fail-closed into fail-open:** the *only* outcome that honors the local
  override is exit code `1` with stderr matching `did not match any file` — that specific
  combination is git's genuine "this path is not tracked" signal. Exit `0` (tracked), exit `128`
  (not a git repository), a missing `git` binary, or any other exit code/stderr combination all fail
  closed to the shipped default. (An earlier draft of this document said "fail closed on any
  non-clean-untracked outcome" without stating this discriminator — ambiguous enough that an
  implementer could reasonably read "non-zero → untracked → honor it," the exact inversion of the
  intended fail-closed behavior. Verified live during Self-Review rework: a tracked local override
  is correctly ignored; the shipped disabled default is used instead.) Identical pattern to `plugin-auditor`'s own
  `references/codex-backend.md` trust check — cited, not re-derived.

## Scope: central + local-machine only (v1)

**Explicitly out of scope for v1:** a project being audited cannot supply its own additional policy
entries beyond this skill's own shipped denylist. The original concept's Open Question 1 — "what's
the trusted baseline for repo-specific policy, given a caller with no PR base/head split to source a
validated version from" — is resolved here by *not building that layer yet*, not by answering the
harder general case. Central policy (this skill's own shipped defaults) plus a local-machine
override (never a repo-tracked file, per the trust check above) is the whole policy surface today.

If repo-specific additive policy is needed later, it needs its own trusted-baseline design — sourcing
it from the target repository's own git history the way marketplace CI sources reviewer instructions
from a validated base SHA is one candidate, but that assumes a PR-shaped caller with a base/head
split, which `plugin-auditor`'s own dispatch (a live working tree, not a PR diff) doesn't have. Not
resolved here.

## `central_policy_version`

**Currently read but not yet propagated anywhere a caller can see it** — `guarded-dispatch.mjs`
resolves this field as part of the merged config but never threads it into the output envelope or
any other value the caller receives. It can't simply be added to the envelope's own `provenance`
object either: `codex-review-bridge`'s `ENVELOPE_SCHEMA` sets `additionalProperties: false` on that
object with a fixed field list. The intended use (a report showing which shipped-denylist version a
dispatch was validated against, per `plugin-auditor/references/codex-backend.md`'s own
`isolation_strength` precedent — something "the caller's own provenance" records, not the envelope
itself) is real but not implemented in this pass. Caller-side wiring is deferred, not silently
dropped — a Self-Review finding caught this document overclaiming the field as already "recorded in
provenance" when nothing in the code did that.
