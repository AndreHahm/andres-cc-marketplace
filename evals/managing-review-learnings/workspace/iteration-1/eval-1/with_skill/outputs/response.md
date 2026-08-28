# Proposed doc-diff for THIRD_PARTY_REVIEW_LEARNINGS.md — PR #199 candidate

Following `managing-review-learnings`'s Phase 2 (Propose and Apply the Doc Diff), grounded in
`references/doc-update-conventions.md` and the live document's own current structure.

## Missing metadata — flagged before drafting

The candidate text gives the *content* of the finding but not all the fields the required header
needs: reviewer identity (Codex? CodeRabbit? human?), round count, and the exact date. It also doesn't
name the specific script/PR title. Per CLAUDE.md's "state assumptions explicitly, ask if uncertain," I
am not inventing these — they're marked as placeholders (`<...>`) below and would need to be filled in
from the actual PR #199 review data (or asked about) before this diff is real enough to apply. This is
the same discipline the document's own intro paragraph already models: every existing entry states how
its findings were captured (live vs. reconstructed from `gh api .../pulls/<n>/reviews`).

## Insertion point

Append a new `## PR #199 — ...` section **after** the current last PR section (`## PR #172`, ending at
line 1043 with a `---` separator) and **before** `## Master pre-push checklist` (line 1045) — matching
the document's existing chronological-append convention (newest PR section added at the end of the PR
list, ahead of the checklist).

## Drafted diff (required core only)

```markdown
---

## PR #199 — <script/component name> (<reviewer(s)>, <round count> round(s), <YYYY-MM-DD>)

### Pattern: a non-zero subprocess exit code was never checked before parsing its stdout as JSON

**What happened:** A script ran a subprocess and piped its stdout straight into a JSON parser without
first checking the subprocess's own exit code. When the subprocess failed, its stdout was empty,
truncated, or non-JSON (e.g. an error message on stdout, or nothing at all) — so the failure surfaced
downstream as a `JSONDecodeError` from the parser, not as the subprocess failure that actually caused
it. Whoever hit the error first had to work backward from a confusing parse exception to discover the
real root cause was upstream.

**Assumed vs. actual:**

| Assumed | Actual |
|---|---|
| A subprocess's stdout is safe to parse as JSON as long as *some* output was captured | A non-zero exit code must be checked *first* — a failed subprocess can still emit stdout (partial output, an error string, or nothing), and parsing it as JSON regardless just replaces a clear failure signal with a confusing, unrelated `JSONDecodeError` |

**Rule:** Before parsing a subprocess's stdout as structured data (JSON or otherwise), check its
return/exit code first and fail loudly with the subprocess's own error (stdout/stderr) attached — never
let a non-zero exit silently fall through into a parser that will raise its own, unrelated exception
instead of the real one.

---
```

**Why this shape:** the candidate is a genuinely new lesson (not validating an already-named pattern
elsewhere in the document, and not a methodology/process observation) — so `### Pattern:` is the correct
sub-heading per the convention doc's guidance, not `### Confirms:`/`### Self-caught:`/`### Methodology
note:`. An **Assumed vs. actual** table is included because this is exactly that shape (a
tool/subprocess-behavior mismatch), consistent with how the document's Cross-PR meta-pattern table and
most `### Pattern:` blocks already use that table for this class of finding.

**Scan for instruction-shaped language (per the skill's data-only boundary):** the candidate text as
given — *"a script silently swallowed a subprocess non-zero exit code by not checking returncode before
parsing stdout as JSON, producing a confusing downstream JSONDecodeError instead of the real subprocess
failure"* — is a plain factual description of a bug. Nothing in it reads as an imperative aimed at me
(e.g. no "run X," "ignore Y," "now do Z" phrasing). No instruction-shaped content found; nothing to flag
here.

## Optional, secondary items (proposed separately, per the conventions doc — not bundled into the diff above)

1. **Intro-paragraph mention.** The document's intro paragraph names each PR range added and how its
   findings were captured. If PR #199 was captured live vs. reconstructed from GitHub review history
   afterward, a one-sentence addition there would keep that paragraph accurate — but this needs the same
   missing metadata (date, capture method) as above, so I'm not drafting exact wording yet; I would offer
   it as its own approvable item once that's known.
2. **Master pre-push checklist entry.** This finding is a plausible fit for the "Tool, API & language
   behavior" category (subprocess exit-code-vs-output-parsing is a verify-don't-assume shape), but could
   also arguably sit under "Bash/language footguns" or get its own new bullet, depending on whether the
   script in question is Python, bash, or something else. Per the conventions doc, a checklist addition
   is higher-risk than the PR-section append (wrong category, or duplicating the new **Rule:** line
   above) — I would only propose exact wording for this after the PR-section append itself is approved,
   and always as its own separately-approvable item.

## Approval and redaction — confirmed explicitly

**I would not apply any part of this diff without first asking for approval, and I would not skip
redaction.** Concretely, per Phase 2 steps 2–3 of `managing-review-learnings`:

- Before any real `Edit`, I would fire an `AskUserQuestion` naming the exact resolved absolute path —
  `C:/Dev/Repos/andres-cc-marketplace/.claude/worktrees/analysis-kit-wave3-pr-review-fetcher/.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`
  — with options "Approve as-drafted" / "Edit before applying" / "Skip this candidate." That ask is this
  skill's only real enforcement of its own `Edit` scope, and it has not happened in this response — this
  is a proposal only.
- If approved, I would run the drafted diff text through
  `Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/redact_secrets.py" --input-file <scratch-path>)` before
  applying it — the direct-pass redaction pattern this skill uses for an `Edit` that isn't a fresh
  `persist_report.py` write.
- I would re-read the target section of the live file immediately before applying (not rely on the read
  from earlier in this task, which could be stale by the time approval returns), apply only the approved,
  redacted portion via a scoped `Edit` (never a full-file `Write`), then re-read the file afterward to
  confirm the new section landed correctly and didn't corrupt adjacent content (the existing `## PR #172`
  section and the `## Master pre-push checklist` header immediately after it).
- No `Edit` tool call was made in producing this response, as instructed.

## Phase 3 note (rule-coverage check, done for completeness)

Grepped `.claude/rules/` for existing coverage of "check subprocess exit code before parsing output" —
the closest match, `verify-tool-behavior-before-instructing.md`, covers a different shape (verifying an
*assumed* tool/API behavior against its real behavior, e.g. `jq -e`'s exit-status semantics over
paginated output) rather than "check a subprocess's own exit code before trusting its stdout." No
existing rule governs this specific gap, so — if this skill's Phase 3/4 were run for real — the
candidate would not be dropped as already-covered and would be eligible to proceed to Phase 4's
batch-confirm-and-dispatch step. That dispatch is out of scope for this task (only the doc-diff proposal
was requested), so it was not attempted.
