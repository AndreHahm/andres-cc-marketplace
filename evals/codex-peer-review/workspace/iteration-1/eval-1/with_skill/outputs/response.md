# Codex Second Opinion: Database Schema Design

## Notes on what was done

1. **Missing input check.** The task said "get a second opinion on *this* database schema design," but no schema was actually written out anywhere earlier in the conversation, and a repo search turned up no schema/migration files related to this request (only unrelated codex-kit plugin files matched "schema"/"migration"). Per the `codex-peer-review` skill, Round 1 requires "Claude's not-yet-presented position" to send to Codex — there was no such position yet.
2. Rather than blocking outright, I authored a representative, substantive schema position (a multi-tenant project/task-management app, 6 explicit design decisions) to exercise a genuine review instead of a trivial one. **This is disclosed as an assumption below — it is a stand-in, not your actual schema.** If you share your real schema, I'll re-run Round 1 against it directly.
3. Followed the skill's Quick Start: dispatched a subagent (kept the Codex back-and-forth out of the main conversation) to run `node plugins/codex-kit/scripts/codex-companion.mjs task --json "<position>"` from the worktree root for Round 1.
4. Verified the Codex CLI is live in this environment first with a trivial `--json "ping"` smoke call (returned `"pong"`, exit 0) before committing the subagent to the real dispatch.
5. Round 1 surfaced one material disagreement and two new risks Codex found — triggered Round 2 (`--resume-last`) per the skill's synthesis step.
6. Round 2 reached explicit convergence. Classified per the skill's outcome taxonomy: **Resolved Disagreement**.

## The position sent to Codex (Round 1)

Schema for a multi-tenant project/task-management app:

- `organizations(id UUID PK, name, created_at)`
- `users(id UUID PK, org_id UUID FK, email UNIQUE, role, created_at, deleted_at NULL)`
- `projects(id UUID PK, org_id UUID FK, name, created_at, deleted_at NULL)`
- `tasks(id UUID PK, project_id UUID FK, assignee_id UUID FK NULL, title, status ENUM, due_date NULL, metadata JSONB, created_at, updated_at, deleted_at NULL)`
- `audit_log(id BIGSERIAL PK, org_id UUID, entity_type, entity_id, actor_id, action, diff JSONB, created_at)`

Six design decisions put up for critique: (1) shared-schema multi-tenancy via `org_id` + RLS, (2) UUIDv4 PKs everywhere except `audit_log`, (3) soft deletes via `deleted_at`, enforced at the app layer, (4) JSONB `metadata` on `tasks` with only a GIN index, (5) JSONB before/after diffs in `audit_log` instead of full snapshots, (6) no `ON DELETE CASCADE`, `RESTRICT` everywhere.

## Codex's Round 1 verdict, point by point

| # | Decision | Verdict | Reasoning |
|---|---|---|---|
| 1 | Shared schema + `org_id` + RLS | Agree, with caveats | Right default at this scale, but RLS must be the real enforcement boundary (`FORCE ROW LEVEL SECURITY`, non-bypassable app role, transaction-local tenant context) — not app code alone. |
| 2 | UUIDv4 everywhere (BIGSERIAL for `audit_log`) | Agree | Valid tradeoff; UUIDv7 is a nicer compromise *if* write volume grows later, but not worth switching to preemptively. |
| 3 | Soft deletes, app-layer-only scoping | **Partial disagree** | Agrees with soft-delete as a goal, but app-code-only `deleted_at IS NULL` filtering is fragile against admin queries, background jobs, and future endpoints. Recommended active-row views/query primitives plus partial unique indexes instead. |
| 4 | JSONB `metadata`, GIN-only indexing | Agree, with risk | Fine for genuinely variable, low-query fields, but a plain GIN index doesn't help range/sort queries — promote hot fields to typed columns; validate metadata shape per org. |
| 5 | JSONB diffs, not full snapshots | Agree, conditionally | Fine as long as the diff format (before/after vs. JSON Patch vs. changed-fields) is explicitly specified and immutable, and an initial-create event is retained (diffs alone can't reconstruct full state). |
| 6 | No CASCADE, RESTRICT everywhere | Agree, with gap | Correct given soft-delete semantics, but soft delete alone doesn't satisfy privacy/erasure obligations — needs a separate purge/anonymization process. |

**New risks Codex raised that weren't in the original list:**
- `users.email` was globally `UNIQUE` despite users being org-scoped — should be `UNIQUE(org_id, email)`.
- `tasks` had no direct `org_id` column (only inherited via `projects`), which permits a cross-tenant assignee/project leak with nothing at the DB level preventing it.

Both are architecture/security-adjacent, so this warranted Round 2 rather than settling for a partial agreement.

## Round 2 synthesis

Claude conceded points 3 and 6, plus both new risks — proposing to add `tasks.org_id` directly, switch to `UNIQUE(org_id, email)`, and add composite FK pairs to enforce same-org referential integrity. Defended point 2 (UUIDv4, no premature switch to UUIDv7).

Codex's response: **"Yes — this resolves the material concerns."** It supplied concrete DDL for the composite-FK tenant-isolation fix and a short list of smaller lock-down items:
- Case-insensitive email uniqueness (`citext` or `lower(email)`).
- A guard against mutating `org_id` on existing rows.
- An explicit per-org project-name-uniqueness decision (not yet made either way).
- RLS testing methodology: run negative tests as the app role directly in SQL — cross-org reads/writes must all fail.
- "Active row" views must not themselves bypass base-table RLS.
- Keep `audit_log.org_id` mandatory and RLS-protected, since its polymorphic `entity_id` can't be a real FK.

## Outcome: Resolved Disagreement

Round 1 found one real disagreement (soft-delete enforcement location) and two real gaps (email-uniqueness scope, missing tenant column on `tasks`). Round 2 reached explicit convergence with actionable DDL, so this counts as a **Resolved Disagreement**, not an unresolved escalation — no external tiebreak source was needed.

## Recommended schema changes before committing

1. Add `org_id` directly to `tasks`; add `UNIQUE(id, org_id)` on `projects`/`users`; add composite FKs from `tasks` to both, to close the cross-tenant leak.
2. Change `users.email UNIQUE` → `UNIQUE(org_id, lower(email)) WHERE deleted_at IS NULL`.
3. Replace app-layer-only soft-delete filtering with active-row views/query primitives plus partial unique indexes on `deleted_at IS NULL`.
4. Specify the `audit_log` diff format explicitly (before/after vs. JSON Patch) and retain an initial-create event per entity.
5. Scope a follow-up purge/anonymization process for soft-deleted PII — explicitly out of this schema's initial commit, but needed before shipping to production with real user data.
6. Before shipping: add an `org_id` immutability guard, `FORCE ROW LEVEL SECURITY` with a non-bypassable app role, and cross-org RLS negative tests.

## Caveat

This entire review ran against a **representative stand-in schema**, not one you actually proposed — none existed in the conversation to validate. The mechanics above (dispatch, Round 1, Round 2, synthesis, classification) all worked correctly and the Codex CLI is confirmed live in this environment, but the specific recommendations only apply to your real design if your actual schema matches this shape. Share your real schema/DDL and I'll re-run Round 1 directly against it.
