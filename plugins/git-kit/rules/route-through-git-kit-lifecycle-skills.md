# Route Git Operations Through git-kit's Lifecycle Skills

## When this applies

Any git or GitHub operation in this repo that corresponds to one of git-kit's six lifecycle skills:
starting a new branch or worktree, committing, opening a PR, reviewing/commenting on a PR, merging a PR,
or syncing back to `main` after a merge.

## Rule

Use the matching lifecycle skill instead of the equivalent raw command, in this order:

```
starting-work → commit → create-pr / collaborating-on-a-pr → merge-pr → finishing-work
```

- **Starting new work** → `Skill(starting-work)` — syncs `main`, validates the branch name, asks
  worktree vs. plain branch.
- **Committing** → `Skill(commit)` — staging review, sensitive-file scan, message confirmation.
- **Opening a PR** → `Skill(create-pr)`, or `Skill(collaborating-on-a-pr)` when an issue
  should be linked.
- **Reviewing a PR** (approve/comment/request changes) → `Skill(collaborating-on-a-pr)` — adds
  CODEOWNERS context `gh-operations`' raw reference commands don't.
- **Merging** → `Skill(merge-pr)` — readiness and merge-rights checks before merging.
- **Cleaning up after a merge** → `Skill(finishing-work)`, which hands off to `/git-cleanup` for
  the actual branch/worktree deletion.

**Dispatch-name form: use the bare skill name, not a `git-kit:`-scoped one.** In this repo's own dev
sessions, git-kit's skills are exposed via the `.claude/`-mirrored copy under their bare name (e.g.
`starting-work`), not under a `git-kit:` namespace prefix — verified live (issue #367): `Skill(commit)`
resolves; `Skill(git-kit:commit)` fails with `Unknown skill: git-kit:commit`. This mirrors how this repo's
own available-skills listing actually presents every one of this repo's own plugins' skills (unprefixed),
in contrast to genuinely externally-installed marketplace plugins in the same listing (`codex:`,
`coderabbit:`, etc.), which do carry a prefix. If a session's own available-skills listing shows a given
skill under a `plugin:` prefix instead (e.g. an external install of git-kit with a naming collision against
another installed plugin), use that prefixed form instead — the form that actually appears in the current
session's own listing always wins over what's hardcoded here.

`git-kit`'s hard-block `PreToolUse` hooks enforce the raw-command bypass for `commit`, `create-pr`,
`merge-pr`, `starting-work`'s branch creation, `collaborating-on-a-pr`'s reviewer actions, and
`git-cleanup`'s destructive branch-delete/worktree-remove actions — this rule is the discoverable,
human-readable statement of that same chain, not a duplicate enforcement mechanism.

**The marker handshake is a policy guardrail, not a security boundary.** Each of these hooks checks for a
plaintext, unauthenticated marker file (guard-type + timestamp, no signature) that the allowlisted skill
writes immediately before running its guarded command. This stops *accidental* bypass — forgetting to go
through the matching skill — but not a *deliberately adversarial* agent, which could write the same
marker string via a second raw command and satisfy the check without ever running the skill. Treat the
hooks as guardrails against habit and mistake, not as proof that a guarded command actually came from the
skill that's supposed to own it.

**`Skill()` output isn't proof of currency for an unmerged worktree edit.** A `Skill(<name>)`
dispatch (bare name — see the dispatch-name form above) always resolves to the primary checkout's own
`.claude/`-mirrored copy of that skill — never a session's own worktree, even when the current session
just edited that exact skill's `SKILL.md` inside an unmerged worktree. Dispatching the skill by name
after such an edit silently runs the *old*, pre-edit instructions, with no error at any layer — the
returned output looks completely normal, so the staleness is invisible unless the reader happens to
notice the missing logic. This has independently reproduced twice in this repo's own history: treat a
`Skill()` dispatch as authoritative only when the skill being called hasn't itself been edited in an
unmerged worktree this session; otherwise, read the worktree's own current file directly instead of
dispatching, or merge the worktree's change first.

**Never silently substitute a manual reimplementation for a failed or skipped dispatch.** If a
`Skill()` call to one of these six lifecycle skills errors (e.g. `Unknown skill: ...`), or if a task
squarely inside one of their documented "When to Use" lists is about to proceed via raw `git`/`gh`
commands instead of the skill, stop and report the dispatch failure or the decision to skip it to the
user — never fall back to manually narrating or reimplementing the skill's own documented procedure
(marker handshakes, staging review, round/dedup budgets, reply-then-resolve discipline) as a silent
substitute. A hand-rolled reimplementation looks identical in its own output to a real dispatch but
skips whatever safeguard the skill exists to enforce, with nothing here or in the guard hooks below
able to tell the difference after the fact (issue #367).

**The marker-handshake guard can be hand-satisfied without the guarded skill running at all** — writing
`git-write-marker.sh`'s marker file directly, then issuing the raw command it's meant to gate,
passes the guard exactly as if the skill itself had run (issue #165). This is the same class of gap as
the paragraph above, one level lower: even a dispatch that *did* happen can still have been faked at the
marker level. Both gaps share the same root cause — the guard only checks for a signal a real dispatch
happens to leave behind, not that the dispatch itself occurred — and share the same accepted mitigation:
this rule's own explicit disclosure, not a stronger mechanical check, since neither the hook nor this
skill's own instructions can observe whether a `Skill()` call actually ran from inside the shell
environment a marker script executes in.

**Verified (2026-09-26, issues #401/#403/#406):** the guard scripts check only the marker's guard-type
and freshness — the skill-name field `git-write-marker.sh` writes is never itself validated against an
allowlist, so "the five/six allowlisted skills" named throughout this file is a documentary convention,
not a code-enforced one. This also rules out the specific stronger-binding idea issue #165 originally
proposed (binding the marker to a process/session identifier): a hand-invocation of the marker script
happens from within the *same* session a real `Skill()` dispatch would also run in, so session/process
identity can't distinguish the two cases either. Issue #406 tracks whether any real enforcement
mechanism is feasible at all under Claude Code's current hook/tool-execution model; until it resolves
that question, this section's "policy guardrail, not a security boundary" framing is the accurate
characterization of what this mechanism currently provides — not an interim state pending a fix
already in progress.

## Why

Each of these six skills exists because the equivalent raw command is missing something the skill adds
(sync-before-branch, sensitive-file scanning, CODEOWNERS context, merge-rights verification, cleanup
hand-off) — using the raw command silently skips that safeguard. Without a single place stating the full
chain, each individual skill's own cross-references only cover its immediate neighbors, and the seams
between non-adjacent skills (e.g. why a review action shouldn't go through `gh-operations`) tend to stay
undocumented until a specific gap is noticed and patched one skill at a time.
