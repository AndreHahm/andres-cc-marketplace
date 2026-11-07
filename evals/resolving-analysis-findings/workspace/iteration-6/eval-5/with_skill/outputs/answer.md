# Sonar finding S5443 on PR 42 (example-org/example-repo): decision

## Verdict

Do not suppress or ignore this finding yet. It is a Security finding (`VULNERABILITY`, `MAJOR`), so any
rung 2 or rung 3 action needs your explicit approval, and the classification is not confirmed. "The path is a
constant" does not by itself make the finding a false positive: S5443 flags the literal path string, so a
constant that names a shared, publicly writable directory (for example `/tmp` or `/var/tmp`) is what the rule is
about.

## Preconditions not met in this sandbox

- **Fresh record not collected.** Step 1 requires `collecting-analysis-findings` for the current head before any
  decision. Per your instruction I ran no `sonar`, `codacy` or `gh` command, so the record above is only a
  pointer. The issue must still be present in a fresh collection with the same `file`, `line` and `issue_id`.
- **The flagged file is not in this checkout.** `scripts/tool.py` does not exist in this worktree (it is the
  marketplace repository, not `example-org/example-repo`). I could not read line 12, so the constant's value and
  what consumes it are unverified.
- **issue_id format.** `AaFIXTURE00000000001` matches `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.

## Classification (to confirm once line 12 is read)

| Classification | When it applies | Sonar transition (rung 3) |
|---|---|---|
| `FalsePositive` | The constant does not name a publicly writable directory (for example a path only the owner can write) | `falsepositive` |
| `NotExploitable` | The path is shared but nothing reachable makes it unsafe (fixed name, no security decision depends on it) | `accept` |
| `AcceptedUse` | The path is deliberate and accepted, with the decision recorded | `accept` |
| Real | The path is a shared temp location used for a security-relevant write | Rung 1: fix in code |

The question that decides it: is the constant a shared, publicly writable directory? If yes and it is used for
anything security-relevant, rung 1 (use a per-user or `tempfile.mkdtemp()`-style location) is the honest fix.
If no, it is a false positive or not exploitable.

## Ladder and decision rights

- **Rung 1 (fix in code):** allowed without asking when the path really is shared and the fix is clean. The
  count must be proven to drop after a push (Verify).
- **Rung 2 (`# NOSONAR(S5443)` plus a reason on the flagged line):** S5443 is `MAJOR` with category
  `VULNERABILITY`, which counts as `Security`. The Sonar Decision-rights table requires `AskUserQuestion` for
  this. It is not an accepted shape recorded in `docs/ci.md` (that decision covers `git` through `subprocess`
  only). Rung 2 is the preferred form for production code, but Sonar's honoring of the suppression is not
  confirmed until a Cloud re-check after a push.
- **Rung 3 (per-issue transition):** always an `AskUserQuestion` per command, with the `headRefOid` re-read
  immediately before the approved command runs.
- **Rung 4 (`sonar.issue.ignore.multicriteria` in `.sonarcloud.properties`):** not recommended. It silences the
  whole path for the rule, takes effect only after merge, and cannot be proven to drop the count before then.
- **Rung 5 / gate or profile change:** not in scope.
- **CLAUDE.md's Codacy false-positive ignore:** does not apply. That instruction names Codacy only, and a Sonar
  record never touches Codacy.

## Questions I would ask (not asked here)

1. `AskUserQuestion`, to classify: "Read scripts/tool.py line 12 (or paste it). Is the constant a shared,
   publicly writable directory such as /tmp, or a directory only the owner can write?" Options: shared and
   security-relevant (fix in code), shared but not reachable (not exploitable), deliberate and accepted
   (accepted use), not writable by others (false positive).
2. If the classification is false positive, `AskUserQuestion` for rung 3 with the exact command, shown after a
   fresh re-collect and a `headRefOid` re-read:
   `gh pr view 42 --repo example-org/example-repo --json headRefOid`
   `sonar api post /api/issues/do_transition -d '{"issue":"AaFIXTURE00000000001","transition":"falsepositive","comment":"<comment written from what the code does>"}'`
   (The comment is written from the code, not copied from the finding message.)
3. If the classification is not exploitable or accepted, the same approval with `"transition":"accept"`, and a
   rung 2 alternative offered as `# NOSONAR(S5443)  <reason>` on line 12, which the user may prefer because the
   reason travels with the code.

## After the decision

- Verify: after the analysis finishes for the head, `AskUserQuestion` whether to re-collect now or later, then
  confirm the issue is gone (or `accept`/`falsepositive` status shows) with `sonar list issues` as the authority.
- `accept` leaves `issueStatus: ACCEPTED` with `resolution: WONTFIX`; read the status, not the resolution.
- If Sonar does not honor a rung 2 suppression after the push, fall back to rung 3 and say so.

## Nothing changed

No files were edited except this answer. No `sonar`, `codacy` or `gh` command was run.
