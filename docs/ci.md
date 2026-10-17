# Marketplace CI

This repository's pull requests are gated by a single consolidated GitHub Actions workflow,
`.github/workflows/marketplace-ci.yml`, triggered on `pull_request` (`opened`, `synchronize`,
`reopened`, `edited`, `labeled`). It runs deterministic checks plus a Codex-dispatched delta review
against `scripts/marketplace_ci/`'s own logic — see `.draft/2026-08-07-plugin-marketplace-ci-implementation-plan.md`
for the full design history and `plugins/codex-kit/skills/plugin-marketplace-review/SKILL.md` for the
Codex review policy itself.

## Required status checks

These are the exact check-run names GitHub reports for this workflow (verified live against a real PR,
not hand-typed):

| Check name | Job | What it verifies |
|---|---|---|
| `Hygiene (PR contract)` | `hygiene` | PR title/template conformance, author-privilege policy (`check-pr`), run from a base-SHA-restored copy of `scripts/` and of the CODEOWNERS/template inputs |
| `Python quality (ruff, ty, pytest)` | `python-quality` | `ruff format --check`, `ruff check`, `ty check`, `pytest -q` against `scripts/`+`tests/`; plus `pre-commit`'s `end-of-file-fixer` over the files the PR changes (the job name predates this step and is kept because it is a required-check name) |
| `Marketplace mirror/export parity` | `marketplace-parity` | `check-all` — every plugin's generated `.claude`/`.agents`/`.codex` mirror/export is in sync with its canonical source |
| `Plugin component-file prefix permanence (R33)` | `prefix-permanence` | Runs `check-prefixes` then `check-prefix-permanence --base-sha`, both from a base-SHA-restored, trusted copy of `scripts/` (same principle `compute-scope`/`codex-review`/`publish` already apply to their own decision code — this is the one trusted evaluation point for both checks; `marketplace-parity`'s own `check-all` also runs `check-prefixes`, but from the untrusted PR checkout, same as its pre-existing mirror/export constituents). `check-prefixes` verifies every file under a registered, prefixed plugin's in-scope directories carries that plugin's own `<prefix>-` basename, validates every registered prefix's own format and marketplace-wide uniqueness, cross-checks `marketplace-inventory.json`'s `source` field against the authoritative `marketplace.json` entry, treats a manifest-listed plugin as checked regardless of its curated `status` (a plugin genuinely absent from the manifest is the only kind exempted), and refuses to trust any single source for a name `marketplace.json` lists more than once. `check-prefix-permanence` compares `marketplace-inventory.json`'s `plugins[].id`-keyed records between the PR's base and head; fails if any record that had a registered prefix at base now has a different or missing prefix, its `name` changed (a rename un-joins a still-live plugin from `marketplace.json`'s authoritative entry, since `check-prefixes` looks it up by name), or the record itself disappeared — the layer that catches a hand-edited inventory file or a delete-and-rebootstrap, not just the `marketplace-inventory` CLI's own `update` path (`reconcile.apply_update`'s write-once guard covers only that path). |
| `Fork PR (unsupported — explicit terminal result)` | `fork-unsupported` | Only runs (`if:`) when the PR head is a fork; fails explicitly rather than leaving Codex review silently pending. **Reports `skipped` on a same-repo PR** — a `skipped` conclusion satisfies a required check in GitHub's branch protection, so this doesn't block ordinary same-repo PRs. |
| `Compute Codex review scope` | `compute-scope` | Cheap, Node/Codex-CLI-free job that computes whether the diff is eligible for the automatic reviewer-scope bypass (see below) and, on a `synchronize` event, whether this push rebased onto a newer base. Checks out the PR's own head SHA directly (never the async `refs/pull/<n>/merge` ref `codex-review` uses) so its scope decision can't disagree with what `codex-review` actually reviews — then restores `scripts/marketplace_ci/` itself from the **trusted base SHA** before scoring, so the decision logic isn't evaluated by a version of itself the PR could have edited (same principle `prepare_reviewer_instruction` already applies to reviewer instructions). Not a required check itself, but `publish` now depends on it having actually **succeeded** — a failure, cancellation, or timeout (5 min) here fails `publish` closed, it does not silently read as "not eligible, run `codex-review` normally." |
| `Codex delta review` | `codex-review` | Dispatches the reviewer set from `derive_review_scope` via `codex-review-bridge` — including `full`-mode escalation's own defined, bounded reviewer set (see "Full-mode escalation" below). Skipped when `compute-scope` reports the diff bypass-eligible, in addition to the existing fork-PR skip. Fails only on a finding that blocks under "Diff-scoped blocking" below, not on any Critical/Major anywhere in a touched file. |
| `Publish Codex policy result` | `publish` | The single check branch protection should actually require for Codex policy: first requires `prefix-permanence` to have **succeeded on its own**, checked before anything else in this job — including before the SHA-bound bypass attestation below, since it's a deterministic, mechanical gate, not the Codex review the attestation exists to skip. Then passes if `compute-scope` succeeded AND (`codex-review` succeeded, OR was skipped **with `compute-scope`'s own `bypass_eligible` output confirming why**), OR if a valid SHA-bound bypass attestation + `s: codex review bypassed` label is present for the current head SHA. Now runs unconditionally for every same-repo PR (only a fork PR skips it) rather than only when `codex-review` itself ran. Keys the "was this skip legitimate?" check off `compute-scope`'s explicit output rather than `codex-review`'s bare result — `codex-review` also depends on `hygiene`/`python-quality`/`marketplace-parity`/`prefix-permanence`, any of which failing independently also produces a `skipped` `codex-review`, which the bare-result check alone would have accepted as a clean pass. The direct `prefix-permanence` check closes exactly that residual gap for `prefix-permanence` itself: without it, an inventory-only PR that is legitimately `bypass_eligible=true` (unrelated to prefix-permanence) but ALSO fails `prefix-permanence` would have had its `codex-review` skip read as a clean pass, since `bypass_eligible=true` alone doesn't distinguish "skipped because of a legitimate scope bypass" from "skipped because a sibling dependency happened to fail." |

Every job in the workflow sets its own `timeout-minutes`, a generous multiple of its measured run time, so a
hung step cannot hold a required check pending for GitHub's 360-minute default. A job that times out counts as
not having succeeded, so `publish` fails closed on it; `publish` and `fork-unsupported` carry limits of their own.

Configure branch protection to require: `Hygiene (PR contract)`, `Python quality (ruff, ty, pytest)`,
`Marketplace mirror/export parity`, `Plugin component-file prefix permanence (R33)`,
`Fork PR (unsupported — explicit terminal result)`, and
`Publish Codex policy result`. Do **not** separately require `Codex delta review` or
`Compute Codex review scope` — `publish` already depends (transitively) on both and is the check that
knows about every skip/bypass path; requiring `Codex delta review` directly would make a
legitimately-bypassed PR's skip block the merge again, defeating the bypass entirely.

## External Codex connector review status

A separate workflow, `.github/workflows/await-codex-review.yml`, makes the otherwise invisible
wait for the *external* `chatgpt-codex-connector[bot]` GitHub App reviewer visible as a pull
request check (`Codex review status / Await Codex review`). This is unrelated to the `codex-review`
job documented above — that job dispatches this repository's own `codex-review-bridge` reviewers
via `OPENAI_API_KEY`; `await-codex-review.yml` only polls for a review submitted by the separate,
externally-connected `chatgpt-codex-connector[bot]` account. It is currently visibility-only, not
a required status check. See [`docs/await-codex-review.md`](await-codex-review.md) for the full
contract, result semantics, and adoption-mode details.

## Configuring the review model

`codex-review-bridge` never passes `--model` to `codex exec` by default — every dispatch falls through
to whatever `~/.codex/config.toml` resolves after the workflow's own `codex login --with-api-key` step,
which is an account/API-key-level default this repo doesn't control. If that default resolves to an
expensive model, set the **repository variable** `CODEX_KIT_REVIEW_MODEL` (Settings → Secrets and
variables → Actions → Variables — not Secrets, since a model slug isn't sensitive) to a specific model
slug. The workflow passes it through as an environment variable to the `codex-review` job; `codex-review-bridge`'s
`bridge-invoke.mjs` reads it and passes `--model <value>` to every reviewer it dispatches in that run.
Leave it unset to keep using the account default. Invalid values (anything outside
`^[A-Za-z0-9._-]{1,64}$`) fail the job with a clear message rather than surfacing as an opaque Codex CLI
error.

## Configuring the review timeout

Every `codex-review-bridge` dispatch shares `runCodexExec`'s own 240000ms (4 min) default timeout unless
overridden. On a large delta PR, a single reviewer's one-call review can legitimately need longer than
that to complete against its full scope — confirmed live: a 100-changed-path PR pushed
`plugin-rulebook-checker`'s dispatch past the default, first as a strained/malformed response, then as a
hard timeout on retry. The `codex-review` job sets
`CODEX_KIT_REVIEW_TIMEOUT_MS: ${{ vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '600000' }}`: the repository
variable of that name when it is set, else a 10 min fallback written in the workflow. That gives every
dispatched reviewer more headroom within the job's own 45-minute budget, and a maintainer can raise it
without editing the workflow. Invalid values (non-numeric or non-positive) fail the job with a clear
message, same as the model override.

### Concurrency, timeout retries and the dispatch budget

`dispatch_reviewers` (`scripts/marketplace_ci/review.py`) runs reviewers on a pool of two workers
(`DISPATCH_MAX_WORKERS`) rather than one after another; the result keeps the scope's own reviewer order.
A reviewer whose bridge call fails with the bridge's structured `timeout` error is retried up to twice
(`DISPATCH_MAX_TIMEOUT_RETRIES`), so a reviewer can make up to three calls. Only that `timeout` category
is retried among failed bridge calls — a non-zero exit for any other reason, or malformed bridge output, fails
immediately so a real bridge or validation fault is never masked by a retry. (A successful call that returns
an empty review has its own single retry, described below.)

The whole dispatch has a 40-minute budget (`DISPATCH_BUDGET_SECONDS`), kept under the job's own 45-minute
`timeout-minutes`. No bridge call starts, first attempt or retry, unless the per-call timeout
(`CODEX_KIT_REVIEW_TIMEOUT_MS`) plus 60 seconds of process slack still fits in what is left. A reviewer that cannot start or retry within the
budget is reported as failed with a `dispatch budget exhausted` error, so the job exits with a clear result
instead of being killed mid-call. `codex-review-result.json` carries a `reviewer_attempts` map (reviewer name
to bridge calls made) so a reviewer that needed retries stays visible even when the run passes. When a
reviewer fails, the file is still written, with a `dispatch_failed` list (reviewer, attempts, error) and
`blocking: true`, so the uploaded `codex-review-result` artifact holds a machine-readable copy of the error
(the same text the log line carries); the job still exits 2. Every other exit-2 path of `run-codex-review`
(unresolvable base SHA, failed `git diff`, an undefined full-mode dispatch, a reviewer with no or invalid
output) writes `{"status": "could_not_run", "blocking": true, "error": ..., "provenance": ...}` the same way,
which also overwrites a stale `codex-review-result.json` a PR might have committed, so the artifact always
reflects this run.

## The reviewed delta and the result status

`codex-review` checks out `refs/pull/<n>/merge`, so the PR's own delta is the merge commit's first parent
to `HEAD`. The event's `base.sha` is the fork point and does not move when the base branch does; diffing
against it on the merge ref put everything the base gained since into the review (128 files instead of 13
on PR #567) and made the Tier-1 hard-refuse step refuse PRs for files other people changed (issue #572).
A plain-shell step, `Derive the delta base from the merge commit`, runs first, before any PR code (the merge
ref carries the PR's own `scripts/marketplace_ci`, so this decision cannot live in it). It takes
`git rev-parse HEAD^1` as the base and passes it, as `BASE_SHA`, to the Tier-1 refusal step and to
`run-codex-review --base-sha`. Reviewer instructions are read at that same base, which is the current base
tip. It fails closed, writing a `could_not_run` result file, unless all five hold: the event base SHA
resolves; `HEAD` has exactly two parents; the second parent is the event's PR head (so `HEAD` is a merge of
it, not an author-made commit); the event base is an ancestor of the first parent; and the first parent is an
ancestor of `refs/remotes/origin/<base branch>` (an author-made merge of their own commit on top of base
passes the first four alone). A base branch that moved on since the checkout still passes. Steps that diff against the PR
head (`compute-scope`, `check-pr`, every `merge-base "$BASE_SHA" "$PR_HEAD_SHA"` step) were already
correct and are unchanged. An attested bypass clears this guard like every other `codex-review` refusal.

`compute-scope` and `run-codex-review` both start from one helper (`compute_pr_delta`). Only the review then
collapses identical mirrors, so for a large mirrored diff the two scopes can differ: 26 identical pairs are 52
paths (a closure-overflow `full` scope) to the bypass decision but 26 paths (a `delta` scope) to the review.
That direction is fail-safe, since a larger bypass scope only means Codex runs. A canonical `plugins/<plugin>/...` file and
its byte-identical `.claude/...` copy (same blob and mode, plugin listed in the **base's**
`.claude/marketplace-sync.json`, not a declared divergence exception) are reviewed once, under the canonical
path. A drifted pair, or a mirror changed alone, is kept, because the drift is what the reviewer must see.

`codex-review-result.json` has a top-level `status` (`findings`, `clean` or `could_not_run`) on every payload
shape. Every shape `run-codex-review` writes itself (a completed review, a failed dispatch, any other exit-2
failure) also has `provenance` and a per-reviewer `reviewer_results[<name>]` of `{status, attempts}`. Both are
empty or null only when nothing ran (a failure before dispatch); a failure after dispatch (a reviewer with no
or invalid output, a failed classification) keeps the reviewers that did run, marking one whose output did not
validate `could_not_run`. The workflow's pre-dispatch guard refusal, which runs before any Python, writes only
`status`, `blocking` and `error`. `blocking` is unchanged. A run with
any failed reviewer is `could_not_run` as a whole, never a clean review of the rest. `provenance` records
`head_sha` (the PR head, the merge commit's second parent), `merge_ref_sha`, `base_sha` (the base the delta
used), and the `model` and `cli_version` the reviewers reported. The job exposes the status as the
`review_status` output, and `publish` words its message by it (a blocking finding, could not run, or passed
clean); the job result alone still decides pass or fail.

Each bridge process runs in its own session and is killed, together with its whole process group on POSIX runners (the bridge
spawns a `codex` child; elsewhere only the direct process is killed), if it outlives its own timeout plus 60 seconds (`_PROCESS_SLACK_SECONDS`, counted in
the budget check too); that is reported as failed and never retried. The failed reviewer's stderr text is
stripped of control characters before it reaches the CI log. An `OSError` while dispatching one reviewer (for
example a missing `node` binary) fails only that reviewer; any other exception is a defect and propagates.

A reviewer that returns no findings and a verdict starting with `Inconclusive` (for example when its command
bridge failed before any file could be read) is retried once (`DISPATCH_MAX_EMPTY_RETRIES`, counted apart
from the timeout retries and bound by the same budget check), because a sandbox that fails to start can be
transient. The retry log line carries the first attempt's inspection limit, so a failure that a retry then
clears stays visible in the log. The check cannot tell a transient failure from a legitimate `Inconclusive`
verdict, so the latter also spends one extra call before it fails the same way. If the retry is also empty it is reported as failed, not completed, with the reviewer's full first
inspection limit in the error (up to 2000 characters, control characters stripped). The
output envelope has no structured field for "inspected nothing", so this keys on the verdict's own prefix: a
deliberately narrow, fail-closed check that can miss a differently worded empty pass but never fails a review
that raised findings. A reviewer that legitimately finds nothing to review but words its verdict
`Inconclusive` (for example `plugin-rulebook-checker` on a diff with no component files) is blocked the same
way; that outcome is expected and needs a manual review or an attested bypass.

The `CODEX_KIT_REVIEW_TIMEOUT_MS` environment value is the only per-call timeout the dispatcher reads. The
workflow fills it from the repository variable of that name, falling back to the literal in the expression
(before issue #572 it was a hard-coded literal, so the variable had no effect, #471). The local parity
wrapper (`git-codex-parity-review.py`) does the same: it reads the variable with `gh variable list` and asks
node to apply the bridge's own test (`Number(value)` is a positive integer), because JavaScript's number
grammar (`0x10`, `1e-0`, `+5`, ...) is too open-ended to re-implement. An accepted value is passed on
verbatim; otherwise the wrapper uses the fallback it parses from the workflow's expression and prints a
warning, whether the variable was rejected or node could not be run. Keep the expression in that exact
shape, because the wrapper parses it.

Usable range of the variable: the bridge accepts any positive integer (`Number()` forms such as `0x927c0` included, which the dispatcher reads the same way, so its kill timer and budget check agree with the bridge), but two limits sit behind that test.
Above 2,147,483,647 ms Node clamps the timer to 1 ms, so every Codex call times out at once; and above about
2,340,000 ms (39 minutes) one call plus its 60 seconds of slack no longer fits in the 40-minute dispatch
budget, so the dispatcher refuses every reviewer with "dispatch budget exhausted". Both fail closed (the
review fails, never passes), but one bad value fails `codex-review` on every PR until it is fixed. Below those
limits a large value still shrinks the room for retries and for reviewers that start later, since each needs a
full call plus slack in what remains of the budget; the current value, 720000, leaves room for about three
full-length calls in sequence.

## The review contract

`scripts/marketplace_ci/review_contract.py` is the one place CI's Codex delta review and the local parity
wrapper (`git-codex-parity-review.py`) agree on severity, the finding envelope, the exceptions registry,
the reviewer roster and the pins (issue #573). It is Tier 1: `run-codex-review` imports it, so it imports
nothing else from the repo, and a PR that edits it needs the maintainer bypass attestation.

**Severity.** One scale, `critical | major | minor`, meaning the impact if the finding is true (not how sure
the reviewer is). Every vocabulary in use maps onto it:

| Source | Native value | Canonical |
|---|---|---|
| review envelope, `*-reviewer` agents | `critical` / `major` / `minor` | unchanged |
| `plugin-validator` | `critical` / `warning` | `critical` / `major` |
| `plugin-rulebook-checker` | `fail` / `advisory` | `critical` / `minor` |
| R13/R18 size tiers | `Critical` / `Warning` | `critical` / `major` |
| R13/R18 size tiers | `Soft Warning` / `Weak Warning` | `minor` |

A test keeps the rulebook rows equal to `plugin-rulebook/references/evidence-schema.md`.

**Finding envelope.** The contract defines `rule_class` (`line | measurement | graph | judgment`,
default `judgment`), `evidence_type` (`verifier_output | hunk_level_code | repo_policy |
contextual_reasoning`) and `risk` (`reachable`, `exposure`, `mitigation`), next to the `confidence` a
reviewer already returns, and `validate_review_output` parses them. No current reviewer can emit them:
the bridge's output schema (`bridge-invoke.mjs`) forbids extra properties, so until it gains them (Phase 2)
every finding is `judgment` with no evidence type or risk. An unknown value in a parsed envelope fails it
(the run is `could_not_run`) rather than being ignored. Only `severity`, `rule_class` and the exception
match feed the gate in this phase; the rest is recorded in the result and shown.

**The computed gate.** `gate_decision` in `review.py` is the one place that decides, per finding, `block`,
`notice` or `suppressed`; `blocking_findings` and the result file both use it. A finding blocks when it is
Critical or Major and on a changed line (see [Diff-scoped blocking](#diff-scoped-blocking)). A model
reviewer's `measurement` finding is a notice until the Phase 2 verifiers can confirm the measurement;
that lets a model's own label downgrade its finding, which is safe only while the bridge's output schema
has no `rule_class` property (a test fails if it gains one).
Each finding in the result records `gate`, `rule_class`, `source`, `suppressed` and the `exception` it
cites, and the result records `exceptions_loaded`.

**The exceptions registry.** `review_exceptions.yaml` lists documented repo decisions that reviewers
otherwise report the opposite of. Each entry has `rule`, `path` (a glob: `**/` crosses directories, `*`
and `?` stay inside one segment), `reason` and `authority` (the repo file that states the exception).

- It suppresses **script** findings only: a script finding for that rule on a matching path is kept with
  `suppressed: true` and the entry cited, and never blocks. A model finding is never suppressed.
- It is appended to every model reviewer's instruction as a `[documented exceptions]` briefing, so the
  reviewer is told the decision exists. The entries are rendered as one JSON-escaped line each and framed as
  repository data, never instructions. The briefing says an entry covers only the exact rule and paths it
  names, never excuses a security, permission or trust-boundary finding, and that a finding an entry seems
  to cover is reported as minor with the entry cited, not omitted. A reviewer's free-text `axis` is not a
  registry rule id, so this part is guidance to the model, not a mechanical suppression.
- A finding path that is absolute, climbs with `..`, or contains a backslash or control character matches
  no entry. A `**` in a pattern must be a whole path segment, and fields may not contain control
  characters (only `reason` may span lines) or exceed 1000 characters.
- When reviewers' findings are merged, `source` is part of the dedup key and the copy kept is one the
  gate can still block on, so a merge never turns a blocking finding into a notice or lets a script
  finding absorb a model finding.
- It is git-tracked only, with no local override. If it cannot be read or is malformed (a repeated YAML
  key included, since the parser would otherwise keep the last value and hide the first), `run-codex-review`
  exits 2 (`could_not_run`) before dispatching anything.
- It is Tier 1, so a PR cannot suppress a finding about itself by editing it: editing it hits the
  Tier-1 hard-refuse step, and every later registry edit needs the maintainer bypass attestation.

A script finding is built by `review_verifiers.py` (see [Script verifiers](#script-verifiers)); only
the verifiers whose rule id has a registry entry can be suppressed, and `r6-bash-scope` has none.

**Roster and pins.** `ROSTER` lists every reviewer with a selector label. Only the baseline set
(`DELTA_VALIDATE`) is derived from it; the audit and governance routes stay hand-written in `review.py`,
and a test checks that every reviewer they name is in `ROSTER`. Every instruction file is
`.codex/agents/<name>.toml`, read from the PR's base commit.
`CODEX_CLI_VERSION` is the pinned Codex CLI, and `MODEL_VARIABLE` names the repository variable that holds
the model. The workflow cannot import the contract, so its `npm install -g @openai/codex@<version>` line is
a second copy of the version; a test fails if the two differ. The parity wrapper compares the local Codex CLI
with the workflow's pin, since that is what CI installs, and reads the contract's pin and variable name as
data (it parses the source, it does not import it) only to catch drift: a contract that disagrees with the
workflow is reported as a difference, and a model variable the workflow does not export is not used (if
the workflow exports neither the contract's name nor `CODEX_KIT_REVIEW_MODEL`, no model variable is passed). It falls
back to the workflow alone for a checkout that has no contract. Because it runs the same entry point from the
same checkout, it uses the same roster, severity scale and registry as CI. It says plainly when a run is
not a prediction of CI's result: a different Codex CLI version, an unset model (the local default is
used), or a timeout variable the bridge rejects.

## Script verifiers

`scripts/marketplace_ci/review_verifiers.py` (issue #576, #568 Phase 2) decides mechanical review rules
with code instead of a model, so the same head gives the same answer on every run. It is the first part of
the Phase 2 verifier set; `docs/review-rule-inventory.md` lists every rule a script can decide and which are
planned. `run-codex-review` runs the verifiers in-process, next to the structural check and before any
reviewer is dispatched, and adds their findings to the model reviewers' findings before aggregation. A script
finding carries `source: "script"`, so the computed gate can block on it (Critical or Major on a changed
line, like any other finding) and a registry entry can suppress it; a model finding is never suppressed.

- **What it reads.** The PR's files as committed at `HEAD`, through git objects: never the working tree,
  never a symlink, nothing larger than 1 MB each or 20 MB in total (sizes are checked with
  `cat-file --batch-check` before any content is read), and a body with stray bytes is decoded leniently.
  The frontmatter (at most 100,000 characters) is composed into a YAML node tree and never constructed into
  Python objects, so no tag, timestamp or alias in a PR file can run code or expand in memory. It parses
  data and never executes or imports anything from the PR.
- **`r6-bash-scope`** (rule class `line`, severity `critical`). A skill or command (`allowed-tools`)
  that grants bare `Bash`, `Bash(*)`, a wildcard-only command or a wildcard in the program name
  (`bash*`, `*sh`; a wildcard directory such as `*/scan.sh` still pins a script and passes), or a shell
  interpreter (`sh`, `bash`, `cmd`, `powershell`, however spelled: a path, `.exe`, case, quotes, a backslash
  escape) with no single pinned script, is a finding. The first argument pins a script only when it is a
  plain script path ending in a script extension (`.sh`, `.bash`, `.ps1`, `.cmd`, `.bat`), with a variable
  allowed only as a leading `${CLAUDE_PLUGIN_ROOT}/`, `${CLAUDE_SKILL_DIR}/` or `${CLAUDE_PROJECT_DIR}/`: an option (`-c`, `+x`,
  `cmd /c`), a device (`/dev/stdin`, `/proc/...`), an expansion (`$X`, `${IFS}`) or a pattern does not. An
  agent's `tools` entry of the form `Bash(...)` is a finding, since an agent's `tools` field has no Bash
  scoping and only bare `Bash` grants it. Paths covered (case-insensitively):
  `plugins/*/skills/*/SKILL.md`, `plugins/*/commands/**/*.md` and `plugins/*/agents/**/*.md`, and the same
  under `.claude/`. A finding's line is the YAML node's own position when the value is a single-line scalar
  or a list item, and it cites the opening and closing fence and every line from the key to the entry, so
  an edit to any of them (renaming `disallowed-tools:` to `allowed-tools:`, deleting a line above the
  fence) makes it the PR's. A value that spans lines, or a context over 200 lines, gives no line, and a
  finding without a line counts as changed whenever its file is. A pre-existing grant on an untouched line is a notice, not a block.
- **`frontmatter-unverifiable`** (severity `major`, no line). A changed component file whose Bash grants
  cannot be read exactly is a blocking finding rather than a skip, because otherwise a PR could keep a
  violation by making its file unreadable. The causes are: frontmatter that is not closed, whose fence is
  not exactly `---` on the first line, or that is not valid YAML, a mapping or a single document; a YAML
  alias, explicit tag or merge key; a key that is not a plain scalar; a repeated `allowed-tools` or `tools`
  key, or a column-0 line that looks like that key but is not it; a line break git does not count (a bare
  CR, NEL, LS or PS), which would shift every reported line; a value that is not a string or a list of
  strings; an unbalanced parenthesis or a malformed `Bash(...)` entry; more than 2,000 entries; and a file
  that is a symlink, a submodule, over 1 MB or past the 20 MB total. A file with no frontmatter at all
  grants nothing and is clean.
- **`r13-skillmd-line-count`** and **`r21-description-length`** (rule class `measurement`, severity `major`
  or `critical`). A skill's `SKILL.md` over 490 lines is Major and over 500 is Critical (R13); a `description`
  shorter than 80 or longer than 1018 characters is Major, shorter than 20 or longer than 1024 is Critical,
  and `when_to_use` over 506 is Major and over 512 Critical (R21). The lengths are those of the folded YAML
  value, not the raw text. The thresholds are the rulebook's (`assets/settings.json`); a test keeps them
  equal. Each value is compared with the base (`HEAD^1`, or the old path of a rename): a finding is reported
  only when the PR moves a value into a worse blocking tier, or adds the file, so a PR that merely touches an
  already oversized file is not blocked by it. Weak and Soft Warning tiers are never reported. The finding
  has no line, so it counts as changed whenever its file is. The combined `description` + `when_to_use` limit
  is not checked on its own: it can only be exceeded together with one of the two individual limits. Only
  `SKILL.md` is measured for R13 and R21. Details that close
  evasions: too-short and too-long descriptions are ranked separately (swapping one for the other is
  reported); a missing `description` counts as length 0, so deleting it dodges nothing; the base is used only
  when the old path is itself a skill, so renaming a large reference file into a `SKILL.md` is measured as a
  new file; a lone carriage return counts as a line break; and a repeated or non-string `description` or
  `when_to_use` is an unverifiable finding, not a clean pass.
- **`r18-code-block-line-count`** (rule class `measurement`). A fenced code block of more than 20 lines is
  Major and of more than 30 is Critical, in a skill, command or agent file (not in `references/`, where the
  rulebook itself sends large blocks). Blocks are read as CommonMark does: a fence of three or more backticks
  or tildes, after any blockquote and list markers (nested ones too); closed at the same blockquote depth by a
  fence of the same character at least as long, with no other text and not indented more than three columns
  into its container (absolute for a fence at the top level, the opener's column plus three inside a
  blockquote or list item), so a longer fence holds shorter ones as content; a block that is unclosed ends where its blockquote or list
  item ends, or at the end of the file; a lone carriage return is a line break. The repo already holds
  hundreds of blocks over 20 lines, so a block is counted only when it is not an identical block already in
  the base, and the file is reported only when the PR raised the number of blocks at some tier or worse:
  editing a block without crossing a threshold, or moving it, is not reported. The result is **one finding per
  file with no line**, naming up to five blocks in its evidence. A finding exists only when the PR made the
  file worse against the real base, so it is the PR's by construction; a line would let an edit that leaves
  the fences alone (filling a block in the middle) fall outside the diff. Splitting a Critical block into a
  Critical and a Major one raises the count at the Major tier and is reported; split into blocks of 20 lines
  or fewer instead. The rulebook's in-file `R18 exception` note is **not** honored by the script: a PR could
  type one above its own block and waive its own finding, so a waiver is an entry for
  `r18-code-block-line-count` in the Tier-1 exceptions registry (the note still tells model reviewers and
  humans why). R18 is a size heuristic, not a security boundary: blocks of 20 lines or fewer are never
  reported, however many a file has, so splitting always avoids it. It reads the file once; a stray
  four-space-indented fence at the top level (indented code that contains a fence) can pair with a later
  fence and shift which lines count as a block, which is accepted rather than read twice, since a second
  reading double-counted a region and could block a legitimate PR. Nesting is read to 100 list markers and
  101 blockquote markers per line; an opener nested deeper reads as an empty block, which is accepted.
- **`r34-escaping-path`** (rule class `graph`, severity `critical`, outcome `path-and-mirror`). In a skill's
  `SKILL.md` and its `references/*.md` under `plugins/` (matched case-insensitively), a link or a
  `${CLAUDE_SKILL_DIR}` path that resolves to something that exists outside the skill folder may land only in
  the plugin root's `references/` or `assets/`, or in its `scripts/` when the plugin is listed under
  `scripts_mirrors`; anything else (`docs/`, a repo-root file, a sibling skill's folder, another plugin) is a
  finding on the line that holds it, as is a path that climbs only to come back (`references/../SKILL.md`,
  `references/./../SKILL.md`, a `${CLAUDE_SKILL_DIR}/../...` path that ends inside the skill). A leading `..`
  chain is normal. Links are the ones a CommonMark parser (`markdown-it-py` 4.x, a dev dependency
  hash-pinned in `uv.lock`) finds, read three ways and united: plain CommonMark, CommonMark with GFM tables
  (GitHub splits table cells before it reads code spans), and CommonMark with a leading YAML frontmatter
  block emptied (GitHub and Claude Code split it off). Each reading takes inline links and images,
  reference definitions, GFM footnote definitions (their text is read again as Markdown), and the `href`,
  `src`, `poster`, `data`, `action` and `srcset` attributes of raw HTML. Code (fenced, indented, inline),
  HTML comments, backslash escapes and character references are handled as a renderer handles them. The HTML
  attribute reader has the standard library parser's raw-text (`<xmp>`, `<textarea>`, `<script>`...) and
  CDATA modes switched off, because a renderer shows the tags that follow them; a test pins this against the
  installed Python, whose behaviour changed between releases. A fence that never closes is code to the end
  of its container, as a renderer shows it. `${CLAUDE_SKILL_DIR}` paths (braced or unbraced, quoted or not)
  are read on every raw line, fenced blocks included, as the rulebook says. The target is read as a browser
  would: tab, newline and carriage return dropped, fragment and query split off before percent escapes are
  undone, a backslash read as a separator only when CommonMark does not treat it as an escape, a leading `/`
  a repo-root path. A placeholder (`...`, `*`, `{x}`, `$x`, `<x>`) is skipped only if it survives resolving
  the path: `docs/*/../x.md` is just `docs/`. A repo-root path such as `.github/x.md` is tried against the
  repo root when it does not exist under the skill, and then counts as leaving the skill. URLs, anchors and
  other placeholders are skipped. A finding sits on the line that holds its target within its Markdown block
  and cites every line of that block, the resolved target and the code or HTML block just above it. Because
  an edit anywhere (an indent, a blank line, a fence) can make an old link live, a finding that the same
  check over the base text did not already have (counted per resolved target) is reported for the whole
  file, with its line in the evidence; a new file, with no base, keeps its lines; a block too long to cite
  (over 200 lines) also gives a file-level finding. A document the parser cannot read is a Major finding,
  never a pass: it raised (deep nesting raises `RecursionError`), it is over 250,000 characters (the largest
  real one is 83 KB), or the run's 30-second parse budget was used up (the parser is quadratic on hostile
  input, each document is parsed up to three times plus its base, and all 534 real docs take about three
  seconds). A file stops at 500 findings and then gets one file-level finding, which blocks.
  `scripts_mirrors` is read
  from the **base** copy of `.claude/marketplace-sync.json`, so a PR cannot widen its own allowed folders; a
  missing or unreadable file allows none. A SKILL.md or reference file that cannot be read (a symlink,
  oversized, over the size budget) is a Major finding, not a skip. **Dead links are deliberately not checked:** a script found
  11 on the real tree and 10 were illustrative examples (`attachment-name.png`, `path/to/file.md`), which only
  a human or a model can tell from a real miss, so dead links stay with the model reviewers. On the real tree
  the check reports the two genuine escapes (`../../docs/agy-migration.md` and
  `.github/pull_request_template.md`), which are notices until a PR touches those lines. Accepted: a PR that
  removes a plugin from `scripts_mirrors` and links to its scripts in the same change passes (the base still
  lists it; the file is a governance path a maintainer reviews), and a dead link a later PR makes live is not
  caught by the PR that creates the target when the document is not otherwise changed (when it is, the base
  text is read against the HEAD tree, so the old line is kept, and the finding still cites the target the PR
  added, which makes it the PR's; a test pins this). Also accepted, because they depend on one renderer's reading: where
  `markdown-it-py` and GitHub's `cmark-gfm` disagree on block structure (for example `<search>` is a block
  tag in CommonMark 0.31 and a plain paragraph start in GitHub's older spec), HTML attributes other than
  those listed (`xlink:href`, `background`, `formaction`, `<meta http-equiv=refresh>`), a path written in
  plain prose that is not a link (other than a `${CLAUDE_SKILL_DIR}` path), a `${CLAUDE_SKILL_DIR}` form
  with a default (`:-.`) or a space, a cited path that ends in `:<digits>` (read as a path and a line), and
  the parse budget being wall-clock time, so a very slow runner can refuse documents a fast one reads. A
  parser release can change which links count, so the version is bounded (`>=4.2,<5`); a Dependabot bump
  is covered by `pr_policy.TRUSTED_BOT_PATHS`: a verified Dependabot PR that changes only manifest files
  (`uv.lock`, `pyproject.toml`, ...) passes the merge-rights check without a CODEOWNERS match, as a PyYAML
  bump already does.
- **`r37-executable-bit`** (rule class `graph`, severity `critical`, outcome `structure`). A script that a
  skill or command runs directly by path, because its `allowed-tools` grant starts with
  `${CLAUDE_PLUGIN_ROOT}/` or `${CLAUDE_SKILL_DIR}/` (braced or not, quoted, or after any run of `env`, `exec`, `command`,
  `time`, `nohup` or `nice` words, also by absolute path such as `/usr/bin/env`, their options and
  `NAME=VALUE` assignments; `timeout`, `sudo` and other
  wrappers are not read), must be committed as a regular file with git mode 100755: a shell running a 100644 path fails
  with `Permission denied`. The finding names the reason: mode 100644, a symlink, a submodule, a directory, or
  no such file (the rulebook calls a missing file a FAIL too). A script an interpreter runs
  (`Bash(bash ${...}/x.sh:*)`) needs no bit and is not listed, a glob names no single script, and a path that
  climbs out of its plugin names nothing. Because a `chmod` changes no line of the skill, the verifier reads
  **every** skill and command of a plugin the PR touches. The finding sits on each grant line and cites the
  script's own path, so dropping the bit makes it the PR's. A document in such a plugin that cannot be read
  (a symlink, oversized, a frontmatter the parser refuses) is reported, and when the PR left that document
  alone the finding cites every path the PR changed in that plugin (up to 200; more fails the run closed),
  so a chmod there blocks (each cited path counts for any change to it, `path:*`; see Diff-scoped blocking). A
  grant document that stays unreadable therefore blocks every PR that touches its plugin until it is fixed or a
  registry entry covers it; that is deliberate. A changed document the grant verifier already refuses is
  reported only by it. A grant inside a multi-line YAML value has no file line; it is skipped when the base
  document holds as many such grants of that script (matched one for one) and the script has the same mode there, so an unrelated edit is not blamed for
  an old violation. A script name ending in `:<digits>` is cited as a whole path (`path:*`), since a bare
  citation would read the digits as a line.
  Running out of the read budget also fails the run closed, so a chmod is never let through unseen. The real tree has no violation, so this guards against a repeat of the bug that
  made the rule. **Not covered, and stated here so the claim stays honest:** hook commands (`hooks.json`, or a
  `hooks:` block in skill frontmatter) that are a bare path, the `.claude/` mirror copy of a script, and a
  grant the skill's body never runs directly (the rulebook gives that an informational note; the verifier
  reports it, which is stricter).
  `r29-testing-section` and `r35-standard-sections` are not verifiers: the rulebook matches those headings
  "by substance", and a literal scan found 47 of 150 real skills without a `Quick Start` heading, so a script
  would block on wording.
- **`skill-agent-dependency-cycle`** (rule class `graph`, severity `major`, outcome `call-graph`). A call is a
  literal `Skill(name)` or `Agent(subagent_type: name)` in the body of a skill, agent or command, read from the
  parsed Markdown: running text and inline code spans, raw HTML blocks (a `<details>` block is read, HTML
  comments are not) and link and footnote definitions. Both argument shapes are read, positional and keyed
  (`Skill(skill: x)`, `Skill({ skill: x })`, `Agent({"subagent_type": "x"})`); an agent call may carry a long
  prompt first (the key is looked for up to 4,000 characters on, and never past the next call). A frontmatter
  `allowed-tools` grant (a grant is not a call), a fenced or indented code block and a mention without the
  call syntax are not calls. `Skill(x)` resolves to a skill or a command named `x`, `Agent(subagent_type: x)`
  to an agent. A `plugin:name` target is looked up in that plugin when it is a plugin of this tree (the real
  tree writes `Skill(git-kit:commit)` across plugins, so a typo behind a prefix is a dangling call and a cycle
  written with prefixes is a cycle); a prefix that names no plugin here (`codex:rescue`) is external and
  skipped, as are a placeholder such as `...`, a file name (`x.md`) and a component calling itself (same kind
  and name; a skill and an agent that share a name and call each other are a cycle). Two things are findings:
  a call to a component that does not exist, and a call that closes a cycle among the resolved calls (the
  evidence spells out the cycle). **Only a call the PR introduces blocks**, since the real tree has an
  intentional `commit` <-> `create-pr` cycle (each skips the other's step when it is the nested one) and
  two more skills in the same group that a script would otherwise flag forever. Against the base: a dangling call is new
  when its (caller, kind, target) was not called at all before (a target the PR deleted is a removed-identifier
  matter, not this check's), and a resolved call in a cycle is new when it did not resolve to that component
  before, so creating the target of an old dangling call that closes a cycle counts, and cites the target's
  path. A new call in a document that has a base is reported for the whole file, with its line in the
  evidence, because an edit elsewhere (an indent, a blank line, a fence) can turn old text into a call; with
  no base every call in a changed document is new and keeps its line (the line of the call's target, so a
  call split over several lines reports where the name is), and lone carriage returns, which git does not
  count as line breaks, leave a call with no line. The verifier reads every skill, agent and command of the
  repo (only when the PR touches one), at HEAD and at the base, so a deletion elsewhere is seen. A changed
  component that cannot be read (symlink, oversized, a parser fault such as `RecursionError`) is a finding;
  one the PR left alone adds no call of its own and is ignored. A changed skill, agent or command
  *directory* that is a symlink or submodule is a finding too, since it hides what is behind it. Running out
  of the read budget or of the 30-second parse budget, or more than 500 call problems, fails the run closed.
  An intentional guarded cycle a PR adds takes an entry in `review_exceptions.yaml`, which then covers every
  call problem in that file (an entry matches rule and path, not target). On the real tree it finds no
  unresolved target and, with no base, only the six calls of the existing git-kit cycles; against the base it
  finds nothing. **Accepted, and stated here so the claim stays honest:** a call written with an escape,
  entity or emphasis (`Skill\(x)`, `**Skill**(x)`) or with a homoglyph (the literal syntax is the contract; a
  looser one would flag `skill(s)` in prose), `references/*.md` files (which hold calls on the real tree but
  are not components), the frontmatter ending early at an unindented `...` inside a block scalar, a path matched
  case-insensitively while Claude Code may load only `SKILL.md`, an agent named by its file name while Claude
  Code uses the frontmatter name, two plugins with a component of the same name (they share call history; the
  flat `.claude/` mirror forces unique names), nested command directories (`sub:x` is skipped as a prefix; a nested agent file is named by its file name, and two agent files of one plugin with the same name are reported when the PR changes either of them; a pair that already exists, plus a changed caller that names it, is not, since agent names must be unique and the tree has no nested agent),
  and the `.claude/` mirrors and Codex exports, which are the mirror family's.
- **`r19-mirror-drift`** (rule class `graph`, severity `critical`, outcome `path-and-mirror`). For every
  component a PR touches (both sides of a rename), a `.claude/` mirror or Codex export that has drifted from
  its canonical `plugins/` source: a canonical file whose mirror is missing or different, in the way
  `check-all` judges it. It is a thin wrapper over `run_delta_structural_checks` in `review.py`, which plans
  the mirror and export sync with the real planner (`plan_plugin_sync`, `plan_exports`) against the registry
  in `.claude/marketplace-sync.json`, so pairs, script mirrors, hook merging and declared divergences are
  decided by the one implementation. Each result becomes a finding on the canonical file that cites every
  changed path of its component as `path:*`, a component form only script findings may use (see Diff-scoped
  blocking below): any change to that file, however small, makes the finding the PR's. So a PR that touches a
  component owns the drift in it even when the drifted file itself is untouched, which is what the old check
  did (it blocked on any drift in a touched component); more than 200 changed paths in one component fails
  the run closed. Before #576 this check blocked through its own channel; it now goes through
  `aggregate_findings` and `gate_decision` like every other script finding, so the exceptions registry can
  suppress it. `run-codex-review` still lists the results under `structural_findings` (the parity wrapper
  expects that key) but that list is informational: it no longer blocks by itself. Unchanged from the old
  check, and stated so the claim stays honest: a mirror file with no canonical source (a stale copy) is not
  reported, the planner reads the checked-out working tree rather than git objects (the CI job checks out the
  PR head; a dirty local tree can differ), and `mirror-byte-identity` stays guidance for model reviewers (no
  finding carries that id). The required `marketplace-parity` job (`check-all` on the whole tree) remains a
  second, independent backstop.
- **`removed-identifier-leftover`** (rule class `graph`, severity `major`, outcome `removed-identifier`). A
  skill, agent or command whose name is in the base and not in the head while the live tree still references
  it. Removal is by name within a namespace: a skill and a command share one (`Skill(name)` calls either), an
  agent has its own, so deleting, renaming, or renaming the directory removes a name, while moving a component
  to another plugin, or turning a skill into a command or back, keeps it. A reference is `Skill(name)` for a
  skill or command, or `subagent_type: name` for an agent (positional or keyed, JSON-style quotes included,
  with or without a `plugin:` prefix); and, only when no other component still has the name, `/name` or
  `plugin:name` in backticks (a slash command may carry arguments, `/name --flag`), and the bare name in
  backticks only if it is hyphenated (a single common word
  such as `commit` or `docs` in backticks is ordinary prose). One finding per removed component, on its old
  path (the deleted or renamed path is in the diff, so it is the PR's), with the number of references, the
  number of files and up to five of them. The search is `git grep -a` at `HEAD` (`-a`, because whether a
  file counts as binary can come from a `.gitattributes` the PR itself adds), so it is bounded by the number of
  matching files and sits outside the Python read budget, over `plugins/`, `docs/`, `scripts/`, `.github/` and
  root files, without the exact history files `CHANGELOG`, `CHANGELOG.md` and `RELEASE_NOTES.md` in any
  case (a prefix would also hide a live file such as `commands/CHANGELOG-release.md`). `.claude/`, `.agents/` and `.codex/` are
  the mirror family's, and `evals/` and `issues/` are history. A name the search cannot match safely (a
  space, `+`, `@`, non-ASCII) is a finding of its own, never a skip. It needs a base: with none, nothing is
  known to be removed. The 30-second scan budget is checked before each search and each search has its own 60-second
  timeout, so the step can take longer than 30 seconds in all; running out of either, or removing more than
  200 components, fails the run closed. `checked` lists the
  removed components that were searched. On the real tree, simulating the removal of `merge-pr` gives one
  finding and `example-skill` one finding (2 references in 1 file). A deliberately historical mention (a
  migration note) needs an entry in `review_exceptions.yaml`. **Accepted:** an agent's frontmatter `skills:`
  preload list that names a removed skill, and a rename done only in the frontmatter `name:` (a component's name
  comes from its path), calls split across lines (git
  grep matches line by line), a case mismatch, a nested command name (`commands/sub/x.md` is searched as
  `sub/x`), the `plugin:` prefix also matching an external plugin's name, a removed `x` matching `Skill(x.v2)`,
  live non-mirrored consumers under `.claude/` (such as `settings.json` permission entries), code
  identifiers and rule ids, which `ty`, the tests and the R20 sweep already see.
- **Accepted limits.** The verifier mirrors R6 as written: it judges the four shells R6 names, so `zsh`,
  `pwsh` and other interpreters are outside it. A shell behind a wrapper (`env bash:*`, `FOO=1 bash:*`,
  `/usr/bin/env sh:*`) is read as the shell, using the wrapper list R37 uses (`env`, `exec`, `command`,
  `time`, `nohup`, `nice`, also quoted, by absolute path or in another case; a step beyond R6's text). A
  wrapper word the check cannot read makes the file unverifiable, which blocks: an option outside its table
  (`env -S`, a clustered or abbreviated option), a quoted or escaped option or assignment, or options with
  nothing after them. A bare wrapper grant (`env:*`, `time:*`) lets the caller name any program
  after it, so it is reported like an interpreter. Not judged: other wrappers (`timeout`, `sudo`, `xargs`,
  `setsid`, `stdbuf`, `ionice`, `chroot`); `command -v bash` is flagged although it only looks the
  program up. Also outside it is PowerShell's habit of joining the arguments
  after a script into one command string (Windows only, not verified here) (widening them is a change to R6's
  `forbidden_bash_scopes` and to the verifier together, keeping the settings-equality test). It reads the
  frontmatter with PyYAML; where Claude Code's own parser could read a file differently, the strict
  acceptance above is what limits the gap, and a form it cannot rule out stays an accepted limit. Component
  paths declared in a manifest instead of the default directories are not covered.
- **Cost.** The frontmatter is parsed twice by pure-Python PyYAML, so a bracket bomb is refused first: flow
  nesting deeper than 100 is unverifiable before any parsing.
- **Result file.** `verifiers` lists each verifier (`grant-to-body`, `measurement`, `path-and-mirror`, `structure`, `call-graph`,
  `removed-identifier`) with `status` (`clean`
  or `findings`), the number of findings and the number of files checked.
- **Failure.** A verifier that raises, or a changed component path that is missing from `HEAD`, makes the
  run `could_not_run` (exit 2), like any other infrastructure failure.
- **Trust.** The module is Tier 1 (see below): a PR that edits it is refused automated review and needs the
  maintainer bypass attestation, because a verifier it could weaken would be the PR deciding its own gate.

### Re-running the verifiers on a fix (`handling-review-findings`, #578)

`git-kit`'s `scripts/git-verify-fix-diff.py` is a second entry point to `run_verifiers`, for the fix loop
(`handling-review-findings` step 4) rather than for CI. It is a plugin script, not a `marketplace_ci`
subcommand, so it is outside Tier 1 and needs no bypass attestation; the CI path above is unchanged.

- **Invocation.** `--base <full object id>` diffs the commit before the fix against `HEAD`; `--worktree`
  checks the uncommitted working tree instead, through a throwaway commit built with a temporary index and
  checked out in a temporary shared clone (no ref, index, working-tree or object-store change; the snapshot's
  objects, including untracked non-ignored files, go to a temporary object directory deleted on exit; a hard
  kill leaves it in the system temp directory).
- **Which code runs.** The verifier modules are extracted with `git archive` from the commit where `HEAD`
  last met the target branch (`git merge-base HEAD refs/remotes/origin/HEAD`) and imported from a private
  copy: never from the tree being judged, and never from `--base`, because a PR's own earlier commit can
  precede `--base` and the extracted modules are executed. Without `refs/remotes/origin/HEAD` the run exits
  2 (`git remote set-head origin -a` sets it). The ref is local state, so `--upstream <owner>/<repo>`
  (required; the skill passes the PR's base repository) must match `origin`'s fetch URL, or the run exits 2:
  a clone whose `origin` is a contributor's fork would otherwise trust that fork's default branch. The
  branch still picks which version of the target's verifiers judges it (the one at the merge-base). The
  driver script runs from wherever it is started, so its exit 2 for a fix that edits it catches an honest
  edit only; it removes its own directory from `sys.path` before any other import, so a sibling module a PR
  adds there cannot shadow the standard library or the verifiers' dependencies. CI still judges the pushed
  head.
- **Touched-file logic.** Every finding `run_verifiers` returns for the changed files blocks; the script has
  no touched-line filter of its own. Verifiers that compare with a base compare with `--base` (the commit
  before the fix), so a value already over its limit before the fix and not worse after it passes here while
  CI can still block. A fix that changes `scripts/marketplace_ci/`, `.claude/marketplace-sync.json` or the
  script itself exits 2, because the verifiers cannot grade a change to themselves. `--base` must be an
  ancestor of `HEAD`; without `--worktree` the committed `HEAD` is verified in a temporary clone.
- **Output and exit codes.** One JSON object with `checked` and `blocking`. Exit 0 is clean,
  1 a blocking finding, 2 not verified: the verifiers could not run, the verifiers exist at the target
  branch but not in the tree, the diff is empty, `--worktree` runs in a sparse checkout, or the fix touches
  what grades it. Exit 0 with "nothing to check" happens only where neither the target branch nor
  the tree has `scripts/marketplace_ci/review_verifiers.py` (git-kit is installed in other repositories).
- **Not covered.** It does not run the model reviewers, the structural check or the computed gate, and a
  clean result is not the CI verdict: CI still judges the pushed head.
- **Outcomes ledger.** `scripts/git-review-ledger.py` records one disposition per finding in a gitignored
  `.claude/review-ledger.local.json` (`record` adds it to the repository's `.git/info/exclude` when no ignore
  rule covers it, and refuses to write it if git still does not ignore it; a ledger path that is a symlink or
  contains a control character is refused) and promotes a PR's entries to the tracked `.claude/review-outcomes.json`
  before the PR's last push. It refuses a corrupt file, a path outside `.claude/` and a tracked working ledger.
  Injecting refuted findings into the reviewers' briefing is not done: it would change a Tier-1 file.

## Diff-scoped blocking

`run-codex-review` fails the `codex-review` job (exit 1) only for findings that belong to the PR. A reviewer
reads every touched file as a whole, so it also reports problems that already exist on the base branch; those
used to fail a PR that never wrote them (issue #525). The deciding code is `_classify` in
`scripts/marketplace_ci/review.py` (via `split_findings_by_diff`; `blocking_findings` applies the same test),
called once per run through `_diff_scope` in `__main__.py`:

| Finding | Blocks? |
|---|---|
| Major or Critical on a line the PR changed | Yes |
| Critical or Major on an unchanged line of a touched file | No — kept in the artifact as a notice |
| Any finding in a file the PR did not touch | No — kept in the artifact as a notice |
| Minor | No |
| A mirror or export drift finding (`r19-mirror-drift`) | Like any script finding: Yes when its component has a changed path (it cites them); the registry can suppress it. `structural_findings` still lists it, informationally |

"On a line the PR changed" means the new-side line ranges of `git diff -U0 --text <base>...HEAD`, matched
exactly (no slack window). A pure deletion counts the two lines either side of the removal, and a finding that
names no line counts as on a changed line whenever its file is touched. A cross-file finding also lists the other files involved (`components`); it is judged at each
cited location and blocks when any one of them is on a changed line. A component that names a line is tested
like the primary location. A component that names no line (a bare path) counts only when its file is changed
in full (the list below), never merely because the file is touched: otherwise a one-line edit to a file would
block every finding that cites it. A script finding may instead cite a path as `path:*` (the
`ANY_CHANGE_SUFFIX` in `review.py`), which counts when the file is touched at all; a model finding's `:*` is
ignored, so a model cannot widen its own scope. Script verifiers use it only for paths they already know the
PR changed (`r19-mirror-drift`, and the unreadable-document finding of `r37-executable-bit`). The following
all count as changed in full, so a finding on them blocks whichever line it names:

- a changed path that has no hunk: a pure rename (both the old and the new name), a mode change, an empty or
  binary file;
- a changed symlink, and anything that resolves into one — a PR that adds a link exposes existing, unchanged
  content at a new path, and a reviewer may cite either spelling. A link whose target lies outside the
  repository (up to `/`) therefore makes every finding that resolves into that target block;
- a file that was renamed or copied, or whose mode changed, whether or not it also has edits — its carried-over
  lines become loadable at a new path or mode, which is the same exposure a new symlink creates;
- a file the PR newly adds — every line is new, so a bare component naming it counts;
- a file whose changed lines contain a line break other than `\n` (a bare CR, vertical tab, form feed,
  FS/GS/RS, NEL, U+2028 or U+2029; the CR that ends a CRLF line does not count). Git counts lines by `\n` only,
  but a reviewer may count by these, so its line number cannot be trusted to match git's for that file.

A finding's path is normalised before it is matched (`./x`, `a//b`, `a/../b`, absolute paths under the checkout,
and symlinks resolved against the git root, not the working directory). A symlink is recognised from git's tree
(mode `120000`, target text read from the blob) as well as from the checkout, so `core.symlinks=false` does not
hide one. That lookup is one `git ls-tree` and at most two `git cat-file` calls per run, and it fails closed: if
git cannot answer, or a link's target is missing, longer than 4096 bytes or contains a NUL byte, the run exits 2
instead of skipping the check. Off Linux, paths are also compared after Unicode NFC normalisation and case folding, because the
filesystem there can match a spelling git did not store; on Linux (the CI runner) they are compared exactly. A resolved path outside the checkout adds
no extra spelling to match, unless it lies inside the target of a changed symlink, which blocks.

**Fail closed.** If the changed lines cannot be computed — git fails or cannot start, or the diff output has a
shape the parser does not recognise (a quoted path header, or any line outside a hunk it does not expect) — every
Critical and Major blocks, exactly as before diff scoping. `diff_scoped` in the artifact says which case
applied. The `git diff` call pins `core.quotepath`, the path prefixes, external diff drivers and textconv, and
passes `--text`, so a PR-controlled `.gitattributes` entry such as `-diff` or `binary` cannot turn hunks into
"Binary files differ". The diff output is read with a 64 MiB cap (`_MAX_DIFF_BYTES`); a larger one counts as
uncomputable and takes the fail-closed fallback. An unexpected error while classifying exits 2 and overwrites `codex-review-result.json`
the same way the other exit-2 paths do.

**Accepted residual risk.** Severity does not widen the scope. A PR can remove a guard on one line and leave the
exposed use of it elsewhere in the file; a finding on that unchanged line, Critical or Major, does not block and
appears in the artifact with `"in_diff": false`. Matching also trusts the line number the reviewer reports: a
finding reported on a line other than the one git would give (the odd line breaks above are covered, but not every
way a reviewer can miscount) does not block. In the other direction, a finding about a missing behavior that
the reviewer happens to anchor on a changed line blocks even though the PR did not cause it. An earlier version
of this rule also blocked on any Critical in a touched file; replaying the recorded findings of PRs #524 and #526
showed that rule kept both failing on pre-existing Criticals (an over-length file, a fetched-URL instruction, a
dangling `Skill()` grant), so it was dropped. Use the attested bypass or a manual review for a PR whose risk is of
the deleted-guard kind.

**Reviewer briefing (issue #527).** Blocking alone left each reviewer free to read and judge whole files, so the
findings on the changed lines could still differ between runs of the same head. `run-codex-review` therefore also
appends a `[diff scope]` block to every reviewer's instruction (`render_diff_scope`, from the same ranges the gate
uses): it lists each reviewed path with its changed lines and tells the reviewer to read the rest for context but
report only on the changed ones, or on a problem that a change here, a removal included, plausibly causes or exposes
elsewhere, anchored to the changed line. A path that counts as changed in full above (whole-file range, rename,
mode change, empty or binary file, changed symlink or a path resolving into one) reads `entire file`, and so
does a file with more than 50 changed ranges, which keeps the briefing small and is briefing-only: the gate
still counts only that file's changed ranges; a reviewed path the PR did not touch, such as part of a
`full`-mode dependency closure, reads `context only`. When the changed lines cannot be computed, the instruction is
left exactly as the base SHA holds it, matching the fail-closed fallback. The briefing narrows what the model is
asked to judge; it does not change what blocks. It can still lower how many unchanged-line problems a reviewer
mentions, so fewer `"in_diff": false` notices may appear, and the deleted-guard case above relies on the reviewer
anchoring what a removal exposes to the changed line. A changed path with characters outside `[A-Za-z0-9._/-]`
fails the reviewer (exit 2) instead of being written into the instruction. A name made only of allowed
characters is still shown to the model, fenced as data with the boundary stated before and after it; that
reduces but cannot remove the chance that a hostile file name influences the review. The briefing makes repeated runs more
alike but cannot guarantee they agree, because the model is still non-deterministic.

`codex-review-result.json` carries, in addition to the fields above:

- `diff_scoped` — `true` when the changed lines were computed, `false` for the fail-closed fallback;
- per finding, `components` (the other locations a cross-file finding cites, which can be what put it in the diff),
  `in_diff` (on a changed line or in a changed-in-full path; `null` when `diff_scoped` is `false`)
  and `blocking` (whether that finding failed the job).

`ReviewResult.blocking` (used only by the `check-review-output` command on a single reviewer's envelope) is
unchanged and still counts any Critical/Major.

## Fork PR limitation

`codex-review` needs `OPENAI_API_KEY`, which GitHub Actions does not expose to workflows triggered by a
fork PR (no trusted secret access, by design — a fork PR's workflow content is untrusted). Rather than
leaving the Codex check permanently pending on a fork PR (which would silently block merge forever with
no actionable signal), `fork-unsupported` fails explicitly and immediately when `github.event.pull_request.head.repo.fork`
is true. A fork-originated PR against this repository cannot currently pass Codex review automatically —
it requires either becoming a same-repo branch (push access) or a maintainer's attested bypass (see below).

## Automatic reviewer-scope bypass

Separate from the manual protocol below, `compute-scope` skips `codex-review` entirely — no maintainer
action needed — when `derive_review_scope`'s own scope for the diff resolves to nothing any reviewer
would look at: today's `mode == "light"` (no `plugins/` path touched at all), and the newer case where
`plugins/` paths were touched but every one of them is excluded anyway. That exclusion is deliberately
**narrower** than `plugin-rulebook-checker`'s own target-path exclusion: only an `evals/`-prefixed path or
a plugin-root `LICENSE`/`NOTICE`/`KNOWN_ISSUES.md` (genuinely inert text) qualifies. A plugin's
`README.md`/`CONTRIBUTING.md`/`CHANGELOG.md`/`INSTALLATION.md` do **not** bypass — a security review found
these can carry real signal (a README's install step piping a script to a shell, a CHANGELOG newly
documenting a dependency) that `dependency-reviewer`/`security-reviewer` should still see, even though
`plugin-rulebook-checker`'s own R1-R37 rules never had an opinion on them. The exclusion also only ever
applies to a basename sitting directly at a plugin's own root or the repo root — a same-named file nested
inside a component directory (e.g. `plugins/<name>/commands/README.md`, a real, Claude-Code-loadable
command file) is never excluded, so a component change can't be smuggled past every reviewer by naming it
after an excluded basename. `mode == "full"` (see "Full-mode escalation" below) is never bypass-eligible,
regardless of scope — that path is inherently high-risk by definition, including its own fail-closed
empty-scope gap case. Nor is a diff touching the gate's own code, its CI dependency spec, the PR template,
or a CODEOWNERS file — `.github/`, `scripts/`, `.codex/agents/`, `.claude/rules/`, `pyproject.toml`,
`uv.lock`, `uv.toml`, `.python-version` (a prefix, so `.python-versions` too), `CODEOWNERS`,
`docs/CODEOWNERS` (the three locations `check-pr`'s own merge-privilege matching
reads — `.github/CODEOWNERS` is already covered by the broader `.github/` entry) — ever bypass-eligible,
even mixed with otherwise-eligible files. This is enforced two ways, not just a flag flip:
`derive_review_scope` itself falls through to a real delta dispatch (the baseline three reviewers) for any
diff touching one of these paths, rather than resolving to empty-reviewer `mode == "light"` the way an
equivalent non-self-protected diff would — a security review found an earlier version only forced
`bypass_eligible=False` without also ensuring a reviewer actually ran, so the diff was correctly marked
ineligible but still reviewed by nobody. `is_bypass_eligible`'s own explicit prefix check stays as a
second, independent layer on top. The prefix list covers the whole `scripts/` tree (not just
`scripts/marketplace_ci/`), since `python -m scripts.marketplace_ci` imports `scripts/__init__.py` first —
a narrower list a security review actually found left that one file able to bypass its own review by
sitting just outside the guarded path. It also covers a bare-root `CODEOWNERS` add — a security review
found an unreviewed CODEOWNERS file both grants and denies merge privilege unconditionally (a match is
terminal in `check_merge_rights`, never falling through to the collaborator-permission check), for every
PR after the one that added it, and no such file exists in this repo today, so this is a live gap, not a
hypothetical.

`check-pr` has one narrow exemption: a PR opened by the exact login `dependabot[bot]` (`TRUSTED_BOT_LOGINS`
in `pr_policy.py`) passes the author-privilege check, and passes the merge-privilege check only when every
changed path is a root manifest/lockfile (`uv.lock`, `pyproject.toml`, `package.json`, `pnpm-lock.yaml`); the diff runs with
`--no-renames` so a rename onto one of those names can't hide the deleted source file.
The login is the PR opener and never changes, so the merge-privilege exemption also requires every commit
on the PR (`gh api .../pulls/<n>/commits`) to be authored by `dependabot[bot]`, committed by `web-flow`
and carry a verified signature (`commits_verified_from_trusted_bot`). Any API error or unexpected shape
fails closed (that includes the commit count or last commit SHA disagreeing with the event payload). The
`hygiene` step needs `GH_TOKEN` and `pull-requests: read` for these `gh api` calls. Otherwise the normal CODEOWNERS check applies — that is what stops a write-access
collaborator pushing other changes, or hand-edited manifest content, onto a dependabot branch. The
author-privilege check stays opener-only.

Residual, unverified: whether a write-access collaborator can mint a web-flow-signed commit with a spoofed
`dependabot[bot]` author through the contents or git-commits REST API was not tested live (it needs a
scratch PR on the real repository). If it is possible, that collaborator could edit manifest content on a
dependabot branch and pass merge-privilege; the owner's review and merge remain the backstop.

**Trust boundary, stated plainly, not just narrowed further:** `compute-scope` restores
`scripts/`+`pyproject.toml`+`uv.lock` from the **trusted base SHA** — never the PR's own copy — before
computing the scope decision or installing dependencies for it (same principle
`prepare_reviewer_instruction` already applies to reviewer instructions; see the `compute-scope` job's own
"Restore the base SHA's copy..." step), and fails the job outright if that restore itself can't complete,
rather than falling back to scoring with the PR's own copy. `git diff base...HEAD` is unaffected by this
restore — it compares commit objects, not the working tree, so the PR's real diff is still what gets
scored. The same restore (a no-overlay `git restore`, so files the PR added under `scripts/` are deleted
too, plus `uv.toml`, `.python-version` and `.python-versions` and, in `hygiene`, the CODEOWNERS and
PR-template inputs) runs in `hygiene`, `compute-scope`, `prefix-permanence` and `publish`, followed by
`uv sync --locked --no-config`. A restore cannot remove what base never had, so each of those jobs
also refuses a PR that adds an importable top-level name: a top-level `*.py`, `*.pyc`, `*.pyw`, `*.pyd`
or `*.so` file, a `<dir>/__init__.*` package marker, `.venv` content, or any top-level symlink. This
is a denylist of the forms CPython's importer accepts, not a proof that no other form exists.
`codex-review`, which holds `OPENAI_API_KEY`, cannot restore (its reviewers must see the PR's real
files), so it refuses instead: the same added-name check, plus its Tier-1 hard-refuse step now also
covers `uv.toml`, `.python-version` and `.python-versions`, and its `uv sync` is locked and
config-free. Because that job runs `scripts/` from the PR's own checkout, it also refuses a PR that
adds a file under `scripts/` that could replace an unchanged Tier-1 module — a same-named package
directory, a `.so`/`.pyc`/`.pyw`/`.pyd` file, a `__pycache__` entry, any new `__init__.*` package
marker, or any symlink. The Node chain it runs with the key (`bridge-invoke.mjs`, `codex-exec.mjs`,
`cdx-process.mjs`) is on the Tier-1 list too, as are the two secret-redaction shapes files that
`review.py` and `codex-exec.mjs` load at import (`scripts/marketplace_ci/token_shapes.json` and
the `codex-kit` copy of it): editing either would weaken redaction in the job that holds the key.
The review contract (`review_contract.py`) and the exceptions registry it loads
(`review_exceptions.yaml`) are on the list for the same reason: a PR that could edit the registry
could suppress a finding about itself (see [The review contract](#the-review-contract)).
The script verifiers (`review_verifiers.py`) are on it too: they feed the blocking gate, so a PR must not be
able to weaken its own verifier (see [Script verifiers](#script-verifiers)).

Which refusals the SHA-bound Codex bypass clears: all of `codex-review`'s (its Tier-1 hard-refuse,
including the Node files and the uv/Python-version config, and the shadow checks above), because
`publish` short-circuits on an attested bypass before it reads the Codex result. It does **not** clear
the restore jobs' refusals (`hygiene`, `prefix-permanence`, `compute-scope`, `publish`'s own restore
step): those are deterministic gates, so a PR that legitimately needs a new top-level module, package
or symlink requires a maintainer to change this check first, or an admin merge. "Added by the PR"
means the diff from `merge-base($BASE_SHA, PR head)` to the PR head, not `$BASE_SHA` to the merge
checkout: `$BASE_SHA` can lag the base branch, and the latter would blame the PR for a file the base
branch gained in the meantime, a refusal the bypass cannot clear. Each of those steps first checks
that the checked-out tree is the event's PR head (or its merge checkout's second parent) and stops
with a "re-run this job" error otherwise, because the event payload is frozen when the workflow fires
while the checkout is fetched when the job starts: a newer push in between would put files on disk
that the diff never examined. Because `hygiene` restores
`.github/pull_request_template.md` from the base too, a PR that edits the template (for example by
adding or renaming a required section) is validated against the base template, so its own body may
need to keep the old headings until the PR merges. The five hand-copied blocks are kept identical by
`tests/marketplace_ci/test_workflow_trusted_restore.py`.

This raises the bar against an *unaware* PR touching the bypass logic, dependency spec, or
`scripts/__init__.py` and defeating itself by accident. It is **not** an adversarial-proof boundary, and
doesn't claim to be one: a same-repo PR author can edit `.github/workflows/marketplace-ci.yml` itself,
since GitHub runs a `pull_request` workflow using the PR's own copy of the workflow file for a same-repo
PR — a pre-existing property of every check in this workflow (including `codex-review`'s own dispatch,
which has always run from the PR's head checkout), not something this bypass feature introduces or could
close from inside a Python module it doesn't control the invocation of.

Diff-path parsing for both this bypass decision and `codex-review`'s own scope computation uses
`git diff -z --name-only` (NUL-delimited, never C-quoted), not the more common newline-split form — a
security review found that with git's default `core.quotePath=true`, a non-ASCII path is emitted
C-quoted in plain `--name-only` output (e.g. `"plugins/x/skills/y/caf\303\251.py"`), which fails every
`startswith("plugins/")`-style check downstream and would otherwise silently misroute a real component
change into light/bypass-eligible mode.

This bypass never applies to a rebase onto the base branch: on a `synchronize` event, `compute-scope`
checks whether the PR's base commit was newly absorbed this push (reachable from the new head SHA but
not the old one) and, if so, forces `codex-review` to run regardless of what the scope check found. A
rebase can change how already-reviewed code interacts with what the base branch now contains in ways a
bare changed-file-list diff doesn't capture, so it always gets a real Codex pass. This check fails closed
too — if the old/new head SHAs can't be resolved (e.g. already garbage-collected after a force-push), it
treats the push as a rebase rather than silently assuming otherwise. Crucially, `--before`/`--after` are
only present on a `synchronize` event at all — every other `pull_request` action (`opened`, `reopened`,
`edited`, `labeled`) carries neither, and **the bypass is never eligible without both**, not just when a
detected rebase forces it off. An earlier version only checked ancestry *if* both happened to be
present, which a security review found was a one-push bypass of the whole carve-out: push a rebase (a
`synchronize` event correctly detects it and runs `codex-review`), then edit the PR title (an `edited`
event, with no `before`/`after` at all, silently skipped the rebase check and reported eligible again).
Requiring both present unconditionally closes that gap.

Unlike the manual bypass below, this one is never presented as an override — `codex-review` simply never
had anything to review, so `publish` reports the normal `skipped` conclusion, not a bypass annotation.

### `scripts/marketplace_ci/` changes: real review, not always a manual bypass

A change scoped to `scripts/marketplace_ci/` never qualifies for the automatic bypass above (see
`BYPASS_INELIGIBLE_PREFIXES`, which deliberately still covers the whole `scripts/` tree) — it always falls
through to a real `codex-review` dispatch (the baseline three reviewers, at minimum). But whether that
dispatch actually *runs*, or the `codex-review` job refuses outright and requires the manual bypass
protocol below, depends on which part of `scripts/marketplace_ci/` changed (issue #351, direction #3):

- **Tier 1 (review-dispatch-critical)** — `scripts/__init__.py`, and `scripts/marketplace_ci/`'s
  `__init__.py`, `__main__.py`, `review.py`, `review_contract.py`, `review_verifiers.py`, `git_state.py`, `registry.py`,
  `sync_plan.py`, `conversion.py` — plus `pyproject.toml`/`uv.lock` and the uv/Python-version config files
  `uv.toml`, `.python-version` and `.python-versions`, and the three Node files `codex-review` runs
  with the API key (`plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`,
  `plugins/codex-kit/scripts/lib/codex-exec.mjs`, `plugins/codex-kit/scripts/lib/cdx-process.mjs`)
  and the data those two load at import: the canonical secret token shapes
  `scripts/marketplace_ci/token_shapes.json` and the byte-identical `codex-kit` copy
  `plugins/codex-kit/scripts/lib/cdx-token-shapes.json`, and the documented-exceptions registry
  `scripts/marketplace_ci/review_exceptions.yaml`. The canonical file is copied into
  `analysis-kit`, `promptlibrary-kit` and `codex-kit`; `check-all` runs `check-token-shapes` to fail on a
  drifted copy, and `sync-token-shapes` rewrites the copies (run `sync-plugin-mirrors` after it so
  the `.claude/` mirrors follow). Edit the canonical file only.
  These are the modules `run-codex-review` (and
  `check-scope-bypass`/`check-bypass`/`resolve-attested-actor`) actually load to decide and report this
  review's own outcome (`tests/marketplace_ci/test_import_isolation.py` verifies this both at runtime,
  via a subprocess probe per subcommand, and statically, via an AST scan of every import statement —
  module-level or function-local — in each Tier 1 *Python* module; the three Node files are covered by
  `tests/marketplace_ci/test_workflow_trusted_restore.py`, which asserts their relative imports stay
  inside this set). A same-repo PR touching any of these still hits
  `codex-review`'s own "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical
  code" gate and requires the manual SHA-bound bypass protocol below — no automated pass can safely
  self-evaluate a change to the code that grades it.

  `pr_policy.py` is also in this gate's pathspec list, even though it is *not* part of
  `run-codex-review`'s own import closure — it's gated for a distinct reason: it's the
  merge-privilege-deciding code (`check_merge_rights`'s CODEOWNERS matching) that the `hygiene` job's
  `check-pr` step evaluates. `hygiene` now restores that code and its data inputs from the base SHA
  too, like `compute-scope`/`publish`, but the file stays on this list until a separate decision says
  otherwise: classifying it as Tier 2 would let a same-repo PR tamper with its own merge-privilege
  evaluation and get only automated (never mandatory human) review of that change if the restore were
  ever bypassed or removed.
- **Tier 2 (everything else)** — `sync.py` (the mirror/export apply and staging side), `validators.py`
  (the staged-parity check and the PostToolUse post-edit hook), and the non-Python `rules/`/`hooks/`
  mirror-source data. A PR touching only these now gets **real, non-bypassed** Codex review coverage
  automatically — `__main__.py` imports every CLI handler's own dependencies lazily, inside that
  handler's function body rather than at module level, so `run-codex-review` provably never loads any
  Tier 2 module at all. Tampering with Tier 2 code therefore can't affect how *this review's own*
  outcome is decided or reported — that guarantee is scoped to `codex-review`'s own dispatch decision
  specifically, not to every CI gate `scripts/marketplace_ci/` code feeds (see `pr_policy.py` above for
  the one that still needs the hard refusal for an unrelated reason).

  "Real coverage" here also means a **type-specific** reviewer, not just DELTA_VALIDATE's baseline
  three — none of which review script/rule/hook-manifest correctness (found live, PR #370, Codex
  connector review). `_audit_types_for` (`review.py`) dispatches `scripts-reviewer` for a `.py` change
  under `scripts/marketplace_ci/`, `rule-reviewer` for a `.md` change under
  `scripts/marketplace_ci/rules/`, and `hook-reviewer` for a `.json` change under
  `scripts/marketplace_ci/hooks/` — the same `LAUNCH_AUDIT_BY_COMPONENT_TYPE` mechanism `skills/`/
  `agents/` changes already get, extended to these three Tier 2 surfaces since none of them are a
  `plugins/<name>/<type>/` path that mechanism's own component-type keying can match.

This closes the friction issue #351 opened to track: previously *any* `scripts/marketplace_ci/` change —
including a fix wholly contained in `sync.py`'s apply side — required the same manual bypass-attestation
cycle every time, with no automated safety net beyond the human doing it (hit directly by PR #349's
`_atomic_write` fix). It does not change `is_bypass_eligible`/`BYPASS_INELIGIBLE_PREFIXES` at all — those
intentionally stay broad, since their job is guaranteeing real reviewer coverage for *any*
`scripts/marketplace_ci/` change regardless of tier, not deciding which tier needs the hard refusal.
`tests/marketplace_ci/test_import_isolation.py`'s
`test_workflow_hard_refuse_gate_pathspec_matches_tier1_file_set` cross-checks the workflow gate's
pathspec list against this Tier 1 set mechanically, so the two hand-duplicated lists (a shell pathspec
here, a Python tuple in `review.py`) can't silently drift apart.

## Manual SHA-bound bypass protocol

A PR whose *only* failing required check is `Publish Codex policy result` can be unblocked by a
maintainer (live `write`/`maintain`/`admin` permission) attesting a bypass, bound to the exact head SHA:

1. Post a PR comment containing a hidden marker:
   `<!-- marketplace-ci-bypass-attestation {"schema_version":1,"actor":"<login>","head_sha":"<sha>","reason":"<reason>","created_at":"<ISO-8601 UTC>"} -->`
   The comment must hold exactly one marker, it must be the last thing in the comment (prose may come
   before it, nothing after), and it must sit outside any fenced code block — a marker that fails any of
   these is ignored. The marker is a hidden HTML comment, so a copy buried mid-comment in pasted text
   would otherwise be invisible to the person posting it. A bot account (a login ending in `[bot]`)
   can never attest.
2. Apply the `s: codex review bypassed` label (must already exist in the repo — nothing creates it
   automatically; create it once via `gh label create "s: codex review bypassed"`).
3. Applying the label re-triggers the workflow (`labeled` is in the `pull_request` trigger types);
   `publish` re-checks the attestation via `scripts/marketplace_ci/review.py`'s `check_bypass` — exact
   actor + exact head SHA match, plus a live permission check, counting only comments whose **real GitHub
   author** is the labeler, so a marker forged by anyone else never counts — and reports `Publish Codex policy result`
   as passing, explicitly annotated as bypassed, never as a clean review. Applying a label that's
   **already present** on the PR is a GitHub Actions no-op and does not fire a fresh `labeled` event — a
   re-attestation after a superseded bypass attempt must remove the label first (`gh pr edit --remove-label
   "s: codex review bypassed"`), then re-add it, to force a fresh check run.
4. A new commit changes the head SHA, invalidating any prior attestation — it must be re-attested.

> **The same "must already exist" caveat applies to the `size: XS/S/M/L/XL` labels**
> `.github/workflows/pr-size-labeler.yml` applies (`.github/labels.yml` declares them; `sync-labels.yml`
> only creates/updates them on a **push to `main`** that touches that file — so a PR that adds both the
> workflow and the label declarations in the same change, like this one, can't benefit from that sync
> until it merges). `pr-size-labeler.yml`'s own `gh pr edit --add-label` fails outright (`'size: XL' not
> found`) if the label doesn't exist yet — live-verified on PR #294's own `size-label` check, whose first
> real run only became possible once its trigger was fixed to `pull_request` (a `pull_request_target`-
> triggered workflow that's new to the PR never runs at all until the PR merges, since GitHub resolves
> that trigger's workflow file from the base branch). Bootstrap once via
> `gh label create "size: XS" --color 7EE081 --description "XS: <10 lines changed"` (repeat for
> `S`/`M`/`L`/`XL` with `.github/labels.yml`'s own color/description values) before this workflow's first
> real run on a same-repo PR.

### Attesting without the label (`CODEX_CI_REVIEW_BYPASS`)

The `CODEX_CI_REVIEW_BYPASS` repo variable (`0`=disabled, `1`=enabled; any other non-empty value
fails `publish` closed for every same-repo PR until corrected) is **not** a standalone
bypass — setting it never bypasses anything by itself, and it changes nothing about who can attest
or what an attestation must contain. It only lets `publish` look for a valid attestation on a run
that wasn't triggered by applying the label (e.g. a plain push/`synchronize` event), for which there
is no `labeled` timeline event to resolve a trusted actor from. When set to `1`, `publish` instead
resolves the attesting actor from the **real GitHub author** of a matching comment (`user.login` from
the Comments API — never the marker's own self-declared `actor` field, which is attacker-controllable
comment text) via `resolve-attested-actor` — among the real authors of matching comments it picks the
most recent one that is not a bot and holds a live `write`/`maintain`/`admin` permission, so a later
self-attestation from someone without write access cannot shadow a maintainer's earlier one — then runs
the exact same `check_bypass` attestation check
as the label path: exact head-SHA match, non-empty reason, live `write`/`maintain`/`admin` permission
on that real author. A PR with no matching attestation comment is unaffected by this variable
regardless of its value — every PR still needs its own SHA-bound attestation; this only changes how
the check discovers one.

`Skill(git-kit:create-pr)`, `Skill(git-kit:merge-pr)`, and `Skill(git-kit:commit)` all support
`--bypass-codex-review "<reason>"` to run this protocol as part of the normal PR-creation/merge/push flow
rather than by hand. `create-pr` attests for the PR it just created; `merge-pr` attests (and waits for the
replacement check) for an already-open PR immediately before merging; `commit` attests for an already-open
PR right after pushing a new commit to it — the mid-review-cycle re-push case neither of the other two
covers, since the attestation is SHA-bound and invalidates on every new commit. None of the three skips any
other check, the merge-rights check, or the explicit human merge confirmation — see each skill's own
Boundaries section.

## Full-mode escalation

A PR touching a shared-governance path — the marketplace registry file, `marketplace.json`,
`.claude/marketplace-sync.json`, the repo-specific `.claude/plugin-rulebook.config.json` override, or any
of `plugin-rulebook`'s own content files a reviewer agent's instructions `Glob`/`Read` live from whatever
checkout it's running in (the exact, current list is `review.py`'s own
`_RULEBOOK_GOVERNANCE_RELATIVE_PATHS` — not repeated here, since re-stating it independently is exactly
the kind of duplicate fact that drifts; each of those files escalates in **either** its canonical
`plugins/plugin-devkit/skills/plugin-rulebook/` copy or its `.claude/skills/plugin-rulebook/`
in-development mirror, via `_RULEBOOK_GOVERNANCE_ROOTS`) — or an oversized dependency closure escalates
`derive_review_scope` to `mode == "full"`. Every one of those rulebook-content paths (not just `SKILL.md`,
and not just the canonical copy) is an escalation trigger because a reviewer agent's own instructions
read them live rather than from the validated base SHA — a PR editing only one of them, in only one
location, would otherwise be judged against its own just-edited rule content (found live, PR #276; the
mirror-copy half of this gap was worse than self-judging, since it got zero reviewers dispatched at all).
A third tracked copy, `.agents/skills/plugin-rulebook/`, is a stale, unmaintained artifact from before
`codex_exports.skills` was narrowed (not part of any active sync) — rather than escalating for content no
agent should ever apply, every rulebook-consuming reviewer agent's own instructions explicitly refuse to
load a `.agents/` copy at all, so its content is inert regardless of what it contains.
`plugin-rulebook-checker`'s and `external-references-reviewer`'s shared R23 marketplace-auto-allow scan
(`Glob("**/marketplace.json")`, both delegating to `external-reference-policy.md`'s own Detection
Procedure so the exclusion can't drift between the two callers) excludes every match under `evals/`
before applying the plugin-root-owner walk-up — those are test-fixture output, not real marketplace
manifests, and would otherwise be a zero-reviewer path to smuggling an auto-allowed external reference
past R23. Both triggers now dispatch a defined, bounded reviewer set — a dependency-closure
overflow reuses delta's own baseline reviewers scoped to the full closure; a shared-governance-path
change dispatches a small, fixed set targeted at that file (`plugin-rulebook-checker` +
`consistency-reviewer` for a rulebook change, `plugin-validator` for a registry/manifest change) — never
a marketplace-wide re-review of every plugin. `run-codex-review` still fails closed (exit 2) as a
defensive backstop only if a future escalation trigger is ever added without a matching reviewer set
defined for it; that path is not reachable through either of today's two triggers. See
`plugin-marketplace-review/SKILL.md`'s "Full review escalation" section for the exact per-trigger
reviewer sets.

## Codacy: `git` through `subprocess` in plugin scripts

Codacy's Bandit and Prospector_bandit engines flag three rules on any script that runs `git`, whatever
the arguments are (decided in #581, first seen on PR #579). They are pattern rules, not data-flow
rules, so no code shape of `subprocess.run(["git", ...])` avoids them:

| Rule | Fires on | Decision |
|---|---|---|
| B404 | `import subprocess` | Accept with `# nosec B404 -- <reason>` on the import line |
| B603 | any `subprocess.run`/`Popen` call without `shell=True` | Accept with `# nosec B603` on the call line |
| B607 | a list-form call whose first element is a bare name such as `"git"` | Accept with `# nosec B607` on the call line |

Accept only a call that is list-form, has no `shell=True`, and takes its subcommand as a literal. A
call that puts untrusted text into the command is a real B603 finding: fix it in code. Local `bandit`
honors the comments (0 issues, 24 skipped on the two #581 scripts); whether Prospector_bandit does too
is confirmed only by the Cloud CLI re-check below.

- **Do not replace the bare `git` with an absolute path** to satisfy B607. The command then becomes a
  variable, which Semgrep's `dangerous-subprocess-use` flags at severity Error, trading a Warning for
  an Error. A call that must take a variable command goes through the script's existing `_git` helper.
- **Why inline comments:** a per-issue Codacy ignore keys on an issue id that changes when the code
  moves, so it needs re-applying after edits; a `# nosec` comment travels with the line and carries its
  reason. `.codacy.yml` `exclude_paths` is not a substitute for production scripts, because it drops a
  whole file from a whole engine (see the comments there for the test-harness exclusions).
- **Test-only code** keeps using the `.codacy.yml` test-harness exclusions, or Codacy's per-issue
  ignore (`codacy pull-request ... --ignore-issue <id> --ignore-reason TestCode`).
- **Precedent:** `plugins/workledger-kit/scripts/` (commit `4c2a6d49`) and, from #581,
  `plugins/git-kit/scripts/git-verify-fix-diff.py` and `git-review-ledger.py`. Other git-kit scripts
  still carry the same unsuppressed findings; apply this convention when next touching them.
- **Re-check** with the Codacy Cloud CLI (`codacy pull-request <provider> <org> <repo> <n> --output
  json`, then keep the `Security` category) after the PR's analysis finishes, since the GitHub check
  annotations show only a capped subset.
