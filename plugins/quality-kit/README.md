# quality-kit

A default strategy for resolving static-analysis findings, so a failing check is decided once, by one
procedure, with the reason recorded. Codacy and SonarQube Cloud are the verified providers; the structure
leaves room for others (see `skills/collecting-analysis-findings/references/adapter-contract.md`).

**Status: 1.0.0-alpha.2.** Built from issue #581, where the same Bandit rules on `git` subprocess calls were
handled three different ways across this repository.

## Skills

| Skill | What it does |
|---|---|
| `collecting-analysis-findings` | Reads a PR's, a repository's or the already-ignored findings from Codacy's Cloud CLI or the `sonar` CLI output and writes one provider-neutral record, grouped by rule and file, with a check that the analysis is current for the PR head. Read-only |
| `resolving-analysis-findings` | Decides each finding's outcome on a five-rung ladder (fix, inline suppression, per-issue ignore or transition, path exclusion, pattern or gate change), with decision rights per provider, required reasons, baseline versus new, verification after push, a local pre-PR scan and an author checklist |
| `using-sonarqube-cloud` | Answers ad hoc SonarQube Cloud questions and walks through setup: quality gate lookups, one-off issue queries, `sonar` CLI use, linking a project, Automatic Analysis and `.sonarcloud.properties`. It produces no record, decides no finding and runs no write |

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
  pre-approve the write flags too. For `sonar`, no command is pre-approved directly: the read skills grant only `scripts/sonar_read.py`, a wrapper
  that runs fixed reads from the home directory and drops identity fields. `sonar api post` shares a
  prefix with `sonar api get`, so a direct `sonar api` command always prompts.
- **Repository-specific policy** (which findings this repository accepts, and where) lives in the repository's
  own `CLAUDE.md`, `AGENTS.md` and `docs/ci.md`, not here.

## Requirements

The Codacy Cloud CLI (`codacy`) authenticated for the repository, `gh` for the current PR, and Python 3
(standard library only; the smoke tests were run on 3.13, and no older version was tried). The local pre-PR
scan additionally needs `codacy-analysis` and a `.codacy/codacy.config.json`. For SonarQube Cloud, the `sonar`
CLI authenticated for the project; its pre-PR scan (`sonar analyze`) sends project files to Sonar, whose retention
period is undocumented, so it asks first.

## Language

**Python.** The plugin's scripts are Python, standard library only. The adapters run no subprocess: each reads
the JSON a provider's CLI already printed. Only a smoke test starts one, to exercise an adapter. New scripts added to this plugin stay in Python.

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

## Test

From the plugin root (`plugins/quality-kit/`), each skill owns its smoke test:

```text
python3 -I -B skills/collecting-analysis-findings/scripts/smoke_test.py
python3 -I -B skills/resolving-analysis-findings/scripts/smoke_test.py
```

`-B` matters: `-I` ignores `PYTHONDONTWRITEBYTECODE`, and a stray `.pyc` fails this repository's pre-push
prefix check.

## License

Apache-2.0, see [`LICENSE`](./LICENSE).
