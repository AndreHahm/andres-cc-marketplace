# What happens when `BASE=nonexistent-branch-xyz`

## Short answer

The skill treats this as a **Preflight failure**, not an empty diff. Preflight step 1 explicitly
names "an invalid `$BASE`" as an example of the non-zero-exit case: the run stops with a reported
Git error and a request for a valid `$BASE`, rather than being silently (or even loudly) reported as
"nothing to review." The skill's own text draws this distinction directly and unambiguously — it is
not something that has to be inferred.

## Walking through it

### 1. How `BASE` gets set to `nonexistent-branch-xyz` in the first place

Per **Inputs**: `BASE` is one of two optional inputs, defaulting to `main`, but resolved
conversationally "from what the invoking request actually says ... before Preflight step 1 runs"
(SKILL.md lines 52–61). So by the time Preflight step 1 executes, `BASE` is already bound to the
literal string `nonexistent-branch-xyz` — the **canonical diff command** built just above Preflight
(lines 63–72) is:

```bash
BASE="${BASE:-main}"          # BASE is already "nonexistent-branch-xyz", so this is a no-op
DIFF=(git diff "$BASE...HEAD")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")
```

which resolves to `git diff nonexistent-branch-xyz...HEAD`.

### 2. What Preflight step 1 does with that command

Preflight step 1 (lines 87–91) reads:

> "1. Run `"${DIFF[@]}"` and check its exit status. A non-zero exit (an invalid `$BASE`, no local
> `main` ref, or any other Git error) is a Preflight failure, not an empty scope — report the Git
> error and ask for a valid `$BASE` rather than silently treating it as "nothing to review." Only a
> successful command (exit 0) with empty stdout means the diff is genuinely empty: report "nothing
> to review against $BASE" (mention `$SCOPE` if set) and stop."

Since `nonexistent-branch-xyz` is not a ref that exists anywhere in the repository, `git diff
nonexistent-branch-xyz...HEAD` fails at the Git level (Git can't resolve the three-dot range because
one side of it doesn't resolve to a commit) and returns a **non-zero exit status**, with an error
message on stderr (something like `fatal: ambiguous argument 'nonexistent-branch-xyz...HEAD': unknown
revision or path not in the working tree`).

The skill's own wording is doing double duty here: it doesn't just say "non-zero exit is a Preflight
failure" in the abstract — it explicitly enumerates **"an invalid `$BASE`"** as one of the concrete
triggers for that branch, alongside "no local `main` ref" and "any other Git error." That is exactly
this scenario. So the required behavior is:

- Treat this as a **Preflight failure**, explicitly **not** as an empty scope/empty diff.
- **Report the Git error** to the user.
- **Ask for a valid `$BASE`**.
- Do **not** silently reinterpret the failure as "nothing to review."

Nothing downstream runs: this is Preflight step 1 of a chained, single Bash invocation covering steps
1–6 (per the Preflight section's lead-in, lines 79–85: "Run steps 1-6 below as a single chained Bash
invocation (`&&` between them, one tool call)"). A failure this early means the run never reaches
step 2 (target-path computation), step 3 (`$RUN` scratch dir), step 4/5 (`$REPO_ROOT`/trusted
instruction materialization), or step 6 (dispatcher self-modification check) — and consequently never
reaches the Codex dispatch resolver, Phase 1, Phase 2, or Phase 3 at all. No model is dispatched, and
no `AskUserQuestion` First-Send Confirmation is triggered, because the run never gets that far.

(One implementation nuance worth flagging: because the surrounding instruction says to "check its
exit status" and produce a *differentiated* report depending on that status, the actual shell
invocation has to capture the diff command's exit code/output explicitly — e.g. via a variable —
rather than relying on a bare `&&`-chained pipeline that would just abort silently on failure with no
distinguishing message. The skill's intent, per the quoted step-1 text, is clearly that both outcomes
— non-zero exit vs. exit-0-empty-stdout — produce their own distinct, user-facing report.)

## Does the skill correctly distinguish this from a genuinely empty diff?

**Yes — explicitly, in the same sentence pairing, and reinforced elsewhere in the document.**

The two cases are laid out as a direct contrast within step 1 itself:

| Condition | Exit status | Skill's classification | Required action |
|---|---|---|---|
| `BASE` doesn't exist / no local `main` ref / other Git error | **non-zero** | "a Preflight failure, **not** an empty scope" | Report the Git error; ask for a valid `$BASE` |
| `BASE` is valid, but `HEAD` has no changes relative to it | **zero (0)**, stdout empty | "the diff is genuinely empty" | Report "nothing to review against `$BASE`" (+ `$SCOPE` if set) and stop |

This is reinforced by the **Testing & Validation → Concrete scenarios to check** section (lines
351–353), scenario 1:

> "1. Empty diff against `$BASE` → Preflight step 1 reports 'nothing to review' and stops, no
> dispatch of either model."

That scenario is specifically the *valid-`BASE`-but-no-changes* case — it says "empty diff against
`$BASE`," implying `$BASE` itself resolved successfully and the comparison simply produced no diff
hunks. It is listed as its own distinct scenario precisely because it's a different code path from an
invalid `$BASE`, which the step-1 prose separately calls out by name ("an invalid `$BASE`") as
producing a Git-error report instead.

So the mechanism the skill relies on to tell the two apart is **exit status of the diff command**,
not the emptiness of its output alone:

- Non-zero exit → something is wrong with the ref/command itself (invalid `BASE`, missing `main`,
  etc.) → Preflight failure, error reported, user asked for a valid `BASE`.
- Exit 0 **and** empty stdout → the command ran successfully against a real, resolvable `BASE`, and
  there simply happened to be no differences → "nothing to review," clean stop, no error implied.

Given `BASE=nonexistent-branch-xyz`, the run lands squarely in the first row: `git diff
nonexistent-branch-xyz...HEAD` cannot succeed (nonzero exit), so per the skill's own explicit
instruction this is reported as a Git error / invalid-`BASE` Preflight failure, and the user is asked
to supply a valid `BASE` — it is never characterized as "nothing to review."

## Citations

- Inputs section (`BASE` resolution before Preflight step 1 runs): SKILL.md lines 52–72.
- Preflight lead-in (single chained Bash invocation, steps 1–6): SKILL.md lines 77–85.
- Preflight step 1 (the core distinguishing logic): SKILL.md lines 87–91.
- Testing & Validation, scenario 1 (empty-diff case, contrasted implicitly with the invalid-`BASE`
  case named in step 1): SKILL.md lines 351–353.
