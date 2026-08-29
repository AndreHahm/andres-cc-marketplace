## Summary
A security-motivated environment/credential-stripping step must be scoped to the actual risk path (an untrusted target reaching a trusted credential) — applying it blanket to every subprocess launch can silently break a differently-trusted path, such as a user-configured custom runner that is itself the trust boundary for its own credentials.

## Environment
- **Product/Service**: `plugin-devkit` plugin (source instance: `agent-development`'s `test-agent-trigger.sh`)
- **Region/Version**: this repo, found during PR #132 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A test harness strips credential-shaped environment variables (`_child_env()`) before launching a backend, to protect against an untrusted agent description reaching a live session with real credentials.
2. The same stripping is applied unconditionally before launching *any* configured backend, including a user-configured custom/fallback runner (`AGENT_TRIGGER_LLM_COMMAND`/`LLM_RUNNER_COMMAND`) that requires its own API key (e.g. `OPENAI_API_KEY`, a custom `SERVICE_TOKEN`) to function.
3. Configure a custom runner requiring such a credential and run the harness — the runner launches with its required environment variable already stripped and exits with a provider/auth error, even though this path was never the risk the stripping was meant to guard against.

## Expected Behavior
Credential-stripping should be scoped to the specific path where an untrusted target could reach a trusted credential (here: the built-in provider that loads the untrusted agent description directly) — not applied blanket to every subprocess launch, including ones where the user's own configured runner is the trust boundary for its own credentials.

## Actual Behavior
`_child_env()` stripped credentials before launching any provider, including the custom-runner fallback path, causing it to fail with no usable credentials even in a legitimate, user-trusted configuration.

## Impact
[Severity: Medium] The specific instance was already fixed in `plugin-devkit`'s PR #132 (commit `4e7057c`), scoping the strip to the built-in `claude` provider path only (`env=_child_env() if provider == "claude" else None`). No `.claude/rules/*.md` file currently states "scope a security-motivated environment/credential-stripping step to the actual risk path, not every subprocess launch" — any other harness or dispatcher in this repo (or a future one) that strips environment variables before launching a subprocess could reproduce the same overly-broad scoping and break a legitimately-trusted custom path.

## Additional Context
Mined from PR #132's own review history (`chatgpt-codex-connector[bot]`; 18 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #132` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/132#discussion_r3846426172
