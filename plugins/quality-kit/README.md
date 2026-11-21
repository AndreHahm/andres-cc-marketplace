# quality-kit

A default strategy for resolving static-analysis findings, so a failing check is decided once, by one
procedure, with the reason recorded. Codacy and SonarQube Cloud are the verified providers; the structure
leaves room for others (see `skills/collecting-analysis-findings/references/adapter-contract.md`). Coverage is
handled separately: Codecov as a view, and a coverage tier on patch coverage as the check. Mutation testing
(mutmut) measures how well the tests catch real changes, as data, never as a gate.

**Status: 1.0.0-alpha.4.** Built from issue #581, where the same Bandit rules on `git` subprocess calls were
handled three different ways across this repository.

## Skills

| Skill | What it does |
|---|---|
| `collecting-analysis-findings` | Reads a PR's, a repository's or the already-ignored findings from Codacy's Cloud CLI or the `sonar` CLI output and writes one provider-neutral record, grouped by rule and file, with a check that the analysis is current for the PR head. Read-only |
| `resolving-analysis-findings` | Decides each finding's outcome on a five-rung ladder (fix, inline suppression, per-issue ignore or transition, path exclusion, pattern or gate change), with decision rights per provider, required reasons, baseline versus new, verification after push, a local pre-PR scan and an author checklist |
| `using-sonarqube-cloud` | Answers ad hoc SonarQube Cloud questions and walks through setup: quality gate lookups, one-off issue queries, `sonar` CLI use, linking a project, Automatic Analysis and `.sonarcloud.properties`. It produces no record, decides no finding and runs no write |
| `using-codecov` | Answers ad hoc coverage and Codecov questions (totals, a PR's patch coverage, why coverage dropped), runs the coverage tier locally, and sets up Codecov plus the tier check in any repository. It uploads nothing and changes no Codecov setting |
| `running-mutation-tests` | Picks a module and its test selection, has the `mutation-tester` agent run mutmut in an isolated copy of the working tree, explains the score, and proposes a test or a `# pragma: no mutate` with a reason for each survivor, written only after approval |

| Agent | What it does |
|---|---|
| `mutation-tester` | Copies the working tree to a scratch directory outside the repository, runs `scripts/qlty-mutation-run.py` and `scripts/qlty-mutation-parse.py` there, confirms the repository is unchanged, and returns a digest. Edits no source and writes no tests |

`resolving-analysis-findings` may call `collecting-analysis-findings`; the reverse never happens.

## Boundaries

- **Policy and records only.** Configuring Codacy as a project (tools, patterns, coverage) is outside this
  plugin; the external `codacy-skills` plugin covers that. This plugin does not depend on it and works
  without it. Self-managed SonarQube is out of scope.
- **One provider per run.** A Sonar run never edits `.codacy.yml` or runs `codacy`, and the reverse.
- **Remote writes are gated.** Ignoring, unignoring or reanalyzing through the Cloud CLI, a Sonar issue
  transition, and any change to `.codacy.yml` exclusions, needs an explicit approval each time; a pattern or
  quality-gate change, a Sonar path exclusion (a UI setting), and the bulk forms, are handed to you as an exact
  command or setting and never run by the skills.
- **No Codacy command is pre-approved.** The Codacy CLIs have write flags that a tool grant cannot narrow,
  so every `codacy` and `codacy-analysis` command raises a normal permission prompt showing its text, unless your
  own settings or permission mode already allow it. Approve
  each one once. Never choose "don't ask again" or add a `codacy` or `codacy-analysis` allow rule: that would
  pre-approve the write flags too. For `sonar`, no command is pre-approved directly: the read skills grant only `scripts/qlty-sonar-read.py` (plugin root), a wrapper
  that runs fixed reads from a fresh, empty temporary directory and drops identity fields. `sonar api post` shares a
  prefix with `sonar api get`, so a direct `sonar api` command always prompts.
- **Coverage is not a finding.** `using-codecov` has no record and no ladder. Its tier (green, yellow, orange,
  red on patch coverage, thresholds in `assets/qlty-coverage-tiers.yml` with a per-repository
  `.github/coverage-tiers.yml` override) is computed from the repository's own report by
  `scripts/qlty-coverage-tier.py`, so a Codecov outage never changes it. Other repositories run a vendored copy
  of that script in CI, set up through the skill. Codecov reads go through `scripts/qlty-codecov-read.py`, which
  drops author and title fields and takes an optional `CODECOV_API_TOKEN`.
- **Mutation scores are data.** `running-mutation-tests` never gates a merge. The runner writes `mutants/` and a
  temporary `setup.cfg` only in the tree it runs in (the agent's export, or a CI checkout), and the parser refuses
  a result that disagrees with mutmut's own totals or holds an exit code outside mutmut 3.8.1's table. A mutant
  that no selected test ran is "not measured", never a survivor.
- **Repository-specific policy** (which findings this repository accepts, and where) lives in the repository's
  own `CLAUDE.md`, `AGENTS.md` and `docs/ci.md`, not here.

## Requirements

The Codacy Cloud CLI (`codacy`) authenticated for the repository, `gh` for the current PR, and Python 3
(standard library only; the smoke tests were run on 3.13, and no older version was tried). The local pre-PR
scan additionally needs `codacy-analysis` and a `.codacy/codacy.config.json`. For SonarQube Cloud, the `sonar`
CLI authenticated for the project; its pre-PR scan (`sonar analyze`) sends project files to Sonar, whose retention
period is undocumented, so it asks first. For coverage, `uv` (the tier script needs PyYAML and defusedxml and
runs as `uv run --no-project --no-config --with pyyaml==6.0.3 --with defusedxml==0.7.1`); Codecov reads need nothing for a public repository and a personal
`CODECOV_API_TOKEN` for a private one. For mutation testing, `uv` (mutmut and PyYAML come from
`uv run --with mutmut==3.8.1 --with pyyaml==6.0.3`) and the project's own test dependencies. mutmut needs
`fork`, so on Windows run it inside WSL: the runner exits 3 on native Windows.

## Language

**Python.** The plugin's scripts are Python, standard library only, except `scripts/qlty-coverage-tier.py`,
which needs PyYAML for its thresholds files and defusedxml for a Cobertura report, and exits 3 with a message
when either is missing. The adapters run no subprocess: each reads
the JSON a provider's CLI already printed. The one production subprocess is `scripts/qlty-sonar-read.py`, which runs
the `sonar` CLI, plus `scripts/qlty-mutation-run.py`, which runs pytest and mutmut (fixed argument lists, no shell) in the tree it is given; the smoke tests also start the adapters and a stub `sonar`. New scripts added to this plugin stay in Python.

## Install

```text
/plugin install quality-kit@andres-cc-marketplace
```

## Usage

Ask in plain words; each skill activates on its own trigger phrases:

- "list the Codacy findings for this PR" runs `collecting-analysis-findings`. Add a PR number, `repo` (the
  default branch's security list) or `ignored` (what is already ignored, with reasons) to pick the source.
- "the Codacy check failed on my PR" or "should I ignore this Codacy finding" runs
  `resolving-analysis-findings`, which collects the findings itself and walks the ladder.
- "collect the Sonar findings for this PR" or "the Sonar check failed on my PR" run the same two skills against
  SonarQube Cloud.
- "what is the Sonar quality gate on main" or "how do I link a project to Sonar" runs `using-sonarqube-cloud`.
- "what's the patch coverage on this PR", "which coverage tier will my branch get" or "set up Codecov" runs
  `using-codecov`.
- "run mutation tests on pr_policy" or "why did this mutant survive" runs `running-mutation-tests`.

## Test

From the plugin root (`plugins/quality-kit/`), each skill owns its smoke test:

```text
python3 -I -B skills/collecting-analysis-findings/scripts/smoke_test.py
python3 -I -B skills/resolving-analysis-findings/scripts/smoke_test.py
uv run --no-project --no-config --with pyyaml==6.0.3 --with defusedxml==0.7.1 python -I -B skills/using-codecov/scripts/smoke_test.py
uv run --no-project --no-config --with pyyaml==6.0.3 python -I -B skills/running-mutation-tests/scripts/smoke_test.py
```

`-B` matters: `-I` ignores `PYTHONDONTWRITEBYTECODE`, and a stray `.pyc` fails this repository's pre-push
prefix check. In this repository, `tests/test_quality_kit_smoke.py` also runs all four under pytest, so the
coverage workflow measures the plugin's scripts.

## License

Apache-2.0, see [`LICENSE`](./LICENSE).
