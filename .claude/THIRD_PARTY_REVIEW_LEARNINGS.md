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

### Pattern: a frontmatter validator's substring match accepts an unrelated key sharing a text fragment

**What happened:** A smoke test's frontmatter check used `"name:" in fm` and `"description:" in fm` —
substring matches that also accept `skill-name:` and `long-description:`. The check could pass even when
the actually-required `name`/`description` key was entirely absent from the frontmatter. The identical
defect recurred in a sibling skill's own smoke test (see PR #179 below).

**Rule:** A frontmatter/YAML key-presence check must match anchored, non-comment key lines (e.g.
`^name:\s`/`^description:\s` with `re.MULTILINE`), never a bare substring search — a substring match
accepts any key that merely contains the required key's text as part of a longer name.

### Pattern: a workflow's precondition-check gate assumed a sibling workflow had already established its precondition

**What happened:** A skill's "resolve an issue" workflow gated on an open-question check but never
itself fetched the issue's comments — only a separate "work an existing issue" workflow did. A direct
"resolve issue #N" request (bypassing the other workflow) reached the gate with no real state to check
against, and could close an issue based on absent or stale information.

**Rule:** A workflow step that gates on external state must fetch that state itself whenever the step is
a possible direct-entry point, never assume a sibling workflow already populated it — each entry path
must independently satisfy its own preconditions.

---

## PR #101 — `git-kit` `handling-review-findings` round-budget skill (Devin + Codex, 18 review rounds, 2026-08-22)

### Pattern: a comment-body trigger match can't tell which skill/actor posted it

**What happened:** A review-round budget counter re-derived a "triggered cycle" count by matching PR
comment bodies against a reviewer's trigger string (e.g. `@codex review`). The sibling skill
`codex-review-recovery` posts a byte-identical trigger comment as its own stuck-check retry mechanism,
so its comments were indistinguishable from this skill's own proactive triggers and silently inflated
the count, exhausting the round budget early.

**Rule:** A side-effect counter built on matching a comment's *body text* alone cannot establish which
actor/skill posted it. Combine a per-decision marker with an author-ownership check (`author.login`
verified against the account actually running the skill) — the marker text alone is forgeable by
anyone with repo write access, since it's published in the skill's own docs.

### Pattern: AskUserQuestion's reserved/mandatory options must be budgeted into the cap, and the 2-option floor needs an explicit low-count path

**What happened:** A trigger-ask question capped at 4 total options (3 seeded reviewers + 1 mandatory
"no round now" option) was already at capacity; documentation claiming "nothing assumes exactly three
reviewers" was false, since a 4th reviewer would push the question to 5 options. Separately, when fewer
than `min_rounds` cycles have run and only 0 or 1 reviewers remain eligible, omitting the stop option
(to enforce the floor) produces a 0- or 1-item `options` array, below `AskUserQuestion`'s own 2-option
minimum.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A mandatory/reserved option doesn't count against a variable list's own stated capacity | It does — the reserved slot must be subtracted from the total cap before sizing the variable list |
| The "at least 2 options" structural minimum only matters for an over-full question | It also fails on the *under*-full side: 0 or 1 eligible items with no compensating option is invalid |

**Rule:** When sizing an `AskUserQuestion`'s option list against its per-question cap, budget every
reserved/mandatory option into that cap up front — don't treat "N variable items + 1 fixed item" as
independently bounded. Separately, add an explicit path for 0- or 1-eligible-item cases rather than
assuming the variable list will always land in the tool's 2-4 valid range.

### Pattern: group side effects from one logical decision into one unit of count

**What happened:** Selecting two reviewers in one decision posted two separate trigger comments; the
budget counter counted each comment independently, so a single logical review cycle consumed two units
of the round budget instead of one.

**Rule:** When one user decision fans out into multiple physical side effects (e.g. one comment per
selected reviewer), count the *decision* as the unit, not each side effect — tag every side effect from
one decision with a shared batch identifier and dedupe on that identifier before counting.

### Self-caught: `git ls-files` pathspec fails open when run outside the repo root

**What happened:** A trust-boundary check used `git ls-files --error-unmatch .claude/git-kit.local.json`
(a bare relative pathspec) to decide whether a local settings override file was tracked. Live-verified:
this form reports "no match" from any working directory other than the repo root, even for a genuinely
tracked file — silently treating a tracked (and therefore untrustworthy-for-safety-overrides) file as
untracked. Found via a self-dispatched `security-reviewer` follow-up during this PR's own review thread,
not by a third-party reviewer directly.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A bare relative `git ls-files --error-unmatch <path>` pathspec check is cwd-independent | It fails open (reports "not tracked") whenever invoked from any directory other than the repo root |

**Rule:** A `git ls-files`-based trust/tracked-file check must anchor its pathspec to the repo root
(`:(top,literal)<path>`) and be resolved from a repo-root-anchored path — never a bare relative form,
which silently fails open depending on the invoking shell's current working directory.

---

## PR #108 — `analysis-kit` structural smoke tests + downstream QA fixes (Devin + Codex + CodeRabbit, 16 review rounds, 2026-08-24)

### Pattern: a mirrored script's own relative-path root derivation breaks when run from the mirror copy

**What happened:** A smoke test derived its own plugin root as `SKILL_DIR.parent.parent` — correct only
under `plugins/analysis-kit/`. The byte-identical mirror copy under `.claude/skills/<skill>/scripts/`
resolves that same expression to `.claude`, which has no matching `scripts/`/`references/` directory, so
every mirrored copy's structural checks false-failed while the canonical copy passed.

**Rule:** A script that is deliberately shipped as a byte-identical copy at more than one directory
depth (this repo's `plugins/<name>/` ↔ `.claude/` mirror convention) must resolve its own root by
discovery (e.g. walk up to find `.git`) rather than by a fixed parent-directory-count assumption —
the count is only valid at one of the copy's locations.

### Pattern: a basename-substring "is this grant used" check can't distinguish a real invocation from a documentation mention

**What happened:** A smoke test's `check_bash_grants` reduced each declared grant to its basename and
searched the whole skill body for that string. A grant named only in a `## Reference Guide` table row
(documentation, not an actual invocation) satisfied the "used" check, so a genuinely-unused grant could
hide behind its own documentation mention.

**Rule:** A check for "is this declared permission/grant actually used" must distinguish an executable
invocation from a documentation-only mention of the same name — a bare substring/basename search across
all body text conflates the two. Exclude documentation-only sections (or require an executable-command
shape) rather than matching anywhere.

### Pattern: a workflow's own dependency gate must cover every hard dependency its later, unconditional steps invoke

**What happened:** A direct-fix path's up-front dependency check only required `git-kit` to be resolved.
Its own later, unconditional step invoked `Skill(plugin-rulebook)` — a `plugin-devkit` skill. A supported
standalone configuration (`analysis-kit` + `git-kit`, no `plugin-devkit`) was offered the direct-fix path
and then stalled mid-fix, with modified state, once the undeclared dependency was reached.

**Rule:** A workflow's own up-front "can I run this path" gate must check every dependency its later
steps unconditionally invoke, not just the dependency named at the gate itself — an unconditional
downstream call is an undeclared dependency if the gate doesn't also check for it.

### Pattern: "a path exists at the expected mirror location" doesn't prove it's a 1:1 mirror safe to auto-overwrite

**What happened:** A direct-fix flow treated "a corresponding `.claude/`-side file exists" as sufficient
grounds to resolve and auto-edit it as the source's mirror. For `skills/`/`agents/`/`commands/`/`rules/`
that assumption holds (a clean 1:1 mirror), but `plugins/<name>/hooks/hooks.json` has no such
relationship to `.claude/hooks/hooks.json` — the latter is a *merged aggregate* of several plugins' own
hook configs, not a copy of any single one. Editing "the mirror" there could silently overwrite an
unrelated aggregate file with the wrong plugin's content.

**Rule:** Before treating a resolved "mirror path" as safe to auto-overwrite, verify it is actually a
clean 1:1 mirror of the one source being edited — existence alone doesn't establish that. A
many-sources-to-one merged/aggregate destination is a categorically different case and must be routed
to a hand-off/human path instead of a direct auto-edit.

---

## PR #112 — `codex-kit` full downstream QA audit (Devin + Codex + CodeRabbit, 28 review rounds, 2026-08-24)

### Pattern: an unanchored "sensitive filename" substring match masks ordinary files from review

**What happened:** A secret-filename classifier matched broad terms (`token`, `password`, etc.) anywhere
in a basename, so ordinary files like `tokenizer.ts`, `token_bucket.go`, `password-validator.js` were
classified as sensitive. The consuming code then replaced their contents with a skip marker before
handing them to a review/audit pass — silently producing a "clean" result without ever reviewing the
real content of an ordinary new file. Confirmed real but not fixed in this PR — deferred as a
cross-plugin ownership question (the same pattern is shared with `git-kit`'s `scan-staged-files.sh`),
tracked via issue #109's own candidate 28.

**Rule:** A sensitive-filename classifier used to gate content masking must anchor to genuinely sensitive
filename *shapes* (e.g. `.env`, `id_rsa`, `*.pem`), not match a broad term anywhere in the basename — an
unanchored match doesn't just mis-flag; it silently defeats the review it's embedded in.

### Pattern: reading untracked file content via a symlink-following stat call can leak an unrelated secret's contents

**What happened:** An untracked-file formatter used `fs.statSync()` (which follows symbolic links) to
check a file before reading its content for a review/audit context. An untracked file with a safe-looking
name that is actually a symlink to a real secret (e.g. `~/.ssh/id_rsa`) passed the basename check, and
the *target's* content was then read and forwarded.

**Rule:** A security-relevant "is this safe to read" check on an untracked/unknown file must inspect the
file's own type without following links (`lstatSync()`/equivalent) and skip symbolic links outright
before any content read — a symlink-following stat call defeats a basename-based secret screen entirely.

### Pattern: a "tampered copy" regression test can pass for the wrong reason if the copy runs from a different directory than the original

**What happened:** A smoke test tampered with a copy of a hook script placed under the OS temp directory
to verify the hook's own catch-path behavior. Because the copy's relative imports/assets no longer
resolved from that location, Node could exit during module loading — before the catch path under test
ever ran — and the test's own "non-zero exit means regression detected" assertion still reported a pass,
for a reason unrelated to the code path it was meant to exercise.

**Rule:** A regression test that runs a tampered copy of a script must place that copy beside the
original (not a generic temp directory) so its relative imports/asset resolution stay intact — otherwise
a module-loading crash can make the test vacuously "pass" without ever reaching the logic under test.

### Pattern: a YAML permission-grant scanner anchored to one quoting style misses the equally-valid unquoted form

**What happened:** A smoke test rejecting a prohibited `Skill` grant in `allowed-tools` used a regex
matching only the quoted forms (`"Skill"`/`'Skill'`). A valid, equally-legal bare/unquoted YAML flow-list
entry (`allowed-tools: [Read, Grep, Glob, Skill]`) passed the check and restored the prohibited grant.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A grant name in a YAML flow sequence is reliably quoted | YAML flow-sequence scalars are valid either quoted or bare — a check anchored to one form misses the other |

**Rule:** When writing a check against a YAML list entry's literal text, split and normalize each entry
(strip surrounding quotes/whitespace) before comparing — never anchor the pattern to one specific
quoting style, since YAML permits multiple equally-valid forms for the same value.

### Pattern: a permission-hardening fix scoped to newly-created objects leaves a pre-existing, already-loose object unaddressed

**What happened:** A state directory and a job log file were only narrowed to safe permissions
(`0o700`/`0o600`) via the flags passed to their own creation calls (`mkdirSync`/file-open mode). A
directory or file that already existed on disk before this code ran (e.g. created under an older,
looser-permission code path) never passed back through creation, so it kept its original, looser mode.

**Rule:** A permission-hardening fix must explicitly re-narrow objects that could already exist on disk
before the code path runs (e.g. an explicit `chmodSync`/`fchmodSync` after open/mkdir), not rely solely
on the creation call's own mode flag — that flag only ever governs objects the current run itself creates.

---

## PR #121 — `git-kit` security hardening and rulebook fixes from QA sweep (Devin + Codex + CodeRabbit, 17 review rounds, 2026-08-24)

### Pattern: `core.fileMode=false` locally can mask a missing executable bit on a directly-invoked helper script

**What happened:** Two new helper scripts were committed at git mode `100644` (non-executable) despite
being invoked directly (not via `bash <path>`) from a skill's own instructions. The local dev environment
had `core.fileMode=false` *and* both files already had the executable bit set on local disk — so nothing
in local testing ever surfaced the actual committed mode. A fresh clone with standard Unix checkout
permissions would fail with exit 126 (`Permission denied`) the first time the skill ran.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A script's local on-disk executable bit reflects what's actually committed | With `core.fileMode=false`, git ignores local permission changes entirely — only the index's own recorded mode matters, and it can silently diverge from disk |

**Rule:** For a script a skill invokes directly (not via an interpreter prefix), verify its *git index*
mode (`git ls-files -s <path>` — expect `100755`) rather than trusting a local `ls -la`, especially in
any environment with `core.fileMode=false` (checkable via `git config core.fileMode`) — local disk state
and the committed mode can silently diverge.

### Pattern: a staged-file rename can be silently turned into a deletion by an unstage that only restores the destination path

**What happened:** A sensitive-file scanner built on `git diff --cached --name-only` sees only the
destination path of a staged rename (e.g. `config/plain.txt` → `config/secrets/plain.txt`). When the
scanner "protectively" unstaged the flagged destination path, the rename's source-side deletion stayed
staged, so the commit would have silently recorded a bare deletion of the original file — data loss
disguised as a rejected rename.

**Rule:** A staged-file scan/restore built on rename-blind `git diff --cached --name-only` must switch to
rename-aware `git diff --cached --name-status -M` and, when a flagged path is one side of a detected
rename, restore *both* sides — restoring only the visible destination path silently converts a rejected
rename into a real deletion.

### Pattern: a least-privilege grant-narrowing pass must be reconciled against the component's own documented capability list

**What happened:** An earlier security-motivated narrowing pass replaced an unbounded `Bash(gh pr:*)`/
`Bash(gh issue:*)` grant with an explicit allowlist. The new list omitted several subcommands
(`gh issue view/comment/reopen/pin/transfer`, `gh pr close/reopen/checkout/ready/diff`) that the same
skill's own reference docs still documented as supported — the security fix silently broke advertised
functionality it never checked against.

**Rule:** When narrowing a tool grant for least privilege, cross-check the resulting allowlist against
every subcommand the component's own reference/documentation files claim to support — a scope-tightening
pass that only reasons from "what's obviously dangerous" rather than "what's actually documented as
supported" can regress real, advertised functionality.

---

## PR #132 — `plugin-devkit` self-reflexion and review findings across 4 skills (Devin + Codex + CodeRabbit, 18 review rounds, 2026-08-24)

### Pattern: a credential-stripping subprocess sanitizer applied unconditionally can break a legitimately-trusted custom runner

**What happened:** A test harness stripped credential-shaped environment variables before launching any
backend, to protect against an untrusted agent description reaching a live session. This unconditionally
also stripped credentials from a user-configured custom/fallback runner (`AGENT_TRIGGER_LLM_COMMAND`)
that legitimately needs its own API key to function — the fallback path exited with a provider error
instead of ever running.

**Rule:** A security-motivated environment/credential-stripping step must be scoped to the actual risk
path (an untrusted target reaching a trusted credential) — applying it blanket to every subprocess launch
can silently break a differently-trusted path (a user-configured runner that is itself the trust boundary
for its own credentials).

### Confirms: a frontmatter "required key present" substring check is satisfied by any superstring containing that key

**What happened:** A smoke test's frontmatter check used a bare substring test for `"name:"` and
`"description:"`. `rename:` satisfies the first; `short-description:` satisfies the second — so a file
missing both actually-required keys was reported as having valid frontmatter. This is the same
underlying anti-pattern as PR #108's `check_bash_grants` basename-substring finding above, recurring
independently in a different validator (`check_frontmatter`) in a different skill within the same week.

**Rule:** A "does this required key/name exist" check must anchor to the start of a line (or another
unambiguous boundary), never a bare substring test — a substring/basename match is satisfied by any
superstring that happens to contain it. (See also this document's PR #108 `check_bash_grants` pattern —
the same anti-pattern, independently found twice in five days.)

### Pattern: confirming a script's file location is contained is not the same as confirming it's safe to execute

**What happened:** A skill that reviews a third-party/PR-supplied plugin runs that plugin's own
`scripts/smoke_test.py` after checking the script's resolved path is contained within the checkout (a
symlink-escape guard). Path containment says nothing about what the script does once it actually runs —
`python <path>` executes it with the user's full filesystem/network/environment privileges, so a
malicious target-authored script can exfiltrate credentials or modify files outside the checkout before
producing a PASS/FAIL result. Confirmed real but explicitly deferred rather than fixed in-PR — filed as
issue #134, since closing it properly is a design decision (real sandboxing vs. a new trust gate) that
would itself need its own dedicated security review before shipping.

**Rule:** A path-containment check (blocking symlink escape) is necessary but not sufficient to treat an
untrusted, target-authored script as safe to execute — real safety requires either genuine sandboxing
(OS-level or a credential-stripped subprocess) or an explicit trust-confirmation gate before execution,
not a location check alone.

---

## PR #133 — `plugin-devkit` add skill-authoring-evals upstream source (Devin, 2 review rounds, 2026-08-24)

### Pattern: a three-way tracked mirror's sync/parity config can be incomplete for one of the three copies

**What happened:** This repo tracks three copies of a registry file (`plugins/plugin-devkit/...`,
`.claude/...`, `.agents/...`). The PR updated the first two but not the third; no CI check caught the
drift because the sync/parity config (`.claude/marketplace-sync.json`'s `codex_exports.skills`) doesn't
list this skill at all, so `plan_exports`/`check_staged_parity` never compare its `.agents/` copy.

**Rule:** A mirror-sync/parity tool's own registration list must be checked for completeness whenever a
skill is added — a skill genuinely tracked in 3 locations but only *registered* for 2 of them silently
loses parity checking on the unregistered copy, with no error at any layer.

---

## PR #137 — `git-kit`/`analysis-kit` close plugin-auditor findings on 4 skills (Devin + Codex + CodeRabbit, 8 review rounds, 2026-08-25)

### Pattern: a Git object-ID validation regex rejects case/length variants Git itself accepts

**What happened:** A guard regex (`^[0-9a-f]{7,40}$`) rejected uppercase hex SHAs (which `git rev-parse
--verify` resolves correctly) and 64-character SHA-256-repository object IDs. The identical regex was
independently duplicated into two skills (`analyzing-plugin-components`, `analyzing-sessions`), and a
third, still-unfixed instance was self-disclosed in `plugins/git-kit/scripts/remap-handoff-shas.py`.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A Git object ID is always lowercase hex, 7-40 characters | Git accepts uppercase hex, and a SHA-256 repository's object IDs are 64 characters |

**Rule:** A Git object-ID shape check must accept both hex cases and the repository's actual supported
hash length (`^[0-9a-fA-F]{7,64}$`), verified live against `git rev-parse --verify`/`git show` rather than
assumed from a remembered SHA-1-only shape.

### Pattern: a security allowlist must be the intersection of "valid per the domain tool" and "safe per the execution context" — not either alone

**What happened:** A branch-name guard's regex was too strict, rejecting Git-valid, shell-safe characters
(`+`, `@`, `=`). The reviewer's own suggested alternative — "just validate against Git's own ref syntax" —
was independently verified and proven *unsafe*: `git check-ref-format` accepts many shell metacharacters
(`;`, `&`, `|`, `$`, backticks, parens, quotes) as valid ref-name characters, so adopting it would have
reopened the exact shell-injection surface the guard exists to close.

**Rule:** When correcting a security allowlist that's "too strict," verify any suggested broader rule
(including a reviewer's own alternative) against *both* domains it must satisfy — valid per the consuming
tool, and safe per the execution context the value will be interpolated into — before adopting it; a rule
valid in one domain can be actively unsafe in the other.

### Pattern: a verification step written as a conditional's continuation clause can be structurally unreachable on the untested branch

**What happened:** A "verify remote branch deletion" step was written as prose continuing directly from
"if this command exits non-zero" — with no separate clause at all for the exit-0 (normal success) path.
On a clean successful merge, the entire verification block was structurally unreachable, even though a
separate checklist elsewhere asserted "always checks."

**Rule:** A documented procedural step's own literal grammatical structure can scope a check to only one
branch of a conditional, the same way code can — when a checklist and a step's own prose disagree about
whether a check "always" runs, re-read the step's actual sentence structure for which branch it's
grammatically attached to, don't trust the checklist's summary claim.

### Methodology note: verify a "revert this unrelated formatting" nitpick against the project's own enforced formatter before reverting

**What happened:** CodeRabbit flagged several import-order/wrapping/spacing changes as "unrelated
formatting." Reverting them in a scratch copy and re-running this repo's own mandatory `ruff format`/
`ruff check --fix` reproduced the exact same reordering/wrapping — confirming the "unrelated formatting"
was deterministic output of the project's own required pre-commit tooling, not a discretionary edit.

**Rule:** Before reverting a review finding that flags "unrelated formatting changes," check whether
they're the deterministic output of the project's own enforced formatter/linter — reverting a formatter's
own output just causes it to be silently reapplied the next time the file goes through the project's
required commit flow.

---

## PR #141 — `plugin-devkit` add plugin-inventory and marketplace-inventory skills (Devin + Codex + CodeRabbit, 25 review rounds, 2026-08-25)

### Pattern: comparing ISO8601 timestamp strings lexicographically is not the same as comparing them chronologically

**What happened:** A `graded_at` field was compared as a raw string (`max(..., key=lambda e:
e["graded_at"])`) to find the most recent entry. `2026-08-25T10:00:00+10:00` sorts lexicographically
*after* `2026-08-25T01:00:00Z`, even though the `+10:00` offset makes it chronologically *earlier* in real
UTC time — the wrong score became "current."

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| Sorting ISO8601 timestamp strings lexicographically gives chronological order | It only does when every value shares the same UTC offset/format — mixed offsets (or a bare non-`Z` format) break it |

**Rule:** Before using string comparison to order timestamps, confirm every value is normalized to the
same UTC representation (or parse to a real datetime first) — a lexicographic comparison of ISO8601
strings with differing offsets silently produces the wrong chronological order.

### Pattern: a naive key→record index silently resolves a legitimate key collision by array order, not by an explicit rule

**What happened:** Building a `{key: record}` index via a dict comprehension (or a bare `next(...)`
lookup) over records where two entries can legitimately share the same lookup key (an active and a
retired record with the same name) silently kept whichever record happened to appear last (or first) in
array order. A live update could then land on the wrong (retired) record while the active one stayed
stale, or a conflict could be reported against the wrong record.

**Rule:** When a schema legitimately allows two records to share the same lookup key, an index or lookup
built from that key needs an explicit tie-breaking rule (e.g. always prefer the active record) — silently
resolving the collision by iteration/array order is order-dependent and can silently act on the wrong
record.

### Pattern: an aggregation over a keyed collection that should mirror a sibling collection must reject a partial key set, not silently average the present subset

**What happened:** A security-score rollup averaged whatever entries existed in `component_security_scores`
without checking they matched `component_scores`' full key set. Omitting just one component's security
score meant the rollup silently averaged the *remaining* subset — an omitted critical component became
indistinguishable from "this component scored perfectly," materially inflating the published result.

**Rule:** When an aggregation is supposed to run over a complete, corresponding key set from a sibling
collection, reject a partial/mismatched key set outright before computing the mean/rollup — silently
degrading to "average of what's present" makes a missing value look identical to a perfect one, which is
the worst possible default for anything security- or quality-relevant.

---

## PR #142 — `plugin-devkit` add plugin-conception skill as upstream/maintenance Phase 1 (Devin + Codex + CodeRabbit, 19 review rounds, 2026-08-26/27)

### Pattern: adding a new enumerated classification value to a multi-stage pipeline requires threading it through every consumer

**What happened:** Introducing a `Create` classification (alongside existing Enhance/Repair/Consolidate/
Reposition/Retain/Reject/Defer) required updates in at least five separate places across the same PR:
`plugin-lifecycle-maintenance`'s routing table (had no Create disposition — candidates were silently
stranded), `plugin-lifecycle-upstream`'s auto-detection (resumed Ideate for any brief without checking
classification, including non-Create ones that should have been rejected), `plugin-conception` itself
(wrote a full brief for a Retain outcome that should short-circuit with no brief), `build-handoff-writer`
(never consumed the new Conception Brief artifact type), and `plugin-planning` (assumed
Enhance/Consolidate/Reposition for any brief without validating its actual classification).

**Rule:** When adding a new enumerated classification/type value to a system with multiple independent
consumers (routing tables, auto-detection branches, schemas, downstream agent input contracts), enumerate
every consumer that branches on the existing values and update each one explicitly — a single un-updated
consumer silently drops or misroutes the new value, and this can recur in more than one place in the same
change.

### Confirms: the basename/substring-match anti-pattern recurred a third and fourth time, independently

**What happened:** Both a frontmatter-key check (`"name:" in fm` satisfied by `rename:`) and a Bash-grant
"is this invoked" check (a bare command-word mention, e.g. "date", satisfied an allowed-tools entry with
no actual invocation) recurred in this PR's own new skills — the same underlying anti-pattern this
document already names from PR #108 (`check_bash_grants`) and PR #132 (`check_frontmatter`), now confirmed
a third and fourth independent time within about two weeks.

**Rule:** (Same as PR #108/#132's entries — see those for the full rule.) The recurrence count itself is
the notable fact here: this anti-pattern has now independently appeared four times across four different
skills' own smoke-test validators, suggesting a shared validator module (rather than four independently
hand-written copies) would close the whole class at once.

---

## PR #143 — `git-kit` add resolving-merge-conflicts skill (Devin + Codex + CodeRabbit, 24 review rounds, 2026-08-26)

### Pattern: `${var%.*}` on a dotfile-shaped name strips the whole name to empty, and an empty grep pattern matches everything

**What happened:** `${filename%.*}` (strip the shortest suffix matching `.*`) on a pure dotfile like
`.gitignore` treats the leading dot as *the* extension separator, stripping the entire name to an empty
string. `grep -iF -- "$base_name"` then received an empty fixed-string pattern, which matches every line —
the relocation-target search listed nearly every tracked file in the repository.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| `${filename%.*}` always leaves a non-empty "base name" for any real filename | A pure dotfile (no extension beyond the leading dot) strips to an empty string |
| An empty pattern passed to `grep -F` matches nothing (or errors) | An empty fixed-string pattern matches *every* line |

**Rule:** After a shell parameter-expansion strip operation intended to produce a "base name," explicitly
guard against an empty result (falling back to the original value) before using it as a search pattern —
both halves of this bug (the dotfile edge case, and grep's own empty-pattern behavior) are individually
easy to miss.

### Pattern: `git show N:file` without a leading colon is parsed as a revision literally named N, not an index stage

**What happened:** `git show 2:<file>` / `git show 3:<file>` (no leading colon) is parsed by Git as a
request for a revision named `2`/`3`, which doesn't exist — exiting 128 with `fatal: invalid object name`.
Index-stage syntax requires the leading colon: `:2:<file>`/`:3:<file>`.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| `git show <stage-number>:<file>` addresses an index stage | Git parses this as a revision name; index-stage syntax requires a leading colon (`:<stage-number>:<file>`) |

**Rule:** When addressing a merge conflict's index stage via `git show`, always use the leading-colon
`:<stage>:<file>` form — the bare `<stage>:<file>` form is syntactically valid Git syntax for a different,
unrelated meaning (a revision name), so it fails with a plausible-looking but misleading error rather than
an obvious typo error.

### Pattern: a Git-operation completion check must scope content scans to what changed and model the operation's full state lifecycle

**What happened:** Two related validator bugs in the same conflict-resolution logic: (1) once no unmerged
paths remained, the validator scanned *every tracked file* in the repository for conflict-marker-shaped
lines (`<<<<<<<`, `=======`, `>>>>>>>`), so legitimate content merely resembling a marker (including this
very skill's own documentation) made validation permanently fail; (2) a separate check treated
`MERGE_HEAD`'s mere presence as failure, without accounting for the fact that `MERGE_HEAD` legitimately
persists after every conflict is resolved and staged, until the merge commit itself is created.

**Rule:** A Git-operation completion/validity check needs two disciplines together: scope any content scan
to what actually changed (staged files/diff), never the whole tracked tree, and model the operation's full
state lifecycle explicitly (e.g. "in progress," "resolved but uncommitted," "complete") rather than
treating a state marker's mere presence as equivalent to "not yet done."

### Pattern: a filename beginning with `-` is parsed as a command option unless `--` terminates option parsing first

**What happened:** Found independently in two different scripts of the same skill:
`validate-conflicts.sh`'s `grep '^<<<<<<<\|^=======\|^>>>>>>>' "$file"` and
`handle-deleted-modified.sh`'s `basename "$file"` — both missing a `--` before the variable filename
argument. A Git-valid filename beginning with `-` (e.g. `-a`) is parsed as a command option instead of a
positional argument: `grep` silently read from stdin instead of the file (returning "no match" instead
of detecting a real conflict marker), and GNU `basename -a` exited with a "missing operand" error,
aborting the whole script under `set -e`.

**Rule:** Any command invoked with a variable filename that could plausibly begin with `-` (any Git-valid
path) needs an explicit `--` to terminate option parsing before the filename argument — omitting it lets
an adversarial or merely unlucky filename be silently reinterpreted as a flag.

### Pattern: a backup mechanism preserving original relative paths can collide with a report file written into the same directory

**What happened:** A conflict-resolution backup mechanism copied each conflicted file to a backup
directory under its own original relative path, and separately wrote a generated `SUMMARY.md` report into
the top level of that same directory. A conflicted file that happened to be named `SUMMARY.md` had its
backup silently overwritten by the report — the exact safety net the backup mechanism exists to provide
was lost for that one filename.

**Rule:** When a mechanism backs up files by their original relative path into a directory that also holds
generated metadata/report files, reserve a namespace (e.g. a dedicated `files/` subdirectory) for one of
the two — otherwise any original path matching the metadata filename silently collides with it.

### Self-caught: `CLAUDE_PLUGIN_ROOT` resolves to the plugin's root directory, not an individual skill's own directory

**What happened:** Every script invocation in this new skill used `${CLAUDE_PLUGIN_ROOT}/scripts/<name>`,
which for an installed plugin resolves to `<plugin-root>/scripts/<name>` — but this skill's helper scripts
live under `<plugin-root>/skills/resolving-merge-conflicts/scripts/`, so every call failed with "No such
file or directory." Confirmed against sibling precedent (`analysis-kit`, `codex-kit` both already
reference their own skill-local files as `${CLAUDE_PLUGIN_ROOT}/skills/<name>/...`).

**Rule:** `CLAUDE_PLUGIN_ROOT` always resolves to the *plugin's* root, never an individual skill's own
directory — any reference to a skill-local script/resource must explicitly include the
`skills/<skill-name>/` segment.

---

## PR #147 — plugin-devkit testing-mandate rules (R28-R32) (devin-ai-integration[bot], chatgpt-codex-connector[bot], 11 rounds, merged 2026-08-27)

### Pattern: a content-scan validation heuristic can misclassify a legitimately short, intentional regex as a vacuous assertion

**What happened:** A new plugin-rulebook anchoring check treated every short, unanchored `re.search`
branch in a skill's own quality-gate code as a "vacuous SKILL.md assertion." A real, legitimate check in
`plugin-grader` used exactly this shape to detect shell metacharacters (`&&`, pipes, semicolons)
anywhere in a command line — intentionally short and unanchored, since the pattern must match those
characters at any position. The unconditional new rule produced a false REQUIRED failure on valid code.

**Rule:** A content-scan validation heuristic that flags "suspiciously short/unanchored" patterns as
defects must scope itself to the actual context it's meant to catch (e.g. only assertion-content
variables) rather than applying unconditionally — a short, unanchored regex can be entirely intentional
when the thing it's matching can legitimately appear anywhere in its target string.

---

## PR #148 — stabilize merge-pr/git-worktrees merge-rebase process (devin-ai-integration[bot], chatgpt-codex-connector[bot], 12 rounds, merged 2026-08-27)

### Pattern: a one-shot guard marker consumed by the first attempt of a multi-step operation isn't automatically valid for a fallback retry

**What happened:** `guard-raw-pr-ops.sh` consumes git-kit's one-shot marker file on the *first*
`gh pr merge --rebase` attempt. When that attempt failed and a documented fallback path (readiness
checks, user confirmation, retry) ran afterward, the marker was already gone — the retry was
unconditionally blocked by the same guard regardless of the marker's 60-second TTL, since the TTL never
even got a chance to matter.

**Rule:** A one-shot guard-marker mechanism must be rewritten immediately before *every* attempt of the
guarded operation, not just the first — including inside any documented fallback/retry branch.

### Pattern: `git merge-base --is-ancestor` tests the wrong relationship for "does this commit exist and is it reachable"

**What happened:** For a normal cherry-pick candidate living only on a feature branch, the commit is
*intentionally* not an ancestor of the target — that's exactly why it needs cherry-picking. Using
`--is-ancestor` to validate a commit is real/reachable therefore rejected precisely the commits that
needed the operation, inverting the check's own purpose.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| `git merge-base --is-ancestor <sha> HEAD` can confirm a commit exists/is reachable | It answers a narrower question — "is the first ref an ancestor of the second" — which a legitimate not-yet-merged commit fails by design |

**Rule:** Verify a commit's existence with `git cat-file -e <sha>^{commit}` and its reachability with
`git branch --all --contains <sha>`; reserve `--is-ancestor` for its actual purpose (checking whether one
ref is already integrated into another), never as a general object-existence/reachability check.

### Pattern: a tree-hash-equality dedup heuristic can discard a commit that's structurally identical to an earlier one but semantically required

**What happened:** Two commits sharing the same resulting tree aren't necessarily redundant replays — if
commit A sets a tree, B changes it, and C reverts B back to A's tree, A and C are tree-identical but C is
still required when replaying the sequence (omitting it leaves B's change applied). Classifying tree
equality as "duplicate, safe to drop" can silently produce an incorrect result for exactly this common
revert shape.

**Rule:** Tree-hash equality between two commits should trigger history-aware investigation (or a
user-facing confirmation), never automatic removal from a resolved commit list — content equality
doesn't imply the commit is redundant.

### Pattern: a bare, no-argument `gh repo view` silently resolves to the current checkout's repository, not the repository actually being operated on

**What happened:** When an accepted PR reference pointed to a different repository than the current
checkout (a full cross-repo URL), a later step deriving `{owner}/{repo}` via a fresh `gh repo view` call
(rather than reusing the already-resolved PR's own repo) queried the *current directory's* repository
instead — `gh repo view --help` confirms this is its documented default behavior with no argument.

**Rule:** Once an operation has resolved its real target repository from a specific input (a PR URL, an
explicit `--repo` flag), reuse that resolved value for every subsequent API call in the same operation —
never re-derive repo coordinates via a bare, context-dependent command that silently assumes "the
current directory."

### Pattern: a GitHub REST list endpoint's documented page cap isn't overcome by `--paginate`, and a returned commit SHA isn't guaranteed to exist in the local object database

**What happened:** Two related gaps in the same cherry-pick strategy: GitHub's "list commits on a pull
request" endpoint caps at 250 commits regardless of `--paginate` — a PR with more commits than that
silently truncates, so a strategy relying on it can report success after cherry-picking only part of a
large PR. Separately, even a correctly fetched, valid SHA can be absent from the local git object
database (e.g. a maintainer checkout that never fetched the feature branch), so `git cherry-pick` fails
with an unknown/bad-object error deep into the operation rather than being caught up front.

**Rule:** When a documented API endpoint has a hard page cap, fall back to a genuinely paginated
alternative (e.g. the compare endpoint) once the cap is hit rather than trusting `--paginate` to walk
past a server-side ceiling; separately, verify every commit a remote API returns actually exists locally
(`git cat-file -e`) and fetch it if missing before handing the list to a cherry-pick step.

---

## PR #154 — lazy-load 7 always-loaded plugin rules (chatgpt-codex-connector[bot], devin-ai-integration[bot], 8 rounds, merged 2026-08-27)

### Confirms: this PR is the originating incident behind `.claude/rules/verify-rule-scope-before-lazy-loading.md`

**What happened:** This PR's own review (Codex + Devin) found 2 of 5 proposed path-scoped rules and the
one skill-folded rule needed a full revert — the exact incident already fully documented in that rule's
own "Why" section. No new content to add here beyond the cross-reference. A separate, smaller finding on
this PR (the `.agents/` Codex mirror left un-synced with this PR's changes) is a previously-known,
explicitly-accepted mirror-drift gap confirmed again by the author's own reply on this PR, not a new
systemic gap.

**Rule:** See `.claude/rules/verify-rule-scope-before-lazy-loading.md` — unchanged.

---

## PR #157 — 3 authoring-discipline rules (devin-ai-integration[bot], chatgpt-codex-connector[bot], 5 rounds, merged 2026-08-28)

### Pattern: a rule instructing "add the missing tool grant" doesn't distinguish agent `tools:` frontmatter from skill/command `allowed-tools:` frontmatter — and the two have incompatible syntax

**What happened:** A skill or command's `allowed-tools` needs an exact scoped grant (e.g. `Bash(cmd:*)`);
an agent's `tools` field uses bare tool names with no `Bash(...)` scoping syntax at all — a scoped entry
there is itself the violation, not the fix. Generic rule text written for one component type instructed
an agent edit to add frontmatter that's invalid for agents.

**Rule:** Any rule, checklist, or reviewer instruction touching tool-grant frontmatter must explicitly
distinguish skill/command `allowed-tools` (scoped grants required) from agent `tools` (bare names only,
scoped syntax is itself wrong) — never write "add the grant" generically across both component types.

---

## PR #159 — close command-injection surfaces in commit skill (chatgpt-codex-connector[bot], devin-ai-integration[bot], coderabbitai[bot], 19 rounds, merged 2026-08-28)

### Confirms: `core.fileMode=false` locally can mask a missing executable bit — recurred on a second script

**What happened:** `stage-selected-files.sh` was committed at git mode `100644` despite being invoked
directly (not via an interpreter prefix); local testing never caught it, for the identical reason PR
#121's instance (above) didn't — `core.fileMode=false` plus an already-executable local disk copy. This
is the same already-documented pattern recurring on a different script, not a new one.

**Rule:** See PR #121's entry above — unchanged. Recorded here because a second real occurrence in
production strengthens the case for actually filing the GitHub issue that was drafted but left unfiled
after PR #121 (`issues/2026-08-29-filemode-false-masks-missing-executable-bit.md`).

### Pattern: resolving a value via a separate `git rev-parse` call does not sanitize it against later shell interpolation

**What happened:** A step resolved the current branch name via `git rev-parse --abbrev-ref HEAD`, then
interpolated that resolved value into a generated `git push origin <branch>` shell command. A branch name
is attacker-controllable on a contributed/fetched checkout — `git check-ref-format --branch` accepts a
name like `review/foo;touch${IFS}/tmp/PWN`, and live-verified in a scratch repo, composing that resolved
value into the push command executed the injected `touch`.

**Rule:** Resolving a value through one command does not make it safe to compose into a *different* shell
command afterward — the composition step is where the shell parses metacharacters, regardless of how the
value was obtained. Prefer a fixed command with no interpolation at all (`git push origin HEAD`) over
resolve-then-interpolate whenever the fixed form is available.

### Pattern: `git status --porcelain`'s default untracked-files mode collapses an entire untracked directory into one candidate line

**What happened:** A numbered file-selection UI built on the default porcelain output showed one entry
(`?? newdir/`) for an untracked directory containing multiple files — selecting that single index then
staged every file beneath it, even though the UI's own numbering implied one file per index.
Live-reproduced: a 2-file untracked directory showed as 1 candidate; selecting it staged both.

**Rule:** A file-selection UI built on `git status --porcelain` must pass `--untracked-files=all` to get
one line per actual file — the tool's own default groups an untracked directory as a single unit, which
silently breaks any "one candidate = one file" assumption.

### Pattern: printing an untrusted filename's raw bytes in a numbered selection list can inject control characters that make the display misleading

**What happened:** A `printf '%s'` display of candidate filenames passed newline, tab, and ANSI control
bytes straight through — a crafted filename can visually corrupt or spoof the numbered list, causing a
human to select the wrong index despite reading the display correctly.

**Rule:** When displaying an untrusted filename in any numbered/indexed selection UI, escape it for
display (e.g. `printf '%q'`) while keeping the raw, unescaped bytes in the actual selection pipeline (a
NUL-delimited pathspec, index-based lookup) — display safety and selection correctness need different
treatments of the same string.

### Pattern: a "stage the generated destination when its source is staged" gate must verify the source is fully staged, not merely staged-at-all — and this applies per-contributor when several sources feed one generated artifact

**What happened:** Two related instances of the same gap in the same mirror/hooks-sync staging logic: a
staging helper generated content from working-tree bytes, so a source with unstaged changes *on top of*
what's staged produced a destination that didn't match the staged source, failing the repo's own staged
parity check. Separately, when several sources merge into one generated artifact (e.g. two plugins'
`hooks.json` merging into one output), the merge logic accepted the first staged contributor without
checking that *every* contributor was fully staged — a second, dirty contributor's unstaged edits were
already baked into the merged document and got staged anyway.

**Rule:** A "regenerate and stage a derived artifact when its source(s) are staged" mechanism must confirm
every contributing source has no unstaged changes on top of what's staged (not just "is staged at all")
before staging the derived artifact — check this per-contributor when multiple sources merge into one
output, not just for whichever contributor triggered the check.

### Pattern: iterating "current files" to decide whether to stage a derived artifact misses a source's staged deletion entirely

**What happened:** When a tracked contributing source file was deleted, it was absent from a "current
files" tuple built by scanning what exists on disk now — so the staging decision, built only from that
tuple, couldn't recognize the deletion happened and left the regenerated artifact un-staged, silently
retaining the deleted contributor's content in the generated output.

**Rule:** A mechanism deciding whether to re-stage a derived/generated artifact must check staged
deletions explicitly against git's own staged-paths state, not rely solely on enumerating files that
currently exist — a deletion has no "current file" to enumerate, so it needs its own separate check.

---

## PR #161 — fix Windows Codex dispatch (#78) (devin-ai-integration[bot], chatgpt-codex-connector[bot], coderabbitai[bot], 9 rounds, merged 2026-08-28)

### Pattern: a required-prefix character class in a security-relevant regex can silently exclude the exact literal shape the check exists to catch

**What happened:** A credential-assignment pattern required a leading `[A-Za-z_]` character before the
`CREDENTIAL`/`AUTH` alternation — a bare `AUTH=opaque-value` or `CREDENTIAL=opaque-value` assignment (no
prefix at all) didn't match, because the required leading character class consumed the assignment's own
first letter before the alternation was evaluated. Live node-verified: the regex matched
`SERVICE_CREDENTIAL=...` and `DB_AUTH_VALUE=...` but not bare `CREDENTIAL=...`/`AUTH=...`. A
documentation file containing exactly this bare-assignment shape would have bypassed the secret-file
check before a `danger-full-access` Windows dispatch.

**Rule:** When a security check's regex is built as "optional prefix + required keyword," verify with a
direct test (not just a read-through) that the *bare, unprefixed* form of the keyword still matches — a
required leading character class easily reads as "prefix or nothing" while actually consuming the
keyword's own leading character and defeating the match.

### Confirms: a regression test's crafted target can live somewhere the tool's own baseline scan already reaches directly, making the test pass regardless of whether the mechanism under test exists

**What happened:** A symlink security-regression scenario placed its credential-shaped real target under
a directory the scanner's normal file walk already visits directly (independent of symlink resolution) —
so the test's own assertion held even with the actual symlink-exemption gate removed, giving false
confidence the gate was under test. This is a distinct instance of the same broader theme as the
already-documented "tampered copy" pattern above (a test's placement can make it pass for reasons
unrelated to the code path it's meant to exercise) — the underlying lesson (a test must actually isolate
the mechanism it claims to cover) is the same, even though the specific mechanism here (baseline-reachable
target vs. relative-import breakage) differs.

**Rule:** See the "tampered copy" pattern above — unchanged. A regression test's crafted scenario must be
placed so the *only* way to reach the flagged condition is through the mechanism actually under test, not
somewhere the tool's normal/baseline behavior already reaches independently.

---

## PR #164 — rule-lazy-loading checklist and verification (Devin + Codex + CodeRabbit, 11 rounds, merged 2026-08-28)

### Pattern: a Reference Guide path validator admitted a `..` traversal component before calling `is_file()`

**What happened:** `references/../SKILL.md` matched a permissive `[\w./-]+` character class and resolved
outside the intended `references/` directory, returning PASS for a path that escapes the allowed
directory before the resolved path was ever checked for a traversal component.

**Rule:** A path-validation check using a permissive character-class regex must explicitly reject `..`
path components (e.g. via `.parts`) before resolving or checking the path — a character class alone
cannot distinguish a legitimate relative path from one that escapes its intended directory.

### Pattern: a mandatory quality-gate instruction directed a bare relative path instead of a skill-relative one

**What happened:** A quality-gate instruction told users to invoke `python scripts/smoke_test.py` — no
`${CLAUDE_SKILL_DIR}` anchor — which resolves against the caller's own working directory, not the
skill's. Even this repo has no root-level `scripts/smoke_test.py`, so the mandatory gate would fail, or
could silently execute an unrelated same-named script in the caller's own project.

**Rule:** An instruction invoking a skill-local script must anchor the path to `${CLAUDE_SKILL_DIR}`
(or the plugin-relative equivalent), never a bare relative path — a bare relative path resolves against
whatever directory the invoking process happens to be running from, not the skill's own directory.

### Pattern: a documented placeholder for redacting a sensitive-data category matched that category's own detection regex

**What happened:** The instructed replacement for a real email address was `user@example.com` — which
itself matches the email-detection pattern a security self-check and `rule-reviewer` both apply, so
following the documented remediation could never pass validation.

**Rule:** A documented placeholder/replacement token for a sensitive-data category must itself be
checked against that category's own detection pattern before being documented — a fake-but-real-looking
placeholder can trigger the same validator it's supposed to satisfy.

### Pattern: a mandatory quality-gate script shipped with a plugin imported a dependency only present in the authoring repo's own dev environment

**What happened:** A `smoke_test.py` imported PyYAML, a dev-only dependency of this marketplace repo
(`pyproject.toml`'s real `dependencies = []`; PyYAML only under `[dependency-groups].dev`) — not
installed when the plugin ships standalone into a downstream project, so the "mandatory" quality gate
crashed with `ModuleNotFoundError` outside this repo. It was the only `smoke_test.py` of roughly 48 in
the repo with this import.

**Rule:** A script shipped as part of an installable plugin must not import a dependency that's only
present in the authoring repo's own dev/test environment — a mandatory quality-gate script needs to work
using only the standard library (or dependencies genuinely bundled with the plugin) when run from an
arbitrary downstream installation.

---

## PR #177 — close remaining destructive-cleanup guard bypasses (Devin + Codex, 17 review rounds, merged 2026-08-29)

### Confirms: a character-class/regex-based command guard has a structural, recurring boundary-matching surface

**What happened:** This round alone fixed five distinct instances of the same underlying class in the
git-kit guard scripts: a protected-name prefix (`main/topic`) misclassified as the protected name itself;
a quoted `--format` display value triggering the deletion guard; two separate shell statements' text
cross-contaminating a single-command check; a force-flag match not respecting `--` option termination;
and an option value coinciding with a protected name. Each is a different specific boundary (word
boundary, shell quoting, option-argument association, command separators) that a character-class regex
over raw/flattened command text can only approximate, not resolve exactly.

**Rule:** See the author's own review replies — this is a known, disclosed, already-tracked residual
(issues #120, #180) requiring a real shell tokenizer to close structurally, not a hidden discovery.
Recorded here to name the general pattern (a character-class command guard's boundary-matching surface
is structural, not incidental) for future authors of similar guards elsewhere.

### Pattern: migrating a data source silently dropped a filtering signal the consuming logic's contract depended on

**What happened:** A skill's review-extraction step migrated to `gh pr view --json reviews` from a
previous data source. The new source exposes no actor-type/bot marker, so a "human comments only"
contract silently started retaining bot-authored review bodies — and the human-confirmation gate for
staged writes unconditionally exempted this path, since that exemption predated the migration and only
correctly covered sources that still had a working bot filter.

**Rule:** Before migrating a data source a consuming contract depends on, check the new source's schema
for feature parity with the old one — a filtering signal (actor type, a status field, a timestamp) the
old source exposed can be silently absent from the replacement, breaking a contract nothing in the
migration itself re-verifies.

### Pattern: a one-shot authorization marker's deletion step swallowed its own failure, leaving the marker reusable

**What happened:** `rm -f "$MARKER" || true` treated a genuine deletion failure (e.g. a read-only or
permission-restricted `.git`) the same as success — `allowed` was already set to `true` by that point, so
any later matching destructive command within the marker's 60-second TTL was authorized without a fresh
handshake, defeating the documented single-use guarantee. Present identically across all five guard
scripts in this plugin.

**Rule:** A one-shot authorization marker's deletion/consumption step must be checked for success —
swallowing the deletion failure silently converts a single-use guarantee into a reusable one whenever
deletion fails for any reason (permissions, a read-only filesystem, a race).

---

## PR #179 — PR review-learnings mining and management skills (Devin + Codex + CodeRabbit, 25 review rounds, merged 2026-08-29)

### Pattern: a root-finder's fallback used a hardcoded relative-parent-depth assumption that broke for one of two mirrored copy locations

**What happened:** `start.parents[2]` correctly located the repo root for a skill's `.claude/` mirror
copy, but the same fixed depth resolved to the wrong directory for the plugin's own canonical copy
(`plugins/analysis-kit/...`), since the two mirrored copies sit at different depths from the repo root —
breaking `PLUGIN_ROOT` resolution specifically in the environment (`.git` absent) the fallback exists to
handle.

**Rule:** A root-finder's fallback must not assume a fixed relative-parent-depth applies uniformly to
every mirrored copy location — walk up looking for a directory containing known markers (e.g. both
`plugins/` and `.claude/`), which stays correct regardless of how deep any particular copy sits.

### Pattern: a fixture loader accepted null/non-object array elements, crashing a later step with an uncaught exception type

**What happened:** `{"reviews": [null], "comments": []}` passed a fixture loader's validation; a later
normalization step then called `.get` on `None`, raising an `AttributeError` that the caller's own error
handling (which only caught a custom `FetchError`) didn't cover.

**Rule:** An input loader must validate every element of an array field against the shape later code
assumes (here: "is a JSON object"), raising the caller's own expected exception type on a null or
malformed element — never let a later processing step be the one to discover the bad input, with an
exception type the caller wasn't built to catch.

### Pattern: a CLI path argument's leading `~` wasn't expanded before use

**What happened:** `Path(args.fixture_file)` preserves a literal `~` — a quoted invocation like
`--fixture-file "~/fixture.json"` read a relative `~` path instead of resolving against the user's home
directory. This is a distinct instance of the same broader "tilde isn't auto-expanded" theme already
disclosed in this skill's own Gotchas for `Glob` (which also never expands a leading `~`) — here
affecting `pathlib.Path` instead.

**Rule:** A CLI argument accepted as a filesystem path must call `.expanduser()` (or the equivalent)
before use if a leading `~` is meant to resolve to the home directory — neither `pathlib.Path` nor
`Glob` expand it automatically.

### Pattern: editing a skill's activation description to add a new exclusion silently dropped an existing, still-supported trigger phrase

**What happened:** A prior commit in this same session rewrapped a skill's frontmatter `description` to
add a new exclusion clause and, in the process, dropped two existing trigger phrases ("is this issue
still valid", "reopen issue #N") — even though the skill's own Testing & Validation section still
promised the former and the workflow still supported the latter. Since skill routing is driven by the
frontmatter description alone (not the unloaded body), those exact existing requests could silently stop
selecting the skill, with no error anywhere.

**Rule:** When editing a skill's activation description to add a new exclusion or boundary clause,
diff the result against every trigger phrase already promised elsewhere in the same skill (its own
Testing & Validation section, worked examples) — an edit made for one purpose can silently regress an
unrelated existing guarantee if the full text isn't checked against everything that already depends on
it.

### Pattern: a mirror-parity checker's coverage doesn't extend to every plugin-level directory with a `.claude/` mirror expectation

**What happened:** `scripts/marketplace_ci`'s `check-plugin-mirrors` parity check verifies `skills/`
mirror content but not a plugin-level `references/*.md` file (distinct from a skill's own
`skills/<skill>/references/`) — such a file can drift between its canonical and `.claude/`-mirrored copy
with no tooling signal. Disclosed as a known, out-of-scope limitation rather than fixed in the same PR,
since it's a shared-tooling change affecting every registered plugin.

**Rule:** When a mirror-parity checker is scoped to specific component directories, periodically re-check
that scope against every directory type that actually carries a `.claude/`-mirror expectation — a
checker's own coverage list can silently lag behind the set of directories the mirroring convention
actually applies to.

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
