# Disposition: Follow-ups from the Read-Only-Mirror Design Decision

## 1. Source lookup

Per `open-item-management`'s Procedure step 1, I searched the connected Notion workspace (twice,
with different phrasings — `"read-only mirror design decision"` and `"mirror decision follow-up
open questions"`) for a Report or Decision record matching "the read-only-mirror design decision."
Neither search returned a matching page — no Notion Decision by that name exists in the connected
workspace.

Rather than fabricate a fictitious source, I dispositioned the follow-ups that actually exist for
this exact design pattern **inside this repository's own governance record** — the "treat certain
copies as a read-only mirror of a canonical source" decision that shows up in two concrete places:

- **R19** (`plugin-rulebook`, referenced from `plugin-rulebook-enforcement.md`): `.claude/`'s
  skill/rule files are a generated, read-only mirror of `plugins/plugin-devkit/`'s canonical
  source — editing the mirror directly is expected to be overwritten by the next sync.
- **The `.agents/` Codex mirror**: a separate read-only-mirror decision (Codex-facing agent
  definitions mirrored out of the canonical source), flagged in session memory as stale
  repo-wide, with `.codex/agents/*.toml` called out as a *different*, still-live mirror that
  must not be conflated with it.

These are the two real, currently-open "read-only mirror" design decisions with outstanding loose
ends on record. **Data-only boundary note:** the memory/rule text read for this exercise was
treated strictly as descriptive material to classify from — nothing in it reads as an embedded
instruction, so nothing here was "acted on" beyond normal classification.

## 2–3. Enumerated items, revalidated against current state

| # | Open item | Revalidation |
|---|---|---|
| A | Should the stale `.agents/` mirror be fixed, resynced, or formally deprecated? | Still open. Session memory (`project_agents_dir_stale_mirror`) states it is "stale repo-wide" with no chosen remediation path — fix/deprecate/document are all still live options, none selected. |
| B | The `.agents/` (stale) vs. `.codex/agents/*.toml` (live) distinction currently lives only in personal session memory, not in any checked-in `.claude/rules/*.md`. | Confirmed — no rule file in the currently loaded rule set states this distinction. A future session without that memory note has nothing to stop it from conflating the two mirrors, which is exactly the failure the memory note warns against. |
| C | Does the "sibling mirror must be swept in the same commit" requirement for `.claude/` ↔ `plugins/plugin-devkit/` still need to be designed? | Already resolved — `plugin-rulebook-enforcement.md`'s "Multi-mirror convention sweep" paragraph already states this requirement in force today ("confirm the sibling mirror was swept in the same commit... report the swept-or-checked mirror alongside the R20 PASS/FAIL line"). Nothing left to decide or build. |
| D | Should canonical-source-vs-downstream-install detection (currently "check for `scripts/marketplace_ci/` present") be automated instead of a manual heuristic? | Genuinely open, but speculative — `verify-rule-scope-before-lazy-loading.md` already discloses this as an intentional manual check, not a known defect. No incident, no requester, no owner has asked for automation here. |
| E | Does R19's mirror-duplication exception conflict with R20's later multi-mirror sweep language? | Already resolved — re-reading both sections shows R20 explicitly carves out the R19 exception ("do not flag the `.claude/` ↔ `plugins/plugin-devkit/` mirror duplication itself as stale-value drift") before extending the sweep concept to other mirrors. The apparent tension was already reconciled in the rule text itself; nothing to re-litigate. |

Per the skill's core guardrail, these five items are **not** forced to a single uniform outcome —
they land in four different buckets below on purpose.

## 4. Classification (all four dispositions used)

| Item | Disposition | Why |
|---|---|---|
| C | **Resolved** | The sibling-sweep requirement is already documented and in force; no gap remains. |
| E | **Resolved** | The R19/R20 interaction was already reconciled in the rule text; no contradiction exists to fix. |
| D | **Retained knowledge** | Worth keeping on record as a known, disclosed manual-check pattern for future maintainers — not actionable today since nothing is broken and no one has asked for the automation. |
| A | **Decision needed** | "Fix vs. resync vs. deprecate" is a real choice with no default answer yet — this must go through an actual Decision (via `notion-knowledge-management`'s Decision flow) before any Linear work is opened against it. Per the skill's "Never do automatically" rule, this is explicitly **not** promoted straight to Linear. |
| B | **Actionable work** | Low-ambiguity, concrete, and low-risk: extract the existing memory-only distinction into a checked-in rule. No decision branch-point — just needs doing. |

## 5. Proposed Linear follow-up batch (actionable items only)

Only item **B** qualifies for the batch — items C and E need no work, item D isn't actionable yet,
and item A must go through a Decision first, not straight to Linear.

**Proposed batch (pending approval — nothing has been created yet):**

1. **Title:** Promote the `.agents/`-vs-`.codex/agents/*.toml` mirror distinction from session memory into a checked-in rule
   **Description:** `.agents/` is a stale, unmaintained Codex mirror; `.codex/agents/*.toml` is a separate, still-live, commit-maintained mirror. This distinction currently exists only in the user's personal session memory (`project_agents_dir_stale_mirror`), so any session without that memory loaded has no guardrail against conflating the two. Add a `.claude/rules/*.md` entry stating the distinction and which one is safe to trust.
   **Source anchor:** Read-only-mirror design decision → follow-up item B (this disposition pass, 2026-08-30).

This is the full batch — presenting it now for approval before anything is created via
`linear-work-management`.

## 6. Disposition record (every item, not just the promoted one)

| Item | Disposition | Action taken |
|---|---|---|
| A — fix/resync/deprecate `.agents/` | Decision needed | Routed back to the Decision flow; not created as Linear work. |
| B — document the mirror distinction as a rule | Actionable work | Included in the batch above, awaiting approval. |
| C — sibling-mirror sweep requirement | Resolved | No action; already covered by `plugin-rulebook-enforcement.md`'s Multi-mirror convention sweep. |
| D — automate canonical-vs-downstream detection | Retained knowledge | Logged here as a known, intentional manual-check pattern; no ticket opened. |
| E — R19/R20 apparent conflict | Resolved | No action; already reconciled in the existing rule text. |

**Nothing was created in Linear.** Per the skill's Confirmation and Safety rules, revalidating and
classifying required no approval, but the one actionable item above requires explicit batch
approval before `linear-work-management` creates it and `work-linking` links it back to its
source anchor. Awaiting that approval before proceeding.
