# promptlibrary-kit — User Requirements

**Status:** DRAFT. Candidate requirements, not yet confirmed by the owner. Each area is confirmed,
changed or dropped one at a time; until then nothing here overrides concept V4.

**Sources:** concept V4 (`2026-10-02`, the design source), concept V5 (`2026-10-14`, status only, no
design change), the plugin on `main` at 51fc2b13, and the unmerged branch
`fix/promptlibrary-kit-security-bundle` (head f064a851).

## How to read this

- **ID**: area prefix plus number. IDs stay stable once confirmed; a dropped requirement keeps its ID,
  marked dropped.
- **Requirement**: what a user (or the owner) must be able to rely on, stated as an outcome, not as an
  implementation.
- **Source**: `V4 §<section>` for the concept, `code` for behavior that exists in the plugin but was never
  written down as a requirement, `branch` for behavior only on the security-bundle branch.
- **State**: `met` (on `main`), `partial`, `not met`, `branch` (only on the unmerged branch), `deferred`
  (planned later, V4 "Deferred").
- **Confirm**: `?` until the owner decides; then `yes`, `changed` or `dropped`.

A requirement says *what* must hold. How the code achieves it (for example a validator subcommand) is
listed under "Current mechanism" only so the requirement can be checked against the code; the mechanism
can change without changing the requirement.

**Format (decided 2026-11-16):** each requirement is a user story ("As a ..., I can ..., so that ...")
followed by "What you'll notice", the visible behavior and its trade-offs for a person using the plugin.
Requirements still in the older table form below have not been reviewed yet; each is rewritten when it is
reviewed.

## 1. Purpose and users (PUR)

### PUR-1: Save a repeatable instruction instead of writing a skill

*As a developer who keeps giving Claude the same instruction, I can save it once in my project and run it
by name later, without writing a skill.*

**What you'll notice:** you manage one named prompt per instruction, not a skill folder. A saved prompt
never runs by itself; you name it to run it, or look it up first. If the instruction really needs a
script, tool limits or automatic triggering, you are told to make a skill instead and nothing is saved.
Limits that follow from this (run by name only, plain text, 50 lines, this project only) are separate
requirements: EXE-1, CAT-3, DEF-1.

Source: V4 §Purpose. State: met. Confirmed: yes (2026-11-16).

### PUR-2: Review and approve every prompt before it can run

*As a developer, before a saved prompt can run, I see a review of it with suggested improvements and
approve its exact final text, so that whatever I run later is text I have checked.*

**What you'll notice:** saving takes a few minutes and several questions; a rough prompt cannot be run
straight away. The reviewer only advises and every finding can be ignored: what lets the prompt run is
your approval of the exact text. Text from a web page or a session gets an extra check (hidden
instructions, secrets, provenance, scope). Changing even one word later voids the approval: you approve
again, and an active prompt gets a new version. This applies to every origin, including text you typed
yourself (a lighter path for your own text was considered and declined).

Source: V4 §Purpose, §Verification and Optimization. State: met. Confirmed: yes (2026-11-16).

### PUR-3: Run saved prompts by name, with approvals I can choose to remember

*As a developer, I can run one or more saved prompts by name in my Claude session after seeing their full
text and approving them; I can choose to have an approval remembered, so that an unchanged prompt I have
already approved runs again without asking, until it expires.*

**What you'll notice:**

- **First run, or any run after the text changed:** Claude shows each selected prompt's full text,
  version and verification state, then asks once: *Run once*, *Run and remember (N days)*, or *Cancel*.
- **Remembered run:** if every named prompt has a valid remembered approval, there is no question. Before
  each prompt Claude prints one line: name, version, approved on `<date>`, expires on `<date>`. If only
  some are remembered, only the others are previewed, and one question covers the whole set.
- **When an approval ends:** on its expiry date; when the prompt's text changes; when the prompt is
  deactivated or replaced by a new version; or when you run `/prompt-execution forget <slug>` (or
  `forget --all`), which asks for confirmation first.
- **Unchanged by remembering:** the prompt runs with your session's existing permissions only; CLAUDE.md,
  project rules and permission prompts still apply; a file edited after approval is refused; a failure
  stops the rest of the run and reports what ran; it runs only in an interactive Claude session, never
  headless, on a schedule or in Codex; output is not written back to the prompt.
- **Trade-off you accepted:** a remembered prompt can run without you re-reading it for up to the
  configured lifetime.

**Settings (decided 2026-11-16, per `.claude/rules/ask-before-config-decisions.md`):**

| Item | Decision |
|---|---|
| Setting | Maximum approval lifetime in days: only `30`, `60` or `90`; default `30`. Any other value is rejected, the default is used, and the fallback is reported. |
| Storage | Both: the default in the plugin's tracked `promptlibrary-kit.settings.json`; a per-project override in the untracked `.claude/promptlibrary-kit.local.json`. A tracked copy may only shorten the lifetime, never lengthen it (same trust-boundary pattern as `git-kit`). |
| Format | JSON, the same files as `catalog_root`. |
| Approval store | An untracked project file (for example `.claude/promptlibrary-kit.approvals.local.json`): one entry per prompt with `internal_id`, text hash, executor (`claude`) and approval date. Per project and per machine, never committed; ignored entirely, and reported, if git tracks it. |
| Opt-in | Per approval: nothing is remembered unless you pick *Run and remember*. |

**Changes to earlier decisions:** this replaces V4 Closed Item 2 and V4 §Execution 4 ("an approval of an
earlier preview or an earlier session never substitutes") and narrows V4 §Execution 3 (full-text preview
before every run) to the first run and any run after a text change. EXE-3 and EXE-4 below are rewritten to
match when they are reviewed. Remembering approvals makes `prompt-execution` write a file for the first
time, which is a new security gate: it needs a `security-reviewer` pass before its first commit.

Source: V4 §Purpose, §Execution; owner decision 2026-11-16. State: **not met** (run-once approval only).
Confirmed: yes (2026-11-16).

### PUR-4: Small footprint, with one guard hook that protects the catalog

*As a developer, installing the plugin adds no servers, background activity or network connections of its
own (only a web page I ask to import is fetched, behind a permission prompt), and only one guard hook, so that nothing happens in my sessions unless I invoke a skill, and catalog files
cannot be changed except through the plugin.*

**What you'll notice:** no slowdown, extra messages, accounts or API keys; only `uv` on your PATH is
needed. Nothing is automatic: there are no "save this as a prompt?" suggestions, no syncing, no background
cleanup (approval expiry is checked when you run a prompt). The one hook denies any `Write`, `Edit` or
shell command that changes catalog files or the approvals file other than through the plugin's validator,
including an edit you ask Claude to make by hand. To change a prompt you go through `/prompt-library`.

**What the hook does not do:** it cannot see whether you answered "Approve" in a question. The steps that
ask you first (filing, verifying, activating, running) are still enforced by the skills' instructions;
SEC-3 records that limit. An approval-marker check was considered and declined: it can be satisfied by
anything that can run a command, so it is a guardrail against accidents, not a security boundary.

**Constraints on the hook:** it is a new security gate (a `security-reviewer` pass before its first
commit); if it is Python-backed, it uses the `uv` -> `python3` -> `python` fallback with graceful
degradation (`.claude/rules/require-python-hook-interpreter-fallback.md`); its failure mode (blocked or
let through with a warning when the hook itself errors) must be stated in the README.

**Changes to earlier decisions:** replaces V4 §Purpose "no hooks". The prohibition on an MCP server,
background process and connector stands.

Source: V4 §Purpose; owner decision 2026-11-16. State: **not met** (no hook exists). Confirmed: yes
(2026-11-16).

### PUR-6: Set the plugin up after installing it

*As a developer who just installed the plugin, I can run one setup skill that checks what the plugin
needs, creates my catalog and writes my local settings, and I can re-run it later as a health check.*

**What you'll notice:** `/prompt-library-setup` (user-invoked only) walks through four steps, each shown
and confirmed before it changes anything:

1. **Check prerequisites:** `uv` works; you are in a git repository (warns if not); `session-kit` is present
   (optional, needed only to import a past session by ID).
2. **Create the catalog** at the resolved catalog root, showing the path first.
3. **Write local settings:** `.claude/promptlibrary-kit.local.json` with your `catalog_root` and approval
   lifetime (30/60/90 days), and make sure git ignores it and the approvals file.
4. **Report status** (also the whole run when everything is already set up; changes nothing): catalog
   valid, where each setting came from, approvals in force and when they expire, guard hook active.

Setup becomes the main way to start. The first `/prompt-library add` in a project without a catalog
still offers to create one (V4 behavior, kept as a fallback).

Source: owner decision 2026-11-16. State: **not met** (no setup skill exists). Confirmed: yes
(2026-11-16). Name checked against `plugin-rulebook/references/naming-conventions.md` (skill: noun
phrase).

### PUR-5: Local library now; Notion becomes the main library later

*As a developer, I can use the whole prompt library in my own project with no account, credentials or
external service today; once Notion support arrives, Notion becomes the main library for its configured
scope and my project keeps a checked-in copy, so that prompts can later be shared beyond one repository.*

**What you'll notice now:** the library is a folder of text files in your repository; no login, API key or
service, and it works offline. Committed prompts are shared with teammates through git, with history, and
are readable by anyone who can read the repository. There is no library outside git and no way to share a
prompt with another repository except copying it.

**What you'll notice once Notion support arrives (DEF-3):** for prompts in Notion's configured scope,
Notion is the source of truth and the project's catalog becomes a checked-in snapshot of it. Reading and
running prompts from that snapshot still works offline; adding or changing such a prompt needs Notion
access (through `workmanagement-kit`). A sync you start yourself shows the file changes for you to apply;
it never writes local changes back to Notion and never silently overwrites a local edit.

Source: V4 §Authority and Trust Model, §Wave 1; owner decision 2026-11-16 (confirms V4's Wave 1 direction:
Notion authoritative, not an optional add-on). State: met now; Notion part deferred and blocked (#267).
Confirmed: yes (2026-11-16).

## 2. Catalog and records (CAT)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| CAT-1 | The catalog lives in the using project, not in the plugin; the plugin ships no prompt data. | V4 §Catalog Location | met | ? |
| CAT-2 | Each prompt record carries the 16 fields of V4's record model (name, area, slug, internal_id, version, short_description, status, previous_id, origin, source_ref, prerequisites, boundaries, references, attachments, verification, prompt_text). | V4 §Record Model | met | ? |
| CAT-3 | A prompt's text is at most 50 nonblank lines. | V4 §Record Model | met | ? |
| CAT-4 | Slugs are `<area>__<name>` in kebab-case, immutable, never reused; display names never build a path. | V4 §Slug and path rules | met | ? |
| CAT-5 | Retrieval and execution use only a complete, validated catalog; a missing, inconsistent or partially written catalog is "unavailable", never guessed from stray files. | V4 §Layout, §Interrupted updates | met | ? |
| CAT-6 | An interrupted catalog change leaves the catalog unusable for retrieval and execution, and management refuses new changes until the user restores it; nothing is repaired silently. | V4 §Interrupted updates | met (plus rollback, see CODE-6) | ? |
| CAT-7 | A stored prompt can never be loaded by Claude Code as project instructions (the catalog may not sit inside `.git`, `.github` or Claude Code's configuration folders). | code (`FORBIDDEN_ROOTS`) | met | ? |

## 3. Intake (INT)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| INT-1 | A prompt can be added from five origins: written by the user, by Claude or by Codex; taken from a Claude Code session; or imported from the web. | V4 §Intake Sources | met | ? |
| INT-2 | Every intake produces a draft, never an active prompt. | V4 §Intake Sources | met | ? |
| INT-3 | The intake path, not the user, sets `origin` for fetched (`web`) and session (`session`) text, so the import review cannot be skipped by a label. | V4 §Authority and Trust Model | met | ? |
| INT-4 | Session text can be selected or pasted in-session; reading a past session by ID works only when `session-kit` is installed, and the plugin never reads transcript files by itself. | V4 §Intake Sources | met | ? |
| INT-5 | Before a prompt is created, the user is asked whether it should be a skill instead, and offered to revise a near-duplicate; both are recommendations, the user decides. | V4 §Intake Triage | met | ? |
| INT-6 | Only the user can start an add, revise, activate or deactivate (the management skill cannot be started by the model). | V4 §Components; code (`disable-model-invocation`) | met | ? |

## 4. Screening for secrets and personal data (SCR)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| SCR-1 | Secrets in `session`, `web`, `claude` and `codex` text block the draft; the user sees where it matched and removes it. Nothing is auto-redacted and the secret is never echoed. | V4 §Import review; code (extended to `claude`, `codex`) | met | ? |
| SCR-2 | For `user` text, a match is a warning the user may accept. | code | met | ? |
| SCR-3 | The screen is re-applied at every later filing, verification and activation step, so a secret added later is still blocked. | code | met | ? |
| SCR-4 | Screened shapes include cloud and API keys, tokens, bearer and authorization headers, PEM blocks, home-directory paths, and credentials embedded in URLs. | V4 §Import review; code (URL credentials, shared `plib-token-shapes.json`) | met | ? |
| SCR-5 | Email addresses are screened (except git SSH remotes `git@host:path` and reserved example domains). | branch (ad706e64, 7df79b46) | branch | ? |
| SCR-6 | Phone numbers and other personal data are left to the reviewer's findings, not blocked by the screen. | code | met | ? |

## 5. Review and optimization (REV)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| REV-1 | Every prompt gets a quality review (clarity, boundaries and prerequisites, the line limit, redundancy, an unambiguous success condition, executor-neutral wording) before it can be activated. | V4 §Quality review | met | ? |
| REV-2 | `session` and `web` prompts also get an import review: injection-like content, secrets and personal data, provenance, scope fit. | V4 §Import review | met | ? |
| REV-3 | The reviewer proposes an optimized rewrite as a diff; nothing is rewritten without the user's approval. An initial draft is rewritten in place; an active or inactive prompt gets a new version. | V4 §Optimization | met | ? |
| REV-4 | The reviewer can only report and propose; it cannot approve, activate, edit or write anything. | V4 §Optimization, §Components | met | ? |
| REV-5 | The reviewer treats the prompt as data: it never follows instructions in it, never quotes secrets, and cites hostile text by line only. | V4 §Authority and Trust Model; code (agent) | met | ? |
| REV-6 | The reviewer reviews exactly the one record the user is filing, and cannot be pointed at, or tricked into reading, any other file (outside the catalog, an unlisted file, or a file reached through a link). | code + branch | partial (see note) | ? |

**Note on REV-6.** This is the requirement `review-path` exists for. Current mechanisms:

- On `main`: the skill passes the reviewer an absolute file path; the agent reads only that file.
  Nothing stops a path outside the catalog or through a link.
- On the branch: the validator's `review-path` checks the path (inside the catalog, a listed record, no
  link or junction on the way), and the agent re-checks it as text before reading. Step 4.5's review found
  a remaining gap: a link swapped in between the check and the agent's read escapes it.
- Proposed alternative: the skill passes the record's text and metadata (from `show --history`) to the
  reviewer inline, and the reviewer reads no file at all. REV-6 then holds without `review-path`,
  because there is no file read left to steer.

Whichever mechanism is chosen must satisfy REV-1 to REV-6 together; the choice is an implementation
decision made against this requirement, not a change to it.

## 6. Verification and lifecycle (LIF)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| LIF-1 | No prompt becomes active without a quality approval bound to its exact text; `session` and `web` prompts also need an import approval bound to their exact text. | V4 §Verification record | met | ? |
| LIF-2 | Changing a prompt's text invalidates earlier approvals; an approval never silently carries over. Line endings do not affect this (CRLF and LF agree). | V4 §Verification record | met | ? |
| LIF-3 | Lifecycle: draft -> active <-> inactive; revising creates a new draft version; finalizing makes the old version historical; a historical version never becomes active again. | V4 §Lifecycle | met | ? |
| LIF-4 | A revision never retires the active prompt until the new version is finalized. | V4 §Lifecycle, §Acceptance | met | ? |
| LIF-5 | At most one active version per prompt. | V4 §Lifecycle | met | ? |
| LIF-6 | Every catalog change is shown to the user and approved first. | V4 §Lifecycle | met (by skill text, see SEC-3) | ? |
| LIF-7 | An approval applies only to the text the user was shown: if the file changes after the user saw it, the change is refused. | code (`--expect-sha256`) | met | ? |
| LIF-8 | A draft left by an interrupted add or revise can be resumed from where it stopped, without repeating approvals already bound to its current text. | code | met | ? |

## 7. Retrieval (RET)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| RET-1 | The user can find, list and show a stored prompt and its version history. | V4 §Scope | met | ? |
| RET-2 | Retrieval is read-only and never runs a prompt. | V4 §Components | met | ? |
| RET-3 | Retrieval starts only on a clear request to find or show a stored prompt. | V4 §Components | met | ? |
| RET-4 | Invisible or look-alike characters in a prompt are listed by position whenever its text is shown. | code (`hidden_characters`) | met | ? |

## 8. Execution (EXE)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| EXE-1 | Only the user can start a run; a mention of a prompt, or text inside one, can never start it. | V4 §Execution 1 | met | ? |
| EXE-2 | Only active prompts whose text still matches their approvals can run; a mismatch is refused and reported, never run anyway. | V4 §Execution 2 | met | ? |
| EXE-3 | Before a run, the user sees each selected prompt's full text, name, version, origin and verification state. | V4 §Execution 3 | met | ? |
| EXE-4 | One approval covers exactly the shown set, order and executor; any change needs a fresh preview and approval; an earlier approval never substitutes. | V4 §Execution 4 | met | ? |
| EXE-5 | Prompts run one after another; a failure or interruption stops the run and reports what ran, what was in flight and what did not start. | V4 §Execution 5 | met | ? |
| EXE-6 | An approved prompt runs with the session's existing permissions only: it cannot widen tools, change the approval flow, load other prompts or edit the catalog; its output is not written back. | V4 §Execution 6 | met | ? |
| EXE-7 | Execution is in Claude only. | V4 §Execution | met | ? |

## 9. Trust and safety (SEC)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| SEC-1 | Prompt text is data everywhere except an approved run, including its metadata, links and examples. | V4 §Authority and Trust Model | met | ? |
| SEC-2 | Imported text (web pages, sessions) is untrusted: its instructions are never followed, at intake, review or retrieval. | V4 §Authority, §Intake Sources | met | ? |
| SEC-3 | Approval steps are enforced by the skills' instructions; the validator checks hashes and validity but cannot see whether the user was asked. This limit is documented. | code (README Safety design) | met (documented limit) | ? |
| SEC-4 | `origin` is a claim, not an attestation; a hand-edited `origin` is outside the guarantees and documented as such. | V4 §Authority | met | ? |
| SEC-5 | No file write or page fetch by the management skill happens without a normal permission prompt. | code (no Read/Write/WebFetch grants) | met | ? |
| SEC-6 | Each new security gate gets a `security-reviewer` pass before its first commit. | V4 §Plugin Conventions | ? (V5 H7: unverified for the original gates) | ? |

## 10. Configuration and paths (CFG)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| CFG-1 | One setting: the catalog root path, default `.claude/prompts/`, overridable per project in an untracked local file. | V4 §Configuration | met | ? |
| CFG-2 | A tracked override is ignored and reported (so a repository cannot redirect the catalog). | V4 §Path trust boundary | met | ? |
| CFG-3 | The catalog root can never resolve outside the project root, whatever the path form (`..`, absolute, links, junctions, case, drive letters, UNC, 8.3 names). | V4 §Path trust boundary | met | ? |
| CFG-4 | An invalid override falls back to the default and is reported. | V4 §Path trust boundary | met | ? |
| CFG-5 | The validator runs isolated from the project's own Python environment and settings. | code (`uv run --isolated`) | met | ? |

## 11. Platform and quality (QA)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| QA-1 | Behaves the same on Linux, macOS and Windows 11, verified by tests on each. | V4 §Acceptance | partial (Windows local, Linux CI; macOS never run) | ? |
| QA-2 | The plugin has been run live from an installed session, end to end. | V5 H1 | partial (`--plugin-dir` runs 2026-10-14; no marketplace install) | ? |
| QA-3 | `prompt-reviewer` triggers as intended. | V5 H2 | not met (trigger-test tool crashes, #460) | ? |
| QA-4 | Python, standard library only; scripts use the `plib`/`promptlib` prefix. | V4 §Plugin Conventions | met | ? |

## 12. Deferred (planned later, must stay possible) (DEF)

| ID | Requirement | Source | State | Confirm |
|---|---|---|---|---|
| DEF-1 | General (cross-repository) prompts, as a second catalog with `scope: general`, without changing the record format or hashes. | V4 §Deferred, §Extension Seams | deferred | ? |
| DEF-2 | Codex execution, as a second executor needing its own approval. | V4 §Deferred, §Extension Seams | deferred | ? |
| DEF-3 | Notion as the authority for a configured scope, with a user-invoked `prompt-sync` that never silently overwrites tracked files. Blocked until `workmanagement-kit` publishes the four-part contract (#267). | V4 §Wave 1; V5 §3 | deferred, blocked | ? |
| DEF-4 | How several catalogs combine (precedence, slug conflicts) is deliberately not designed yet. | V4 §Extension Seams | deferred | ? |

## 13. Behavior in code that V4 never stated (CODE)

Listed so each is either promoted to a requirement above or recorded as an implementation detail.

| ID | Behavior | Where | Proposed home |
|---|---|---|---|
| CODE-1 | Catalog may not sit in `.git`, `.github` or Claude Code config folders | validator `FORBIDDEN_ROOTS` | CAT-7 |
| CODE-2 | Hidden-character reporting in every text display and approval | validator, all three skills | RET-4 |
| CODE-3 | Secret screen also blocks `claude` and `codex` text, and re-screens at every later step | validator | SCR-1, SCR-3 |
| CODE-4 | Email screen with git-remote and example-domain exemptions | branch | SCR-5 |
| CODE-5 | `review-path` record-path gate for the reviewer | branch | REV-6 (mechanism) |
| CODE-6 | Atomic writes and rollback of a partly failed status move | validator | CAT-6 |
| CODE-7 | `discard-orphan` repair offer for an orphan from an interrupted draft | prompt-library step 1 | CAT-6 / LIF-8 |
| CODE-8 | `--expect-sha256` binding an approval to the shown text | validator | LIF-7 |
| CODE-9 | Input files read only from the catalog or the system temp directory | validator | SEC-5 |
| CODE-10 | Shared token-shape list with `analysis-kit` (`plib-token-shapes.json`) | scripts | SCR-4 |
