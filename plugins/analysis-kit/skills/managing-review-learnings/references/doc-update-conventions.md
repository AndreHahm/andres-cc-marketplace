# THIRD_PARTY_REVIEW_LEARNINGS.md Update Conventions

Grounded directly in the live document's own structure (`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`), not
an invented format. Read the document's own current intro paragraph and at least one existing `## PR #N`
section before drafting a diff — this file describes the shape, the live document is the source of truth
for exact current wording.

## Append: a new PR section

**Required — the core of every append:**

```markdown
## PR #<N>[ / #<N2> / ...] — <short title> (<reviewer(s)>, <round count> rounds, <YYYY-MM-DD>)

### Pattern: <name of the recurring shape>

**What happened:** <1-3 sentences>

**Assumed vs. actual** (only for a tool/API/language-behavior mismatch — omit otherwise):

| Assumed | Actual |
|---|---|
| <what was assumed> | <what's actually true> |

**Rule:** <the generalizable rule, in the document's own imperative style>
```

**`<reviewer(s)>` persists beyond this document.** The header line records third-party reviewer
identities (a bot name, a human handle) into a git-tracked document — already this document's own
existing convention, low sensitivity since these are public PR reviewers. But the same identifier can
also travel further: if this candidate is later dispatched to `github-issue-lifecycle` (the calling
skill's own Phase 4), it becomes part of a public GitHub issue's body too. Not a reason to omit it —
just don't treat it as staying contained to this document once written.

- Use `### Pattern:` for a genuinely new lesson (the common case). Use `### Confirms:` for a finding that
  validates an already-named pattern from elsewhere in the document without adding a new one, `###
  Self-caught:` for something the fixing session found on its own rather than a reviewer, or `###
  Methodology note:` for an observation about the review *process* itself rather than a code defect — all
  four forms are already in live use; pick the one that actually matches the candidate, don't force
  everything into `### Pattern:`.
- Multiple sub-patterns under one PR section are normal (see the live document's own PR #47, #92, #88
  sections) — one `## PR #N` header can carry several `### Pattern:`/`### Confirms:` blocks.
- Place a multi-PR section (`## PR #61 / #62 / #65 / #68 — ...`) only when the source candidates
  themselves span multiple PRs that were clearly one continuous effort — don't invent this grouping for
  otherwise-unrelated PRs just to save a header.

**Optional, secondary — propose separately, never bundle into the same silent edit:**

- **Intro-paragraph mention.** The document's own intro paragraph (top of the file) names each PR range
  added and how its findings were captured (`"captured live during those PRs' own review rounds"` vs.
  `"reconstructed afterward from each PR's actual GitHub review history... since this document didn't
  exist while those PRs were in flight"`). Adding a matching sentence keeps that paragraph's own claim
  complete, but is optional connective narrative, not load-bearing — offer it as a separate, explicitly
  optional item in the proposed diff, never assume it's wanted.
- **Master pre-push checklist entry.** The document's closing `## Master pre-push checklist` section
  organizes checkable items by category (Tool/API/language behavior, Chain/state/timing, Scope &
  completeness, Docs & evals, Bash/language footguns, Security & verification) and its own heading line
  lists every PR number analyzed so far. Adding a checklist bullet here is higher-risk than the PR-section
  append (picking the wrong category, or duplicating the PR section's own **Rule:** line) — propose it
  only when the candidate's rule is genuinely a new, checkable pre-push item distinct from an existing
  bullet, and always as its own separately-approvable diff item, never folded into the PR-section append.

## Reorganize: meta-pattern table update or consolidation

- **Cross-PR meta-pattern table.** The document's own early "Cross-PR meta-pattern" table (Assumed
  behavior / Actual behavior, one row per PR) is specifically for the tool/API/language-behavior mismatch
  shape — propose a new row only when the candidate is that shape and doesn't already have a row for the
  same PR.
- **Consolidation.** Only merge two existing entries when they describe the *same actual root cause*, not
  merely similar wording or topic — the same "content comparison, not location/wording alone" discipline
  `mining-review-learnings`'s own Phase 3 exclusion check already applies. Name both entries being merged
  explicitly in the proposed diff; never present a full-document rewrite as the only reviewable unit.

## What this skill never touches

The document's own intro paragraph's first two sentences (the **Goal:** statement) and the closing
attribution line are the document's own stated purpose — never propose rewriting those as part of a
routine append or reorganize; if they seem genuinely out of date, flag that as its own explicit,
separately-approved item, not a silent side effect of adding one PR's findings.
