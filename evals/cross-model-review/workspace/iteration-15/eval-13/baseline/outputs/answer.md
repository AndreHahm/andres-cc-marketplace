# What the (baseline) cross-model-review skill has you do after the EnterWorktree refusal

Source read: the `plugins/git-kit/skills/cross-model-review/` copy given for this run (SKILL.md,
`references/codex-pass-assembly.md`, `references/scoped-review.md`, and grep across the other references).

## Short answer

This version of the skill **does not cover this situation**. It has no mention of `EnterWorktree`, of
Claude Code's "too complex to verify that it stays inside the worktree" refusal, of a script-file form
of the Preflight, or of the session scratchpad directory. So it gives no instruction to write anything,
anywhere, to work around the refusal. What it does say, applied literally, leads to **stop and report**,
not to an improvised alternative.

## Item by item

**What you write, where, with which tool.** Nothing. The skill only defines one Preflight form: "Run
steps 1-6 below as a single chained Bash invocation (`&&` between them, one tool call)" (SKILL.md,
Preflight). It names no alternative form, such as a script file. It also says outright: "**This skill has
no `Write` grant**" (it cannot be limited to a path). Every file the model writes must go through
`scripts/git-review-write-run-file.sh` into `$RUN`, and "Never write to any path inside the repository
itself". `$RUN` does not exist yet, because the refused chain is what creates it (`RUN=$(mktemp -d)`).
So the skill gives no sanctioned way to write a Preflight script file before the Preflight runs.

**What the file may and may not contain.** Not specified, because no such file exists in this version.

**What you show the user.** The skill doesn't say to show a script. The only user-facing steps it
defines around Preflight are its `AskUserQuestion` gates: `PLANNER_TOUCHED`, a missing prompt on
`$BASE`, `PLAN_FAILED`, and the First-Send Confirmation. Here you report the refusal: Claude Code
refused the chained Preflight, and the skill documents no other form.

**How and from where you run it.** The chain runs from the checkout (work tree) root. The planner
wrapper exits 2 from a subdirectory (`references/scoped-review.md` section 1). In this repo's sessions,
`${CLAUDE_PLUGIN_ROOT:-.claude}` resolves to the `.claude/` mirror scripts, which are deliberately
ungranted and so raise a permission prompt. It names no alternative way to run.

**What one approval of that run covers.** The skill defines no single approval for a Preflight script.
The only "one answer covers all of them" approval is the First-Send Confirmation for the Codex
dispatches: two per batch that has eligible paths, plus a possible timeout retry per batch. It does not
cover Preflight.

**The PLANNER_TOUCHED stop.** This diff edits `skills/cross-model-review/`, so the grep at the top of the
Inputs block sets `PLANNER_TOUCHED=1`. The chain then prints `PLANNER_TOUCHED=1: ask the user first`
and exits 0 before `mktemp`, the index helper or the planner run. You then ask through
`AskUserQuestion` whether to run the working-tree review scripts anyway. They execute code from the
branch under review with your permissions and no sandbox. The other choice is to stop. Only an explicit
yes re-runs the **whole** chain, unchanged, with `PLANNER_APPROVED=1` set first. Record the choice in
`inspection_limits` and disclose it again at the First-Send Confirmation (clause (c)). The catch: in
this scenario the chain never ran at all, so the refusal comes before this stop. Even after a yes, the
re-run is the same chained command, and Claude Code would refuse it again for the same reason.

**How a Write permission prompt should be answered.** Not addressed. The skill only has guidance for
the Codex fallback script's permission prompt: don't choose "don't ask again", and an unanswerable
question counts as declined. It has none for a `Write` prompt, because it never uses `Write`.

**No scratchpad directory / the new form also refused.** Not addressed. The closest general rule is in
`references/codex-pass-assembly.md`: a write helper's refusal is a failed write, "stop and report it,
never fall back to another way of writing the file". The resolver section also says "never ... ad hoc".
Applied to this case, if the only documented Preflight form is refused, stop, report the refusal to the
user, and don't hand-build a substitute such as split calls or a self-authored script.

## Net procedure under this version

1. Don't retry the chain in pieces. Bash calls share no shell state, and the skill requires a single
   call. Don't write a script file: there is no `Write` grant, and no write location before `$RUN` exists.
2. Report to the user that Claude Code refused the Preflight in the EnterWorktree-isolated session, and
   that this skill version documents no workaround.
3. Offer, through `AskUserQuestion`, either to stop, or for the user to run the review from a session
   that isn't EnterWorktree-isolated (for example one started in the worktree directory itself). There,
   the chain hits the `PLANNER_TOUCHED` stop and its yes/stop question as described above.
