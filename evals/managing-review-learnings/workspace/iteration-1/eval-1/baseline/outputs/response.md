# Proposed doc-diff: add PR #199 Pattern entry to THIRD_PARTY_REVIEW_LEARNINGS.md

## What I read first

I read the full current file (`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`, 1205 lines) before drafting
anything, to copy its actual structure rather than guess at it. Relevant structural facts:

1. The document is organized as one `##` section per PR (`## PR #<N> — <short description> (<reviewer(s)>,
   <round count>, <date>)`), each containing one or more `### Pattern: <title>` subsections. Each pattern
   subsection follows a **What happened:** paragraph, an optional **Assumed vs. actual:** table (used when
   the root cause is a tool/API/language behavior mismatch), and a closing **Rule:** paragraph. Sections are
   separated by a horizontal rule (`---`).
2. The most recent PR section already in the file is `## PR #172 — \`github-issue-lifecycle\` skill,
   freestanding issue work (Codex, 2 rounds, 2026-08-28)`, immediately followed by a `---` and then the
   `## Master pre-push checklist` section that closes the document.
3. **Important precedent I checked before proposing anything:** PR #172's two patterns (the `--duplicate-of`
   flag, and the shell-injection-via-double-quotes finding) were added as their own PR section but were
   **not** back-filled into the Master pre-push checklist's bullet items, and the checklist's own title line
   ("all PRs analyzed, including this session's #61/#62/#65/#68/#76/#79/#92/#88") was not updated to mention
   #172 either. That tells me the most recent real editing practice in this file is "append a new PR
   section only" — the checklist sync is not done on every PR. Per the repo's own Surgical Changes principle
   (CLAUDE.md §3: touch only what you must, match existing style even if you'd do it differently), I'm
   mirroring that same minimal-diff precedent for PR #199 rather than also editing the checklist or the
   opening provenance paragraph (lines 1–18), which likewise was never updated for #172.

## Assumptions I'm stating explicitly (per CLAUDE.md §1: state assumptions, don't hide confusion)

The mined candidate gives me the *content* of one finding but not the surrounding metadata this file's
convention requires in the section header and attribution line: which script/component was under review,
which reviewer(s) found it (Codex/CodeRabbit/Devin/cross-model-review), how many review rounds the PR went
through, and the merge date. I do not have access to PR #199's actual GitHub history in this task, so I am
NOT going to invent specifics (a fabricated round count or date would itself be exactly the kind of
unverified-claim problem this document's own "Precision Self-Audit Trigger" and Master checklist warn
against). Below I mark every such gap with a `<PLACEHOLDER>` and treat resolving them as a precondition for
the real edit, not something to guess through.

## Proposed diff

Insertion point: between the `---` that closes the PR #172 section (current line 1043) and the blank line
before `## Master pre-push checklist` (current line 1044/1045) — i.e. appended as the newest PR section,
directly following #172 and preceding the Master checklist, exactly where #172 itself was appended after
#88.

```diff
@@ -1041,6 +1041,22 @@
 scratchpad file), never a double-quoted inline argument.
 
 ---
 
+## PR #199 — <PLACEHOLDER: script/component name> (<PLACEHOLDER: reviewer(s), e.g. Codex>, <PLACEHOLDER: N> round(s), <PLACEHOLDER: YYYY-MM-DD>)
+
+### Pattern: a subprocess's non-zero exit code was never checked before its stdout was parsed as JSON
+
+**What happened:** <PLACEHOLDER: script/function name> invoked a subprocess and passed its stdout
+directly to a JSON parser without first checking the subprocess's `returncode` (or using an
+exit-code-checking call form such as `subprocess.run(..., check=True)`). When the subprocess failed, its
+stdout was empty, partial, or plain-text (e.g. an error message on stdout instead of stderr, or no output
+at all) rather than valid JSON — so the parser raised `JSONDecodeError` instead. The failure that actually
+reached the caller (and any downstream log/CI output) was a confusing JSON-parsing error, masking the real,
+more actionable cause: the subprocess itself failed.
+
+**Rule:** After invoking a subprocess whose stdout is meant to be parsed as structured data (JSON, YAML, or
+similar), check the subprocess's exit status *before* attempting to parse stdout — via an explicit
+`returncode` check or a `check=True`-equivalent call — and surface the subprocess's own failure (ideally
+including its stderr) on a non-zero exit. Never let a failed subprocess's output fall through to a parser
+that will raise its own, unrelated-looking exception; that exception becomes the reported symptom instead
+of the real root cause, costing a debugging round to work backward from the parse error to the actual
+subprocess failure.
+
+---
+
 ## Master pre-push checklist (all PRs analyzed, including this session's #61/#62/#65/#68/#76/#79/#92/#88)
```

### Section/heading conventions followed

- `##` for the PR-level section, named `PR #<number> — <short description> (<reviewer(s)>, <round count>,
  <date>)` — matches every existing PR section's header format (e.g. `## PR #172 —
  \`github-issue-lifecycle\` skill, freestanding issue work (Codex, 2 rounds, 2026-08-28)`).
- `###` for the individual pattern, titled `Pattern: <one-line description of the shape of the bug>` —
  matches the convention used throughout (e.g. `### Pattern: \`gh issue close\` has a dedicated
  reason/flag for each closure type, not just one generic path`).
- **What happened:** / **Rule:** bolded lead-in paragraphs, no bullet list, matching PR #172's two patterns
  exactly (PR #172 did not use an Assumed-vs-actual table for either of its two findings, so I likewise
  omitted one here — the finding isn't really a "the tool's documented behavior differs from what I assumed"
  case, it's a "we didn't add the check at all" case, which several other patterns in the file present the
  same prose-only way, e.g. PR #92's idempotency-guard-ordering pattern).
- Closing `---` horizontal rule, matching every section boundary in the file.
- No change to the Master pre-push checklist's bullet items or its title line, no change to the opening
  provenance paragraph — following the PR #172 precedent described above, not because those would be wrong
  to update in principle, but because the file's own most recent real edit didn't do it, and CLAUDE.md's
  Surgical Changes principle says match existing practice rather than "improve" adjacent content that
  wasn't part of the request.

## Would I ask for approval before making the real edit? Yes — explicitly, for two separate reasons

1. **Missing/placeholder metadata.** I do not have PR #199's real script name, reviewer, round count, or
   date. Writing those into a permanent, git-tracked project-history document as guesses would plant a false
   claim in a file whose own stated purpose is precision (and which has an explicit "Precision Self-Audit
   Trigger" in this repo's `plugin-rulebook-enforcement.md` for exactly this failure class: absolute/specific
   claims that turn out to be unverified). Per this repo's `ask-before-structural-grounding.md` and
   `disclose-before-overriding-decisions.md` rules' shared spirit — don't silently fill gaps with invented
   specifics — I would ask the user (or pull the real PR #199 review-history via `gh api
   repos/.../pulls/199/comments` the way prior "reconstructed" entries in this file were built) to fill in
   the four placeholders before writing anything for real.
2. **General practice for this file.** Even with the metadata resolved, I would not silently run `Edit` on a
   shared, git-tracked learnings document that other sessions/skills read as an authoritative pre-push
   checklist source. I'd show the exact diff above (or the corrected version once placeholders are filled)
   and get an explicit go-ahead before applying it — consistent with this repo's general "no silent writes
   to a shared/tracked doc" posture (e.g. `require-inventory-updates-for-new-plugins-and-components.md`'s
   "No silent writes" section, applied here by analogy even though this isn't an inventory file).

## Redaction

I reviewed the mined candidate text and my proposed addition for anything sensitive (credentials, PII,
internal-only paths/hostnames, tokens). The candidate is fully generic — "a script," "a subprocess," "stdout
as JSON" — with no identifying or sensitive content, and I did not introduce any in the diff above (the
placeholders are structural gaps, not redacted secrets). If the real PR #199 specifics (once supplied) turn
out to include anything sensitive — e.g. an internal-only hostname, a credential accidentally visible in a
review comment — I would redact that specific content before writing it into this file, since
`THIRD_PARTY_REVIEW_LEARNINGS.md` is a git-tracked, shipped document, not a private scratch file. I would
flag any such redaction explicitly rather than silently dropping it, the same disclosure standard this
repo's `disclose-before-overriding-decisions.md` rule sets for any content removed from what would otherwise
be a straightforward transcription of the finding.

## Summary

- No `Edit` tool call was made — this is a proposal only, as instructed.
- The diff above is ready to apply once `<PLACEHOLDER>` values (component/script name, reviewer(s), round
  count, date) are confirmed against PR #199's actual review history.
- I would ask for explicit approval before applying it, both because of the placeholder gaps and as a
  standing practice for edits to this shared document, and would redact any sensitive content surfaced by
  the real PR #199 details before writing it in.
