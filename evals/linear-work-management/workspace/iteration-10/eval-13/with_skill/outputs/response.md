# Walkthrough: resolving repository slug `Acme/Widgets.git` (create, test_run true)

Dry run only. No Linear tool was called and no script was run. I followed the "Resolving a repository slug" section of `linear-work-management/SKILL.md`, with the Versioned Configuration and Local Override rules from `FOUNDATION_CONTRACTS.md`.

## Steps

1. **Local Override trust check.** You told me this passes, so I treat `.claude/workmanagement-kit.local.json` as confirmed untracked and honor its overrides. In a live run I would first run `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`. Exit 1 is the only outcome that passes. If it failed, I would return a rejection and stop.

2. **Normalize the slug.** `Acme/Widgets.git` becomes `acme/widgets.git` after lowercasing. Removing one trailing `.git` gives `acme/widgets`. It matches `^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$`, so it is valid.

3. **Look up an exact key in `linear.repositories`.** `acme/widgets` is the single key, so it is a match. There is no second key that normalizes to the same value, so there is no configuration error. The mapping is `production_team_id: T-PROD`, `test_team_id: T-TEST`.

4. **Check the operation in use.** The caller wants a create, which is a write, so the operation is `linear.write`. It is `verified` with a non-null `verified_at`, so this check passes.

5. **Choose the team.** The caller asked for a test run, so I pick `test_team_id`, which is `T-TEST`. It is non-null, so there is no null-ID rejection.

6. **Confirm the team is in the operation's `team_ids`.** `linear.write.team_ids` is `[T-PROD]`. `T-TEST` is not in that list, so the check fails. The rejection is per team. The production team is in scope, but the test team is not. I do not fall back to `T-PROD`, because a test run must never be routed to the other environment's team.

## Result returned to plugin-integration-intake

**Rejected.**

- Slug: `acme/widgets` (normalized from `Acme/Widgets.git`)
- Environment requested: test
- Team: `T-TEST`
- Reason: the mapped `test_team_id` `T-TEST` is not in `linear.write`'s approved `team_ids` (`[T-PROD]`), so it is out of scope. A mapped team outside the operation's `team_ids` is rejected, never silently used. Test-run work for this repository is therefore rejected. Production work for `acme/widgets` (`T-PROD`) would still resolve.
- What was verified: the Local Override trust check passed; the slug is valid and matched exactly; `linear.write` is verified with a non-null `verified_at`; the team choice followed the test-run signal.
- Not done: no guessing, no fallback to `T-PROD`, no write. This section only resolves and writes nothing.

Fix for the installer, if test runs should be allowed: add `T-TEST` to `linear.write.team_ids` in the local override. The array replaces the shipped one wholesale, so the override must list every team it wants, for example `[T-PROD, T-TEST]`.
