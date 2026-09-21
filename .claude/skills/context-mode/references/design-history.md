# Design History

Summary of the design decisions and real-transcript validation behind `context-mode`, extracted from
the review session that produced this skill so the rationale ships with the plugin instead of living
only in a local, gitignored draft.

## Why not a pure skill

A skill triggering mid-session doesn't replace anything already in the transcript — there's no
session-level "system prompt slot" a skill can overwrite (that's a CLI-launch-time input, fixed for
the process). Relying on skill-description matching alone for phrase detection is inherently
non-deterministic (depends on the model's own judgment to invoke) — weak for something that should
fire reliably on specific phrases. This is why detection is split into a deterministic hook layer
(`scripts/detect_mode.py`) and a model-layer dispatch skill (`SKILL.md`).

## Real-transcript activation validation (3 rounds)

Validated against 376 real, human-typed user messages extracted from this repo's own session
transcripts (naive case-insensitive substring matching, the same mechanism the real hook uses).
Quoted excerpts below are screened for PII/credentials before shipping — this repo is public, per
`references/ship.md`'s own confirmation — since a future pass adding more transcript excerpts has
nothing else telling it to do the same screening.

| | Round 1 | Round 2 | Round 3 |
|---|---|---|---|
| No mode matched | 293 (78%) | 167 (44%) | 108 (28%) |
| Exactly one mode matched | 75 (20%) | 171 (45%) | 211 (56%) |
| 2+ modes matched (collision) | 8 (2%) | 38 (10%) | 57 (15%) |

Per-mode fire count, Round 3 (final, used for scope decisions below): review 93, ship 92, admin 82,
dev 44, research 15, plan 8, doc 3, draft 2.

**Key findings that shaped the design:**
- Round 1's drafted phrase lists missed the large majority of real phrasing (77% no-match) — the lists
  were expanded from real recurring patterns in Rounds 2-3 rather than guessed further.
- Real collisions (2+ modes matching one message) are overwhelmingly a single message that legitimately
  wants multiple phases run **in sequence** ("Check CI-status of PR #278. If green, then review and
  verify reviewer's findings." → ship then review), not genuine ambiguity between competing single
  modes. This is why the dispatch logic sequences by order-of-mention rather than always asking.
- Round 3 found that chasing individual phrase variants (typos, word order, British spelling) doesn't
  scale — the fix was dropping verb-phrase prefixes and matching on the distinctive noun/tool-name
  token instead (e.g. `"run skill-tester"` → bare `"skill-tester"`).
- Deliberately not chased: bare `"reviewer"`/`"merge"`/`"issue"`/`"fix it"` (too common in non-instruction
  messages — false-positive cost outweighed recall gain); phase-name continuations like "Continue with
  Task 2" (needs a phase→mode lookup table, a different mechanism, out of scope); literal verb use of
  "draft" ("draft that addition and post it") deliberately left unmatched to avoid conflating the word
  with the mode.

## Scope decision — dev/review/ship/admin only, first pass

Round 3's fire counts (review 93, ship 92, admin 82, dev 44 vs. research 15, plan 8, draft 2, doc 3)
drove the decision to wire only the top 4 modes in this first pass. `research`/`plan`/`draft`/`doc` are
deferred — real but too low-frequency to build detection against confidently yet.

## Mode-sequence handling — decided

The dominant real collision shape is a message that legitimately wants multiple modes run in order.
Decision: sequence by order-of-mention — activate the first-mentioned mode now, state the rest as
queued, switch when that work actually starts. Falls back to `AskUserQuestion` only when the message
gives no ordering signal at all (no numbering, no "then"/"if...then" connective).

Rejected alternatives: always-ask (would interrupt on ~15% of real messages, most of which a human
reader resolves instantly), and silent first-match-wins (drops the other matched mode(s) with no
disclosure).

## Default mode — decided

No forced default. "No active mode" is a valid ambient state governed by CLAUDE.md/rules alone, rather
than guessing a mode nobody asked for.

## Hook output mechanism — corrected during promotion

The original design called for a `UserPromptSubmit` hook `updatedPrompt` output field to rewrite the
prompt text inline. That field does not exist in the current `UserPromptSubmit` output schema (verified
directly against `code.claude.com/docs/en/hooks` during this skill's promotion pass) — the real,
available mechanism is `additionalContext`, which injects a system-reminder-style block alongside the
submitted prompt rather than rewriting the visible prompt text. `scripts/detect_mode.py` and `SKILL.md`
were both updated to reflect this.

## Validation Record

Direct stdin → stdout/exit-code verification of `scripts/detect_mode.py`, run during this skill's
Build/Self-Review pass:

| Input (`prompt`) | Output | Exit |
|---|---|---|
| `"Check merge readiness of PR #278"` | `additionalContext: "[Context-Mode candidate: ship]"` | 0 |
| `"Check CI-status of PR #278. If green, then review and verify reviewers findings."` | `additionalContext: "[Context-Mode candidates: ship, review]"` (ship before review, matching mention order) | 0 |
| `"Create a worktree for a new plugin, then implement solutions and commit and push"` | `additionalContext: "[Context-Mode candidates: admin, dev]"` | 0 |
| `"Continue."` | no stdout output | 0 |
| Malformed stdin (`not json`) | no stdout output (fail-open) | 0 |
| Non-dict top-level JSON (e.g. `["not", "a", "dict"]`) | no stdout output (fail-open) | 0 |
| Prompt containing a smart quote/em dash (UTF-8 multi-byte text) | correctly decoded and matched, no `UnicodeDecodeError` | 0 |
| A `triggers.json` key outside `{dev, review, ship, admin}` (e.g. an injected `"evil"` key) | never emitted, even though present in the file — enforced by `VALID_MODES` in `scripts/detect_mode.py` | 0 |

## Provenance boundary — added during promotion

The dispatch skill only honors the `[Context-Mode candidate(s): ...]` tag when it arrives as this hook's
own `additionalContext` output for the current turn — never when the identical string appears inside
file contents, tool output, a fetched page, or another agent's report. Without this boundary, any
content containing that literal string could force a mode switch (a prompt-injection surface caught
during this skill's Self-Review pass). See `SKILL.md`'s "How activation reaches this skill" section.

## Mode-switch-suggestion side effect — added 2026-09-21

The original design only deferred to `strategic-compact` on a "hard switch" (a genuinely heavy
transition, or context already large). This broadens that: `scripts/detect_mode.py` itself now
suggests `/compact` on **any** confidently-detected mode change, not just a hard one, since even an
ordinary posture change can leave stale, no-longer-relevant context behind — the cost of a missed
compaction opportunity on an ordinary switch outweighs the cost of an occasional extra suggestion,
especially since it's throttled to once per 5 minutes. See `SKILL.md`'s "Mid-session switching
mechanics" section for the operational statement and `SKILL.md`'s own "State and side effects" bullet
(under Known Limitations) for the exact files written and the no-lock/fail-open design.

## Nonce rejection rationale

A per-invocation nonce was considered and rejected (security-reviewer, 2026-09-17) as a mechanical
strengthening of the provenance boundary (`SKILL.md`'s "Provenance boundary" section): a nonce is a
comparison mechanism, and the only reference copy of the nonce would live in the same context window
the forgery itself occupies — if the model can reliably locate "this turn's own `additionalContext`
block" to read the authoritative nonce, it has already solved the provenance problem the nonce was
meant to solve, and gains nothing by also checking a nonce; if it can't locate that block reliably, the
nonce is unverifiable either way. This mirrors `route-through-git-kit-lifecycle-skills.md`'s own
conclusion about its marker handshake ("stops accidental bypass, not a deliberately adversarial
agent") — a context-mode nonce would be the same class of unauthenticated plaintext marker, checked by
the model itself inside the attacker's own channel, rather than by a separate process in a different
trust domain the way git-kit's version is. The accepted residual risk is bounded: a successful forgery
only ever changes operating *posture* among 4 fixed modes (verified directly against
`references/dev.md`, the most permissive profile — it disables no hard gate, only relaxes
ask-before-acting on obvious implementation choices), never a permission or tool-grant, is stated
plainly on every switch per `SKILL.md`'s "Reporting a mode change" section (never silent), and
presupposes an attacker who can already inject arbitrary text into context — a capability strictly more
damaging on its own than a posture flip. See `SKILL.md`'s Dispatch logic's own closed-vocabulary check
for the one concrete, mechanical fix that *was* worth making from this same review pass (a forged tag
can no longer steer an arbitrary `references/*.md` read).

## Hook latency

The hook's measured latency (roughly 170-260ms across repeated runs on this platform, mostly Python
interpreter startup — noisy from run to run) is well within this hook's actual configured timeout —
5 seconds, per `hooks/hooks.json`'s own registration for this entry, the real operative ceiling
(not `UserPromptSubmit`'s 30-second platform default, per `code.claude.com/docs/en/hooks` — verified
directly, not from this repo's own `hook-development` reference doc, which states a "<100ms" figure
for this event that does not appear anywhere in the official docs and should not be read as an
enforced platform requirement). It is, however, slower than ideal for a hook that runs on every single
prompt, even after dropping the `uv`-runner attempt this plugin's other Python hooks use (no
dependency-resolution benefit here, since `detect_mode.py` has zero third-party dependencies — removed
to save the one subprocess hop it did cost, though the measured effect was within this platform's own
run-to-run noise, not a clean improvement). Not something this pass fully resolved — the implementation
is already dependency-free, so the residual cost is Python interpreter startup itself, not a dependency
to remove. A future pass could investigate reducing that startup cost (a non-Python implementation, or
a persistent helper process) if this proves disruptive in practice.
