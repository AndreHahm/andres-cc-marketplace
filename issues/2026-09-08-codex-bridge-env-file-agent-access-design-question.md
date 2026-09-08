## Summary
Design question: should the codex bridge exclude a real `.env` file from what the AI agent can access, rather than only refusing the whole `danger-full-access` dispatch when one is present?

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs`
- **Region/Version**: N/A

## Reproduction Steps
N/A — this is a forward-looking design question, not a reproducible bug. Raised during the session that closed issue #295, deferred because no real `.env` file currently exists in this repo to design or test against.

## Expected Behavior
Unclear yet — that's the open question this issue tracks. One candidate: a real, gitignored `.env` file should never be readable by the AI agent at all, even if the rest of the dispatch is otherwise legitimate.

## Actual Behavior
Today, `guarded-dispatch.mjs`'s `walkFiles` deliberately walks gitignored files (a `.env` file is its own documented textbook case) specifically so `checkSecretFiles` can detect one and refuse the **entire** `danger-full-access` dispatch (`secret_file_in_scope`) before any Codex process starts. This means the agent never runs at all when a real `.env` is present — it's an all-or-nothing refusal, not a per-file exclusion from whatever the agent can subsequently access.

## Impact
**Low** — no known live incident; this is a proactive design question. Worth deciding deliberately before a real `.env` file exists in a repo this tooling is used against, rather than improvising a fix under pressure at that point.

## Additional Context
Raised while closing issue #295 (which added `.secretlintignore` consultation to `scan-staged-files.sh` and `guarded-dispatch.mjs`). A proposal to add `.env`/`.env.*` to `.secretlintignore` to address this was explicitly rejected in that discussion: it would not change `guarded-dispatch.mjs`'s own behavior at all (a `.env` match is a *strict* pattern, and that fix's own C1 correction specifically requires no strict pattern also match before honoring any `.secretlintignore` exemption — verified via a passing regression test), and it would separately reopen a real, already-fixed CI vulnerability (`.secretlintignore` is the same file the CI secretlint job consults; `.env`/`.env.*` were deliberately removed from it in PR #294's round-2 fix, specifically so a force-added `.env` still gets caught by CI).

**Open question this issue tracks:** is "refuse the entire dispatch on any `.env` sighting" the right, sufficient policy going forward, or should there be a narrower mechanism that excludes just that one file from whatever the agent can access while still allowing the dispatch to proceed for everything else? The latter would be a meaningfully different, larger change (an actual access boundary, not just a preflight filename check) — worth a dedicated design pass once a real `.env` file exists to design and test against, rather than speculating now.

Refs: #295
