# Sonar finding python:S1192 on scripts/helper.py line 30 (PR 43, example-org/example-repo)

## Decision

Take rung 1 (fix in code): extract the literal into a module-level constant named for what it means, replace every
occurrence of that literal in the file with the constant, and leave behavior unchanged. Do not suppress and do not
send a Sonar transition for this finding.

If you would rather keep the literal inline, the fallback is rung 2: `# NOSONAR(S1192)` plus a reason on the line
Sonar reports, decided and disclosed without an `AskUserQuestion` because the finding is `MINOR`, `CODE_SMELL`, not
`VULNERABILITY`. Do not use rung 3 (a `falsepositive` or `accept` transition): that is a remote write, it needs a
per-command approval, and the classification would be wrong, since S1192 is not a misreading of the code.

## Why rung 1

- The ladder says take the lowest honest rung. A constant with the same value removes the finding outright, changes
  no behavior, and needs no suppression that has to be maintained.
- "Nothing feeds it" answers a security question (is the literal reachable from untrusted input). It does not
  answer S1192, which is a maintainability rule about duplicated literals. The finding is not a `Security` finding,
  so the security reasoning does not decide the rung.
- "Deliberate" does not block the constant. A fixed value can be named once and reused; the value stays fixed.
- Classification: this is not `FalsePositive` (the rule does not misread the code) and not `NotExploitable` (that
  wording is for a real pattern with no reachable harm, which fits a security-style finding better). Those labels
  only matter at rung 2 as comment wording and at rung 3.

## What I would change

1. Re-check first. Before any edit, re-run `collecting-analysis-findings` for PR 43's current head and confirm the
   finding (`scripts/helper.py`, line 30, `AaFIXTURE00000000002`) is still in the fresh record (skill step 1).
   The record says `head current`, but the step is required before an edit.
2. In `scripts/helper.py`, count every occurrence of the duplicated string literal in the whole file, not only
   line 30. S1192 is a per-file duplication rule, so a constant that replaces only the flagged line can leave the
   other copies in place and the finding will still fire. Replace all occurrences in that file in the same change.
3. Add one module-level constant, named after the meaning of the value (not the value itself), placed with the
   file's other module-level names. Reference the constant at each former literal site.
4. Do not touch other files. Path check: `scripts/helper.py` is a relative in-repository path and passes the
   step-5 denylist.
5. Verify (skill Verify section): after the push, re-collect Sonar for PR 43 and confirm this finding is gone and no
   new `python:S1192` appeared on the file. If it did not drop, take rung 2 next and say why.

## What I could not check

- `scripts/helper.py` is not in this worktree (``),
  so I did not read line 30 or count the other occurrences. The file belongs to `example-org/example-repo` PR 43.
  I relied on your check that the literal is fixed and nothing feeds it. Before any edit, confirm the duplicate
  count in that repo's file, because it decides whether a constant alone removes the finding.
- The Sonar state was not re-read (no `sonar` or `gh` commands were run, as instructed). The record's `head current`
  is taken as given.
- Whether Sonar reports one issue per file or one per duplicate was not checked; the sibling sweep in step 2 covers
  either case.

## Nothing changed

No file was edited in the repository, and no Sonar, Codacy or GitHub command was run. The only write is this file.
