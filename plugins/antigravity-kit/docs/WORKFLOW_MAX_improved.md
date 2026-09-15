# Max Workflow — Repository Suitability Analysis & Project Foundation

> Determine whether a local copy of a GitHub repository is the right foundation for an own project. If suitable, establish ownership, quality baseline, target roadmap, and governance framework — so that the first line of new code is written on a known foundation with a clear direction.

---

## How to Use

1. Steps run sequentially unless `Prerequisites` allow parallelism. Steps marked
   with `Parallelizable with:` can be launched together to save time.
2. Each step starts with an **interview** (agent asks, human answers), then the
   agent executes and presents results for **approval**. Before each interview,
   the agent must present a **Step Context Preamble** (see below).
   **The interview is a blocking gate** — the agent must not begin execution
   until the human has answered the interview questions. Skipping interviews
   to save time is not permitted; if the human defers, the agent records the
   deferral and proceeds with the agent's best judgment, noting the skipped
   decision in the phase self-review.
3. Mark each step complete in `docs/WORKFLOW_STATE.md` after approval.
4. Steps marked `Mandatory: No` can be skipped — record the skip reason.
5. After each step, the agent runs the **Sub-Step Detection Rules** checklist.
6. After each phase, the agent runs the **Phase Gate** checkpoint, presents a
   **Per-Phase Self-Review and Self-Critique** (see below), and then presents
   a **Phase Summary** (see below).
7. The agent must follow the **Retry Limit Principle** (see below) — never
   silently retry a failing task more than 3 times.
8. The agent must follow the **Communication Guidelines** (see below) —
   especially when using background subagents or requesting approvals.
9. All evaluation artifacts are written to `docs/draft/<repo-name>/` unless
   the human specifies otherwise.
10. The workflow has **29 steps across 8 phases** (Steps 1–28 plus the
    mandatory Step 29 retrospective). All step counts and progress indicators
    must say "Step N of 29, Phase M of 8".

## Sub-Step Detection Rules

After completing each step's main work, the agent checks:

1. **Produced an artifact?** → Self-review required
2. **Made claims about codebase?** → Self-verify required
3. **Involved evaluation/analysis?** → Self-critique required
4. **Had alternatives?** → Decision-making required
5. **Modified files?** → Validation required
6. **Output consumed by next step?** → Approval required
7. **Processed multiple items?** → Iteration with checkpoints required

If any answer is "yes" but the sub-step wasn't performed, the agent flags it as a gap.

## Retry Limit Principle

After **3 failed attempts** at any task (fixing a test, building, running a
command, etc.), the agent must **stop, categorize, and escalate**. Never
silently retry indefinitely.

**Protocol:**

```
ATTEMPT 1: Fix the failure
  → If fixed: move on
  → If not fixed: proceed to attempt 2

ATTEMPT 2: Try a different approach
  → Communicate: "First approach didn't work. Trying X instead."
  → If fixed: move on
  → If not fixed: proceed to attempt 3

ATTEMPT 3: Last try with explicit warning
  → Communicate: "This is my third attempt. If this doesn't work,
     I'll stop and categorize all remaining failures for your review."
  → If fixed: move on
  → If not fixed: STOP and escalate

ESCALATION (after 3 failed attempts):
  1. Stop fixing — switch to categorization mode
  2. Classify each remaining failure:
     - FIXABLE: real bug, can be fixed with more investigation
     - PLATFORM: OS-specific issue (Windows path, encoding, etc.)
     - PRE-EXISTING: existed before our changes, not our responsibility
     - BLOCKING: prevents progress, needs human decision
  3. Present the categorized list to the human
  4. Ask: "Should I (a) keep trying on FIXABLE items, (b) document
     PLATFORM/PRE-EXISTING items and move on, or (c) something else?"
```

This applies to all repetitive tasks: test fixes, build errors, lint failures,
CI debugging, etc.

## Step Context Preamble

Before every interview question block, the agent must present a **3-line
context preamble** so the human never has to guess what step they're in or
what the questions affect:

```
## Step N of 29, Phase M of 8 — [Phase Name]

**Goal:** [What this step accomplishes — 1 sentence]
**What happens next:** [What the agent will do after the interview — 1 sentence]
**Decision needed:** [What the human is deciding — 1 sentence]
```

Then the interview questions follow, with each option including a
parenthetical implication:

```
Q: [Question text]
  - Option A (faster, less detailed)
  - Option B (slower, more detailed)
  - Option C (balanced)
```

**Example:**

```
## Step 12 of 29, Phase 4 of 8 — Evaluate

**Goal:** Evaluate strengths, weaknesses, opportunities, and threats
for the project and each component cluster.
**What happens next:** I'll analyze all source files and produce
docs/SWOT.md with findings per cluster. This feeds into the TODO
backlog (Step 14) and scorecards (Step 17).
**Decision needed:** How to group components for analysis.

Q: Should components be analyzed individually or grouped?
  - Group by cluster (5-6 modules per SWOT, ~10 SWOTs, faster)
  - Individual analysis (20+ SWOTs, more detail, much slower)
  - By layer (5 SWOTs: core/skills/agents/scripts/config)
```

## Phase Summary

At each phase gate, the agent presents a **Per-Phase Self-Review and
Self-Critique** (see below), then a **Phase Summary** before requesting
approval to proceed:

```
═══ PHASE N COMPLETE — ENTERING PHASE N+1 ═══

**Completed:** [N] steps, [N] artifacts created
**Key findings:** [1-2 sentence summary of what was learned]
**Next phase:** [Phase name] — [1 sentence description]
**Approval needed:** Do you approve Phase N as complete?
```

## Per-Phase Self-Review and Self-Critique

Before presenting the Phase Summary and requesting approval, the agent must
run and present a short self-review with self-critique. This is **mandatory
at every phase gate** — it is not optional and must not be skipped.

The self-review covers four items, presented as a short section immediately
before the Phase Summary:

1. **Sub-Step Detection check:** For each step in this phase, did it produce
   an artifact, make claims about the codebase, involve evaluation/analysis,
   have alternatives, modify files, have output consumed by the next step, or
   process multiple items? For each "yes," confirm the corresponding sub-step
   (self-review, self-verify, self-critique, decision-making, validation,
   approval, iteration) was actually performed. Flag any skipped sub-steps
   as gaps.

2. **Self-critique:** What did you miss this phase? Where might the analysis
   be biased or shallow? What would you do differently if you re-ran this
   phase? Be honest — don't sugarcoat.

3. **Self-review:** Re-read the artifacts produced this phase. Are they
   internally consistent? Do cross-references resolve? Are there
   contradictions between artifacts? Are there claims not backed by evidence?

4. **Interview compliance:** Did you ask every interview question the workflow
   specifies for each step in this phase? If not, list which questions were
   skipped and whether the skipped decision affected the outcome. This is the
   most common failure mode — be rigorous about checking it.

Keep it concise — a few bullet points per item is sufficient. The goal is
honest accountability, not performative completeness. If everything was done
correctly, say so briefly; don't invent problems.

## Communication Guidelines

### Background Subagents

When launching a background subagent for a large task (SWOT, scorecards,
architecture analysis):

1. **Announce it**: "Working on [X] in the background. I'll notify you
   when it's done."
2. **Use the wait productively**: "Meanwhile, let me ask about Step N+1..."
3. **Notify on completion**: "The [X] analysis is complete. Here's a summary..."
4. **Specify output constraints**: Tell the subagent to keep output under
   12KB (safety margin below the 15KB truncation threshold), or to write
   files directly instead of returning content, to avoid truncation.
5. **Select the right subagent profile:**
   - Use a **write-capable** subagent profile (e.g. `subagent_general` or
     equivalent) when the subagent should write artifacts directly to disk.
     Instruct it: "Write the document to `[exact path]` and return only a
     1-paragraph summary."
   - Use a **read-only** subagent profile (e.g. `subagent_explore` or
     equivalent) only for pure research tasks where the subagent returns
     findings to the main agent for synthesis.
   - **Never** launch a read-only subagent for a document-generation task
     and then manually write its returned content to a file — this causes
     truncation, content loss, and an unnecessary manual step.

### Approval Requests

Each approval request must include:
1. **What was done** — concrete summary of work completed
2. **What artifacts were created** — file paths and counts
3. **What happens next if approved** — the next step or phase
4. **What happens if not approved** — what will be revisited

### Progress Indicators

- Show "Step N of 29, Phase M of 8" with each interaction
- At phase gates, show "Artifacts created so far: N files across M phases"
- Use visual phase separators (see Phase Summary above)

## Phase Overview

The workflow has **29 steps across 8 phases**. Steps 1–28 produce evaluation
and planning artifacts. Step 29 (Session Retrospective) closes the workflow by
capturing lessons learned for future runs.

| Phase | Steps | Gate | Parallelizable Steps |
|---|---|---|---|
| 1 — Appropriate & Verify | 1–6 | Codebase clean, tested, rebranded | — |
| 2 — Understand | 7–9 | Architecture, deps, capabilities mapped | 7 ∥ 8 |
| 3 — Envision | 10–11 | Roadmap complete | — |
| 4 — Evaluate | 12–14 | SWOT + TODOs complete | 12 ∥ 13 |
| 5 — Score | 15–19 | Scorecards + responsibilities complete | 15→16, then 17, then 18 ∥ 19 |
| 6 — Decide | 20 | Go/No-Go verdict recorded | — |
| 7 — Operationalize | 21–24 | Docs, policies, ADRs complete | 21 ∥ 22, then 23, then 24 |
| 8 — Own & Plan | 25–28 | Git, CI/CD, upstream, migration ready | 25, then 26 ∥ 27, then 28 |
| Post-Workflow | 29 | Retrospective complete | — |

## Field Reference

- **Mandatory:** Must this step always run?
- **Project-specific:** Is the content tied to this exact project?
- **Project-type agnostic:** Does the structure work for any project type?
- **Adaptation Steps:** What to change for other project types (if not agnostic)
- **Actor:** Agent / Human / Collaborative
- **Effort:** S (<30min) / M (30min–2hr) / L (2+hr) / XL (multi-session)
- **Prerequisites:** Which steps must be complete before this step can start
- **Skip Condition:** When can this step be skipped?
- **Iteration Pattern:** How multiple items are processed (if applicable)
- **Phase Gate:** Checkpoint criteria (only on last step of each phase)

---

## Step 1 — Multi-Agent Cleanup

**Mandatory:** Yes (if multi-implementation) | **Project-specific:** Yes | **Project-type agnostic:** No
**Adaptation Steps:** Redefine "unwanted variants" per project type (e.g. remove Vue keep React, remove Flask keep FastAPI).
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** None (first step)
**Skip Condition:** Repository contains only one implementation — no cleanup needed.
**Iteration Pattern:** N/A (single deletion pass)

**Description:** Remove all non-target implementations, profiles, scripts, and fixtures from the local copy.
**Purpose:** Strip down to the single implementation that will serve as the foundation.
**Goals:**
- Delete all code/configs/scripts belonging to non-target implementations.
- Leave only the target implementation and shared infrastructure.
**Requirements:**
- File deletion privileges.
- Knowledge of which directories belong to which implementation.
**Constraints/Boundaries:**
- Do not delete core protocol/spec files shared across implementations.
- Preserve target implementation directory entirely.
**Input:** Local working copy of the multi-implementation repository.
**Output:** Repository containing only the target implementation.
**Decisions:**
- Which directories are implementation-specific vs. shared.
- Whether any code needs rescuing before deletion.
**Artifacts:** Deletion of unwanted directories/files. No file artifact created.

**Interview Questions:**
1. Which implementation is the target (keep) vs. unwanted (delete)?
2. Are there any shared files that must be preserved?
3. Should any code be rescued from a doomed directory before deletion?

**Sub-Steps:**
- [Decision] Agent presents deletion plan → human approves before execution
- [Self-verify] After deletion, agent scans for residual references
- [Approval] Human confirms cleanup is complete

**Output Hand-off:** Cleaned repository → Step 2 scans for residuals.

**Prompt Sample:**

> This is a local copy of a [project type]. I will use this to create my own [project name]. Cleanup this local copy keeping only [target implementation] and removing [unwanted implementations].

---

## Step 2 — Residual Reference Cleanup

**Mandatory:** Yes (if Step 1 performed) | **Project-specific:** Yes | **Project-type agnostic:** No
**Adaptation Steps:** Scan for references to deleted components using project-appropriate search.
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 1 complete
**Skip Condition:** Step 1 was skipped (no deletions performed).
**Iteration Pattern:** N/A (single scan-and-fix pass)

**Description:** Scan all remaining files for residual references to deleted implementations and remove them.
**Purpose:** Ensure no broken paths, stale test steps, or orphaned metrics remain.
**Goals:**
- Zero residual references to deleted implementations in executable/config files.
- All test scripts, CI configs, and budget files reflect only the target implementation.
**Requirements:**
- Grep or code-search capability.
- Understanding of which references are stale vs. legitimately retained.
**Constraints/Boundaries:**
- Do not remove references to required subdirectory names.
- Test fixture content may contain internal links that are not repo-level references.
**Input:** Repository after Step 1 deletions.
**Output:** Repository with zero stale references.
**Decisions:**
- Whether each residual reference is stale (delete) or benign (keep).
- Whether a test script section can be trimmed vs. requires rewrite.
**Artifacts:** Updated CI configs, test scripts, budgets, README files.

**Interview Questions:**
1. Are there any references that look stale but are actually intentional?
2. Should test fixtures with internal links to deleted paths be updated or left as-is?

**Sub-Steps:**
- [Self-review] Agent re-reads all modified files for consistency
- [Self-verify] Agent runs final grep to confirm zero residuals
- [Approval] Human confirms zero residuals before proceeding

**Output Hand-off:** Clean repository → Step 3 checks for broken config directories.

**Prompt Sample:**

> *(Implicit follow-up — agent proactively scans for residual references after deletions are confirmed.)*

---

## Step 3 — Remove Broken Config Directories

**Mandatory:** No (only if broken config dirs exist) | **Project-specific:** Yes | **Project-type agnostic:** No
**Adaptation Steps:** Identify and remove any config directories pointing to deleted implementations.
**Actor:** Collaborative | **Effort:** S
**Prerequisites:** Steps 1–2 complete
**Skip Condition:** No broken config directories exist after Steps 1–2.
**Iteration Pattern:** N/A

**Description:** Delete broken config directories, confirm core protocol files are kept, clean stale references from docs.
**Purpose:** Eliminate last broken pointers while preserving protocol/spec files the target depends on.
**Goals:**
- Remove broken config directories and all references to them.
- Preserve core protocol/spec files.
- Clean documentation of stale references.
**Requirements:**
- Understanding of which files are config (deletable) vs. protocol (must keep).
**Constraints/Boundaries:**
- Core protocol files must not be modified.
- Only remove implementation-specific sections from docs, keep general sections.
**Input:** Repository after Steps 1–2.
**Output:** Repository with no broken config directories.
**Decisions:**
- Each suspicious directory/file: delete vs. keep.
**Artifacts:** Deleted directories, updated docs.

**Interview Questions:**
1. Are there any config directories that might be broken pointers?
2. Which files are core protocol (must keep) vs. implementation-specific (can delete)?

**Sub-Steps:**
- [Decision] Agent presents keep/delete list → human approves
- [Self-verify] Agent confirms no references to deleted dirs remain
- [Approval] Human confirms before proceeding

**Output Hand-off:** Clean repository → Step 4 rebrands.

**Prompt Sample:**

> Are these directories/files necessary, or should I remove them? [list of suspicious paths]

---

## Step 4 — Rebrand and Relicense

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None — any project needs identity and license setup.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 1–3 complete
**Skip Condition:** Never (identity and license are always required for a derivative project).
**Iteration Pattern:** N/A

**Description:** Replace author, URL, names, versions, and license across all metadata files. Add attribution and third-party notices. Decide on translation/language files.
**Purpose:** Establish full ownership identity and legal compliance for the derivative work, including a clear language policy.
**Goals:**
- All metadata reflects new author, repo URL, project name, and version.
- License changed with proper attribution to original source.
- Original license text preserved in third-party notices.
- Non-English documentation files (e.g. translated READMEs) are either
  rebranded, dropped, or explicitly deferred — not left ambiguous.
**Requirements:**
- New identity parameters (author, GitHub user, URL, names, versions).
- New license text.
- Original license text for attribution.
- Inventory of all non-English documentation files in the repository.
**Constraints/Boundaries:**
- License change requires attribution to original source.
- Third-party notices must preserve original license text verbatim.
- Translation parity is an ongoing maintenance burden — the default for
  derivative projects is English-only unless the human explicitly opts in.
- If translations are dropped, associated drift-detection tests must also be
  removed (not left as failing tests).
**Input:** New identity parameters, inventory of non-English files.
**Output:** Fully rebranded repository with legal compliance and a clear language policy.
**Decisions:**
- License choice (Apache 2.0, MIT, etc.).
- Version reset strategy (0.1.0 for new project vs. continue upstream versioning).
- Translation policy: keep, drop, or update non-English documentation.
**Artifacts:** Updated `README.md`, metadata files, `LICENSE`, `THIRD_PARTY_NOTICES.md`.
Optionally: removed translation files and associated tests.

**Interview Questions:**
1. What is the new author name, GitHub username, and repo URL?
2. What license should the project use? (Consider compatibility with original license)
3. What version should the project start at?
4. Who should be credited in the attribution section?
5. **Should non-English documentation files (e.g. translated READMEs) be kept,
   dropped, or updated for the new project?**
   - Keep and rebrand (maintain translation parity — ongoing burden)
   - Drop entirely (English-only — simpler maintenance; **default for derivative projects**)
   - Drop now, allow community-contributed translations later (English-only
     with a documented contribution path)
   - Update and rebrand (one-time effort to rebrand existing translations)

**Sub-Steps:**
- [Decision] Agent presents rebrand plan including translation policy → human approves
- [Validation] Agent verifies all metadata files are consistent
- [Self-review] Agent re-reads all modified files
- [Self-verify] Agent greps for old names/URLs to confirm none remain
- [Self-verify] If translations dropped, agent confirms associated drift-detection tests are also removed
- [Approval] Human confirms rebrand is complete

**Output Hand-off:** Rebranded repository → Step 5 restructures. Translation
policy established here is referenced by Steps 7 (architecture), 12 (SWOT),
17 (scorecards), and 20 (decision gate) — they no longer need to evaluate
translation files as open questions.

**Prompt Sample:**

> Replace author, github-user, github-repo, etc.: [new identity parameters]. Create attribution and third-party notices. Change license from [old] to [new]. Decide on non-English documentation: keep, drop, or update.

---

## Step 5 — Directory Restructure

**Mandatory:** No (only if structure needs changing) | **Project-specific:** Yes | **Project-type agnostic:** No
**Adaptation Steps:** Restructure per project type conventions (e.g. `src/` for libraries, `packages/` for monorepos).
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Step 4 complete
**Skip Condition:** Directory structure already follows conventions.
**Iteration Pattern:** N/A

**Description:** Move project to conventional directory layout, update all path references.
**Purpose:** Adopt a structure that is self-explanatory and matches deployment/publishing expectations.
**Goals:**
- Project lives at conventional location.
- Zero stale references to old paths.
- All tooling and docs reference new paths.
**Requirements:**
- File-move capability (user may perform move).
- Search capability to find all references.
**Constraints/Boundaries:**
- Do not rename required subdirectories.
- Only move the parent directory, not required inner config.
**Input:** Rebranded repository with old directory structure.
**Output:** Restructured repository with all references updated.
**Decisions:**
- New directory layout and naming.
**Artifacts:** Updated test scripts, CI configs, docs, metadata files.

**Interview Questions:**
1. What is the target directory structure?
2. Are there any path references that might be missed by automated search?

**Sub-Steps:**
- [Decision] Agent presents new structure → human approves
- [Validation] Agent verifies all paths resolve
- [Self-review] Agent re-reads modified files
- [Self-verify] Agent greps for old paths to confirm none remain
- [Approval] Human confirms restructure is complete

**Output Hand-off:** Restructured repository → Step 6 runs tests.

**Prompt Sample:**

> I moved the project from [old path] to [new path]. Update all stale references.

---

## Step 6 — Post-Cleanup Test Verification

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** Use project-appropriate test runner (pytest, jest, go test, etc.).
**Actor:** Agent | **Effort:** S
**Prerequisites:** Steps 1–5 complete
**Skip Condition:** No test suite exists (document this as a gap — tests should be created).
**Iteration Pattern:** N/A

**Description:** Run the full test suite after all cleanup, rebranding, and restructuring to confirm the codebase works.
**Purpose:** Verify that aggressive modifications did not break structural integrity. No analysis on a broken foundation.
**Goals:**
- All remaining tests pass (or failures are documented and understood).
- No broken imports, missing files, or stale path references.
**Requirements:**
- Test runner available.
- API keys for behavioral tests (or skip those).
**Constraints/Boundaries:**
- Behavioral/eval tests may require API keys and incur costs — run structural tests first.
- Test failures caused by cleanup are bugs in Steps 1–5, not in original code.
**Input:** Repository after Steps 1–5.
**Output:** Test results with any failures documented.
**Decisions:**
- Which test layers to run.
- Whether to fix failing tests immediately or document as known issues.
**Artifacts:** Test run output. Optional: `docs/TEST_RESULTS.md`.

**Interview Questions:**
1. Which test layers should be run? (structural only, or also behavioral/eval?)
2. Should failing tests be fixed immediately or documented as known issues?

**Sub-Steps:**
- [Decision] Agent presents test plan → human approves scope
- [Validation] Agent runs tests and verifies results
- [Self-verify] Agent confirms no broken paths cause failures
- [Approval] Human confirms test results are acceptable

**Output Hand-off:** Verified working codebase → Step 7 begins analysis.

**Phase Gate (Phase 1 — Appropriate & Verify):**
- [ ] Codebase contains only the target implementation
- [ ] Zero residual references to deleted components
- [ ] All metadata reflects new identity
- [ ] License changed with attribution preserved
- [ ] Directory structure follows conventions
- [ ] Test suite passes (or failures documented)

**Prompt Sample:**

> Run all structural tests and confirm they pass after cleanup. Document any failures.

---

## Step 7 — Architecture Analysis

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** Adjust architecture dimensions per tech stack (component tree for React, command parser for CLI, service mesh for microservices, etc.).
**Actor:** Agent | **Effort:** L
**Prerequisites:** Step 6 complete (Phase 1 gate passed)
**Skip Condition:** Never — architecture analysis is the foundation for all subsequent steps.
**Iteration Pattern:** N/A (single comprehensive pass)

**Description:** Examine codebase structure, tech stack, external tools, connections, and prerequisites. Document in a single architecture overview.
**Purpose:** Establish a factual baseline of what the repository is and how its pieces fit together.
**Goals:**
- Complete map of repo layout, architecture, and data model.
- Identification of all external tools, connections, and optional dependencies.
- Clear separation of "using" vs. "developing" prerequisites.
**Requirements:**
- Access to all source files, configs, and scripts.
- Understanding of the project's paradigm.
**Constraints/Boundaries:**
- Descriptive, not evaluative — no quality judgments here.
- Document what exists, not what should exist.
**Input:** Cleaned, rebranded, restructured repository.
**Output:** `docs/ARCHITECTURE.md`.
**Decisions:**
- Level of detail (component-level vs. file-level).
- Whether to include diagrams or keep prose + tables.
**Artifacts:** `docs/ARCHITECTURE.md`, `scripts/README.md` (if applicable).

**Interview Questions:**
1. What level of detail is needed? (overview, component-level, or file-level?)
2. Should the doc include diagrams, or is prose + tables sufficient?
3. Are there any external tools or connections you already know about that should be highlighted?

**Sub-Steps:**
- [Self-critique] Agent reviews: what did I miss? What dimensions did I not cover?
- [Self-review] Agent re-reads the architecture doc for errors
- [Self-verify] Agent checks claims against actual source files
- [Approval] Human confirms architecture doc is accurate and complete

**Output Hand-off:** Architecture doc → Steps 8, 9, 21, 22, 23 all consume it.

**Prompt Sample:**

> Analyze the codebase architecture, tech-stack, external tools and connections, prerequisites. Create `docs/ARCHITECTURE.md`.

---

## Step 8 — Dependency & License Audit

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** Adjust dependency scope (runtime deps matter more for non-plugin projects; check package.json, requirements.txt, go.mod, etc.).
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 7 complete
**Skip Condition:** Project has zero third-party dependencies (rare — verify carefully).
**Iteration Pattern:** One audit entry per dependency, batched in groups of 10–15

**Description:** Systematically audit all third-party dependencies for license compatibility, maintenance status, security vulnerabilities, and alignment with chosen license.
**Purpose:** Ensure no dependency introduces legal, security, or operational risk.
**Goals:**
- Complete inventory of all external dependencies with versions and licenses.
- Identification of license incompatibilities.
- Flagging of unmaintained or vulnerable dependencies.
- Updated third-party notices with full attribution.
**Requirements:**
- Access to all dependency declarations.
- Knowledge of license compatibility rules.
**Constraints/Boundaries:**
- Optional/user-installed tools are noted but not blocking.
- Focus on bundled and dev dependencies.
**Input:** `docs/ARCHITECTURE.md` (external tools section), all dependency files.
**Output:** `docs/DEPENDENCY_AUDIT.md`.
**Decisions:**
- Whether each flagged dependency is blocking or advisory.
- Whether to replace, remove, or accept each dependency.
**Artifacts:** `docs/DEPENDENCY_AUDIT.md`, updated `THIRD_PARTY_NOTICES.md`.

**Interview Questions:**
1. Which dependencies are critical (cannot be replaced) vs. optional (can be swapped)?
2. Are there any dependencies you already know have issues?
3. What is the risk tolerance? (Block on any vulnerability, or only on high/critical?)

**Sub-Steps:**
- [Iteration] Agent processes dependencies in batches of 10–15, with checkpoints
- [Decision] Agent presents flagged dependencies → human decides replace/remove/accept
- [Self-critique] Agent reviews: did I miss any dependencies? Any transitive deps?
- [Self-review] Agent re-reads audit doc for accuracy
- [Self-verify] Agent cross-checks audit against actual dependency files
- [Approval] Human confirms audit is complete

**Output Hand-off:** Dependency audit → Step 20 (go/no-go) consumes flagged risks.

**Prompt Sample:**

> Audit all third-party dependencies. For each: name, version, license, maintenance status, security vulnerabilities, compatibility with [chosen license]. Create `docs/DEPENDENCY_AUDIT.md`.

---

## Step 9 — Capability Scope Assessment

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** Redefine capability categories per project type (e.g. "auth", "pagination", "caching" for web apps; "shell completion", "pipe support" for CLIs).
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Step 7 complete
**Skip Condition:** Never — capability mapping is essential for roadmap creation.
**Iteration Pattern:** N/A

**Description:** Map what the repository implements, recommends but doesn't build, and explicitly misses — across all capability categories.
**Purpose:** Determine alignment with intended new direction and identify gaps.
**Goals:**
- Three-tier classification: in-scope, recommended/adjacent, missing/out-of-scope.
- Coverage of all capability categories the user cares about.
- Clear statement of design philosophy.
**Requirements:**
- Deep familiarity with source files and protocol.
- Understanding of user's intended new direction.
**Constraints/Boundaries:**
- Factual mapping, not evaluation.
- "Missing" means "not present," not "should be added."
**Input:** `docs/ARCHITECTURE.md`, all source files.
**Output:** In-chat structured classification.
**Decisions:**
- Which capability categories to assess.
- Where to draw line between "recommended" and "missing."
**Artifacts:** In-chat response. Feeds into Step 10.

**Interview Questions:**
1. What capability categories matter most to you? (e.g. auth, caching, i18n, knowledge graph, ...)
2. What is the intended new direction — what do you want to add or change?
3. Are there capabilities you know exist that I should verify?

**Sub-Steps:**
- [Self-critique] Agent checks: am I biased toward what exists? Did I miss emergent capabilities?
- [Self-review] Agent re-reads classification for consistency
- [Self-verify] Agent checks claims against actual source files
- [Approval] Human confirms classification is accurate

**Output Hand-off:** Capability classification → Step 10 creates roadmap from it.

**Phase Gate (Phase 2 — Understand):**
- [ ] Architecture documented with all dimensions covered
- [ ] All dependencies audited for license/security/maintenance
- [ ] Capabilities classified into in-scope / recommended / missing
- [ ] Design philosophy stated explicitly

**Prompt Sample:**

> What's in the project's scope, what's recommended, and what's missing regarding capabilities (e.g. [category list])?

---

## Step 10 — Roadmap Creation

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Step 9 complete
**Skip Condition:** Never — roadmap is the backbone for all subsequent analysis.
**Iteration Pattern:** N/A

**Description:** Consolidate all capabilities into a structured roadmap with status markers and section-based organization.
**Purpose:** Provide a single navigable document tracking every capability by status.
**Goals:**
- Every capability from Step 9 appears with a status marker.
- Logical section grouping.
- Status markers: ✅ Implemented / 🔶 Partial / ⬜ Missing.
**Requirements:**
- Step 9 classification.
- Understanding of functional grouping.
**Constraints/Boundaries:**
- Roadmap is a snapshot, not a commitment.
- No duplication — cross-reference instead.
**Input:** Step 9 classification, `docs/ARCHITECTURE.md`.
**Output:** `docs/ROADMAP.md`.
**Decisions:**
- Section organization.
- Status marker system.
**Artifacts:** `docs/ROADMAP.md`.

**Interview Questions:**
1. How should capabilities be grouped? (by functional area, lifecycle stage, or priority?)
2. What status markers do you prefer? (emoji, text, checkboxes?)
3. Should the roadmap include effort estimates or just status?

**Sub-Steps:**
- [Decision] Agent presents section structure → human approves
- [Validation] Agent verifies no duplicates across sections
- [Self-review] Agent re-reads roadmap for completeness
- [Approval] Human confirms roadmap is complete

**Output Hand-off:** Roadmap → Steps 11, 12, 14 consume it.

**Prompt Sample:**

> Create a `docs/ROADMAP.md` and add all items (implemented, not implemented and missing) to the roadmap.

---

## Step 11 — Roadmap Expansion

**Mandatory:** No (only if user has additional items) | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** S
**Prerequisites:** Step 10 complete
**Skip Condition:** User has no additional items beyond what Step 9 identified.
**Iteration Pattern:** N/A

**Description:** Add user-specified items to the roadmap, cross-referencing existing rows to avoid duplication.
**Purpose:** Ensure roadmap reflects full intended scope, including items not inferable from codebase.
**Goals:**
- All user-specified categories added.
- No duplication — cross-reference instead.
- New items tagged with appropriate status.
**Requirements:**
- User's explicit list of additional items.
- Existing `docs/ROADMAP.md` to check for overlaps.
**Constraints/Boundaries:**
- User items take priority — add even if they seem covered.
- Each new section should cross-link to related existing rows.
**Input:** `docs/ROADMAP.md`, user's list of additional items.
**Output:** Updated `docs/ROADMAP.md`.
**Decisions:**
- Whether each user item maps to existing row or needs new row.
- Section numbering for new sections.
**Artifacts:** `docs/ROADMAP.md` (updated).

**Interview Questions:**
1. What items should be added that aren't yet covered?
2. For each item: is this a new section, or does it relate to an existing one?
3. What priority/status should each new item have?

**Sub-Steps:**
- [Decision] Agent presents new-vs-cross-reference mapping → human approves
- [Validation] Agent verifies no duplicates
- [Self-review] Agent re-reads updated sections
- [Approval] Human confirms additions are correct

**Output Hand-off:** Expanded roadmap → Steps 12, 14 consume it.

**Phase Gate (Phase 3 — Envision):**
- [ ] All capabilities from Step 9 appear in roadmap
- [ ] User-specified items added without duplication
- [ ] Status markers applied consistently
- [ ] Cross-references between related sections

**Prompt Sample:**

> Add following items to the roadmap (if they are not yet covered): [user's list]

---

## Step 12 — SWOT Analysis: Components

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None — SWOT structure is universal.
**Actor:** Agent | **Effort:** XL
**Prerequisites:** Steps 7, 10–11 complete
**Skip Condition:** Never — SWOT is the evidence base for prioritization.
**Parallelizable with:** Step 13 (test/bench SWOT can run concurrently)
**Iteration Pattern:** One SWOT per component, batched in groups of 6, with checkpoints after each batch
**Subagent Output Constraints:** If using a background subagent, specify: "Keep each SWOT entry to 1-2 sentences. Total output under 15KB. Cite specific files/lines." Alternatively, have the subagent write files directly instead of returning content.

**Description:** Run SWOT for the project as a whole, each skill/module, and every command/component.
**Purpose:** Surface strengths, weaknesses, opportunities, threats per component and systemically.
**Goals:**
- SWOT for the project overall.
- SWOT per component (individually or grouped for tightly-coupled clusters).
- Cross-component patterns section.
**Requirements:**
- All source files read and understood.
- `docs/ROADMAP.md` for opportunity/threat context.
**Constraints/Boundaries:**
- SWOT is evaluative — quality judgments happen here.
- Keep concise — cite specific files/lines.
**Input:** All source files, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`.
**Output:** `docs/SWOT.md`.
**Decisions:**
- Which components to group vs. analyze individually.
**Artifacts:** `docs/SWOT.md`.

**Interview Questions:**
1. Which components should be analyzed individually vs. grouped?
2. Are there any known strengths or weaknesses you want to make sure are captured?
3. What scope should the SWOT cover? (code quality only, or also UX, docs, community?)

**Sub-Steps:**
- [Iteration] Agent processes components in batches of 6, with checkpoints
- [Self-critique] Agent reviews: systemic blind spots? What did I miss across components?
- [Self-review] Agent re-reads each SWOT for consistency
- [Self-verify] Agent verifies findings cite specific source files
- [Approval] Human confirms SWOTs are accurate after each batch

**Output Hand-off:** SWOT → Steps 13, 14, 17 consume it.

**Prompt Sample:**

> Run SWOT-analyses for each component and the project itself.

---

## Step 13 — SWOT Analysis: Test & Benchmark System

**Mandatory:** Yes (if test/bench system exists) | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 12 complete (or in progress — can run in parallel with remaining component SWOTs)
**Skip Condition:** No test or benchmark system exists.
**Parallelizable with:** Step 12 (launch as background subagent while Step 12 component SWOTs are being reviewed)
**Iteration Pattern:** N/A

**Description:** Extend SWOT to cover test system and benchmarking infrastructure.
**Purpose:** Ensure QA infrastructure is evaluated with same rigor as product code.
**Goals:**
- SWOT for test system (coverage, fixtures, CI).
- SWOT for benchmarking (methodology, coverage, regression gates).
- Cross-references to roadmap items.
**Requirements:**
- Test and benchmark directories understood.
- Understanding of test architecture.
**Constraints/Boundaries:**
- Focus on infrastructure, not individual test cases.
**Input:** Test/benchmark directories, `docs/SWOT.md`.
**Output:** `docs/SWOT.md` (updated).
**Decisions:**
- Whether to combine test + benchmark or keep separate.
**Artifacts:** `docs/SWOT.md` (updated).

**Interview Questions:**
1. Is there a benchmarking system, or just tests?
2. Are there any known test coverage gaps you're already aware of?
3. Should CI activation status be evaluated as part of this SWOT?

**Sub-Steps:**
- [Self-critique] Agent reviews: did I evaluate methodology, not just coverage?
- [Self-review] Agent re-reads SWOT additions
- [Self-verify] Agent verifies claims against actual test files
- [Approval] Human confirms test/bench SWOT is accurate

**Output Hand-off:** Complete SWOT → Step 14 creates TODOs from it.

**Prompt Sample:**

> Add SWOT-analyses for the test-system and benchmarking to `docs/SWOT.md`.

---

## Step 14 — Prioritized TODO Backlog

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 12–13 complete
**Skip Condition:** Never — TODOs convert analysis into action.
**Iteration Pattern:** N/A

**Description:** Synthesize SWOT weaknesses/threats + roadmap gaps into a classified, prioritized backlog.
**Purpose:** Convert findings into an actionable, ranked work list.
**Goals:**
- Every SWOT weakness/threat has a TODO item.
- Every roadmap gap has a TODO item.
- Items classified by type and prioritized P0–P3.
- Source back-references to SWOT/roadmap.
**Requirements:**
- `docs/SWOT.md` and `docs/ROADMAP.md` complete.
- Understanding of dependency ordering.
**Constraints/Boundaries:**
- TODOs are a live backlog — delete when shipped, don't mark done.
- P0 items must be fixable before scope-widening.
**Input:** `docs/SWOT.md`, `docs/ROADMAP.md`.
**Output:** `docs/TODOs.md`.
**Decisions:**
- Priority assignment criteria.
- Whether to include effort estimates.
**Artifacts:** `docs/TODOs.md`.

**Interview Questions:**
1. What priority criteria should be used? (P0 = correctness/security, P1 = high-value, P2 = features, P3 = speculative?)
2. Should items include effort estimates?
3. Are there any items you want to force into P0 that the analysis might rank lower?

**Sub-Steps:**
- [Decision] Agent presents priority assignment → human approves
- [Validation] Agent verifies every W/T has a TODO, every TODO has a source
- [Cross-ref] Agent verifies every roadmap gap (⬜) has a TODO item, and every TODO has a roadmap section ref
- [Self-critique] Agent checks: is ordering biased? Are P0 items truly blocking?
- [Self-review] Agent re-reads backlog for consistency
- [Self-verify] Agent verifies traceability links resolve
- [Approval] Human confirms backlog is complete and correctly prioritized

**Output Hand-off:** TODO backlog → Steps 15, 17, 20, 28 consume it.

**Phase Gate (Phase 4 — Evaluate):**
- [ ] SWOT completed for all components and project overall
- [ ] SWOT completed for test/benchmark system
- [ ] Every weakness/threat has a TODO item
- [ ] Every roadmap gap has a TODO item
- [ ] TODOs classified by type and prioritized P0–P3
- [ ] Source back-references resolve

**Prompt Sample:**

> Create `docs/TODOs.md` containing a backlog of classified and prioritized open items based on `docs/SWOT.md` and `docs/ROADMAP.md`.

---

## Step 15 — Scorecard Template Creation

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** No
**Adaptation Steps:** Replace/adjust scoring dimensions per project type (add Type Safety for TS/Go, API Design for web apps, reframe UX per project type).
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 12–14 complete
**Skip Condition:** Never — scorecards standardize evaluation.
**Iteration Pattern:** N/A

**Description:** Design a reusable evaluation template with frontmatter, scoring dimensions, weighted formula, and grade bands.
**Purpose:** Standardize component evaluation for comparability and auditability.
**Goals:**
- Template with identity metadata and cross-links.
- 9 weighted scoring dimensions.
- 0–5 rubric with anchors.
- Weighted total formula and grade bands.
- Per-component-type weight adjustment guidance.
**Requirements:**
- Understanding of what dimensions matter for this project type.
- Consensus on weight allocation.
**Constraints/Boundaries:**
- Template must be general enough for all component types.
- Weights must sum to 1.0.
- N/A dimensions trigger weight redistribution.
**Input:** `docs/SWOT.md`, `docs/ROADMAP.md`.
**Output:** `docs/templates/SCORE_CARD.template.md`.
**Decisions:**
- Which dimensions to score.
- Default weight allocation.
- Grade bands.
**Artifacts:** `docs/templates/SCORE_CARD.template.md`.

**Interview Questions:**
1. Which scoring dimensions matter most for this project type?
2. What should the default weights be? (or should I propose a set?)
3. What grade bands do you prefer? (A-F, 1-10, pass/fail?)
4. Should any dimensions be project-type-specific (e.g. Type Safety for TS projects)?

**Sub-Steps:**
- [Decision] Agent presents dimensions + weights → human approves
- [Validation] Agent verifies weights sum to 1.0, formula is correct
- [Self-review] Agent re-reads template for clarity and completeness
- [Approval] Human confirms template is ready to use

**Output Hand-off:** Template → Steps 16, 17 consume it.

**Prompt Sample:**

> Create a scorecard template with [N] weighted scoring dimensions, 0–5 rubric, weighted total formula, and letter grades. Applicable to [component types].

---

## Step 16 — Template Enhancement: Responsibilities, Boundaries, Constraints

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Agent | **Effort:** S
**Prerequisites:** Step 15 complete
**Skip Condition:** Never — responsibilities and boundaries are essential for architecture planning.
**Iteration Pattern:** N/A

**Description:** Add responsibilities, boundaries, and constraints section to the template.
**Purpose:** Capture the contractual surface of each component beyond scores.
**Goals:**
- Responsibilities subsection.
- Boundaries subsection with hand-off table.
- Constraints subsection covering tool/permission/dependency limits.
**Requirements:**
- Template from Step 15.
- Understanding of component interaction patterns.
**Constraints/Boundaries:**
- Responsibilities should be right-sized.
- Boundaries must include out-of-scope inputs callout.
**Input:** Template (current state).
**Output:** Template updated with new section, subsequent sections renumbered.
**Decisions:**
- Section numbering and placement.
**Artifacts:** `docs/templates/SCORE_CARD.template.md` (updated).

**Interview Questions:**
1. Should boundaries be a table or prose? (table recommended for scanability)
2. Are there any specific constraint categories to include? (tool scope, permissions, data-mutation limits, concurrency, performance budget?)

**Sub-Steps:**
- [Validation] Agent verifies section numbering is intact
- [Self-review] Agent re-reads updated template
- [Approval] Human confirms enhancement is correct

**Output Hand-off:** Enhanced template → Step 17 instantiates it.

**Prompt Sample:**

> Add responsibilities, boundaries and constraints to the template.

---

## Step 17 — Scorecards for All Components

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** No
**Adaptation Steps:** Redefine component types per project type (routes, services, models for web apps; subcommands, flag parser, I/O handlers for CLIs).
**Actor:** Agent | **Effort:** XL
**Prerequisites:** Steps 15–16 complete
**Skip Condition:** Never — scorecards quantify quality and surface systemic patterns.
**Iteration Pattern:** One scorecard per component, batched in groups of 5–6, with checkpoints after each batch
**Subagent Output Constraints:** If using a background subagent for scorecard generation, specify: "Write each scorecard as a separate file. Keep each scorecard under 3KB. Use compact format — scores table + bullet lists, not full template repetition. Return only the index file content." This avoids output truncation.

**Description:** Instantiate scorecard template for the project and every component.
**Purpose:** Generate complete scored evaluation to quantify quality and surface systemic patterns.
**Goals:**
- 1 project scorecard.
- 1 scorecard per component type.
- Navigational index with summary table.
**Requirements:**
- Completed template (Step 16).
- `docs/SWOT.md` for strength/weakness bullets.
- `docs/TODOs.md` for action links.
- All source files read.
**Constraints/Boundaries:**
- Every score of 1–2 needs matching weakness bullet.
- Every score of 5 needs matching strength bullet.
- Reuse SWOT findings — cite, don't duplicate.
- No scoring unread files.
**Input:** Template, SWOT, TODOs, all source files.
**Output:** Scorecard files + index.
**Decisions:**
- Per-component weight adjustments.
- Score calibration baseline.
**Artifacts:** `docs/scorecards/*.md`, `docs/scorecards/_index.md`.

**Interview Questions:**
1. Which components should be scored individually vs. grouped?
2. Should weight adjustments be applied per component type? (e.g. security weighted higher for ingest/auth components)
3. How should scorecards be batched? (all at once, or in groups with review checkpoints?)

**Sub-Steps:**
- [Iteration] Agent creates scorecards in batches of 5–6, with checkpoints
- [Decision] Agent presents weight adjustments per component → human approves
- [Self-critique] Agent checks: score calibration consistent? Any inflation?
- [Self-review] Agent re-reads each scorecard for formatting and completeness
- [Self-verify] Agent verifies every extreme score (1-2 or 5) has evidence
- [Approval] Human confirms each batch before proceeding to next

**Output Hand-off:** Scorecards → Steps 18, 19 consume them; Step 20 cites them.

**Prompt Sample:**

> Now create a scorecard for the project and each of its components.

---

## Step 18 — Scorecard Documentation & Agent Instructions

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 17 complete
**Skip Condition:** Never — documentation ensures reproducibility.
**Iteration Pattern:** N/A

**Description:** Create README explaining scorecard fields and agent instructions for creating/updating scorecards.
**Purpose:** Make the scorecard system self-documenting and reproducible.
**Goals:**
- README with field explanations, formulas, rubrics.
- Agent instructions with creation workflow, calculation rules, consistency rules.
**Requirements:**
- Completed scorecards as reference.
- Template for field definitions.
**Constraints/Boundaries:**
- Agent instructions must cover weight redistribution for N/A.
- Must prohibit score inflation and require evidence for extremes.
**Input:** Template, completed scorecards.
**Output:** README and agent instruction files.
**Decisions:**
- Whether to include worked examples.
- Status discipline (draft → reviewed → final).
**Artifacts:** `docs/scorecards/README.md`, `docs/CLAUDE.md` (or equivalent agent instructions).

**Interview Questions:**
1. Should the README include worked calculation examples?
2. What status lifecycle should scorecards follow? (draft → reviewed → final?)
3. Should agent instructions be in a separate file or appended to existing instructions?

**Sub-Steps:**
- [Self-review] Agent re-reads both files for clarity
- [Self-verify] Agent verifies formulas match template
- [Approval] Human confirms documentation is clear and accurate

**Output Hand-off:** Documentation → Step 19 uses scorecards; future scorecard creation follows these instructions.

**Prompt Sample:**

> Create a README explaining scorecard fields and agent instructions for creating/updating scorecards and calculating values.

---

## Step 19 — Responsibility Matrix & Boundaries Consolidation

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 17 complete
**Skip Condition:** Never — consolidated view is essential for architecture planning.
**Parallelizable with:** Step 18 (both consume scorecards; can run concurrently)
**Iteration Pattern:** N/A

**Description:** Extract responsibilities and boundaries from all component scorecards into two consolidated documents.
**Purpose:** Single-glance view of ownership and hand-offs.
**Goals:**
- Responsibility matrix table grouped by functional cluster.
- Boundaries doc with per-component statements and hand-off map.
**Requirements:**
- All component scorecards with completed responsibilities/boundaries sections.
**Constraints/Boundaries:**
- Exclude project-level scorecard.
- Extract directly without adding new analysis.
- Link back to source scorecards.
**Input:** All component scorecards.
**Output:** Two consolidated documents.
**Decisions:**
- Cluster organization.
- Whether to include hand-off direction column.
**Artifacts:** `docs/RESPONSIBILITY_MATRIX.md`, `docs/BOUNDARIES.md`.

**Interview Questions:**
1. How should components be clustered? (by function, by lifecycle stage, by layer?)
2. Should the hand-off map show bidirectional relationships or just from→to?

**Sub-Steps:**
- [Decision] Agent presents clustering → human approves
- [Validation] Agent verifies all components are covered
- [Self-review] Agent re-reads both docs for consistency
- [Self-verify] Agent verifies content matches scorecards
- [Approval] Human confirms consolidation is complete

**Output Hand-off:** Matrix + boundaries → Step 20 uses them for go/no-go assessment.

**Phase Gate (Phase 5 — Score):**
- [ ] Scorecard template created with dimensions, weights, and grade bands
- [ ] Template enhanced with responsibilities, boundaries, constraints
- [ ] Scorecards created for project and all components
- [ ] Scorecard documentation and agent instructions created
- [ ] Responsibility matrix and boundaries consolidated from scorecards
- [ ] All scorecards have evidence for extreme scores (1-2 or 5)

**Prompt Sample:**

> Create `docs/RESPONSIBILITY_MATRIX.md` and `docs/BOUNDARIES.md` based on responsibilities and boundaries in all component scorecards.

---

## Step 20 — Go/No-Go Decision Gate

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 7–19 all complete
**Skip Condition:** Never — this is the workflow's core question.
**Iteration Pattern:** N/A

**Description:** Formally evaluate all evidence and record a verdict: proceed, proceed with conditions, or start fresh.
**Purpose:** The workflow's core question, answered explicitly — not implicitly assumed.
**Goals:**
- Documented verdict (PROCEED / PROCEED WITH CONDITIONS / START FRESH).
- Reasoning grounded in specific prior artifacts.
- If conditions: explicit list of what must be met before new development.
- If start fresh: what to salvage without the codebase.
**Requirements:**
- All prior analysis artifacts (Steps 7–19).
**Constraints/Boundaries:**
- Output is a verdict, not findings.
- Every claim must cite a specific prior artifact.
- P0 TODOs are conditions (fix first or accept risk explicitly).
**Input:** All prior artifacts.
**Output:** `docs/DECISION.md`.
**Decisions:**
- Verdict.
- Which P0 items are blocking vs. accepted-as-risk.
- Whether to set a re-evaluation checkpoint.
**Artifacts:** `docs/DECISION.md`.

**Interview Questions:**
1. Based on the evidence, I recommend [VERDICT] because [1-2 sentence reasoning]. Do you agree, or do you want a different verdict?
2. If proceeding with conditions: I recommend classifying P0.[N] as blocking and P0.[M] as accepted risk because [reasoning]. Do you agree?
3. Should we set a re-evaluation checkpoint after certain conditions are met?

> **Pattern:** The agent presents a **recommended verdict with evidence** first.
> The human approves, rejects, or modifies — they don't choose from scratch.
> This is the most critical approval in the workflow.

**Sub-Steps:**
- [Draft] Agent drafts DECISION.md with recommended verdict and evidence summary
- [Decision] Agent presents recommended verdict → human approves, rejects, or modifies
- [Self-critique] Agent reviews: is evidence sufficient? Am I biased toward proceeding?
- [Self-review] Agent re-reads decision doc for logical consistency
- [Self-verify] Agent verifies every claim cites a specific artifact
- [Approval] Human signs off on verdict — this is the most critical approval in the workflow

**Output Hand-off:** Decision → Steps 24 (ADRs), 28 (migration) consume the verdict.

**Phase Gate (Phase 6 — Decide):**
- [ ] Verdict recorded: PROCEED / PROCEED WITH CONDITIONS / START FRESH
- [ ] Every claim in decision doc cites a specific prior artifact
- [ ] If PROCEED WITH CONDITIONS: blocking P0 items listed
- [ ] If START FRESH: salvageable elements identified
- [ ] Re-evaluation checkpoint defined (if applicable)

**Prompt Sample:**

> Based on all evidence gathered, record a formal go/no-go decision in `docs/DECISION.md` with verdict, reasoning, and conditions.

---

## Step 21 — Quick Start Guide

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** No
**Adaptation Steps:** Replace commands with project-appropriate equivalents (npm install/pip install/go install, dev server, etc.).
**Actor:** Agent | **Effort:** M
**Prerequisites:** Step 7 complete (architecture doc needed for accurate commands)
**Skip Condition:** Never — quick start validates the documented workflow is executable.
**Parallelizable with:** Step 22 (developer guide can be created concurrently via background subagent)
**Iteration Pattern:** N/A

**Description:** Write a practical end-to-end walkthrough using the project's own commands/tools.
**Purpose:** Validate documented workflow is executable; serve as onboarding guide.
**Goals:**
- Step-by-step from setup to first meaningful result.
- Quick-reference summary table.
**Requirements:**
- All source files read for accurate documentation.
- A concrete example use case.
**Constraints/Boundaries:**
- User guide, not developer guide.
- Must reflect actual behavior, not aspirational.
**Input:** All source files, `docs/ARCHITECTURE.md`.
**Output:** `docs/QUICK_START.md`.
**Decisions:**
- Example use case choice.
- Which optional steps to include.
**Artifacts:** `docs/QUICK_START.md`.

**Interview Questions:**
1. What example use case should the quick start demonstrate?
2. Which steps are essential vs. optional?
3. Should the guide include troubleshooting tips?

**Sub-Steps:**
- [Decision] Agent presents example use case → human approves
- [Validation] Agent verifies commands/flags match actual implementation
- [Self-review] Agent re-reads guide for clarity
- [Self-verify] Agent checks every command against source
- [Approval] Human confirms guide is accurate and usable

**Output Hand-off:** Quick start → Step 22 (dev guide) cross-references it.

**Prompt Sample:**

> Create `docs/QUICK_START.md` to [demonstrate the project's core workflow with a concrete example].

---

## Step 22 — Developer Setup Guide

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** No
**Adaptation Steps:** Replace dev workflow per project type (hot reload for web, linking for CLIs, cross-compilation for Go).
**Actor:** Agent | **Effort:** M
**Prerequisites:** Steps 7 complete (Step 21 not strictly required — can run in parallel)
**Skip Condition:** Never — developer onboarding is essential for maintainability.
**Parallelizable with:** Step 21 (quick start guide can be created concurrently via background subagent)
**Iteration Pattern:** N/A

**Description:** Create a guide for developers to clone, set up, run, test, debug, and contribute.
**Purpose:** Onboarding path for project development (vs. usage, covered by Quick Start).
**Goals:**
- Clone and setup instructions.
- How to run each test layer.
- How to debug and add new components.
- Contribution conventions.
**Requirements:**
- `docs/ARCHITECTURE.md`, test docs, agent instructions.
**Constraints/Boundaries:**
- Developer guide, not user guide.
- Cross-reference Quick Start and Architecture, don't duplicate.
**Input:** Architecture, test docs, existing instructions.
**Output:** `docs/DEVELOPER_GUIDE.md`.
**Decisions:**
- Whether to include IDE setup recommendations.
- Whether to include "first contribution" walkthrough.
**Artifacts:** `docs/DEVELOPER_GUIDE.md`.

**Interview Questions:**
1. What IDE(s) should the guide recommend?
2. Should it include a "first contribution" walkthrough?
3. Are there any dev environment quirks to document?

**Sub-Steps:**
- [Self-review] Agent re-reads guide for completeness
- [Self-verify] Agent verifies instructions are executable
- [Approval] Human confirms guide is accurate

**Output Hand-off:** Dev guide → Step 24 (ADRs) may reference it; future contributors use it.

**Prompt Sample:**

> Create `docs/DEVELOPER_GUIDE.md` covering: setup, running tests, debugging, adding components, contribution conventions.

---

## Step 23 — Policies Consolidation

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Agent | **Effort:** L
**Prerequisites:** Steps 7, 10–11, 14 complete
**Skip Condition:** Never — policies make implicit rules explicit and navigable.
**Iteration Pattern:** One pass per policy domain, with checkpoints after each domain
**Subagent Strategy:** For large codebases, split into two background subagent passes: (1) extract all policy statements with source citations, (2) classify enforcement status (Enforced/Conventional/Gap). This avoids output truncation on large policy sets.

**Description:** Search entire codebase for all policy-related content and consolidate into a single document with enforcement status.
**Purpose:** Make implicit policies explicit and navigable; highlight enforcement gaps.
**Goals:**
- All policies from all sources consolidated.
- Each tagged: Enforced / Conventional / Gap.
- Each has source citation.
- Policy Gap Summary cross-referenced to TODOs.
**Requirements:**
- All source files.
- `docs/ROADMAP.md` and `docs/TODOs.md` for gap cross-referencing.
**Constraints/Boundaries:**
- Extract, don't invent — only what exists or is explicitly planned.
- "Enforced" means there's a mechanism, not just a doc statement.
**Input:** All source files, roadmap, TODOs.
**Output:** `docs/POLICIES.md`.
**Decisions:**
- Policy domain organization.
- Whether to include planned policies from roadmap.
**Artifacts:** `docs/POLICIES.md`.

**Interview Questions:**
1. What policy domains should be covered? (security, privacy, data integrity, editorial, performance, ...)
2. Should planned/not-yet-implemented policies be included? (tagged as Gap?)
3. Are there any policies you want to explicitly add that aren't in the codebase?

**Sub-Steps:**
- [Iteration] Agent processes policy domains one by one, with checkpoints
- [Decision] Agent presents enforcement status for ambiguous policies → human decides
- [Validation] Agent verifies all sources are covered
- [Self-critique] Agent reviews: did I miss any policies? Any domain under-covered?
- [Self-review] Agent re-reads policies doc for consistency
- [Self-verify] Agent verifies all citations resolve
- [Approval] Human confirms policies are complete

**Output Hand-off:** Policies → Step 24 (ADRs) may reference them; Step 28 (migration) checks compliance.

**Prompt Sample:**

> Create `docs/POLICIES.md` and add all directly or indirectly available policies with enforcement status and source citations.

---

## Step 24 — Architecture Decision Records (ADRs)

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 4, 5, 20 complete (key decisions must exist before recording them)
**Skip Condition:** Never — ADRs capture why decisions were made, preventing future drift.
**Iteration Pattern:** One ADR at a time, with review after each

**Description:** Establish an ADR system with template and initial records capturing key decisions from this workflow.
**Purpose:** Create a durable mechanism for recording *why* decisions were made.
**Goals:**
- ADR template with standard fields.
- Initial ADRs for key workflow decisions.
- ADR convention documented.
**Requirements:**
- Key decisions from Steps 1–20 to record.
- Understanding of ADR format.
**Constraints/Boundaries:**
- ADRs are immutable once Accepted — supersede with new ADR.
- Keep concise — detail lives in referenced artifacts.
**Input:** All prior decisions.
**Output:** `docs/adr/` directory with template and initial ADRs.
**Decisions:**
- ADR numbering scheme.
- Status values.
- Which decisions warrant ADRs.
**Artifacts:** `docs/adr/TEMPLATE.md`, 4–6 initial ADRs.

**Interview Questions:**
1. Which decisions from this workflow should be recorded as ADRs?
2. What ADR format do you prefer? (Nygard, MADR, custom?)
3. Where should ADRs live? (`docs/adr/`, `docs/decisions/`, other?)

**Sub-Steps:**
- [Iteration] Agent creates ADRs one by one, with review after each
- [Decision] Agent presents which decisions warrant ADRs → human approves
- [Self-review] Agent re-reads each ADR for clarity
- [Self-verify] Agent verifies ADRs match actual decisions made
- [Approval] Human confirms ADRs are accurate

**Output Hand-off:** ADRs → Future decisions follow the ADR convention established here.

**Phase Gate (Phase 7 — Operationalize):**
- [ ] Quick start guide created and verified against actual implementation
- [ ] Developer setup guide created with test/debug/contribution instructions
- [ ] All policies consolidated with enforcement status and citations
- [ ] ADR system established with template and initial records
- [ ] ADR convention documented for future use

**Prompt Sample:**

> Establish an ADR system. Create template and initial ADRs for key decisions: [list of decisions]. Document the ADR convention.

---

## Step 25 — Repository Ownership Task List

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Step 20 complete (go/no-go decision must be PROCEED or PROCEED WITH CONDITIONS)
**Skip Condition:** Step 20 verdict is START FRESH (no upstream to detach from).
**Iteration Pattern:** N/A

**Description:** Create task list for transforming local working copy into independently-owned GitHub repository.
**Purpose:** Concrete git-level steps to detach from upstream and establish ownership.
**Goals:**
- Decision: history-preserving mirror vs. fresh init.
- GitHub repo creation (not Fork button).
- Remote repointing, attribution, metadata, push, verification.
**Requirements:**
- GitHub CLI or web UI.
- Git installed.
- New GitHub repo URL.
**Constraints/Boundaries:**
- Never use Fork button — permanently links upstream.
- Attribution must be committed.
**Input:** Local working copy, new GitHub account/repo.
**Output:** Task list (12 items).
**Decisions:**
- History model: preserve vs. fresh.
- Whether to keep upstream remote for monitoring.
**Artifacts:** In-chat task list. Optional: `docs/OWNERSHIP_TASKS.md`.

**Interview Questions:**
1. Should the repository preserve full git history from upstream, or start fresh?
2. What should the new GitHub repo URL be?
3. Should an `upstream` remote be kept for monitoring? (read-only, never for merging)
4. What should the default branch name be? (main, master, other?)

**Sub-Steps:**
- [Decision] Agent presents history model options → human chooses
- [Validation] Agent verifies repo is accessible and no fork banner appears
- [Self-review] Agent re-reads task list for completeness
- [Self-verify] Agent verifies no lingering upstream ties
- [Approval] Human confirms ownership is established

**Output Hand-off:** Owned repository → Steps 26, 27 operate on it.

**Prompt Sample:**

> Create a tasklist to create and own a local copy of a GitHub repository, if a fork or a clone is not enough.

---

## Step 26 — CI/CD Re-Establishment

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** No
**Adaptation Steps:** Replace CI pipeline per project type (lint+typecheck+test+build for web; lint+test+publish for CLI; goreleaser for Go).
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 6, 25 complete
**Skip Condition:** Never — CI is essential for ongoing quality.
**Iteration Pattern:** N/A

**Description:** Set up CI/CD for the new repository — automated tests, validation, branch protection, optional publishing.
**Purpose:** Replace stripped CI with a working pipeline for the new repo identity.
**Goals:**
- GitHub Actions workflow configured.
- All test layers runnable in CI.
- Branch protection with required status checks.
- Build/validation step.
**Requirements:**
- GitHub repo created (Step 25).
- CI config updated and tested locally (Step 6).
- API keys as GitHub secrets for behavioral tests.
**Constraints/Boundaries:**
- Structural tests on every push; behavioral on PRs or scheduled (cost).
- Never hardcode secrets.
- Publishing should be manual-triggered.
**Input:** Updated CI config, GitHub repo with admin access.
**Output:** Working CI pipeline with green builds.
**Decisions:**
- Which test layers run on push vs. PR vs. scheduled.
- Whether to enable required checks immediately.
- Whether to set up release-based publishing.
**Artifacts:** `.github/workflows/ci.yml` (or equivalent), branch protection rules.

**Interview Questions:**
1. Which tests should run on every push vs. PR vs. scheduled?
2. Should branch protection require all status checks, or just a subset?
3. Should the pipeline include automated publishing on release?
4. What secrets need to be configured? (API keys, deploy tokens, etc.)

**Sub-Steps:**
- [Decision] Agent presents CI pipeline plan → human approves
- [Validation] Agent verifies pipeline produces green build
- [Self-review] Agent re-reads workflow file for correctness
- [Self-verify] Agent confirms secrets are not hardcoded
- [Approval] Human confirms CI is working

**Output Hand-off:** Working CI → Step 27 (upstream tracking) can monitor upstream CI too.

**Prompt Sample:**

> Set up CI/CD for the new repository. Configure GitHub Actions, branch protection, and secrets. Verify green build on default branch.

---

## Step 27 — Upstream Tracking Strategy

**Mandatory:** No (only if upstream is active) | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** S
**Prerequisites:** Steps 7, 25 complete
**Skip Condition:** Upstream repository is inactive/abandoned, or Step 20 verdict was START FRESH.
**Parallelizable with:** Step 26 (CI/CD and upstream tracking are independent)
**Iteration Pattern:** N/A

**Description:** Define and document a strategy for monitoring upstream and selectively incorporating changes.
**Purpose:** Benefit from upstream improvements without re-coupling.
**Goals:**
- Document upstream repo URL and release cadence.
- Define monitoring routine.
- Define cherry-pick/porting workflow.
- Define what to port vs. skip.
**Requirements:**
- Upstream repo URL.
- Understanding of shared vs. divergent components.
**Constraints/Boundaries:**
- Never merge upstream directly — always cherry-pick or manually port.
- Ported changes must pass tests and be scored.
**Input:** Upstream URL, `docs/ARCHITECTURE.md`.
**Output:** `docs/UPSTREAM_TRACKING.md`.
**Decisions:**
- Monitoring frequency.
- Whether to maintain read-only `upstream` remote.
- Which components track upstream vs. diverge.
**Artifacts:** `docs/UPSTREAM_TRACKING.md`.

**Interview Questions:**
1. Is the upstream repository still actively maintained?
2. How often do you want to review upstream changes? (monthly, per-release, on-demand?)
3. Which components should stay aligned with upstream vs. diverge?
4. Should we maintain a read-only `upstream` remote for diffing?

**Sub-Steps:**
- [Decision] Agent presents tracking strategy → human approves
- [Self-review] Agent re-reads strategy doc for completeness
- [Approval] Human confirms strategy is workable

**Output Hand-off:** Tracking strategy → Step 28 (migration) references it for long-term maintenance.

**Prompt Sample:**

> Define a strategy for monitoring the original upstream repository and selectively incorporating fixes without re-coupling. Create `docs/UPSTREAM_TRACKING.md`.

---

## Step 28 — Migration Strategy

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** M
**Prerequisites:** Steps 10–11, 14, 20, 23 complete
**Skip Condition:** Never — migration strategy ensures safe transition from current to target state.
**Iteration Pattern:** N/A

**Description:** Define the path from current state to target state — intermediate milestones, backward compatibility, risk mitigation.
**Purpose:** Plan the migration path so existing functionality is not broken during transition.
**Goals:**
- Migration phases mapped to roadmap sections and TODO priorities.
- Backward compatibility policy.
- Intermediate milestones.
- Risk assessment per phase.
- Versioning strategy.
**Requirements:**
- `docs/ROADMAP.md`, `docs/TODOs.md`, `docs/DECISION.md`, `docs/POLICIES.md`.
**Constraints/Boundaries:**
- Existing user data must not be broken by changes.
- P0 items must be resolved before scope-widening.
- Each phase should be independently shippable.
**Input:** Roadmap, TODOs, decision, policies, architecture.
**Output:** `docs/MIGRATION_STRATEGY.md`, `docs/CHANGELOG.md` (initialized).
**Decisions:**
- Phase ordering.
- Compatibility policy and deprecation timeline.
- Whether to maintain a changelog.
**Relative Time Ordering:** Even though exact timelines can't be predicted, assign
relative ordering to each phase: "immediate" (Phase 0), "next sprint" (Phase 1),
"next quarter" (Phases 2-3), "later" (Phases 4-5). This helps with planning without
committing to specific dates.
**Artifacts:** `docs/MIGRATION_STRATEGY.md`, `docs/CHANGELOG.md`.

**Interview Questions:**
1. What phase ordering makes sense? (P0 fixes → security → privacy → features → performance?)
2. What backward compatibility guarantees are needed? (semantic versioning? deprecation periods?)
3. Should each phase produce a tagged release?
4. What is the risk tolerance for breaking changes in early phases?

**Sub-Steps:**
- [Decision] Agent presents phase plan → human approves
- [Validation] Agent verifies each phase is independently shippable
- [Self-critique] Agent reviews: risk blind spots? What could go wrong?
- [Self-review] Agent re-reads strategy for completeness
- [Approval] Human confirms migration strategy is workable

**Output Hand-off:** Migration strategy → Step 29 (retrospective). Development
work follows the phased plan. **CHANGELOG.md must be created in this step** —
it is not optional. Initialize it with the current evaluation state and all
decisions made during the workflow.

**Phase Gate (Phase 8 — Own & Plan):**
- [ ] Repository independently owned on GitHub (no fork banner)
- [ ] CI/CD pipeline running with green builds
- [ ] Branch protection enabled
- [ ] Upstream tracking strategy defined (or skipped with reason)
- [ ] Migration strategy with phased plan documented
- [ ] Backward compatibility policy defined
- [ ] Changelog initialized with current state

**Prompt Sample:**

> Define a migration strategy from current state to target state. Create `docs/MIGRATION_STRATEGY.md` covering: phased plan, backward compatibility, milestones, risk assessment, versioning. Initialize `docs/CHANGELOG.md`.

---

## Step 29 — Session Retrospective

**Mandatory:** Yes | **Project-specific:** No | **Project-type agnostic:** Yes
**Adaptation Steps:** None.
**Actor:** Collaborative | **Effort:** S
**Prerequisites:** Steps 1–28 complete (all 8 phase gates passed)
**Skip Condition:** Never — the retrospective improves future workflow runs.
**Iteration Pattern:** N/A

**Description:** Reflect on the workflow execution itself — what worked, what didn't, what to change. Track deviations from the workflow and recommend improvements.
**Purpose:** Improve the workflow for future runs by capturing lessons learned.
**Goals:**
- What worked well (keep doing)
- What didn't work (stop or change)
- What was missing (add to workflow)
- What was redundant (remove from workflow)
- Workflow deviations and gaps observed during this session
- Recommended changes to WORKFLOW_MAX_improved.md based on this run
- Estimated time per phase (for future planning)
**Requirements:**
- All 28 implementation steps completed
- Honest assessment of workflow execution
- Per-phase self-review records from each phase gate
**Constraints/Boundaries:**
- This is about the *workflow process*, not the *codebase being evaluated*
- Be honest — don't sugarcoat issues
- Actionable suggestions, not vague complaints
- Reference specific phase self-reviews where deviations were noted
**Input:** All workflow artifacts, WORKFLOW_STATE.md, per-phase self-review
records, session experience.
**Output:** `docs/RETROSPECTIVE.md`.
**Decisions:**
- Whether to update WORKFLOW_MAX_improved.md based on findings
**Artifacts:** `docs/RETROSPECTIVE.md`.

**Interview Questions:**
1. What parts of the workflow felt smooth and efficient?
2. What parts felt confusing, slow, or frustrating?
3. Were there any steps that felt unnecessary or redundant?
4. Was there anything missing that would have helped?
5. Should the recommended workflow changes be applied to
   WORKFLOW_MAX_improved.md now, or documented for future consideration?

**Sub-Steps:**
- [Self-critique] Agent reviews: where did I struggle? Where did the human
  seem confused? Did I skip interviews? Did I use the wrong subagent profile?
  Did I miss any artifacts?
- [Self-review] Agent re-reads retrospective for actionability
- [Approval] Human confirms retrospective is accurate and actionable

**Output Hand-off:** Retrospective → Future workflow runs incorporate lessons
learned. The todo list is only marked complete after this step is done.

**Prompt Sample:**

> Reflect on this workflow execution. What worked, what didn't, and what should be changed for future runs? Track deviations from the workflow and recommend improvements. Create `docs/RETROSPECTIVE.md`.

---

## Workflow Completion Checklist

After all 29 steps are complete, verify:

- [ ] All 8 phase gates passed (with per-phase self-review presented at each)
- [ ] `docs/WORKFLOW_STATE.md` shows all 29 steps complete
- [ ] All artifacts created and cross-referenced
- [ ] DECISION.md verdict is PROCEED or PROCEED WITH CONDITIONS
- [ ] MIGRATION_STRATEGY.md has phased plan with relative time ordering
- [ ] CHANGELOG.md initialized with current evaluation state
- [ ] CI/CD plan exists (even if not yet executed)
- [ ] Ownership task list exists (even if not yet executed)
- [ ] Translation/language policy decided in Step 4 (not deferred to Step 20)
- [ ] Retrospective captures lessons learned and workflow deviations
- [ ] Recommended workflow changes documented for future consideration
- [ ] The first line of new code has a known foundation and clear direction
