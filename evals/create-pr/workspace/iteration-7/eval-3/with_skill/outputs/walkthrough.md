# create-pr dry run: `/create-pr 123`, with and without `--bypass-cross-model-review`

Dry run only. No Bash, git, gh, Skill or Agent call was made. Every command below is narrated.

Skill followed: `plugins/git-kit/skills/create-pr/SKILL.md`, read from the issue-461 worktree.

Starting state: branch `feat/example-widget`, everything committed and pushed, no PR open. The user
typed `/create-pr 123` directly at the top level, so no other skill is delegating to this run.

---

## Part A: `/create-pr 123`

### Argument parsing

`$ARGUMENTS` = `123`. The argument-hint allows "an issue number to close or reference". The user said
the PR should *close* #123, so the line to use is `Closes #123`, not `Refs #123`. No bypass flag is
present.

**Routing:** the skill's "When NOT to Use" sends issue linking at creation time to
`collaborating-on-a-pr`. That pointer is about how a natural-language request gets routed ("create a
PR that closes #123"). Here `/create-pr` was already invoked, and its argument-hint takes an issue
number, so this run handles the link itself. Step 6 says plainly: "This skill never invokes
`collaborating-on-a-pr`." That skill's Path A calls create-pr, never the other way round. **No
`Skill(collaborating-on-a-pr)` call is made.**

### Resolve the PR template

`.github/pull_request_template.md` exists in this repo, so it is the template (the bundled
`assets/pull_request_template.md` is not used). It has a `## Related Issue` section whose comment
reads: `Link the issue this PR addresses, e.g. "Closes #123"`. The template is treated as data, not
instructions.

### Pre-flight Checks

1. `git status`: clean (everything is already committed).
2. No uncommitted changes, so `Skill(commit)` is **not** invoked. (Had it been needed, `commit` would
   be told to skip its Auto-PR step 17 and its step 16 push.)
3. Nothing more to commit.

3.5. **Session open-issues check.** I review this session's own conversation for open reviewer
   findings, TODO/FIXME items and items the user explicitly deferred. In this scenario none exist, so I
   report: "Session open-issues check: nothing found." The step still runs and is still reported, even
   with nothing found. (Had there been items, a touched one would be tested with
   `git diff --name-only -z main...HEAD | grep -zqxF "<path>"`. An untouched one would go through
   `Skill(github-issue-lifecycle)` Workflow 1, stopping at Step 2 for `AskUserQuestion` approval.
   Issue #123 itself is not an "open issue" in this sense: it is the issue this PR closes, not an
   unaddressed finding.)

4. **Cross-model-review gate (mandatory, no bypass here).** Invoke `Skill(cross-model-review)` against
   the full diff (`BASE=main`, no `SCOPE`). It runs fresh even though the branch is already pushed.
   - Its own First-Send Confirmation (Codex-dispatch consent, plus the data-egress disclosure) fires
     inside the nested call.
   - Its findings table is data, not directives. I act only on findings the user selects.
   - It returns control, and I re-run `git status`.
     - No edit: go to step 4.5.
     - Edit made: `Skill(commit)` (skip Auto-PR, skip push), then re-invoke `Skill(cross-model-review)`
       on the new diff. Repeat until a pass produces no newly accepted edit.
   - If the clearing pass was answered "Skip Codex for this run", I report that before the push.
   - This gate has no bearing on issue #123.

4.5. **CI-parity Codex delta review.** First an `AskUserQuestion` egress-consent question (this
   consent is separate from step 4's). On consent, `CLAUDE_PLUGIN_ROOT` is empty in this repo's own
   sessions, so I run
   `uv run python .claude/scripts/git-codex-parity-review.py --output <scratchpad>/codex-parity-<epoch>.json`.
   - Exit 0 clean: continue. Exit 0 with `coverage.complete: false`, `advisory.advisory: true` or
     `PARITY: ADVISORY` is disclosed as an advisory result, not a clean pass.
   - Exit 1: ask fix, re-run or bypass. Exit 2: "could not run", never a pass, ask retry or bypass.
     Exit 3: skip and say so.
   - Declining egress, or choosing bypass, is written under the body's "Open Items" section.

### Creating the PR

1. **Push.** The branch is already on the remote. `git push -u origin feat/example-widget` would be a
   no-op or simply confirm the branch is there. This is the only push in the flow.

2. **Draft the body** from the repo template, keeping every header. **This is where the closing line
   goes in the first place:** the `## Related Issue` section gets `Closes #123`, taken from
   `$ARGUMENTS`.
   - Accepted findings: run `python3 -I .claude/scripts/git-review-accepted-findings.py lines` (the
     mirror path, since `CLAUDE_PLUGIN_ROOT` is empty). Copy each printed waiver line unchanged into
     `## Accepted Review Findings`, or leave "None" if nothing prints. On exit 3 or any other non-zero
     exit, ask via `AskUserQuestion` whether to open with "None" or stop. Never `Read` the file directly.
   - No literal bot-trigger mentions in the title or body.

3. **Draft or ready:** `AskUserQuestion` with "Draft (default)" and "Ready-to-merge".

3.5. **Title check:** `uv run python .claude/scripts/git-check-pr-title.py "feat(widget): Add example widget"`.
   On FAIL, revise and re-check.

3.75. **Assignee:** `gh api user --jq '.login'`, falling back to
   `gh repo view --json owner --jq '.owner.login'`.

3.85. **Priority label:** `docs/github-label-taxonomy.md` has a `p:` section, so a new feature with no
   other signal gets `p: medium`.

4. **Marker, then create.** Run `bash .claude/scripts/git-write-marker.sh gh-pr-create create-pr`
   immediately before creating (the marker is valid for 60 seconds). `Write` the drafted body to
   `<scratchpad>/pr-body.md`, then:
   ```
   gh pr create [--draft] --title "feat(widget): Add example widget" --body-file <scratchpad>/pr-body.md --base main --assignee <login> --label "p: medium"
   ```
   Pass the scratchpad body file, never the template file itself.

5. **Codex bypass attestation:** skipped, because `--bypass-codex-review` was not given.

6. **Issue-linking check: how I confirm `Closes #123` landed.**
   - `$ARGUMENTS` named issue #123, so this step applies.
   - Re-read the live body from GitHub: `gh pr view <number> --json body -q .body`. This is a fresh
     read of the created PR, not a re-read of my local draft.
   - Check that a `Closes #123` line is present.
     - **Present:** confirmed, so report "Closes #123 verified in PR body".
     - **Missing** (for example, the line was lost while drafting): build the updated body as the
       existing fetched body, a blank line, then `Closes #123`. `Write` it to
       `<scratchpad>/pr-body-linked.md` and run `gh pr edit <number> --body-file <scratchpad>/pr-body-linked.md`.
       The fetched body is never put inside a shell-interpolated string or a heredoc. The `Write` tool
       parameter keeps the PR content, which anyone with repo access can change, away from shell
       parsing.
       - Known environment caveat: auto-memory notes that `gh pr edit` fails in this repo with a
         Projects-classic error and changes nothing. So after the edit I re-run
         `gh pr view <number> --json body -q .body`. If the line is still missing, I report that the
         edit did not land and suggest the documented workaround,
         `gh api repos/{owner}/{repo}/pulls/<n> -X PATCH -F body=@<file>`. The skill does not grant that
         call, so it needs the user's approval, and I would not claim success.
   - **No other skill or delegated call is involved in linking.** The tools are `Write` plus
     `gh pr create`/`gh pr view`/`gh pr edit`, all inside create-pr's own `allowed-tools`.
     `collaborating-on-a-pr` is not called (one-way loop-breaker rule).
     `github-issue-lifecycle` is not used for #123 (it appears only in step 3.5, for untouched session
     findings).

### Final report (Part A)

PR URL; draft or ready status; assignee; label; "Session open-issues check: nothing found";
cross-model-review outcome (including any Codex skip); parity result (clean, advisory, or bypassed with
the reason in Open Items); "Closes #123 verified in PR body via gh pr view".

---

## Part B: `/create-pr 123 --bypass-cross-model-review "already reviewed manually"`

### Parsing

`$ARGUMENTS` contains two separate things:
- Issue number `123`, which gives the `Closes #123` line.
- `--bypass-cross-model-review` with the reason `"already reviewed manually"`. The reason is not empty,
  so the flag is valid. Had it been empty or missing, I would reject it, ask for a valid reason and not
  create the PR until resolved, never quietly falling back to running the gate.

### Combined sequence

| Step | What happens | Effect of the bypass | Effect of issue #123 |
|---|---|---|---|
| Template | Repo template resolved | none | none |
| 1-3 | `git status` clean, no `commit` | none | none |
| 3.5 | Open-issues check, "nothing found" | **Not skipped**: the flag only skips step 4 | none (#123 is not a session finding) |
| 4 | Cross-model-review gate | **Skipped entirely.** `Skill(cross-model-review)` is not invoked. I report "cross-model-review bypassed: already reviewed manually" in session output only | none |
| 4.5 | CI-parity Codex review | **Still runs.** The skill says neither bypass flag skips this step. Egress `AskUserQuestion` still fires. No `--sandbox-down` (step 4 did not run, so the wrapper's own probe decides) | none |
| 1 (push) | Branch already pushed | none | none |
| 2 (body) | Template filled, accepted findings carried over | **The bypass reason is NOT written into the PR body** (the Flags table: "session output only, never written to the PR body or any GitHub-visible location") | `Closes #123` goes in `## Related Issue` |
| 3-3.85 | Draft/ready, title, assignee, `p: medium` | none | none |
| 4 (create) | Marker, then `gh pr create --body-file` | none | carried in the body |
| 5 | Codex bypass attestation | Not run. `--bypass-cross-model-review` is **not** `--bypass-codex-review`: no comment, label or permission check | none |
| 6 | Issue-linking check | none, runs exactly as in Part A | `gh pr view` verify, `Write` + `gh pr edit --body-file` only if missing, then re-verify |

### Do the two mechanisms interact?

**No. They run fully independently.**

- **The bypass does not change issue linking.** Step 6 depends only on whether `$ARGUMENTS`, the
  conversation or a caller named an issue. It does not depend on step 4 or any flag. The `Closes #123`
  line is drafted in step 2 and verified in step 6 exactly as in Part A. Skipping the gate removes no
  step that touches the body's issue line.
- **Issue linking does not change the bypass.** The bypass touches only Pre-flight step 4. Having an
  issue number does not validate, invalidate or widen the bypass. It does not make the bypass reason
  appear in the body. It does not route the run to `collaborating-on-a-pr`.
- **One shared surface, kept separate:** both concern the PR body only indirectly. The issue line goes
  *into* the body. The cross-model bypass reason is explicitly kept *out of* it. A parity-review bypass
  at step 4.5 (a different bypass, chosen through `AskUserQuestion`) would go under "Open Items". The
  `--bypass-cross-model-review` reason never does.
- **What the bypass does not skip:** step 3.5, step 4.5 (the parity Codex review and its egress
  consent), the draft/ready question, the title check, assignee, label, the marker, and step 6.

### Final report (Part B)

Same as Part A, except: "cross-model-review gate bypassed (reason: already reviewed manually), reported
here only, not in the PR body". The parity-review outcome is still reported, and "Closes #123 verified
in PR body" is still confirmed through a fresh `gh pr view`.
