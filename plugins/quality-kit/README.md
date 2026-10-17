# quality-kit

A default strategy for resolving static-analysis findings, so a failing check is decided once, by one
procedure, with the reason recorded. Codacy is the first and only verified provider; the structure leaves
room for others (see `skills/collecting-analysis-findings/references/adapter-contract.md`).

**Status: 1.0.0-alpha.1.** Built from issue #581, where the same Bandit rules on `git` subprocess calls were
handled three different ways across this repository.

## Skills

| Skill | What it does |
|---|---|
| `collecting-analysis-findings` | Reads a PR's, a repository's or the already-ignored findings from Codacy's Cloud CLI output and writes one provider-neutral record, grouped by rule and file, with a check that the analysis is current for the PR head. Read-only |
| `resolving-analysis-findings` | Decides each finding's outcome on a five-rung ladder (fix, inline suppression, per-issue ignore, `exclude_paths`, pattern or gate change), with decision rights, required reasons, baseline versus new, verification after push, a local pre-PR scan and an author checklist |

`resolving-analysis-findings` may call `collecting-analysis-findings`; the reverse never happens.

## Boundaries

- **Policy and records only.** Configuring Codacy as a project (tools, patterns, coverage) is outside this
  plugin; the external `codacy-skills` plugin covers that. This plugin does not depend on it and works
  without it.
- **Remote writes are gated.** Ignoring, unignoring or reanalyzing through the Cloud CLI, and any change to
  `.codacy.yml` exclusions, a pattern or the quality gate, needs an explicit approval each time.
- **Repository-specific policy** (which findings this repository accepts, and where) lives in the repository's
  own `CLAUDE.md`, `AGENTS.md` and `docs/ci.md`, not here.

## Requirements

The Codacy Cloud CLI (`codacy`) authenticated for the repository, `gh` for the current PR, and Python 3.11 or
newer. The local pre-PR scan additionally needs `codacy-analysis` and a `.codacy/codacy.config.json`.

## Language

**Python.** The plugin's scripts are Python, standard library only, and run no subprocess: the adapter reads
a JSON file the Cloud CLI already wrote. New scripts added to this plugin stay in Python.

## Install

```text
/plugin install quality-kit@andres-cc-marketplace
```

## Test

Each skill owns its smoke test:

```text
python3 -I -B skills/collecting-analysis-findings/scripts/smoke_test.py
python3 -I -B skills/resolving-analysis-findings/scripts/smoke_test.py
```

`-B` matters: `-I` ignores `PYTHONDONTWRITEBYTECODE`, and a stray `.pyc` fails this repository's pre-push
prefix check.
