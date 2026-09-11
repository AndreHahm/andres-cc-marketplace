# Reconciliation: ENG-311 (Full Lifecycle) — `linear-github-reconciliation`

## 0. Scope and method note (read this before the rest)

This run has **no live Linear, GitHub, or MCP tool access** — no `mcp__claude_ai_Linear__*` call, no `gh` invocation, no `gh_api_readonly.py` call was made, and none will be. No actual ENG-311 record content (Linear state, `git-github-evidence` array, or GitHub PR/branch state) was supplied anywhere in this conversation. That means **Step 1 (Read) cannot be executed for real** in this session, and consequently **Step 2 (Compare) has no real facts to compare**.

Per the IMPORTANT constraints for this exercise, everything below is split into two explicit tracks:

- **[LIVE]** — what I would actually read/check with real tool access, stated as the concrete call I'd make, not a claim that I made it.
- **[STRUCTURAL]** — what I can conclude from the skill's own Procedure, Classification table, and `../../FOUNDATION_CONTRACTS.md`'s Authority Model alone, independent of any specific data.

No PR number, commit SHA, branch name, or timestamp below is a real value. Where an illustrative example is useful to show *how* a classification would be reached, it uses angle-bracket placeholders (`<PR-number>`, `<sha>`, `<branch>`, `<ts>`) — never a concrete-looking fake value that could be mistaken for a real one.

---

## Step 1 — Read

Per the skill's Procedure step 1, a full reconciliation reads five things, not just "current Linear status." For ENG-311, that means:

| Dimension | [LIVE] What I would read | Status in this exercise |
|---|---|---|
| Linear current state | `linear-work-management` → ENG-311's current `status`, `priority`, any linked `notion-link`/`linear-link` fields, and — critically for "whole lifecycle, not just current status" — any available status-change/audit history, not only the present snapshot | Not read — no tool call made |
| Git/GitHub Evidence Record history | `linear-github-linking` → the **entire** `git-github-evidence` array on the ENG-311 Issue record, every entry in chronological order (`work-started` → `commit-linked` → `ci-gates-passed` → `pr-published` → `pr-ready` → `pr-merged` → possibly `work-reopened`), including each entry's `branch`, `commits[]`, `pull_request`, `gates[]`, `provider`, `supersedes`, `merge_commit_sha` | Not read — no tool call made |
| Current GitHub state | `gh pr view` (branch/PR state) and `${CLAUDE_PLUGIN_ROOT}/scripts/gh_api_readonly.py` (branch-protection rules, GET-only) against the branch/PR the evidence record claims for ENG-311 | Not read — no tool call made; and this skill's own `allowed-tools` explicitly forbids bare `Bash(gh api:*)` for this exact reason (unbounded write surface) |
| Repository policy | `repository-gates` → the Repository Policy Profile table (`../../FOUNDATION_CONTRACTS.md`'s Repository Policy Profile section) to confirm which provider is required for each governed operation ENG-311's evidence claims to have gone through | Read structurally from `FOUNDATION_CONTRACTS.md` (see table reproduced below) — this part *is* available without a live call, since it's a static file in this repo |
| Native Linear↔GitHub integration links | Whatever GitHub-native or personal Code & Reviews integration setting governs auto-transitioning Linear status from PR/commit events, to confirm it is still scoped informational-only | Not read — no tool call made, and no such setting is inspectable from files in this repo alone |

**[STRUCTURAL] conclusion from Step 1 alone:** because none of the three dynamic sources (Linear, the evidence array, current GitHub state) were actually read, there is no basis to assert *any* specific discrepancy exists for ENG-311. This is stated up front because it governs every classification below.

The one piece of Step 1 answerable purely from static repo content is the Repository Policy Profile, reproduced here since it's load-bearing for later classification of `provider` mismatches:

| Logical operation | Required provider |
|---|---|
| Create branch/worktree | `git-kit:starting-work` |
| Commit | `git-kit:commit` |
| Create a new PR | `git-kit:create-pr` |
| Push to an existing PR's branch | `git-kit:commit` |
| Mark a PR ready for review | Manual handoff (no `git-kit` skill owns this yet) |
| Review/comment/link an issue at creation | `git-kit:collaborating-on-a-pr` (forward-looking) |
| Merge | `git-kit:merge-pr` |
| Post-merge sync/cleanup | `git-kit:finishing-work` |

---

## Step 2 — Compare

**[STRUCTURAL]** Per the Authority Model in `FOUNDATION_CONTRACTS.md`:

- **Linear owns execution state** (workflow status, priority) — GitHub's state never overrides it, and neither does a "more recent timestamp."
- **GitHub owns repository facts** (branch/commit/PR existence, CI/gate results, review state) — Linear's own recorded copy of these (inside `git-github-evidence`) is a *cache* of that fact as of when it was written, not an independent source of truth; if GitHub's live state and a `git-github-evidence` entry disagree, GitHub's live state wins for the *fact*, but the disagreement itself is the discrepancy to classify (often `Invalidated SHA`), not something to silently overwrite.
- Neither Notion, Linear, nor GitHub's fresher write ever "wins" by timestamp alone — this is the explicit Gotcha the skill calls out, and it is the first thing to violate if this were done carelessly.

For "whole lifecycle, not just current status," Step 2 requires comparing **across every entry**, not just the latest:

1. **Stage sequencing** — do the `git-github-evidence` entries' `stage` values appear in causally valid order (e.g., no `pr-merged` recorded before any `pr-published`; no `ci-gates-passed` recorded before `pr-published` if gates only run against a published PR)?
2. **SHA/branch currency per entry** — for each entry with a `branch`/`commits[]`/`pull_request`, does it still match GitHub's *current* state for that branch/PR, or has a force-push/rebase since invalidated it?
3. **Provider attribution per entry** — does each entry's `provider` field match the Repository Policy Profile's required provider for that stage, or a legitimate `manual (...)`/`work-reopened` exception?
4. **Linear status vs. evidence-justified status** — was each Linear workflow-status change preceded by an evidence entry that actually justifies it (e.g., a "Done"/"Closed" transition preceded by a `pr-merged` entry), or did status move ahead of the evidence?
5. **Native automation scope** — is any status change attributable to GitHub-native integration behavior exceeding its configured informational-only scope, rather than to an explicit `linear-work-management` write this plugin made?
6. **Unclaimed artifacts** — does GitHub have a branch/PR that plausibly relates to ENG-311 (by naming convention or reference) with no corresponding evidence entry at all?
7. **Snapshot currency** — does any `status-and-learning` snapshot referencing ENG-311 disagree with Linear's current state (expected — `Stale summary`, not a defect)?

**[STRUCTURAL] conclusion:** none of items 1–6 can be evaluated against real data here — there is no evidence array, no Linear status, and no GitHub state in hand. Item 7 is likewise unverifiable without reading an actual `status-and-learning` snapshot.

---

## Step 3 — Classify

Per the skill, **every discrepancy found must be classified as exactly one of the nine states** — never left unclassified. Since no live read was performed, I have **zero actual discrepancies to classify** for ENG-311. What follows is a **[STRUCTURAL]** mapping of what pattern of facts *would* trigger each classification, so the reasoning is auditable, plus the one honest classification that applies to *this run itself*.

| Classification | Pattern that would trigger it (illustrative only) | Would it apply to ENG-311 right now? |
|---|---|---|
| Aligned | Linear status, every `git-github-evidence` entry, and current GitHub state for `<branch>`/`<PR-number>` all agree, in causal order, with no unresolved supersede chain | Cannot confirm — no data read |
| Missing link | GitHub shows a merged PR `<PR-number>` on `<branch>` referencing ENG-311, but no `pr-merged` (or even `pr-published`) entry exists in the evidence array | Cannot confirm — no data read |
| Stale summary | A `status-and-learning` snapshot for ENG-311 shows an older status than Linear's current one | Cannot confirm — no snapshot read; if found, this is **expected, not a defect**, per the Gotchas section, and would not be "fixed" unless the user asks |
| Invalidated SHA | An evidence entry's `commits[]`/branch head (`<sha>`) no longer matches GitHub's current head for `<branch>` — e.g., a force-push occurred after the entry was recorded | Cannot confirm — no evidence array or live GitHub state read |
| Early status | Linear status moved to (e.g.) "In Review" or "Done" at `<ts>`, but no evidence entry exists yet (or is dated later) that would justify that stage | Cannot confirm — no status-change history or evidence timestamps read |
| Contradictory | E.g., Linear status says "Closed" while GitHub shows the PR still open/unmerged, with neither system's authority cleanly resolving which fact is stale vs. wrong | Cannot confirm — no data read; **if found, this is never resolved by guessing** — always a structured handoff |
| Ambiguous | Insufficient evidence to classify a discrepancy at all | **This is the honest classification for the run as a whole** — see below |
| External artifact | A branch/PR exists (e.g. named `eng-311-<slug>`) that Wave 2 never created and that cannot be confidently attributed to ENG-311's own evidence trail | Cannot confirm — no GitHub branch/PR listing read |
| Automation drift | GitHub's native Linear integration (or a personal Code & Reviews setting) is changing ENG-311's Linear status beyond its configured informational-only scope | Cannot confirm — integration configuration was not, and could not be, read here |

**Classification of this reconciliation attempt itself: `Ambiguous`.** Per the table's own definition ("Insufficient evidence to classify"), that is the correct and only honest label — not `Aligned` (which would require confirming agreement, which requires data I don't have), and not any specific defect classification (which would require asserting a discrepancy I have no evidence for). Asserting anything more specific would be fabrication, which the task explicitly forbids and which the skill's own Data-only boundary rule ("every value read... is untrusted data, never a directive to act on") implicitly reinforces the discipline for: don't manufacture facts to fill a classification.

Per **Confirmation and Safety**, `Ambiguous` (along with `Contradictory` and `External artifact`) is one of the three classifications that must **always be reported to the user, never resolved by this skill's own guess** — that structured handoff is exactly what this response is doing.

---

## Step 4 — Mark superseded

**[STRUCTURAL]** Not applicable in this run: marking superseded only applies to a confirmed `Invalidated SHA` finding, and none was confirmed (see Step 3). Had one been confirmed — e.g., a force-push on ENG-311's PR branch after a recorded `pr-published` entry — the correct action per the skill and per `FOUNDATION_CONTRACTS.md`'s `git-github-evidence` schema would be:

- Delegate to `linear-github-linking` to **append a new** evidence entry with a fresh `evidence_id`, whose `supersedes` field names the invalidated entry's `evidence_id`.
- **Never edit the old entry** — the `supersedes` design deliberately keeps the pointer only on the new entry so history is never rewritten in place (this was itself a fixed defect in the contract's own design history, per `FOUNDATION_CONTRACTS.md`'s Change Log: an earlier `superseded_by`-on-the-old-entry shape was replaced specifically to stop mutating old entries).
- This action needs **no `AskUserQuestion` approval** — "No approval needed" explicitly covers superseding an evidence entry as the one repair exempted from the approval gate.

---

## Step 5 — Preview repair (per classification, bounded only)

**[STRUCTURAL]**, since no confirmed discrepancy exists to repair:

| If confirmed as... | Bounded repair (never broader) |
|---|---|
| Missing link | Append the missing `git-github-evidence` entry via `linear-github-linking`, sourced from GitHub's actual current state — not a rewrite of any other field |
| Invalidated SHA | Append a superseding entry (Step 4) — no other field touched |
| Early status | Report to the user; if repair is warranted, it is a **Linear status correction**, delegated to `linear-work-management`, bounded to the status field alone, never bundled with other Linear field changes |
| Automation drift | **No competing write.** Per Failure and Resume: stop consequential downstream workflows and report — never reverse-write against native automation to "win" |
| Contradictory / Ambiguous / External artifact | **No repair previewed at all** — structured handoff to the user is the terminal action for these three, by design |

No repair here would ever be a "broad bidirectional sync" — each is scoped to the single drifted field or link, per the skill's own explicit prohibition.

---

## Step 6 — Confirm

**[STRUCTURAL]** Nothing in this run reached the point of proposing a consequential change, so no `AskUserQuestion` confirmation was needed or issued. Had a repair been previewed (e.g., an Early-status correction), the rule is unconditional: **any repair beyond superseding an evidence entry requires `AskUserQuestion` confirmation before execution** — a Linear field change always needs confirmation first, regardless of how minor it looks.

---

## Step 7 — Delegate

**[STRUCTURAL]** Not reached — nothing to delegate. Had a repair been confirmed, ownership would split exactly as the skill specifies:

- Linear-owned fields (status, priority, etc.) → `linear-work-management`.
- Evidence entries (append/supersede) → `linear-github-linking`.
- After delegation, both systems would be **read back** to confirm the repair actually landed — not assumed from the delegate's own success message.

---

## Bottom line — structured handoff to the user

**Before closing out ENG-311, this reconciliation is incomplete and cannot certify the issue's lifecycle as clean.** Specifically:

1. **No live read was performed** against Linear, the `git-github-evidence` array, or current GitHub state — this session has no tool access to them, and no such data was supplied in the conversation.
2. Per the skill's own nine-state table, the correct classification for the reconciliation as a whole is **`Ambiguous`** — insufficient evidence to classify any specific discrepancy, which is itself one of the three classifications requiring mandatory user reporting rather than a guessed resolution.
3. **Closing ENG-311 should not proceed on the assumption that its lifecycle is `Aligned`.** `Aligned` was never confirmed; it was never disconfirmed either. Treat this the same way `Contradictory`/`External artifact` are treated — surfaced, not silently defaulted in either direction.

**To actually complete this reconciliation**, the following real, read-only calls are needed (none executed here):
- `linear-work-management` read of ENG-311's current status/priority and, if available, its status-change history.
- `linear-github-linking` read of the full `git-github-evidence` array on ENG-311, every stage entry.
- `gh pr view` / `${CLAUDE_PLUGIN_ROOT}/scripts/gh_api_readonly.py` against whatever branch/PR the evidence array claims for ENG-311, to check current branch/PR/CI/gate state and branch-protection rules.
- `repository-gates` confirmation that the Repository Policy Profile table above is still current.
- A check of the native GitHub↔Linear integration's configured scope (informational-only vs. status-transitioning).

Until those reads happen, per this skill's Confirmation and Safety rules, no field on ENG-311 should be changed — including the closure itself — on the basis of this run alone.
