# Plan: gates for a Wave 2 PR (plan-only, no tools that touch git, gh or the network)

**Assumptions:** the branch is `fix/issue-461-workmanagement-kit` in the worktree. No PR exists yet, and the Linear issue state is unknown. I read only `FOUNDATION_CONTRACTS.md`, `versioned-configuration.json`, `.pre-commit-config.yaml` and the first 927 lines of `.github/workflows/marketplace-ci.yml`. No Glob was available, so I could not list every workflow file.

## Steps in order

1. **Resolve the policy profile (`repository-gates`, step 1).** Read `versioned-configuration.json`. `repository_policy.provider_profile` is `null` and `repository_policy.gate_discovery` is `"unconfigured"`. The local override would only be merged after the `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"` trust check. I would not run that check in this plan-only pass, so I assume the override is absent or untrusted.
2. **Stop with a manual handoff.** The profile is unset, so no provider is resolved. Per the skill's Failure and Resume section, I would state that `repository_policy.provider_profile` is missing. I would not fall back to a raw `git` or `gh` command, and I would not pick a broader provider.
3. **Ask the user (exact question, via AskUserQuestion):** "The repository policy profile is unset. Set `provider_profile` to `git-kit` in the local override and continue discovery, or stop here?" Options: "Set to git-kit and continue" and "Stop here". I would not write the config myself.
4. **If the user sets it to `git-kit`, discover gates (no execution).**
   - Pre-commit (`.pre-commit-config.yaml`): stage `pre-commit` runs `marketplace-ci check-all --staged`, ruff, gitleaks, markdownlint, yamllint, shellcheck and standard hooks. Stage `pre-push` runs `marketplace-ci check-all --committed HEAD`, plus a warn-only `check-trust-boundary`.
   - PR required checks: the branch-protection read through `wmgt_gh_api_readonly.py` is a network call, so I would list it as pending. A 403 or 404 means "not discoverable", not "none".
   - CI workflow `Marketplace CI` (`marketplace-ci.yml`). The jobs I could read: "Hygiene (PR contract)", "Python quality (ruff, ty, pytest)", "Plugin Node tests (node --test)", "Marketplace mirror/export parity", "Plugin component-file prefix permanence (R33)". "Review helpers on Windows Git Bash (informational)" is not in any `needs`, so it cannot block. The codex-review and publish jobs are past line 927, so I would Grep for their real display names before recording any Codex gate.
   - I would not assume a "Review Changes" gate. Nothing I read names one.
5. **Record (only after a real read-back).** Each gate would be recorded as a `git-github-evidence` entry with owner, check display name, SHA, result and invalidation condition. The caller supplies the SHA. The Linear connector cannot yet write this custom field (the connector-limitation note), so the encoding must be settled first.
6. **Validity check (only when asked).** Compare the recorded SHA with the current SHA, both supplied by the caller. On a mismatch, report the gate as needing a rerun.

## What I would never do

- Run any gate's own logic (lint, CI, merge), or call `git`, `gh` or the GitHub API.
- Invoke `git-kit` skills, or write to Linear or Notion.
- Read the workflow's secret-bearing paths or try to determine current HEAD myself.
- Treat a 403/404 on branch protection as "no gates".
- Invent gates, or accept a display name I have not seen in real output.
- Continue past the manual handoff without the user's answer.

## Open items

- The rest of `marketplace-ci.yml` (lines 928 to 2936) is unread, so the Codex review job's display name is unknown.
- `host-profile.json` was not read, since it does not change the gate list.
