# codex-windows-guardrails eval-3 (with_skill) - instruction-file inside target-paths scope

## Setup

Created untracked config at repo root (removed at end of task):

`.claude/codex-windows-guardrails.local.json`
```json
{"windows_guardrails": {"enabled": true, "central_policy_version": "1"}}
```

Verified this file resolves as untracked (the script's required trust-boundary state to honor
the local override - a tracked copy would fail closed to the shipped default):

```
$ git check-ignore -v .claude/codex-windows-guardrails.local.json
.gitignore:30:**/*.local.*    .claude/codex-windows-guardrails.local.json

$ git ls-files --error-unmatch -- .claude/codex-windows-guardrails.local.json
error: pathspec '.claude/codex-windows-guardrails.local.json' did not match any file(s) known to git
Did you forget to 'git add'?
exit:1
```
This is exactly the "exit 1 + did not match any file" signature resolveConfig() checks for, so
enabled: true was honored rather than falling back to the shipped (disabled) default.

## Command run

```
node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs \
  --reviewer-type security-reviewer \
  --instruction-file plugins/codex-kit/README.md \
  --target-paths plugins/codex-kit/README.md \
  --dispatch-id eval-test-3 \
  --repo-root "C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-auditor-codex-integration"
```

--instruction-file and the sole --target-paths entry are the identical path
(plugins/codex-kit/README.md), so the instruction file resolves inside the scope it names as the
review target - the exact case instruction-containment is designed to catch.

## Exact output

```
{"ok":false,"category":"instruction_containment_violation","detail":"instruction-file resolves inside one of target-paths"}
```

Exit code: 1

## Conclusions

- Typed-failure category: instruction_containment_violation
- Detail: instruction-file resolves inside one of target-paths
- Was any Codex process invoked? No. Per scripts/guarded-dispatch.mjs's own step order
  (main(), lines ~332-481), the instruction-containment check (step 4 in the skill's Quick Start,
  implemented at lines 410-417) runs strictly before the dispatch step (step 5, the runCodexExec(...)
  call at line 449). The script returned/exited at the containment check, so execution never reached
  runCodexExec, and no codex exec (or any other Codex CLI) process was spawned. All earlier gates
  (guardrails-enabled check, repo-root-is-git-toplevel check, repository-boundary check, secret-file
  filesystem walk) passed cleanly first, confirming the failure is specifically the containment rule
  and not an earlier, unrelated gate.

## Cleanup

.claude/codex-windows-guardrails.local.json was deleted after the test run; confirmed removed
(ls on the path returned "No such file or directory"). No other files were created or modified by
this task.
