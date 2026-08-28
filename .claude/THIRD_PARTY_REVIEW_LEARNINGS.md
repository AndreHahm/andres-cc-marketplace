# Third-Party Review Learnings

**Goal:** reduce the number of paid third-party review round-trips (Codex, CodeRabbit, cross-model-review)
a PR needs, by catching these bug classes *before* pushing — via self-run traces, live verification, and
schema/docs checks — rather than relying on the reviewer to find them. Findings for PR #54/#55 were
captured live during those PRs' own review rounds; findings for PR #52/#51/#49/#47 were reconstructed
afterward from each PR's actual GitHub review history (`gh api .../pulls/<n>/reviews` and `.../comments`),
cross-checked against fix commits, since this document didn't exist while those PRs were in flight. PR
#61/#62/#65/#68 (added 2026-08-19) were captured live too, built directly from this document's own
brainstormed action list. PR #76 and PR #79 (added 2026-08-22) were reconstructed the same way as
PR #47/#49/#51/#52 — from each PR's actual GitHub review history, cross-checked against fix commits —
since this document didn't exist while they were in flight (both merged 2026-08-20). PR #92 (added
2026-08-21) was also captured live, across four consecutive review rounds on the same mechanism. PR #88
(added 2026-08-22) was also captured live — a new skill built, then used live (manually, since not yet
merged) to triage its own introducing PR's review rounds. Every finding cited below was real and confirmed
fixed by a follow-up commit unless noted (a small number were deliberately deferred to a tracking issue
instead — marked as such).
This document exists to shorten the tail next time by naming the recurring *shapes* those findings took.

---

## Cross-PR meta-pattern (spans all six PRs: #54, #55, #52, #51, #49, #47)

**The single largest source of avoidable review rounds is writing an instruction against a *remembered or
assumed* model of a tool/API/language's behavior instead of its actual, checked behavior.** Every PR
reviewed so far has at least one finding of this shape:

| PR | Assumed behavior | Actual behavior |
|---|---|---|
| #47 | `head -1` just stops a pipeline cleanly | `sort \| head -1` under `set -e -o pipefail` can SIGPIPE `sort` and abort the whole script |
| #47 | Bash `$((VAR))` treats `"08"` as the decimal number 8 | Bash arithmetic reads a leading-zero numeral as **octal**, and `08`/`09` are invalid octal digits → hard error |
| #49 | `jq -e 'any(...)'` over `--paginate` output matches if *any* page matched | `jq -e`'s exit status is based only on the **last** value it emitted — an earlier page's `true` is silently overridden by a later page's `false` |
| #49 | A GitHub reaction on a PR can be timestamp-correlated to "the current head" | The Reactions API has **no commit-SHA field at all** — no client-side heuristic can fix this; it's a hard API limitation, not a bug |
| #51 | `gh pr checks` exposes a workflow's **file name** (`await-codex-review.yml`) | It exposes the workflow's **display name** (`"Codex review status"`) — a different string entirely, only discoverable by requesting the JSON field and checking live |
| #52 | A shell variable set in one `Bash` tool call is visible to a later `Bash`/`Read`/`Write` call | **Claude Code's Bash tool has no persistent shell state across calls** — each call is a fresh subprocess ([[feedback_bash_tool_no_persistent_shell_state]], already in memory *before* this PR shipped the bug) |
| #54 | `AskUserQuestion` only caps options-per-question | It **also** caps questions-per-call (4), independently — a second, uncovered dimension of the same tool's schema |
| #55 | Hand-rolled regex can reliably extract Python call-site arguments | Only `ast.parse()` can, because "arbitrary legal Python source" has an unbounded adversarial tail no regex will ever fully cover |

**Rule:** before writing an instruction, script, or workflow step whose correctness depends on how a
tool/API/language actually behaves — not how it's commonly assumed to behave — check the real source:
`ToolSearch`/the tool's own schema, `gh api --help` / `gh <cmd> --help`, a live one-off call against the
real API, or the language's own parser/stdlib instead of a hand-rolled approximation. This single check,
applied consistently, would have caught roughly a third of all findings across these six PRs before the
first push — more than any other individual pattern named below.

---

## PR #54 — `running-a-full-retrospective` Phase 5 redesign (7 Codex rounds, 2026-08-19)

Six of seven rounds were ripple effects of one original design gap in a multi-skill lifecycle chain —
each one only surfaced because a *new* commit got reviewed, not because the chain was re-traced in full
after the first fix.

### Pattern 1: Fixing a lifecycle step's *symptom* without re-tracing the whole chain

**What happened:** Round 1 fixed "the worktree never closes" by adding a `commit → create-pr → merge-pr
→ finishing-work` chain. Round 2's own fix (adding an explicit `cd` into the worktree) broke
`finishing-work`'s precondition, caught in round 3. Round 3's fix (`cd` back before `finishing-work`)
needed a `Bash(cd:*)` grant, missing until round 4 — and round 4 also found the "confirm worktree closed"
claim was false for the pipeline-hand-off path. Round 6 found `finishing-work` was still being invoked
*bare*, so `gh pr view` resolved the wrong branch's PR. Round 7 found two more nested-dispatch collisions
in the same chain.

**Rule:** when a fix changes *where* (cwd/worktree) or *when* (before/after another call) a step in a
multi-skill chain runs, don't just patch the one broken step. Re-simulate the **entire chain**, one call
at a time, tracking cwd/branch/captured-variable state at each point, before considering the fix done.
A chain that's just been edited is exactly the chain most likely to have a second broken link nearby.

### Pattern 2: Writing `Skill(X)` without reading X's full instructions first

**What happened:** Round 4 (bare `finishing-work` call), round 6 (same, plus a stale cache-glob issue),
and round 7 (two separate nested-dispatch collisions: `commit`'s own Auto-PR step, `merge-pr`'s own
post-merge-sync prompt) all trace back to writing "then `Skill(git-kit:X)`" without actually reading X's
own SKILL.md for: (a) does X have its own conditional nested dispatches or `AskUserQuestion`s that could
fire and conflict with the calling skill's own plan? (b) does X assume a particular cwd/branch? (c) does
X need an argument that would silently resolve to the wrong thing if omitted?

**Rule:** before writing an instruction that invokes another skill inside a lifecycle sequence, read that
skill's full SKILL.md (not just its `argument-hint`/description). Specifically check for: any
`AskUserQuestion` it asks unconditionally after success (these are the ones that silently branch); any
assumption about current branch/cwd; any argument whose omission falls back to "current branch" or
similar ambient state.

### Pattern 3: Tool constraints have more than one dimension — check the actual schema, not memory

**What happened:** This whole redesign started because `AskUserQuestion`'s 4-*options*-per-question cap
was hit live. Six rounds later, round 7 found the redesign itself hadn't accounted for the *separate*
4-*questions*-per-call cap — so "split across multiple questions in one call" silently broke down past
12 total findings (4 questions × 3 real options). Both caps were real, but only one had been checked.

**Rule:** when writing an instruction that works around a tool's limit, pull the tool's actual schema
(`ToolSearch("select:<ToolName>")`) and check *every* constrained field, not just the one already known
from a prior incident. A tool can have independent caps that compound (per-question AND per-call here).

### Pattern 4: A tool grant added mid-edit needs to be checked in the same edit, not a later pass

**What happened:** Round 3's fix added a `cd` instruction to the skill body. The corresponding
`Bash(cd:*)` grant wasn't added until round 4 — a full review round later.

**Rule:** any time a `Bash(...)`/`Skill(...)` call is added to a skill's body, immediately grep the
current `allowed-tools` line for the exact matching grant *as part of that same edit* — don't defer this
to a dedicated "tool completeness" pass at the end. The gap between "added the call" and "added the
grant" is exactly the window a review round exists to catch, and it's free to close immediately instead.

### Pattern 5: A "confirm X is done" check must be scoped per-path, not written as one blanket check

**What happened:** Round 4 found that "confirm the worktree is closed" was written as if it applied
uniformly to both the direct-fix path (which this skill controls and can observe) and the
pipeline-hand-off path (which delegates to another pipeline's own internal `starting-work` call — never
visible to this skill). The blanket check would have either false-alarmed on a normal pipeline success or
missed a real dangling worktree on a pipeline failure, because it can't tell the two apart.

**Rule:** when a skill dispatches to two structurally different execution paths (direct execution vs.
delegating to another pipeline/skill), any "verify completion" or "confirm state" check needs its own
per-path evaluation of *whether this skill can actually observe that path's internals at all* — never
write one check and assume it degrades gracefully for the path that doesn't apply.

### Pattern 6: Eval/test artifacts go stale silently when documented behavior changes

**What happened:** Round 5 found that `evals/.../evals.json`'s `expected_output` for eval-3 — and the
already-checked-in grading that scored a response against it — still asserted the *old*, since-corrected
behavior (that the pipeline-hand-off path closes its own worktree). A behavior fix landed without a
matching pass over the eval set that encodes the old behavior as "correct."

**Rule:** whenever a fix reverses or corrects a previously-documented behavior claim, grep the skill's own
`evals.json` for any `expected_output` asserting the *old* claim before considering the fix done. An eval
expectation is a live claim about current behavior, same as SKILL.md prose — it doesn't get a pass just
because it's data rather than instructions.

### Pattern 7: A disclosed limitation isn't a substitute for a fix that's actually cheap and available

**What happened:** Round 6's cache-glob finding had already been disclosed in prose as "a best-effort
check... not a definitive install-state query" — but a real, cheap, authoritative source
(`~/.claude/plugins/installed_plugins.json` + `~/.claude/settings.json`'s `enabledPlugins`) existed and
hadn't been used. Disclosure didn't make the underlying check correct.

**Rule:** before writing a "best-effort"/"not definitive" disclaimer instead of a real fix, check whether
an authoritative source actually exists and is cheap to query. If it does, use it — reserve disclaimers
for cases where no better source is actually available, not as a way to skip a five-minute check.

### Meta-lesson: self-verification (skill-reviewer) catches consistency bugs, not chain-timing bugs

Every fix this session was independently re-verified by a fresh `skill-reviewer` dispatch before pushing,
and that step genuinely caught real regressions before Codex ever saw them (three self-introduced gaps in
round 1's own fix, one unverified `cwd`-rebind claim in round 2). But it did **not** catch the
Pattern-1/Pattern-2 chain-timing bugs (rounds 3, 4, 6, 7) even when run *after* the fix that introduced
them — because a general "is this internally consistent and well-written" review doesn't specifically
simulate multi-skill execution state.

**Actionable fix:** when dispatching a verification pass for a skill whose body chains multiple `Skill(X)`
calls together, explicitly instruct it to do a **step-by-step execution trace** — track cwd/branch/
captured-variable state through the whole chain, and for each `Skill(X)` call, check X's own actual
SKILL.md for preconditions, nested asks, and default-argument fallbacks — not just "does this read
consistently." This is a distinct verification task from general skill-quality review, and it needs to be
asked for explicitly; it isn't the default framing of a "review this skill" dispatch.

---

## PR #55 — `feature/reviewing-evals-skill`, plugin-devkit's `reviewing-evals` skill (6 rounds)

Six review rounds against the same ~250-line script (`scripts/check_evals.py`) found a new, real bug
every single time — `dec5aed` (6 findings), `5025686` (2 findings, on `SKILL.md`), `7826389` (5 findings,
cross-model), `fb1c6ee` (3 findings), `674db8c` (2 findings), `2346f33` (3 findings). That's **21
findings across 6 rounds** on one component. Every finding was real and got fixed — this isn't about
reviewers being noisy. It's about the same *root cause* producing a new symptom each round.

### The one big lesson

**A script whose job is to extract information from arbitrary Python source text is a parser. Write it
as one — use `ast`, not regex — from the first line, not after 4 rounds of regex patches.**

`check_evals.py` extracts `re.findall(...)`/`re.search(...)` call sites, their pattern literals, their
haystack argument, and their flags argument — all from raw source *text* via hand-rolled regex +
string-scanning helpers (`_extract_call_arg_text`, `_split_top_level_args`,
`_split_top_level_alternation`, `_decode_literal`, `_is_complete_literal_arg`, `_noncode_spans`,
`_strip_full_group_wrap`, ...). Each of these was a *correct* fix for the specific bug it addressed. But
collectively they're reinventing pieces of what `ast.parse()` gives for free:

| Regex-parsing bug found | What `ast` gives for free |
|---|---|
| Non-raw literal escapes not decoded (`"^target\\s*$"` → wrong) | `ast.Constant.value` is already the real runtime string, raw or not |
| Concatenated pattern read as just its first fragment (`r"\b" + re.escape(x) + r"\b"`) | A `BinOp`/non-`Constant` node is trivially "not a simple literal" |
| Comment/docstring text scanned as a real call | Comments don't exist in the AST; a docstring is a `Constant`, never a `Call` node |
| Paren inside a string argument desyncing the call-boundary scan | `ast.get_source_segment()` gives the exact source span of any argument node |
| Flags passed via a bare variable, or a mixed expression (`re.MULTILINE \| FLAGS`) | Walk the flags-argument *subtree* directly — no regex-vs-residual heuristic needed |
| Escaped `\$`/`\b` misread as a real anchor | Irrelevant once you're not doing character-level lookback at all |
| Alternation nested inside a group | Still needs real logic, but you're working on the *pattern string itself* (a clean value from `ast`), not also fighting the *outer* Python-syntax extraction at the same time |

None of these fixes were wrong to make. The mistake was the *shape* of the fix each time: patch the
specific regex/string-scanner to handle one more edge case, rather than recognizing that "parse a subset
of Python source" is exactly the kind of problem where hand-rolled text-scanning has an **unbounded
adversarial tail** — there is always one more legal Python construct (implicit string concat,
triple-quoted raw strings, `\N{...}` escapes, a parenthesized flags expression spanning multiple lines, an
`r"""..."""` docstring, ...) that the next reviewer round will find, because a human reviewer thinking
"how else could this be legally written in Python" will always out-pace a hand-maintained regex.

**Actionable rule:** before writing *any* script whose job is "find calls that look like X in a `.py`
file" or "extract argument Y from a Python call," ask: is the input adversarial-only in the sense of
"arbitrary but syntactically valid Python I don't control the shape of"? If yes, use `ast` from the
start. The "surgical / minimal diff" principle (CLAUDE.md §2-3) still applies to *how much of the file
you touch on a given fix* — it does not mean "keep patching a fundamentally wrong approach because a full
rewrite touches more lines." Six review rounds of surgical patches cost more (in money and turnaround)
than one AST-based rewrite would have.

### Concrete gotcha checklist (reusable for the *next* regex-based source scanner)

If a future script still ends up doing textual/regex scanning of source code (a smaller language, a
config format, whatever `ast` doesn't cover), test it against every one of these up front, in the fixture
suite, *before* first push — don't wait for a reviewer to find them one at a time:

1. **Non-literal / constructed values**: f-strings, concatenation (`+`), variables, any expression that
   isn't a bare literal.
2. **Escaping inside the thing you're capturing**: an escaped copy of your own delimiter (`r'quo\"te'`),
   an escaped version of a character you treat as meaningful (`\$` vs `$`, `\b` vs a literal `b`).
3. **Non-raw vs raw source spelling**: a plain string's escapes need real decoding (`ast.literal_eval` or
   equivalent) before the *value* is meaningful — the source spelling and the runtime value are different
   strings.
4. **Comments and docstrings that happen to contain your target syntax as example text.**
5. **Argument-boundary desync**: a paren, comma, or quote *inside* a string argument that isn't part of
   the call's real structure.
6. **"Which argument is which" after the call is found**: don't scan the *whole* trailing argument blob
   for a signal (e.g. `"skill" in arg_text`) when you mean "is argument #2 specifically about SKILL.md" —
   split into real argument boundaries first, then check the *specific* argument, or a later unrelated
   argument's content will produce a false positive/negative on the wrong basis.
7. **Partial resolution of a compound expression**: if an expression mixes something you can resolve with
   something you can't (`re.MULTILINE | SOME_VARIABLE`), resolving the known part and silently dropping
   the rest changes semantics. Treat *any* residual as fully unresolved, not "resolved minus the part I
   understood."
8. **Nesting**: whatever grouping/structural construct your target language has (parens, brackets,
   alternation groups) — check it recursively, not just at the top level. A top-level-only check
   (`^(cat|dog$)` read as one branch) will miss exactly the case where the interesting bug is *inside*
   the group.
9. **Timeouts/resource bounds on anything you evaluate from untrusted input** — this one *was* caught
   proactively during the original build (`dec5aed`'s ReDoS/subprocess-timeout fix was self-identified
   via `skill-reviewer`+`security-reviewer`, not a later PR-review finding), which is the pattern to
   repeat for the other 8 items above: catch it in review *before* the first push, not after.

### Process changes that would have cut rounds, not just fixed bugs

- **Run `cross-model-review` locally before the first push, and treat its findings as the primary
  pre-push gate — not merely one extra opinion.** In this PR, one local `cross-model-review` pass
  (`7826389`) surfaced 5 real findings in a single round-trip, at no GitHub-review latency and no
  marketplace-CI cost. Post-push Codex rounds surfaced findings 1-3 at a time (`dec5aed`: 6, `fb1c6ee`: 3,
  `674db8c`: 2, `2346f33`: 3) — same detection rate per finding, but each round paid the
  push→CI→review→pull-comments round-trip cost on top. Cheaper detection should happen at the cheapest
  point in the loop.
- **When a mechanical checker's whole purpose is auditing *other people's* code, hold its own test suite
  to the reviewer's adversarial standard, not the happy-path standard.** This skill exists specifically
  to catch defect classes in *target* smoke tests; its own extraction logic needed the same adversarial-
  input mindset applied to itself, from the first fixture, not accumulated fixture-by-fixture after each
  review round.
- **When fixing a bug in one function, grep for the same logic pattern in sibling functions.**
  `_branch_anchoring_verdict`'s `right_anchored` check and `_strip_full_group_wrap`'s outer-anchor-
  stripping check independently implemented the exact same "does this text end with `$`/`\b`" logic —
  both had the identical escaped-anchor bug. Caught proactively this round only because the second
  instance was noticed while writing the fix for the first, not because it was independently reasoned
  about; make that grep an explicit step (`grep -n 'endswith\|startswith'` near any anchor/boundary-
  detection fix) rather than relying on incidentally noticing it.
- **Empirically verify a regression fixture actually discriminates old-vs-new behavior** before trusting
  it (a practice already used well this session, worth keeping) — several fixtures in this PR were
  checked against a standalone before/after comparison script when the outcome wasn't obviously
  distinguishing, catching at least one fixture redesign where the first version produced the same
  PASS/FAIL either way.

### Separate, smaller pattern: non-script (SKILL.md/workflow) findings

Two findings (`5025686`) were not about the script at all — a trust-boundary gap (executing
target-authored `smoke_test.*` without delegating to `smoke-tester`'s resolved-path symlink check) and a
mutation-gate gap (Phase 5 telling the operator to "resolve locally" without the pipeline's own gated
fix-and-commit procedure). Both were domain-specific gaps that a dedicated `security-reviewer` dispatch
caught immediately once actually run (same session, proactively) — the lesson here is narrower and
already covered by existing repo rules (`.claude/rules/require-security-review-before-new-gate.md`): a
new trust-boundary or mutation-gate mechanism needs `security-reviewer` *before* the first commit that
ships it, not as a reactive fix after a PR-review finding. That rule existed before this PR; this PR is
one more data point that skipping it costs a round.

---

## PR #51 — `codex-review-recovery` skill (7-8 Codex rounds, 2026-08-18, ~15 findings — the richest PR)

Almost every round after the third was some variant of the same underlying shape: **the skill observed
some external state (a PR's head SHA, a workflow run's conclusion, whether a run exists yet) and then took
an irreversible action — post a comment, rerun a workflow — based on a check that had already gone stale
by the time the action executed.** This is a textbook TOCTOU (time-of-check-to-time-of-use) class, and it
recurred in a new place almost every round because each fix closed the one window just found rather than
being applied as a systematic principle across every side-effecting step in the skill.

### Pattern: the same TOCTOU shape, found in a new window each round

1. **Round 2** (`c13a4ca`): a commit pushed while waiting on human confirmation left `headRefOid` stale —
   fixed by re-fetching the head right after confirmation.
2. **Round 4** (`ccd7d02`, finding 1): the workflow rerun triggered by this skill isn't guaranteed to have
   left its old `fail` state by the first poll — an early poll can still read the *stale* pre-rerun
   result and report it as terminal.
3. **Round 5** (`4833c54`, finding 2): the fix for #2 (require observing a transient `queued`/
   `in_progress` state first) broke on a rerun that finished *before* the first poll — every poll then
   saw a genuine fresh `completed` result but discarded it as stale, since no transient state was ever
   observed. Fixed by comparing the run's `attempt` counter against a pre-rerun baseline instead of
   requiring a specific state transition to be witnessed.
4. **Round 5** (`4833c54`, finding 1) and **round 6** (`afb9f09`, findings 1-2): the skill posted its
   `@codex review` retry comment and reran the workflow *before* fully validating the run it was about to
   act on (ambiguous multiple runs for one SHA; the run already resolved to `success` by another
   maintainer; the head moved again during the lookup itself) — each was its own re-check window, found
   and closed one at a time rather than as one "never act before a final, immediate re-check" principle.
5. **Round 7** (`77e6454`): `conclusion` handling assumed a binary success/failure — `timed_out` is a
   distinct, valid GitHub Actions run status the recovery flow didn't recognize, so a timed-out run was
   silently treated as "already resolved" instead of "needs recovery."

**Rule:** any skill or workflow that (a) observes external async state it doesn't fully control (a CI run,
a bot's reaction, another maintainer's action) and (b) then takes a side-effecting action based on that
observation, needs **one explicit design pass enumerating every state-change window between observation
and action** — not a re-check added reactively each time a reviewer finds one. Concretely: list every
side-effecting call in the skill: for each one, what was checked, how long ago, and could the checked
state have changed in that gap? Also enumerate the *full* state space of whatever's being observed (a
GitHub Actions run conclusion has at least `success`/`failure`/`cancelled`/`timed_out`/`neutral`/
`action_required` — not just pass/fail) rather than assuming a binary.

### Pattern: an API field doesn't mean what its human-readable name suggests

**What happened (round 1):** the skill instructed matching a workflow by name, assuming `gh pr checks`
exposed the workflow's file name (`await-codex-review.yml`, the thing visible in the repo). It actually
exposes the workflow's *display name* — this repo's is `"Codex review status"`, an unrelated string set
in the workflow's own `name:` field. No amount of reasoning about the file would have surfaced this; it
required requesting the actual JSON (`--json name,workflow,bucket,link`) and reading the real value.

**Rule:** when an instruction says "match on the workflow/field/resource named X," verify X is the actual
field value returned by the API being called — via a live request — not the name a human would use to
refer to the same thing informally.

### Pattern: a race that genuinely can't be fixed client-side is a documentation problem, not a code problem

**What happened (round 4, `b24a47b`):** a clean review's `+1` reaction can be posted for an *old* head
after a new `synchronize` event already started a fresh run for a new head, because GitHub's Reactions API
has no commit-SHA field to correlate against. Rather than attempting an unfixable heuristic, the fix was
to downgrade the documented certainty of the reaction-based success path (explicitly "best-effort,
non-commit-exact" vs. the review-object path's "commit-exact, reliable") and record it as a permanent
architectural tradeoff.

**Rule:** before spending a round chasing a client-side fix for a race condition, confirm the API actually
carries the information needed to resolve it. If it doesn't, the correct fix is honestly downgrading the
documented guarantee — this is the complementary case to PR #54's Pattern 7 ("a disclaimer isn't a
substitute for a fix that's cheap and available"): here, no fix *was* available, so the disclaimer was the
right call, not a shortcut.

### Smaller, structural findings (round 1 and round 3)

- **Cross-repo `-R`/`--repo` binding dropped after the first step.** A PR URL for a different repository
  was correctly parsed in step 1, but every later `gh pr`/`gh run` command silently fell back to the
  current checkout's own repo instead of carrying the resolved `owner/repo` forward. **Rule:** when a
  skill resolves an identifier (repo, branch, PR number) from user input in an early step, every
  subsequent command that needs it must explicitly reuse the *resolved* value — never let a later step
  re-derive it from ambient state (current directory's git remote) that may not match.
- **New skill missing from the third mirror (`.agents/`).** This repo's own documented convention
  (`plugins/git-kit/README.md:185-193`) requires every git-kit skill to exist in three places
  (`plugins/git-kit/skills/`, `.claude/skills/`, `.agents/skills/`); the new skill (and two files it
  touched, `gh-operations` and `merge-pr`) were missing/stale in the third. **Rule:** when a change
  touches or adds a skill governed by a multi-mirror convention, sweep *all* mirrors in the same commit —
  this is the same class of gap `plugin-rulebook-enforcement.md`'s R20 duplicate-fact sweep already names
  for canonical values; it applies equally to whole-file mirrors.
- **Activation-boundary exclusion written in the wrong field.** A "don't route here, use the other skill"
  exclusion was added only to body prose ("When to Use"), but this repo's own documented convention states
  body text doesn't participate in activation matching — only the `description` frontmatter field does.
  **Rule:** an activation/routing boundary between two skills must live in both skills' `description`
  frontmatter, reciprocally — see `.claude/rules/resolve-activation-overlap-bidirectionally.md`, which
  this finding is a direct instance of.
- **A newly-required shell command wasn't in `allowed-tools`.** An earlier round's fix added an explicit
  30-second polling delay, but no `Bash(sleep:*)` grant existed for it. Same root cause as PR #54's
  Pattern 4 above — recurs here as its own independent instance.
- **A stale eval expectation after a behavior-changing fix.** Reordering the skill's steps (validate the
  run before posting a retry comment, not after) left `evals/codex-review-recovery/evals.json`'s eval-5
  still asserting the *old* behavior (a comment gets posted even when no run matches) — same class as
  PR #54's Pattern 6.

---

## PR #52 — `cross-model-review` skill (3 rounds, 2026-08-18, ~14 findings)

### Pattern: Claude Code's own execution model was assumed, not verified — recurring, high-severity

**What happened (round 1, P1):** the skill's Preflight phase computed several shell variables (`$RUN`,
`$REPO_ROOT`, `$DIFF_STR`, a `DIFF` array) in one `Bash` call, then referenced them by name in later
`Bash`, `Read`, and `Write` tool calls across multiple phases — including after an intervening
`AskUserQuestion`. **Claude Code's Bash tool has no persistent shell state between separate tool calls** —
this is a known, already-documented fact in this repo's own session memory
([[feedback_bash_tool_no_persistent_shell_state]]) that predates this PR, yet the skill's own design
violated it. Every `$VAR` reference after the first Bash call would have silently resolved to nothing.

**Fix:** run Preflight steps 1-6 as a single chained Bash invocation that ends by echoing the resolved
values, then treat every later `$VAR` reference in the document as shorthand for that literal,
already-resolved value — not a live shell variable.

**Rule:** this is the single most expensive class of finding across all six PRs reviewed, because it's a
foundational fact about the execution environment, not a one-off bug — every future skill whose body
spans multiple tool calls and needs to carry a computed value forward must resolve that value once, in
one call, and either echo it into every subsequent instruction as a literal, or use a wrapper script that
holds the state itself. Check this explicitly for any new multi-phase skill design, since it's cheap to
verify and expensive to discover via a review round (this finding alone likely blocked the entire skill
from functioning at all, not just one edge case).

### Pattern: a scope filter applied to one use doesn't automatically apply to a different downstream use

**What happened (round 2):** Preflight's `SCOPE`-filtered diff was correctly used to build the review
payload, but the *separate* dispatcher-trust check (which must warn before executing changed
dispatcher/bridge code with elevated permissions) was built from that same `SCOPE`-filtered list — so a
scope-narrowed review could hide a dispatcher-script change from its own mandatory trust disclosure.

**Rule:** when a diff/file list is filtered for one purpose (what to review), any *other* consumer of
"what changed in this diff" (a security/trust check, a mirror-sync check, an eval-staleness check) needs
its own explicit, unfiltered pass over the same diff — never assume a filtered list built for purpose A is
safe to reuse for purpose B's own correctness-critical logic.

### Pattern: a "when NOT to use" exclusion can silently contradict the skill's own advertised examples

**What happened (round 2):** the skill unconditionally excluded "reviewing an open PR," but a draft PR is
already technically an "open PR" — which directly conflicted with the skill's own documented example
("review this before I mark the draft ready") and its stated purpose of reviewing a local diff before
flipping a draft to ready.

**Rule:** after writing a "When NOT to Use" exclusion, check it against the skill's own worked examples
and stated primary use case for self-contradiction — not just against other skills' domains (the more
common activation-overlap check per `resolve-activation-overlap-bidirectionally.md`). A skill can
accidentally exclude itself.

### Other findings

- **Marketplace-relative dispatcher path isn't portable.** The Codex dispatcher was resolved via a path
  relative to the marketplace checkout root; when `git-kit` is installed standalone into an unrelated
  project, that path doesn't resolve. Left open deliberately (not fixed) as a pre-existing, shared
  architectural convention with `plugin-auditor`'s own Codex dispatch — noted as a cross-plugin
  architectural change out of scope for this PR, not silently dismissed.
- **A degraded/fallback mode needs a complete alternate control-flow, not just a branch point.** The
  advertised "Claude-only" fallback (when Codex is unavailable) didn't actually skip the later phases that
  assumed Codex's output files existed — those phases would still try to read a nonexistent envelope. Same
  class as PR #54's chain-re-tracing lesson (Pattern 1): a fallback branch has to be traced all the way
  through every later step that assumed the normal path, not just declared at the branch point.
- **Untrusted diff content fed to a `danger-full-access` process needs closing-tag neutralization on
  every dispatch path**, not just the primary one — a Windows fallback dispatcher copied embedded content
  verbatim into a prompt block without the same `neutralizeClosingTags` pass the primary bridge used,
  opening a prompt-injection path from arbitrary diff content. Caught and fixed proactively within the
  same PR, not via a later incident — the lesson is to check *every* dispatch path shares one shared
  sanitization step, not just the one exercised in normal testing.
- **No precedence rule when two reviewer models' verdicts conflict across passes** (a challenger's later
  refutation vs. Phase 1's initial agreement) — synthesis had no defined tiebreak, so a disproven finding
  could still rank as High confidence. A cross-examination design needs its conflict-resolution rule
  specified before shipping, not left implicit.
- **A newly-required shell command (`grep`, `echo`) wasn't in `allowed-tools`** — introduced by round 1's
  own fix (the "single chained Bash invocation" pattern above), caught in round 2. Same recurring class as
  PR #54 Pattern 4 and PR #51's `sleep` gap above — this is now confirmed across three separate PRs.

---

## PR #49 — `await-codex-review` GitHub Actions workflow (5 Codex rounds, 2026-08-17, 7 findings)

A polling workflow that waits up to 30 minutes for a Codex review to land, checking both the PR's review
list and its reaction list. Every finding was from Codex; all were fixed same-day.

### Pattern: the same `jq --paginate` bug, found once, then found again in a sibling block two rounds later

**What happened:** round 1 found that `jq -e 'any(...)'` over `--paginate` output only bases its exit
status on the *last* page emitted — a match on an earlier page can be silently overridden by "no match" on
a later page, causing a false timeout. Fixed for the reviews-list check (`jq -s -e 'add | any(...)'`,
slurp-and-flatten). **Round 3 found the exact same anti-pattern, unfixed, in the separate reactions-list
check** — a structurally identical block that used the same broken `--paginate` + `any()` pattern but
hadn't been touched by round 1's fix because it was a different code block doing the analogous check on a
different endpoint.

**Rule:** this is the same "grep for the same logic pattern in sibling code" lesson PR #55 already names
(its Process-changes section) — but here it cost a full extra review round because the sibling block
wasn't checked at fix time. When a review finding identifies a bug in one block, before considering the
fix complete, grep the rest of the changed file (and ideally the rest of the component) for the same
anti-pattern signature (here: `--paginate` piped into a `jq -e` without `-s`/slurp) rather than trusting
that the one instance found is the only instance that exists.

### Pattern: `set -eo pipefail` in a GitHub Actions `shell: bash` step aborts on the first transient failure

**What happened (round 2):** a `gh api` call inside a variable assignment (`reviews="$(...)"`) failing
transiently (a flaky network blip) terminated the entire job immediately, because GitHub Actions runs
`shell: bash` steps under `-eo pipefail` by default — even though the workflow's whole design intent was
to tolerate exactly this kind of transient failure across a 30-minute polling window.

**Rule:** any command inside a polling/retry loop that can legitimately fail transiently must be wrapped
so its failure is caught and handled *within* the loop (`if ! result="$(...)"; then ...; continue; fi`),
not left to the shell's default errexit behavior to terminate the whole script — this applies to every
step of a loop meant to tolerate failure, not just the ones an author happens to think of as "the risky
one."

### Pattern: an off-by-one that silently drops the last observation window

**What happened (round 5):** the poll loop's structure was check → sleep → (loop back to check), so
after the *last* check-then-sleep, the loop condition ended it and fell straight to a failure message
with no final re-check — meaning a review that landed during that last sleep, within the documented
30-minute window, was still reported as a timeout.

**Rule:** in any "poll N times, sleep between polls, then give up" loop, verify explicitly that the
*last* action before giving up is always a check, never a sleep — this usually means moving the sleep to
the top of the loop body (skipped on the first iteration) rather than the bottom, and re-deriving the
iteration count from the actual deadline rather than reusing a round number.

### Pattern: a baseline snapshot taken "at job start" can already be stale by the time it's taken

**What happened (round 3):** the workflow snapshotted existing reactions "at job start" to use as a
baseline for detecting a *new* one later — but if the external reviewer's reaction landed between the
triggering PR event and this job actually starting (or during the baseline-fetch's own retries), it was
already included in the "baseline," so the workflow had no remaining signal and timed out on a review that
had, in fact, already completed. Fixed by anchoring freshness to the triggering event's own
`pull_request.updated_at` timestamp (captured before the job even starts) instead of "whatever existed
when this job happened to start observing."

**Rule:** when a workflow needs to distinguish "new since I started watching" from "already existed," anchor
the cutoff to an event timestamp that's independent of *this job's own* start time — a job-start snapshot
always has a race window between the triggering event and the job's own first observation.

---

## PR #47 — scratchpad-cleanup scripts, bash + PowerShell (3 rounds, 2026-08-17, 4 findings)

Small utility PR, but the findings cleanly illustrate two separate classes.

### Pattern: a "staleness scan" needs to enumerate every real activity signal, and each round found the next uncovered one

1. **Round 1** (CodeRabbit): `Get-ChildItem` without `-Force` silently omits hidden files, so a hidden
   recent file could cause an active session to be misclassified as stale.
2. **Round 2** (Codex): even after round 1's fix, both scripts only considered *file* timestamps — a
   session that created a new empty subdirectory, or deleted its newest file, has real recent activity
   recorded only as a *directory* mtime, which neither script's age calculation looked at.

**Rule:** when writing a "how recently was this touched" check over a directory tree, the first design
pass should explicitly enumerate the full set of activity signals (visible files, hidden files, directory
mtimes, symlinks if relevant) rather than starting from "scan files" and having each gap found one review
round at a time. This is the same "completeness of an extraction/scan" theme as PR #55's `ast`-vs-regex
lesson, applied to filesystem scanning instead of source parsing.

### Pattern: an unvalidated numeric input reached bash arithmetic directly

**What happened (round 3):** a user-supplied age threshold like `"08"` or `"09"` is valid as a decimal
day count, but bash's `$((...))` arithmetic context reads a leading-zero numeral as **octal** — and `08`/
`09` aren't valid octal digits, so the script crashed with "value too great for base." Separately, an
all-digit but oversized input could overflow the multiplication into a negative threshold, which would
make *every* session appear eligible for deletion — a dangerous silent failure mode for a destructive
cleanup script. Fixed by bounding the input to a fixed digit count and forcing explicit base-10 parsing
(`10#$DAYS`).

**Rule:** any numeric input from a user or config that flows into bash arithmetic needs (a) an explicit
bound on digit count/magnitude and (b) explicit base-10 forcing (`10#$VAR`) before use in `$((...))` —
bash's default octal-on-leading-zero behavior is a well-known but easy-to-forget footgun, and it's
especially dangerous here because the overflow failure mode was "delete more than intended," not just a
crash. Also worth a SIGPIPE-under-`pipefail` check on any `sort | head` pattern in the same script family
(flagged independently in round 1 on the same file) — both are cheap, mechanical bash pitfalls worth a
standing pre-push check for any new bash script in this repo.

**Refinement, verified live 2026-08-19 (`scripts-reviewer` Check 7 work, PR #65):** `10#$VAR` alone breaks
on a *signed* value — `10#-08` and even plain `10#-8` (no leading zero at all) are both themselves
"invalid integer constant," because the sign has to sit *outside* the base-qualified literal
(`-10#08` evaluates correctly to `-8`; `10#-08` does not). A script that legitimately accepts a negative
value needs the sign stripped and validated separately, magnitude-bounded and base-10-forced on the
unsigned remainder (`10#${VAR#-}`), then the sign reapplied afterward — `10#$VAR` is only safe as written
for an already-known-non-negative input.

---

## PR #61 / #62 / #65 / #68 — plugin-devkit rules & checkers built from this document (2026-08-19)

This session acted directly on the brainstorm this document produced: added `reviewing-evals`'s 7th
defect-class check (PR #61), built `check_tool_grants.py` (PR #62), added `scripts-reviewer` Checks 7-8
(PR #65), and added the `verify-tool-behavior-before-instructing` rule itself (PR #68). New shapes found
along the way, distinct from anything above:

### Pattern: a rule about precision can itself contain the imprecision it warns against

PR #68's own review — twice, by two different mechanisms — found an overstated absolute claim inside the
brand-new `verify-tool-behavior-before-instructing.md` rule's own body:

1. A local `cross-model-review` pass (single-model, Claude-native — no Codex dispatch) caught an invented
   specific number ("found six review rounds apart") with no supporting evidence, in a rule whose entire
   point is "don't assert unverified specifics."
2. A real Codex PR review, on the same file, separately caught "Only `ast.parse()` can" (copied from this
   very document's own PR #55 row) overstating the claim — other real parsers (`libcst`, `parso`) can also
   do the job; the real point ("a real parser, not regex") didn't need the absolute framing.

**Rule:** a new rule/doc whose subject is precision, verification, or avoiding overstated claims needs an
extra self-audit pass over its *own* prose for the same defect before push — this class of component is
disproportionately likely to contain it, precisely because absolute-sounding language ("only X can",
"always", "never") is the natural way to state a rule crisply, and that's exactly the shape the rule itself
is warning against.

### Pattern: a review-suggested fix can introduce its own new defect class

`scripts-reviewer`'s Check 8 (PR #65) recommended `|| true` as the fix for a SIGPIPE-abort false failure
(an early-exiting consumer like `head` killing an upstream producer like `sort` under `pipefail`+`set -e`).
A later Codex review on the same PR found `|| true` unconditionally converts *any* nonzero exit from that
pipeline into success — not just the SIGPIPE case — silently masking a genuinely different failure (a
permission error, a missing input file, disk I/O failure) that should have aborted loudly. The fix traded a
safe, loud failure for an unsafe, silent one. (Tracked, not yet fixed:
[#67](https://github.com/AndreHahm/andres-cc-marketplace/issues/67).)

**Rule:** when a fix (yours or a reviewer's suggestion) resolves a cited finding by suppressing/catching an
error class, check what *else* that suppression now silently swallows — not just whether the original
symptom is gone.

### Pattern: a mechanical check for "protection present" must recognize equivalent alternate protections, not just one literal idiom

`scripts-reviewer`'s Check 7 (PR #65) flagged any bash arithmetic on a numeric value without a literal
`10#$VAR` base-10-forcing prefix as Critical. A later Codex review found a real false-positive case: a
script whose upstream regex validation (`^(0|[1-9][0-9]{0,2})$`) already structurally rejects every value
that could be misread as octal, making the specific bug the check exists to catch impossible regardless of
the missing literal prefix. (Tracked, not yet fixed:
[#66](https://github.com/AndreHahm/andres-cc-marketplace/issues/66).)

**Rule:** a mechanical/heuristic check for "is the known-bad pattern mitigated" should check whether
*equivalent* protection exists in another form before flagging the one canonical idiom's absence — not
every fix looks like the fix the checker was written against.

### Confirms: `cross-model-review` catches real issues even in single-model (Claude-only) mode, at zero Codex-dispatch cost

Both local `cross-model-review` passes run this session (PR #65, PR #68) were single-model — the user
declined Codex dispatch each time via the mandatory First-Send Confirmation — yet both still surfaced real,
confirmed findings before the first push (3 on PR #65, 1 on PR #68, the "six review rounds apart" claim
above). This strengthens the existing "run `cross-model-review` locally before the first push, treat its
findings as the primary pre-push gate" recommendation (PR #55 section, above): even the free, Claude-native-
only path catches real issues other reviewers would otherwise have to find later, at push→CI→review round-
trip cost.

### Two more "assumed vs. actual" tool-behavior instances (same shape as the Cross-PR meta-pattern above), self-caught this session

| Assumed behavior | Actual behavior |
|---|---|
| `gh api repos/{owner}/{repo}/pulls/comments/{id}/replies` replies to a PR review comment | 404s — the real endpoint requires the PR number in the path: `repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies` |
| `git ls-remote --heads origin <branch> && echo found \|\| echo not-found` correctly reports whether the branch still exists | `git ls-remote` exits `0` whenever the *query itself* succeeds, regardless of whether any ref matched — a deleted branch still produces exit `0` with empty output; only the actual output content (not the exit code) tells you whether a match was found |

Neither was caught by a reviewer — both were self-caught live in this session (the first via a 404 on
attempted use; the second by noticing the script's own logic always printed "found" regardless of the real
state, and re-running with a bare command to check actual output). Both fit the existing Cross-PR
meta-pattern exactly and are recorded here rather than added to that table directly, since that table's own
title scopes it to the original six PRs analyzed before this session's work began.

---

## PR #76 — `recheck-state-before-side-effecting-action` rule (Codex, 4 review rounds, 2026-08-20)

Reconstructed from PR #76's actual GitHub review history (`gh api .../pulls/76/comments`, cross-checked
against fix commits) — this document didn't exist while the PR was in flight. All 4 review rounds were
Codex-only; 6 of 7 findings were fixed, 1 deferred to issue #77.

### Pattern: a new component authored with the wrong *shape* for its type isn't caught by content review alone

Round 1's first finding: `.claude/rules/recheck-state-before-side-effecting-action.md` shipped as a
numbered procedural walkthrough — the shape of a workflow/skill step-by-step, not a rule.
`rule-development/SKILL.md`'s own required template (Description → Incorrect → Correct) was never
followed, even though the file's *content* (the actual TOCTOU guidance) was accurate and well-reasoned.
Content-focused review — is this advice correct, is it clearly written — doesn't catch a structural
mismatch between what a component actually contains and what its own type requires it to contain.

**Rule:** before or immediately after writing a new plugin component (a rule, a skill, an agent), check
that specific component type's own required template/shape — not just whether the content itself is
correct. This is the review-finding-shaped counterpart to
`.claude/rules/consult-naming-conventions-first.md`'s already-learned lesson about component *naming*
(check the convention before naming, not after) — the same principle, one level up: check the convention
for a component's *structure*, not just its name, before writing it.

### Pattern: the fix for a finding can re-assert the very defect the finding raised

Round 2 fixed "this `MUST` rule has no deterministic enforcement" by adding an "Enforcement" section —
which round 3 then found was *itself* broken: it cited the evidence that human review isn't deterministic,
then named human review as the enforcement backstop anyway, directly contradicting itself in the same
paragraph meant to resolve the original finding. The bug wasn't caught by re-reading the fix once it was
written — it took a genuinely *fresh* review round on the already-"fixed" text.

**Rule:** a fix for "X is missing/wrong" needs its own honest check for "does my fix actually avoid
restating X," not just "does my fix add the thing that was missing" — adding an enforcement section
satisfies the finding's literal ask (a section exists) without necessarily satisfying its substance (the
section is coherent). This is the same failure mode PR #68's "a rule about precision can contain its own
imprecision" names, one step removed: there, a *new* component's own prose repeated the defect it was
about; here, a *fix* for an already-identified defect repeated that same defect inside the fix itself.
Extends, doesn't replace, the existing pattern.

### Confirms: "enumerate the full state space" compounds when the first fix is itself incomplete

Round 1 found the rule's own workflow-run-conclusion example was truncated (an ironic finding, given the
rule's whole point is enumerating full state spaces); round 3 found the *fix* for that (adding a `status`
gate before trusting `conclusion`) was itself incomplete — it covered `queued`/`in_progress` but missed 3
more real nonterminal statuses (`requested`/`waiting`/`pending`), caught only by a fresh live check of
`gh --help`. Same lesson as the existing Master checklist item ("have I enumerated the *full* state
space...") — worth noting only because it recurred *twice in the same PR*, once in the original content
and again in that content's own fix.

---

## PR #79 — mandatory `cross-model-review` gate in `create-pr` (Codex + Devin, 3 review rounds, 2026-08-20)

Reconstructed from PR #79's actual GitHub review history. Introduced a mandatory pre-push adversarial-
review gate into `create-pr`'s Pre-flight Checks. 3 review rounds; the round-1 finding recurred, unfixed,
in a second entry path found in round 3 and deferred to issue #81 — the same finding, in a different door,
twice.

### Pattern: a new mandatory gate needs checking against *every* path that reaches the guarded action, not just the one that motivated it

Round 1: two reviewers (Codex and Devin), reasoning independently, both found that `create-pr`'s new
mandatory pre-push review gate could be bypassed — when `create-pr` starts with uncommitted changes, it
invokes `commit` first, and `commit`'s own step 16 can push on its own (auto-push, or an accepted prompt)
*before* the new gate ever runs. Fixed by adding a reciprocal push-skip clause to `commit`'s
nested-invocation path. Round 3, a purely mechanical review pass over the *already-fixed* file, found the
identical bug class in a **second, entirely separate entry path that was never checked**: `commit`'s own
*native* Auto-PR flow (`push_auto_pr: true`, or an accepted post-push prompt) still pushes and then invokes
`create-pr` *after* the push already happened — the new gate reviews an already-published diff on this
path, exactly as it did on the first. The same finding also named a *third* consumer sharing the identical
`commit`→`create-pr` chain shape (`running-a-full-retrospective`'s direct-fix flow) as needing the same
check. This second instance was deliberately deferred rather than fixed in this PR — filed as issue #81,
explicitly named by the author as "same class of bug as #80, but in a different path."

**Rule:** when a new mandatory gate is inserted to guarantee "X always happens before Y," don't stop at
fixing the one path that motivated the gate — enumerate *every* entry path that can reach Y and check each
one independently. Two reviewers converging on the same finding in the primary path (a high-confidence
signal per PR #92's existing lesson) says nothing about whether a *second*, different path to the same
guarded action was ever traced — that took a third, separate round. This sharpens PR #54's "re-trace the
whole chain" pattern into something more specific and more dangerous: it's not just about timing within one
chain, it's about a gate silently having *multiple doors*, and fixing the one a reviewer happened to walk
through first doesn't mean the others were checked.

### Confirms: a behavior-changing fix needs every other section of the same file re-checked, not just the section that changed

Round 2 found that fixing the actual dedup-loop procedure (no longer carrying forward a previously-declined
finding into a later review pass) left the file's own Testing & Validation section still asserting the
*opposite*, pre-fix behavior — two sections of the same document, one correct and one now stale, directly
contradicting each other. Same shape as PR #54's Pattern 6 (a stale eval expectation after a behavior fix)
and this session's own PR #88 findings, just pointed at prose-vs-prose self-consistency within one file
rather than eval-vs-behavior — worth noting as a third confirming instance of "a fix's own aftermath needs
tracing through every place the old behavior was described, not just the place it was implemented."

---

## PR #92 — `await-codex-review.yml` trigger-scope + Checks-API redesign (Devin + Codex, 4 review rounds, 2026-08-21)

Narrowed `await-codex-review.yml`'s trigger from firing on every `synchronize` push to only firing when
Codex's connector would actually re-review (PR opened non-draft, marked ready-for-review, or an explicit
`@codex review` comment), and redesigned `codex-review-recovery` around the resulting `issue_comment`
trigger. The mechanism went through four review-driven rounds on the same PR before landing — each round's
fix created the exact substrate the next round's finding needed to exist.

### Pattern: a correctly-verified fact, traced to only one of its two consequences

Before the first push, `issue_comment` events resolving `GITHUB_SHA`/`GITHUB_REF` to the **default
branch's** commit (not the PR's) was independently verified live against GitHub's own docs — and used
correctly to fix one real problem: `codex-review-recovery`'s own search couldn't filter by `--commit
<PR head SHA>`, since that would never match. What verification caught was applied; what it *didn't*
prompt was tracing the *same* fact's second consequence in the *same* diff: the workflow's own job status
(driven by that same `GITHUB_SHA`) would *also* attach its implicit check-run to the wrong commit,
regardless of the skill's own search logic — never showing up in `gh pr checks` for the PR at all. That
second consequence was caught only a review round later, by both reviewers independently (Devin's analysis
tier, Codex P1).

**Rule:** when live verification of a tool/API fact changes one piece of a diff, don't stop after applying
it there — grep the rest of the *same* diff (and, if the fact is about an ambient value like `GITHUB_SHA`,
every place that value or its logical equivalent is read) for other code paths the same fact would also
affect. A verified fact is only as useful as how completely its consequences were traced.

### Pattern: two reviewers independently converging on the identical root cause is a high-confidence signal — but doesn't mean the fix is complete

Round 1 of live review on this PR produced four findings, but really only two distinct root causes — Devin
and Codex each independently found *both* the concurrency-cancellation bug (workflow-level `concurrency` is
evaluated before the job's own `if:`, so any PR comment could cancel an in-progress wait) and the
check-attachment bug above, using different reasoning paths (Devin's "Prompt for agents" traced the
concurrency-group mechanics directly; Codex's P1 finding traced the consequence for
`codex-review-recovery`'s own reported behavior). Two independently-reasoning reviewers landing on the same
conclusion is strong evidence the finding is real, not a false positive — but it does **not** mean the
*fix* was complete: fixing round 1's two root causes (via a concurrency-group-isolation change and an
explicit Checks-API-managed check-run) introduced the exact standalone-check-run shape that round 3's
`gh pr checks`-workflow-field bug then exploited.

**Rule:** treat convergent independent findings as high-confidence signal to prioritize, not as proof the
resulting fix is itself complete — a fix for a convergent finding still needs its own trace-the-consequences
pass (see the pattern above), especially when the fix changes *how* state is represented (here: a
standalone check-run object with no workflow association, a genuinely new kind of entity this repo's
tooling hadn't had to read before).

### Confirms: iterative review-driven redesign of one mechanism cascades across rounds — same shape as PR #54 Pattern 1

Four consecutive rounds reworked the same "find the fresh check state" mechanism in
`codex-review-recovery`: round 1 shipped `gh run list`/`gh run view` (self-caught bug: filtered by
`--commit`, which can never match an `issue_comment`-triggered run); round 2 replaced that with `gh pr
checks` polling by `startedAt` (review-caught: `gh pr checks`'s `workflow` field is never populated for a
standalone Checks-API check-run, so this could never find the fresh entry, and a cancelled run was never
finalized, leaving it stuck `in_progress`); round 3 replaced `gh pr checks` with a direct Checks-API query
for step 6 only (review-caught: the *same* `workflow`-field gap also blinded steps 2/4's own initial state
check to a standalone check-run's failure, and a `$REPOSITORY` shell variable this skill never defines had
been copy-pasted from the workflow's own `env:` block). Each round's fix was correct for the finding it
addressed and simultaneously left behind (or newly created) the exact gap the next round's reviewers found
— the same "fixing a symptom without re-tracing the whole surface" shape PR #54's Pattern 1 names for
multi-skill lifecycle chains, here applying to a single mechanism redesigned incrementally under review
pressure instead. Reinforces that same rule: when a fix changes *how* a piece of state is represented or
read, re-simulate every consumer of that state end-to-end, not just the one the current finding names.

### Self-caught: `gh api`'s auto-POST default doesn't tell you which HTTP method the *target endpoint* needs

`gh api`'s own documented default ("GET normally, POST if any `-f`/`-F` parameters are given") correctly
matches GitHub's "Create a check run" endpoint (`POST /check-runs`) without an explicit `--method`. It does
**not** extend to "Update a check run", which is `PATCH`-only — passing `-f` fields there without
`--method PATCH` would silently send a POST that doesn't do what the code intends. Self-caught before any
push, by checking the *specific* endpoint's own required method rather than assuming the CLI's generic
default-method rule covered both the create and the update call.

**Rule:** a tool's own generic default-behavior rule (e.g. "adds `-f` → switches to POST") answers "what
method will this tool send," not "what method does this specific endpoint need" — check each individual
REST endpoint's own required method, especially when a create and an update call sit next to each other in
the same script and only one of them happens to align with the tool's default.

### Pattern: a completion/idempotency guard set *before* confirming the guarded action's own success can mask a real failure and produce the wrong fallback value on retry

The workflow's `finalize_check_run` function set its `ALREADY_FINALIZED` guard unconditionally, before
attempting the PATCH call it guards. A transient PATCH failure (network blip, momentary API error) would
still trip the guard — silently masking the failure (the check-run stays `in_progress` with no further
attempt) and, worse, if a later retry path *had* fired anyway, it would have used a different, incorrect
fallback conclusion (`cancelled`) instead of the real one (`success`/`failure`) the original call was
trying to record. Found by Codex (P2), not self-caught. Fixed by moving the guard-set to *after* a
confirmed-successful PATCH, and separately tracking the intended conclusion value (`FINAL_CONCLUSION`) so a
retry — from an `EXIT`/`INT`/`TERM` trap in this case — uses the *correct* value rather than a generic
fallback.

**Rule:** in any retry/cleanup/trap design with an idempotency guard ("only do this once"), set the guard
*after* confirming the guarded action actually succeeded, not before attempting it — setting it early turns
every transient failure into a permanent, silent one. If a fallback value exists for the "never attempted"
case, keep it structurally distinct from "attempted and failed," since a naive retry can otherwise
overwrite a correct-but-not-yet-recorded outcome with the wrong one.

### "Assumed vs. actual" tool-behavior instances from this PR (same shape as the Cross-PR meta-pattern above)

| Assumed behavior | Actual behavior |
|---|---|
| A job-level `if:` gates whether workflow-level `concurrency`'s `cancel-in-progress` can cancel another run | GitHub evaluates workflow-level concurrency at run-creation time, **before** any job-level `if:` runs — a run whose own job will be skipped can still cancel an unrelated in-progress run sharing its concurrency group (reviewer-caught, both Devin and Codex independently) |
| `gh pr checks`'s `workflow` field is populated for any check-run associated with a commit | It's derived from `checkSuite.workflowRun.workflow.name` (confirmed by pulling `gh`'s own source, `pkg/cmd/pr/checks`) — a check-run created directly via the Checks API (no Actions workflow run backing it) has no `workflow` value, so matching on `workflow`+`name` together can never find it (reviewer-caught, Codex P1 + Devin analysis) |
| `issue_comment`-triggered GitHub Actions runs check out/report against the PR's head commit, same as `pull_request` events | `issue_comment` events resolve `GITHUB_SHA`/`GITHUB_REF` to the **default branch's** latest commit (confirmed against GitHub's own docs before the first push, but only one of its two consequences was traced then — see the first pattern above) |

Extends the existing Cross-PR meta-pattern table's own shape (PR #51's row above is the closest sibling:
another `gh pr checks`-field-derivation gotcha, this time about `workflow` rather than the display-vs-file
name distinction) — recorded here per that table's own established convention of scoping new PRs to their
own subsection rather than appending to the six-PR table directly.

---

## PR #88 — `handling-review-findings` skill build + live dogfooding (Codex + Devin + CodeRabbit, 5 review rounds, 2026-08-21/22)

Built a new git-kit skill formalizing PR-review-finding triage, then used it live (manually — the skill
wasn't yet merged, so not dispatchable via `Skill()`) to triage its own introducing PR's review rounds.
This immediately surfaced gaps no internal review had caught, because they only manifest against live
GitHub state. Also includes a security-relevant hook change that recurred across 4 independent bypass
techniques found by 3 different reviewers before the fix's root design (a substring-matching carve-out)
was abandoned rather than patched a 5th time.

### Headline pattern: a substring-matching security carve-out is not a defensible boundary — every "fix" just relocates the bypass

`guard-raw-pr-review.sh`'s `gh api graphql` branch tried to carve out an exception for a "verifiably
read-only" `reviewThreads` lookup by checking the raw command string for the literal word
`"reviewThreads"` with no `"mutation"` keyword present. Four independent techniques, found by three
different reviewers across two rounds, each made those literal substrings say something other than what
the command actually executes:

1. A live self-dispatched `security-reviewer` pass (this session) found file/`$(cat ...)`-supplied
   indirection (`-F query=@file`), plus `--input <file>` as an equivalent bypass, in the same pass.
2. Codex (live PR review, next round) found a plain shell variable holding the query
   (`gh api graphql -f query="$var"`).
3. CodeRabbit (live PR review, same round as #2) found adjacent-quote string concatenation splitting the
   literal word "mutation" across a quote boundary (`query='mut'"ation ..."`) so it never appears as a
   contiguous substring — a genuinely different technique from Codex's, found independently in parallel.

Each fix closed exactly the one shape just found and left the carve-out's fundamental approach
(substring-match a shell command for a safety decision) intact — which is why a different bypass appeared
in the very next round every time. The fix that actually stuck was removing the carve-out entirely: deny
every `gh api graphql` call unconditionally, with no read-only exception at all, even though that means a
genuinely safe lookup now also needs the marker handshake.

**Rule:** when a "detect if this specific dangerous case applies" check is built as string/regex matching
over a raw shell command, and a *second* reviewer finds a *different* way to defeat the same check, stop
patching the blacklist — the approach itself is the bug, not the specific gap. The number of ways to make
a substring "not appear literally while still being executed" (indirection via a file, a variable, a
command substitution, string concatenation, arithmetic construction, base64, ...) is unbounded — the same
"unbounded adversarial tail" shape PR #55's `ast`-vs-regex lesson already names for source-code parsing,
here applying to shell-command safety classification instead. If the check's own false-negative cost is a
security bypass (not just a wrong classification), prefer an unconditional deny with no carve-out over an
increasingly elaborate blacklist.

### Pattern: your own fix for a reviewer finding can rest on the same class of unverified assumption the finding itself was about

A `cross-model-review` pass (this session, before the first push) flagged that `API_RE`'s prefix regex
required `gh`/`api` to sit immediately adjacent, and claimed `gh` accepts global flags (`-R owner/repo`,
`--hostname ...`) before the `api` subcommand — citing this as the reason a caller might write
`gh -R owner/repo api ...` and bypass the guard. The fix widened the prefix class to tolerate flags there.
A follow-up `security-reviewer` dispatch, live-testing the *corrected* file, found the widened prefix had
itself regressed a real, already-covered case (bare-whitespace/`env`-prefixed invocations no longer
matched) — and, checking the *premise* live (`gh --help`/`gh api --help`), found `gh`'s root command has
no persistent flags besides `--help`/`--version`, and `gh api` has no `-R`/`--repo` flag either: **there
was no real `gh <flag> api ...` invocation for the widening to defend against in the first place.** The
original finding's cited bypass didn't reproduce; the fix for it was a pure regression.

**Rule:** a finding from a review pass (`cross-model-review`, Codex, any reviewer) is not automatically
ground truth just because it cites a plausible-sounding tool-behavior claim — verify the claim live
*before* writing the fix, the same "verify, don't assume" discipline this whole document is about, applied
to the *reviewer's own reasoning* and not just your own. Live-testing the premise (`gh --help`) takes
under a minute and would have prevented shipping a regression as the fix for a bug that never existed. A
second review pass on your own fix is what actually caught this here — but catching it one round later is
strictly worse than catching it before the first commit.

### Pattern: a claimed bug, grounded in real documentation, that still doesn't reproduce live

Codex flagged `gh api graphql -f cursor=null` as broken, citing `gh api --help`'s own documented
distinction between `-f` (raw string parameter) and `-F` (typed parameter with magic `null`/number
conversion) — reasoning that `-f cursor=null` sends the literal three-character string `"null"`, not a
real JSON `null`, to a nullable GraphQL variable. Live-testing the exact command against the real API
(twice, independently earlier in the session, plus a clean isolated third test specifically to check this
claim) showed it succeeds and returns correctly paginated results every time. The claim's underlying
documentation citation was accurate; its conclusion about this specific case wasn't confirmed by
execution.

**Rule:** even a reviewer finding that cites real, correctly-read documentation still needs to be verified
by execution before being accepted or declined — a true premise (`-f` is documented as "raw string")
doesn't guarantee the specific conclusion drawn from it (that this exact GraphQL server/variable
combination breaks) without actually running it. This is the same discipline as the Cross-PR meta-pattern
table, pointed at a *reviewer's* claim instead of your own instruction — declining a finding also needs
live evidence, not just "that reasoning sounds plausible so I'll trust it" in either direction.

### Confirms and extends: `gh`'s own subcommands have inconsistent, non-obvious flag support — verify per-subcommand, not per-CLI

Three separate, real findings in this PR were all instances of "assumed a `gh` flag/default that a sibling
subcommand supports also applies here":

| Assumed | Actual |
|---|---|
| `gh api` supports `-R "<owner>/<repo>"` like `gh pr`/`gh issue` do | `gh api` has **no** `-R`/`--repo` flag at all (`gh api --help`) — REST calls must embed the resolved owner/repo directly in the endpoint path; GraphQL calls need `GH_REPO=<owner>/<repo>` instead |
| `gh issue list`/`gh issue create` don't need `-R` since the checkout's own repo is "obviously" the target | They silently default to the *local checkout's* repo when `-R` is omitted — exactly wrong when the PR being triaged is in a different repository, and unlike `gh api`, these two *do* support `-R` |
| `gh issue list` with no flags searches every issue | Defaults to `--limit 30`, **and** to `--state open` only (`gh issue list --help`) — both silently narrow a dedup search below "every issue that could match," in two independent dimensions found by two different reviewers in two separate rounds |

**Rule:** extends the Cross-PR meta-pattern table's own existing rows (PR #51's `gh pr checks`
display-vs-file-name gap, PR #92's `workflow`-field-empty-for-standalone-check-runs gap) — a single CLI
tool's subcommands do not share a uniform flag surface or a uniform set of "sensible" defaults, even
within the same tool family (`gh pr`/`gh issue`/`gh api` all handle repo-targeting differently;
`gh issue list` narrows on two independent axes at once). Never assume a flag or default carries across
sibling subcommands — check each one's own `--help` output.

### Pattern: an API field's name describes a different relationship than the one actually needed

`SKILL.md`'s checkout-verification logic checked `isCrossRepository` (true/false) plus a `headRefName`
string match to decide "does this local checkout belong to the PR being triaged." Both reviewers (Devin
independently, then Codex with "fresh evidence beyond the earlier finding") found this checks the wrong
relationship: `isCrossRepository` describes the PR head's relationship to its own *base* repository, not
whether *this checkout* belongs to that repository — a same-repo PR whose head branch name coincidentally
matches the local branch name passes the check even when the checkout is a different repository entirely.
The fix bound the check to `headRepositoryOwner`/`headRepository`/`headRefOid` instead — fields whose
names, once actually read from `gh pr view --help`'s own field list, unambiguously identify the head.

**Rule:** a field whose name reads as "is this the right thing" needs its actual documented semantics
checked before being trusted for a safety-relevant comparison — `isCrossRepository` sounds like it should
answer "is this checkout in the wrong repo," but it answers a related, different question. This is the
same class as PR #51's `gh pr checks` display-name gap and PR #92's `workflow`-field gap: a field's
intuitive name and its actual, documented meaning can diverge, and only reading the real field list
(not guessing from the name) catches it.

### Pattern: narrowing a regex's search scope doesn't fix a false positive if the false-triggering text is inside the narrowed scope too

Codex found `guard-raw-pr-review.sh`'s endpoint checks (`REPLIES_RE`/`GRAPHQL_RE`) search the *entire*
command string independently of where the matched `gh api` invocation is — so `gh api
repos/o/r/issues/1/comments -f body=graphql` (an unrelated REST call whose comment *body* happens to
contain the word "graphql") gets misclassified and denied. A same-session fix attempt narrowed the search
to just the specific matched `gh api` invocation's own captured text — and didn't actually fix it: a flag
*value* like `-f body=graphql` is still part of that invocation's own text, so the narrowed search still
matched it. The rewrite also reintroduced 2 already-fixed regressions (the whitespace-prefix case) by
redefining the boundary class from scratch instead of reusing the already-verified one. Verified via a
full regression battery before committing anything, so the broken fix was caught and discarded rather than
shipped — filed as a tracked issue instead, since correctly distinguishing "the actual endpoint argument"
from "any other flag's value" needs real `gh` argv-aware parsing, not a regex-only patch.

**Rule:** when a regex-based check's false-positive is "matches the target pattern somewhere it
shouldn't," narrowing the search's *scope* (whole command → one sub-invocation) only helps if the
unwanted match was outside the new scope — if it's a flag *value* within the very invocation you're
trying to permit, scope-narrowing doesn't touch it at all. This is the same underlying limitation as the
carve-out pattern above and PR #55's `ast`-vs-regex lesson: reliably distinguishing "the positional
endpoint argument" from "an arbitrary flag's value" requires actually parsing the command's argument
structure, not pattern-matching over its raw text, regardless of how the search is scoped.

### Pattern: a finding source isn't monolithic — different GitHub review-comment types have structurally different follow-up capabilities

Codex found `SKILL.md`'s Workflow assumes every finding is an inline PR review comment (with a
`comment_id`/thread node the reply/resolve mechanics can act on) — but step 1's own fetch
(`gh pr view --json reviews,comments`) also surfaces PR review *bodies* (a top-level summary, no line
association) and would equally surface a plain conversation comment if one were checked. Neither has a
resolvable thread. The skill can commit and push a fix for such a finding, then have no defined way to
complete its own required reply/resolve step. (Tracked, not yet fixed:
[#94](https://github.com/AndreHahm/andres-cc-marketplace/issues/94).)

**Rule:** when a skill's design assumes "a finding" is one uniform kind of object, check whether the
actual data source (here, three structurally different GitHub API objects — inline review comments, review
bodies, conversation/issue comments) really is uniform before building follow-up logic that assumes it —
the same "enumerate the full state space of anything you're branching on" principle PR #51's Master
checklist already names for a run's `conclusion` field, applied here to "what kind of thing is a finding."

### Methodology note: dogfooding a newly-built skill against its own introducing PR is a high-value, cheap verification step

`handling-review-findings` was built to formalize triaging PR review findings — and this session then
manually followed its own documented Workflow (not yet mergeable, so not dispatchable via `Skill()`) to
triage the review rounds on the very PR introducing it. Round 1 alone surfaced 4 real bugs (the `-R`
misuse, the missing `-R` on `gh issue`, two pagination gaps) that no internal self-review,
`plugin-rulebook-checker` pass, or `security-reviewer` dispatch had caught — because they only manifest
when the documented commands are actually run against live GitHub state with a real cross-repo/
many-issues/many-comments scenario, not when the prose is merely read for internal consistency.

**Rule:** for a skill whose entire job is orchestrating external tool calls, internal review (rulebook
compliance, activation boundaries, consistency checks) cannot substitute for actually running its own
documented commands against the real target system at least once before considering it done — the class
of bug this catches (wrong flags, wrong defaults, incomplete example commands) is systematically invisible
to prose-level review.

---

## PR #172 — `github-issue-lifecycle` skill, freestanding issue work (Codex, 2 rounds, 2026-08-28)

### Pattern: `gh issue close` has a dedicated reason/flag for each closure type, not just one generic path

**What happened:** An instruction folded every "Declined" reason (including "duplicate") into the
generic `not planned` close path. `gh issue close --help` documents a dedicated `--duplicate-of
<number-or-url>` flag together with a `duplicate` reason, which is what actually preserves GitHub's own
duplicate-issue relationship and link to the canonical issue — the generic path silently discards that
data.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| Any "Declined" reason, including duplicate, can close via the generic `not planned` path | `gh issue close` has a dedicated `--reason duplicate --duplicate-of <canonical>` path that preserves the duplicate link; the generic path discards it |

**Rule:** Before folding several "declined" sub-reasons into one generic close path, check the tool's
own `--help` for a reason-specific flag that preserves data the generic path would silently drop.

### Pattern: untrusted issue/comment text in a Bash double-quoted `gh` argument is a shell-injection surface, not a style nit

**What happened:** A workflow placed generated comment/title text directly inside a Bash command's
double quotes before passing it to `gh issue comment`/`gh issue create`. Double-quoting does not
suppress `$(...)`/backtick/`$VAR` shell expansion, so text containing shell syntax — plausible in
summarized pasted logs or attacker-controlled issue content — can execute before `gh` ever receives it.
`gh issue comment --help` documents `-F, --body-file <file>` specifically to read body text from a file
instead of a shell argument.

**Rule:** Any generated text that will be interpolated into a `gh`/git shell command and did not
originate as a fixed literal must go through that command's own `--*-file` flag (reading from a
scratchpad file), never a double-quoted inline argument.

---

## Master pre-push checklist (all PRs analyzed, including this session's #61/#62/#65/#68/#76/#79/#92/#88)

### Tool, API & language behavior — verify, don't assume

- [ ] Does any instruction depend on a tool/API/language behaving a specific way? Verify that behavior
      live (schema via `ToolSearch`, `--help`, a real API call, the language's own parser) rather than
      assuming it from memory or an intuitive field name.
- [ ] Any tool-limit workaround (splitting across multiple calls/questions/batches): checked the tool's
      *full* schema for every constrained dimension, not just the one already known from a prior incident?
- [ ] Does a skill body span multiple tool calls and need to carry a computed value forward? Is that value
      resolved once and echoed as a literal into later instructions, never referenced as a live shell
      variable across separate `Bash` calls?
- [ ] Any new script whose job is "find/extract X from arbitrary source text in language L": using L's
      real parser (`ast` for Python, etc.) instead of hand-rolled regex/string-scanning?
- [ ] Any REST API call whose path includes a nested resource ID (e.g. a PR review-comment reply): checked
      the endpoint's *actual* required path segments live, not assumed from the sibling read/list endpoint's
      shape? (`.../pulls/comments/{id}/replies` 404s; the real path is
      `.../pulls/{pull_number}/comments/{comment_id}/replies`.)
- [ ] Any script that branches on a CLI command's exit code alone (`cmd && ... || ...`) to detect "did X
      happen": confirmed the command actually returns nonzero on the negative case, rather than exiting `0`
      whenever the query itself succeeds regardless of match (e.g. `git ls-remote` on a nonexistent ref)?
- [ ] A `gh api`/similar CLI call that both creates *and* later updates the same kind of resource: checked
      each call's *specific target endpoint* for its own required HTTP method, rather than trusting the
      tool's generic default-method rule (e.g. "adds `-f` → switches to POST") to cover both calls — a
      create and an update endpoint for the same resource can require different methods even when the
      tool's own default only happens to match one of them.
- [ ] Any GitHub Actions workflow using `issue_comment`: does any instruction assume `GITHUB_SHA`/
      checked-out content matches the PR's head? It resolves to the *default branch's* latest commit
      instead — confirmed against GitHub's own docs. This is specific to `issue_comment`, not a general
      non-`pull_request`-event rule: `push` sets `GITHUB_SHA` to the pushed commit, and
      `workflow_dispatch` uses the selected ref's own latest commit — check each event type's own
      documented `GITHUB_SHA` resolution rather than assuming this one behavior generalizes.
- [ ] Any GitHub Actions workflow with `concurrency:` set at the workflow (not job) level: does any job have
      its own `if:` condition? Concurrency is evaluated at run-creation time, *before* that `if:` runs — a
      run whose job will be skipped can still cancel an unrelated in-progress run sharing its group unless
      the group key itself accounts for this.
- [ ] Any code path reading `gh pr checks`' `workflow` field: confirmed the check-run in question is backed
      by an actual Actions workflow run, not created directly via the Checks API (`POST /check-runs`) —
      the field is derived from `checkSuite.workflowRun.workflow.name` and is empty/absent for a standalone
      check-run, so `workflow`+`name` matching can never find one.
- [ ] Any `gh <subcommand>` call assuming a flag or default carries over from a sibling subcommand (e.g.
      `-R` on `gh api` because `gh pr`/`gh issue` support it, or `gh issue list` searching every issue by
      default): checked that *specific* subcommand's own `--help` output, not inferred from a sibling's
      behavior? `gh api` has no `-R`/`--repo` flag at all; `gh issue list` defaults to `--limit 30` *and*
      `--state open` simultaneously.
- [ ] Any API field whose *name* suggests it answers "is this the right target/state" for a
      safety-relevant comparison (e.g. `isCrossRepository` for "does this checkout match"): confirmed via
      the tool's own documented field list that its actual semantics match what's being checked, not just
      what the name implies — a field can describe a real but different relationship than the one needed.
- [ ] A reviewer's finding (Codex, CodeRabbit, `cross-model-review`, human) cites a specific tool/API
      behavior as its justification: verified that specific claim live *before* accepting the finding and
      writing a fix — and before declining it, too. A finding grounded in real, correctly-read
      documentation can still draw a conclusion that doesn't hold for the specific case in question; a
      fix for a finding whose own premise doesn't reproduce is a fix for a bug that never existed, and
      risks being a regression itself.
- [ ] When narrowing a regex/pattern-match's search *scope* to fix a false positive: confirmed the
      unwanted match is actually located *outside* the narrowed scope — narrowing from "whole command" to
      "one sub-invocation" does nothing if the false-triggering text (e.g. a flag's own value) is still
      inside that sub-invocation. If the check needs to distinguish "the actual target argument" from "any
      other argument's value," that's real parsing, not a matching-scope adjustment.
- [ ] Does a skill's design assume "a finding"/"an event"/"a request" is one uniform kind of object? Check
      whether the actual data source can return structurally different object types (e.g. an inline PR
      review comment vs. a review body vs. a plain conversation comment — only one has a resolvable
      thread) before building follow-up logic that assumes uniformity.

### Chain, state & timing

- [ ] Every `Skill(X)` call in the changed body: read X's *actual current* SKILL.md this session (not
      recalled), checked for unconditional nested asks, cwd/branch assumptions, and default-argument
      fallbacks?
- [ ] Every multi-step chain that was just edited: re-simulated the *entire* chain end-to-end, tracking
      cwd/branch/captured-variable state at each step — not just the step that changed?
- [ ] Does this skill/workflow observe external async state (a CI run, a reaction, another actor's
      action) and then take a side-effecting action on it? Does every such action have its own
      *immediate* re-check right before it fires, not a check inherited from an earlier step?
- [ ] Have I enumerated the *full* state space of anything I'm branching on (a run conclusion, a status
      field) rather than assuming it's binary?
- [ ] Every "confirm X is done/closed" check: does it apply uniformly across every path that reaches it,
      or does it need to be scoped per-path because one path's internals aren't actually observable here?
- [ ] When live-verifying a tool/API fact changed one piece of the current diff, grepped the *rest* of the
      same diff (and every other reader of the same ambient value, e.g. `GITHUB_SHA`) for other places that
      same fact would also apply — a verified fact applied to fix one symptom doesn't mean its other
      consequences were traced.
- [ ] Any retry/cleanup/trap logic with an idempotency guard ("only do this once"): is the guard set *after*
      confirming the guarded action actually succeeded, not before attempting it? And if a distinct fallback
      value exists for "never attempted," is it kept structurally separate from "attempted and failed," so a
      retry can't overwrite a correct-but-unconfirmed outcome with the wrong fallback?

### Scope & completeness

- [ ] If a diff/file list is filtered for one purpose (e.g. what to review), does any *other* check that
      also needs "what changed" (trust/security check, mirror-sync check, eval-staleness check) use its
      own correct, independently-scoped pass rather than reusing the filtered list?
- [ ] After writing a "When NOT to Use"/exclusion clause, does it contradict any of this skill's *own*
      worked examples or stated primary use case?
- [ ] Does this change touch a skill governed by a multi-mirror convention (e.g. git-kit's
      `plugins/`/`.claude/`/`.agents/` triple)? Have all mirrors been swept in this same commit?
- [ ] Every new `Bash(...)`/`Skill(...)` call added: is its exact matching grant already in
      `allowed-tools`, checked in this same edit?
- [ ] When a review finding identifies a bug in one function/code block: grepped the rest of the
      file/component for the same anti-pattern signature before considering the fix complete?
- [ ] Does a mechanical/heuristic check flag the *absence* of one canonical mitigation idiom? Checked
      whether an *equivalent* alternate protection already exists elsewhere (e.g. upstream input
      validation that makes the specific bug structurally impossible) before flagging it?
- [ ] Does a fix (yours or a review suggestion) resolve a finding by suppressing/catching an error class
      (e.g. `|| true`)? Checked what *else* that suppression now silently swallows, not just whether the
      original symptom is gone?
- [ ] Is this component itself a rule/doc about precision, verification, or avoiding overstated claims?
      Given its own prose an extra pass for the same defect (absolute language like "only X can", "always",
      "never") before push — this class of component is disproportionately likely to contain it.
- [ ] Writing a new plugin component (rule, skill, agent, command)? Checked that specific component type's
      own required template/shape (e.g. a rule needs Description/Incorrect/Correct, not numbered
      procedural steps) — not just whether the content itself is accurate — before or immediately after
      writing it, not left for a reviewer to catch as a structural mismatch.
- [ ] Does a fix for "X is missing/wrong" actually avoid restating X inside the fix itself? Adding the
      thing a finding asked for (an enforcement section, a status check) satisfies the finding's literal
      ask without guaranteeing the addition is itself coherent — re-read the fix as skeptically as the
      original finding was read, ideally in a genuinely fresh pass, not just a glance after writing it.
- [ ] Does this change insert a new mandatory gate ("X must always happen before Y")? Enumerate *every*
      entry path that can reach Y, not just the one that motivated the gate — two reviewers converging on
      the same finding in the primary path is a high-confidence signal that finding is real, but says
      nothing about whether a second, different path to the same guarded action was ever checked.

### Docs & evals

- [ ] Does this change reverse or correct a previously-documented behavior claim? If so, grep
      `evals/<skill>/evals.json` for any `expected_output` still asserting the old claim.
- [ ] Any "best-effort"/"not definitive" disclaimer in the diff: is there actually a cheap, authoritative
      source that would make this a real check instead of a disclaimer? (If the underlying race genuinely
      can't be fixed client-side — no API field to correlate against — an honest disclaimer *is* the
      correct fix, not a shortcut; see PR #54 Pattern 7 vs. PR #51's reactions-API case.)

### Bash/language footguns

- [ ] Any numeric input flowing into bash `$((...))` arithmetic: bounded in digit count and forced to
      base 10 (`10#$VAR`)?
- [ ] Does that value need to accept a negative number? `10#$VAR` alone breaks on a signed value
      (`10#-08`/`10#-8` are both "invalid integer constant") — sign must be stripped/validated separately
      and reapplied after base-10 forcing on the unsigned remainder.
- [ ] Any `sort | head` (or similar early-exiting consumer) in a bash script running under
      `set -e -o pipefail`: confirmed it can't SIGPIPE-abort on large input?

### Security & verification process

- [ ] Does this change introduce a new trust-boundary or mutation-gate mechanism? If so, has
      `security-reviewer` run against it *before* this first commit (see
      `.claude/rules/require-security-review-before-new-gate.md`)?
- [ ] Is a security-relevant check (a guard, a carve-out, an exception to a deny-by-default rule) built as
      string/regex matching over a raw shell command or other unstructured text? If a *second* reviewer
      finds a *different* way to defeat the same check, stop patching the blacklist — remove the
      carve-out/exception in favor of an unconditional deny rather than iterating toward a 5th bypass.
- [ ] For a skill whose whole job is orchestrating external tool calls: has its own documented Workflow
      actually been run (manually, if not yet mergeable/dispatchable) against the real target system at
      least once — not just reviewed for prose consistency — before considering it done? Wrong flags,
      wrong defaults, and incomplete example commands are systematically invisible to prose-only review.
- [ ] Did I run `cross-model-review` locally before the first push, and treat its findings as the primary
      pre-push gate? (Confirmed worth doing even when declining Codex dispatch — single-model,
      Claude-native-only passes caught real issues on both PR #65 and PR #68, at zero extra dispatch cost.)
- [ ] If dispatching a verification pass, does the prompt explicitly ask for a step-by-step execution
      trace of the chain (not just a general quality/consistency review)?
