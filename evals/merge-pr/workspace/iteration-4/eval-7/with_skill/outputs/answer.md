# Step 2 — Status Check Classification (merge-pr)

Per `merge-pr`'s SKILL.md step 2, every context named in the base branch's
`branchProtectionRule.requiredStatusCheckContexts` list is cross-referenced against step 1's
already-fetched `statusCheckRollup`, and classified into exactly one of four states
(passing / failing / pending / missing).

## Required contexts (4, from the GraphQL query)

| Required context | Matching `statusCheckRollup` entry | Classification | Why |
|---|---|---|---|
| `Hygiene (PR contract)` | `CheckRun`, `status: COMPLETED`, `conclusion: SUCCESS` | **passing** | `COMPLETED` + `SUCCESS` conclusion matches the passing rule directly. |
| `Python quality (ruff, ty, pytest)` | `CheckRun`, `status: IN_PROGRESS` | **pending** | `IN_PROGRESS` status matches the pending rule (`QUEUED`/`IN_PROGRESS`/`WAITING`/`REQUESTED`/`PENDING`). Never reported as failing or missing. |
| `Fork PR (unsupported)` | *no entry at all* | **missing** | No `CheckRun`/`StatusContext` entry with this `name`/`context` string appears anywhere in `statusCheckRollup` — it has never run for the current head commit. This is distinct from pending: nothing has actually started, vs. something running that hasn't finished. |
| `Publish Codex policy result` | `CheckRun`, `status: COMPLETED`, `conclusion: SUCCESS` | **passing** | `COMPLETED` + `SUCCESS` conclusion matches the passing rule directly. |

## Readiness determination

Step 2 requires **every** required context to classify as passing. Here, 2 of 4 do not:

- `Python quality (ruff, ty, pytest)` — **pending**
- `Fork PR (unsupported)` — **missing**

**The `--bypass-codex-review` exception does not apply here**, for two independent reasons:
1. No such flag was given in this scenario.
2. Even if it had been, the exception only fires when `Publish Codex policy result` is the
   *sole* non-passing required context. Here it already classifies as **passing** (nothing to
   bypass), and two *other* required contexts (`Python quality...`, `Fork PR (unsupported)`) are
   independently non-passing — either fact alone would make the exception inapplicable.

## Conclusion

**This PR is NOT ready to merge.**

Per step 2's instructions, when any check fails and no bypass exception applies, stop here — do
not proceed to step 3 (merge-rights check). The reportable readiness message:

> 2 required contexts not satisfied:
> - `Python quality (ruff, ty, pytest)` — **pending** (still running for the current head commit)
> - `Fork PR (unsupported)` — **missing** (never ran for the current head commit)

Both must reach a `passing` classification (or the narrow `--bypass-codex-review` path must be
invoked and apply — which it doesn't here, since Codex's check is already passing and other
required checks are also non-passing) before this PR can proceed to the merge-rights check.
