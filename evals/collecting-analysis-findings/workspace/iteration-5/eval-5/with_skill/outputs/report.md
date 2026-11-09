# Sonar findings collection: example_project PR 651 (skill test, eval 5)

## Commands run, in order

1. Read `plugins/quality-kit/skills/collecting-analysis-findings/SKILL.md` (Read tool), then `references/sonar-adapter.md`.
2. `ls -la` of `scripts/fixtures/sonar/`; `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/collect_sonar.py --help`.
3. `mkdir -p -m 700` and `chmod 700` on `<scratchpad>/eval-col-5/`; `ls -ld` to confirm mode drwx------.
4. Inspected the head of `pr-list.json` and `pr.json` (`head -c`).
5. `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/collect_sonar.py --kind pr-status --project example_project --pull-request 651 --input - --output <scratchpad>/eval-col-5/sonar-status.json < scripts/fixtures/sonar/pr-list.json` (exit 0)
6. `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/collect_sonar.py --kind pr --project example_project --status <scratchpad>/eval-col-5/sonar-status.json --input - --output <scratchpad>/eval-col-5/findings-record.json < scripts/fixtures/sonar/pr.json` (exit 0, 3 findings)
7. `PYTHONDONTWRITEBYTECODE=1 python3 -I scripts/collect_sonar.py --kind pr-status --project example_project --pull-request 651 --confirm <scratchpad>/eval-col-5/findings-record.json --input - --output <scratchpad>/eval-col-5/findings-record.json < scripts/fixtures/sonar/pr-list.json` (exit 0, snapshot consistent)
8. Read `<scratchpad>/eval-col-5/findings-record.json` (Read/cat).
9. `mkdir -p` the outputs directory, `cp` the record into it, and wrote this report.

No `gh`, `sonar`, or other network command was run. No repository file was edited.

## Result

- Provider: SonarQube Cloud, project `example_project`, PR 651.
- Findings: 3, all `shell:S7688` (CODE_SMELL, MAJOR), all in `.claude/hooks/dck-session-context.sh` at lines 8, 9 and 15. Message text not reproduced.
- Quality gate: OK. Analysis date 2026-11-07T06:52:54+0000.
- Currency: the record's `head_commit_sha` (1111...1111) equals the GitHub head you gave (1111...1111). `is_analysing` is null (Sonar has no running flag), so the SHA comparison decides: the counts are current for that head.
- `snapshot_consistent`: true, but see caveat.

## Caveats

- The fixture set has one `pr-list.json`, so the third (confirm) pipe re-read the same saved file rather than a live read. The `true` value only shows the two pipes agree on this saved data; it does not show a live re-analysis did not land between reads. Treat it as not verified live.
- The head SHA came from your message, not from `gh pr view` (which was not run).
- Record path: `<scratchpad>/eval-col-5/findings-record.json`; copy at the outputs directory above.
