# repository-gates: resolving policy and discovering gates for a Wave 2 publish

Following `workmanagement-kit`'s `repository-gates` SKILL.md procedure exactly, in the order the
skill itself lays out: (1) resolve the repository policy profile, (2) discover the actual configured
gates, (3) state what that means for publishing a PR on a Wave 2 Linear-issue branch. I never ran
this skill's own internal logic (no linting, no CI re-run, no merge) — only discovery reads, per its
own "When NOT to Use."

## Step 1 — Resolving the Repository Policy Profile

Per SKILL.md's "Resolving the Repository Policy Profile" section, step 1: read
`versioned-configuration.json`'s (schema v2) `repository_policy.provider_profile` and `github` fields,
merged with `.claude/workmanagement-kit.local.json`'s override, subject to the same tracked-vs-untracked
trust-boundary check `FOUNDATION_CONTRACTS.md`'s Local Override section requires.

**Shipped config read** (`plugins/workmanagement-kit/versioned-configuration.json`, schema v2):

```json
{
  "version": 2,
  "github": {
    "repository_slug": null,
    "canonical_url": null,
    "default_branch": null,
    "native_automation": "unconfigured"
  },
  "repository_policy": {
    "provider_profile": null,
    "gate_discovery": "unconfigured"
  }
}
```

**Local override check:** `Glob` for `**/workmanagement-kit.local.json` found no such file anywhere in
the worktree. Ran the exact trust-boundary check `FOUNDATION_CONTRACTS.md` specifies for this file
anyway (mirroring `commit`'s own trust check), as the skill requires doing *before* honoring any
override:

```
git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"
→ exit 1: "did not match any file(s) known to git"
```

Exit 1 is the "confirmed-untracked" branch of that check — but since the file doesn't exist at all,
there is nothing to merge in. The shipped defaults stand unmodified: `provider_profile: null`.

**Applying step 2 of the skill's procedure:** `provider_profile` is unset (`null`), and `gate_discovery`
under the same `repository_policy` block is also `"unconfigured"` — the whole policy block is
unresolved, not just the one field. Per the skill's own instruction:

> If `provider_profile` is unset/`unconfigured`, or names a provider other than `git-kit`: stop with a
> manual handoff (see Failure and Resume) — **never** select a broader provider or fall back to a raw
> `git`/`gh` command for a governed operation.

**Result: this is the skill's documented stop condition.** I am not selecting `git-kit` by inference
from step 3's table (the fixed-profile table in `FOUNDATION_CONTRACTS.md`'s "Repository Policy Profile"
section) even though that table *describes* what this repository's profile is supposed to be once
configured — the live `versioned-configuration.json` this skill is required to read has not actually
been set to that value yet. Treating the documented-target table as if it were the resolved live config
would be exactly the "silently select a provider" failure this skill exists to prevent. I am also not
falling back to a raw `git push` / `gh pr create` for the eventual publish step.

**Manual handoff, stated per "Failure and Resume":**
- Missing: `repository_policy.provider_profile` in `plugins/workmanagement-kit/versioned-configuration.json` (currently `null`).
- No `.claude/workmanagement-kit.local.json` exists to supply an override.
- No raw-command fallback will be attempted for the eventual publish operation.
- This must be resolved (by running whatever Foundational Setup step in `workmanagement-kit` sets
  `repository_policy.provider_profile` to `"git-kit"`, matching `FOUNDATION_CONTRACTS.md`'s documented
  fixed profile for this repo) before any Wave 2 skill may delegate a governed Git/GitHub operation —
  including publishing this PR.

## Step 2 — Discovering Actual Gates

The skill's "Discovering Actual Gates" section is a separate, read-only concern from policy-profile
resolution (it discovers *what checks exist*, not *who is allowed to run them*), so per the skill's own
"No approval needed... all read-only" line under Confirmation and Safety, I still ran it — this is
exactly the information a human resolving the manual handoff above would need. **This is discovery
only; none of it authorizes delegating the actual publish to `git-kit` while the profile above is still
unresolved.**

Per the skill's table, reading the target repository's own configuration — never a hardcoded universal
list:

| Gate | What I found |
|---|---|
| **Pre-commit** | `.pre-commit-config.yaml` exists at repo root. Real hooks configured: `validate-pyproject`, `check-github-workflows`, `uv-lock`/`uv-sync`, `ruff-check --fix`/`ruff-format` (scoped to `scripts/`, `tests/`, `plugins/session-kit/**`), `gitleaks` (secret detection), `markdownlint-cli2` (scoped to `docs/**`), `yamllint`, `shellcheck`, standard `pre-commit-hooks` (trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files ≤1000KB, check-merge-conflict, check-toml, mixed-line-ending, check-executables-have-shebangs), plus a local hook `marketplace-ci-check-staged` (`uv run python -m scripts.marketplace_ci check-all --staged`) bound to the `pre-commit` stage. **This gate exists** and runs at `git commit` time, before `git-kit:commit` would even reach the remote. |
| **Pre-push** | Same file's local-hooks block also installs a `pre-push`-staged hook: `marketplace-ci-check-all` (`uv run python -m scripts.marketplace_ci check-all --committed HEAD`). `default_install_hook_types` in the same file explicitly includes `pre-push`, so this is a real, installed local gate distinct from pre-commit — not just a CI-side check. |
| **PR required checks** | Per the skill's own instruction, this is read via `gh api repos/{owner}/{repo}/branches/{base}/protection` — a live GitHub API call. This test harness has no live `gh`/GitHub API access, so I cannot execute this read and get real branch-protection data back. Per the skill's Failure and Resume / Gotchas, a 403/404 here is treated as "no discoverable required checks, not an error" and must be disclosed as ambiguous (permission-level vs. actually absent) — I extend that same disclosure to "not executable in this harness": **I am not asserting either "protection exists" or "no protection configured."** Origin remote resolves to `https://github.com/AndreHahm/andres-cc-marketplace.git` (`owner/repo` = `AndreHahm/andres-cc-marketplace`), so the real call this step would make is `gh api repos/AndreHahm/andres-cc-marketplace/branches/main/protection`. |
| **Codex delta review** | Enumerated `.github/workflows/*.yml` (19 files) and grepped each for a Codex/AI-review step keyword, per the skill's instruction to match on the *real display name*, not an assumed one. Found **two distinct Codex-related gates**, not one — worth flagging precisely because the skill warns against inventing or conflating gate identities: 1) `.github/workflows/marketplace-ci.yml` — workflow **"Marketplace CI"**, job `codex-review` with display name **"Codex delta review"** (there's also an upstream job `compute-scope` / "Compute Codex review scope" and a downstream `publish` / "Publish Codex policy result" in the same workflow). 2) `.github/workflows/await-codex-review.yml` — workflow **"Codex review status"**, job `await-codex-review` with display name **"Await Codex review"**, which polls for the live `chatgpt-codex-connector[bot]`'s actual review/comment/reaction on the PR's head SHA (triggers on PR opened/ready-for-review, or an `@codex review`/`@codex full review` comment). These are two separately-named, separately-triggered checks — a `gh pr checks` read against a real PR would need to be matched against both display names independently, never assumed to be the same gate under two file names. |
| **Review requirements** | Same as PR required checks above — read from branch protection's `required_pull_request_reviews`, which requires the same live `gh api` call I cannot execute here. Not asserted either way. |
| **Merge rights/method** | Same limitation — `enforce_admins`/`required_approving_review_count` come from the same unreachable branch-protection read; allowed merge methods come from `gh api repos/{owner}/{repo}` (`allow_squash_merge`/`allow_merge_commit`/`allow_rebase_merge`), also unreachable live here. Not asserted either way. |
| **Cleanup rules** | Per the skill's table, this is explicitly *not* independently discovered here — it's delegated to `git-kit:finishing-work`'s own cleanup hand-off convention. |

**Other discoverable CI-side gates worth surfacing to whoever resolves the manual handoff** (found
incidentally while enumerating `.github/workflows/`, not part of the skill's own fixed table, so
reported as extra context rather than folded into the table above): `commit-branch-guard.yml`
("Commit & Branch Guard" → job "Validate commits and branch", triggers on PR opened/synchronize/
reopened/ready_for_review), `pr-validate-title.yml` ("Validate PR Title"), `pr-require-impact-label.yml`
("Require Impact Label"), `security.yml` ("Security"), `dependency-review.yml` ("Dependency review").
Whether any of these are actually configured as *required* status checks on branch protection is exactly
the still-unanswered branch-protection question above — their existence as workflows doesn't by itself
mean they're required-to-merge.

**Never inventing "Review Changes" as a gate:** consistent with the skill's explicit instruction, I did
not include a "Review Changes" gate anywhere above — nothing in this repository's own discovered
configuration (pre-commit config, the 19 workflow files, or the FOUNDATION_CONTRACTS policy table) names
a gate with that identity.

## What this means for publishing the Wave 2 PR

Per the skill's Confirmation and Safety section, discovery itself needed no approval and performed no
writes. But the concrete answer to "what gates apply before I can publish a PR":

1. **Blocking, before anything else:** `repository_policy.provider_profile` is unconfigured in this
   repository's own `versioned-configuration.json`, with no local override present. Per the skill's own
   Step 2 and Failure and Resume, this is a stop condition — I'm reporting it as a manual handoff, not
   silently assuming `git-kit` because that's what the target-state table says it *should* eventually
   resolve to.
2. **Once that's resolved** (and only then), publishing routes through `git-kit:create-pr` /
   `git-kit:collaborating-on-a-pr` per `FOUNDATION_CONTRACTS.md`'s Repository Policy Profile table — not
   a raw `gh pr create`.
3. **Real, locally-enforced gates that already exist regardless of the profile question:** the
   `.pre-commit-config.yaml` pre-commit hook set (secret scanning, linting, marketplace-ci
   `check-all --staged`) and its pre-push counterpart (`marketplace-ci check-all --committed HEAD`) —
   these run on the commit/push mechanics themselves, independent of who orchestrates the PR.
4. **Two distinct Codex gates exist in CI**, "Codex delta review" (inside the "Marketplace CI"
   workflow) and "Await Codex review" (the standalone "Codex review status" workflow) — both would need
   to be matched by their real display names once an actual PR exists, never by their file names.
5. **Branch-protection-derived facts** (required status checks, required reviews, merge-rights,
   merge-method) are genuinely undetermined here — this test harness cannot execute the live
   `gh api .../branches/{base}/protection` call the skill's own procedure calls for, and per the skill's
   Gotchas, that absence must be disclosed as "couldn't check," never silently treated as "no
   protection."

Per the skill's "Recording Gate Evidence" section, this skill itself does not write anything (no Linear
write grant) — it only returns the discovered gate list above; a calling skill (e.g.
`development-to-pr`) would be the one to record each gate's real pass/fail/pending outcome, from its own
read-back, into the Wave 2 `git-github-evidence` record once the operations above actually run.
