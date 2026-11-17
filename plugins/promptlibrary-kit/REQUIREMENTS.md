# promptlibrary-kit — User Requirements

**Status:** CONFIRMED (owner review 2026-11-16 to 2026-11-17). Where this document and concept V4 differ,
this document wins; V4 stays the design history.

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

**Amended 2026-11-17 (DEF-3):** one exception, once Notion support arrives: a change you accept in a Notion
sync becomes active without this review and approval; you still see its full text before its first run.

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
| Approval store | An untracked project file (for example `.claude/promptlibrary-kit.approvals.local.json`): one entry per prompt with `internal_id`, the approval fingerprint (text, attachments and origin, CAT-2, SEC-4), executor (`claude`), approval date and an expiry date fixed when approved (a later lifetime change never extends it). Per project and per machine, never committed; ignored entirely, and reported, if git tracks it. |
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
own (only a web page I ask to import is fetched, behind a permission prompt), and only one guard hook, so that nothing happens in my sessions unless I invoke a skill (apart from the RET-3 hint), and catalog files
cannot be changed except through the plugin.*

**What you'll notice:** no slowdown, accounts or API keys; only `uv` on your PATH is needed. Nothing is
automatic: there are no "save this as a prompt?" suggestions, no syncing, no background cleanup (approval
expiry is checked when you run a prompt). The one exception is RET-3: when a request fits a stored prompt,
Claude names it and its command once per session, which reads the catalog's labels; it never shows,
runs or changes anything. The one hook denies any `Write`, `Edit` or
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
background process and connector stands. Amended 2026-11-17 by the owner to allow the RET-3 hint as the
one exception to "nothing automatic".

Source: V4 §Purpose; owner decision 2026-11-16. State: **not met** (no hook exists). Confirmed: yes
(2026-11-16).

### PUR-6: Set the plugin up after installing it

*As a developer who just installed the plugin, I can run one setup skill that checks what the plugin
needs, creates my catalog and writes my local settings, and I can re-run it later as a health check.*

**What you'll notice:** `/prompt-library-setup` (user-invoked only) walks through five steps, each shown
and confirmed before it changes anything:

1. **Check prerequisites:** `uv` works; you are in a git repository (warns if not); `session-kit` is present
   (optional, needed only to import a past session by ID).
2. **Create the catalog** at the resolved catalog root, showing the path first.
3. **Write local settings:** `.claude/promptlibrary-kit.local.json` with your `catalog_root` and approval
   lifetime (30/60/90 days), and make sure git ignores it and the approvals file.
4. **Offer example prompts** shipped with the plugin; each one you pick is added as a draft (CAT-1).
5. **Report status** (also the whole run when everything is already set up; changes nothing): catalog
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

### CAT-1: My prompts live in my project (and later Notion); the plugin ships examples only

*As a developer, my own prompts are stored in my project (and in Notion once that is available) and
never inside the plugin, so that updating or removing the plugin can never change or delete them; the
plugin ships only example prompts that I can choose to add.*

**What you'll notice:** updating or uninstalling the plugin never touches your prompts. Your library
starts empty; `/prompt-library-setup` offers the shipped examples, and each one you accept is added as a
**draft** that goes through the same review and exact-text approval as any other prompt (PUR-2) before it
can run. An added example is marked `origin: example`, gets the quality review and your approval, and
sits under its own slug like any prompt; changing it later makes a new version in your catalog, never a
change to the plugin's copy. A prompt saved in one project does not appear in another until you add it
there (shared prompts come with Notion, PUR-5).

**Format change:** `example` is a new allowed `origin` value. Under V4's extension rules that is an
additive change with a `catalog_version` bump; catalogs at the current version stay valid.

**Changes to earlier decisions:** replaces V4 §Catalog Location "it ships no prompt data" with "ships no
user prompt data; ships example prompts only", and extends V4's five origins with `example`.

Source: V4 §Catalog Location; owner decision 2026-11-16. State: **partial** (catalog in project: met;
examples, `example` origin and setup offer: not met). Confirmed: yes (2026-11-16).

### CAT-2: What a saved prompt contains, including attached project files

*As a developer, each saved prompt carries a name, area, short description and optional prerequisites,
boundaries, references and attached project files that I write, plus origin, version, status and approval
details the plugin fills in, so that I can tell what a prompt is for and where it came from before I run
it, and its attached files are loaded with it when it runs.*

**What you'll notice:**

- You write: name and area (they form the slug, for example `review__missing-tests`), a short description
  of at most 3 sentences, the prompt text, and optionally prerequisites, boundaries, references and
  attachments. The plugin fills in internal ID, version, status, origin, source (for session and web
  text), approval fingerprints and the link to the previous version.
- Prerequisites and boundaries are shown to you, not enforced: Claude does not check them before a run.
- You cannot add fields of your own (tags, owner); unknown fields are rejected, and a new field needs a
  format version bump.
- **Attachments** are project files loaded into the session together with the prompt when it runs:
  - Only text files inside the project, under the same path rules as the catalog (never outside the
    project, never through a link, never in `.git` or Claude Code's configuration folders), with a size
    limit. No web addresses, so a run never fetches anything (PUR-4).
  - Their content is screened for secrets like the prompt text, shown in the review and in the
    first-run preview, and **fingerprinted together with the prompt text**: if an attached file changes,
    the prompt counts as changed. Its approvals, including remembered ones (PUR-3), are void and it goes
    back through review and approval as a new version (CAT-6, attachments amendment).
  - Trade-off you accepted: editing a file that several prompts attach (for example a style guide)
    re-triggers review and approval for each of them.

**Changes to earlier decisions:** V4 defined `attachments` as "supporting file or resource references"
with no behavior, and V4's verification hashes cover prompt text only (and V4 §Extension Seams relies on
that, so a prompt keeps its verification when moved to another catalog). Loading attachments at run time
and fingerprinting their content changes both: the approval now covers text plus attached content, and a
prompt moved to another project keeps its verification only if its attached files are identical there.
EXE-6 ("cannot load further prompts") is unaffected: attachments are files, not prompts. The fingerprint
change and the new file loading are security-relevant: `security-reviewer` before the first commit.

Source: V4 §Record Model; owner decisions 2026-11-16. State: **partial** (record model met; attachment
loading, path rules for attachments and attachment fingerprints not met; the field is stored but unused
today). Confirmed: yes (2026-11-16).

### CAT-3: Prompt text is at most 50 non-blank lines

*As a developer, a saved prompt's text is at most 50 non-blank lines, and I am asked to shorten anything
longer rather than having it cut, so that prompts stay focused and anything bigger becomes a skill.*

**What you'll notice:** pasting, importing or consolidating more than 50 non-blank lines gets a request to
condense it; nothing is truncated silently. The reviewer reports an over-length prompt as Major and the
checker refuses to file it. Attachments (CAT-2) do not count toward the 50 lines; they have their own
size limit (CFG-6), and are still reviewed, fingerprinted and previewed.

Source: V4 §Record Model, §Intake Sources. State: met (attachment size limit: not met). Confirmed: yes
(2026-11-16).

### CAT-4: Each prompt has a permanent short name (slug)

*As a developer, each prompt has a permanent short name made of area and name (for example
`review__missing-tests`) that I use to run or find it; its display name can be anything, so that names
stay stable across versions and can never be turned into a path or a command.*

**What you'll notice:** slugs are lowercase letters, digits and single hyphens, with exactly one `__`
between area and name. New versions keep the slug, so the slug always runs the current active version.
A slug is permanent: renaming means a new prompt with a new slug, and an old slug is never reused, even
after retirement (a typo stays in history). Display names may contain spaces, capitals and accents and
are never used for file or folder names. Every slug is checked strictly before any command uses it.

Source: V4 §Slug and path rules. State: met. Confirmed: yes (2026-11-16).

### CAT-5: Prompts are used only from a catalog that checks out

*As a developer, I can only browse and run prompts from a catalog that checks out; if one prompt was
changed outside the plugin, only that prompt is unavailable and I am told why, but if the catalog's
structure is broken, nothing is used until it is repaired.*

**What you'll notice:** every browse and run checks the whole catalog first. Two kinds of problem are
handled differently:

| Problem | Effect |
|---|---|
| **Structure:** the catalog index is unreadable or unsupported, a listed file is missing, an unlisted file sits where records live, version chains are inconsistent, a half-finished update | The whole catalog is unavailable for browsing and running; you are told what is wrong and how to recover. The plugin never guesses from loose files. |
| **One prompt:** its text, an attached file (CAT-2) or its origin (SEC-4) no longer matches its approval fingerprint | Only that prompt is unavailable, shown as "changed since approval" with the reason; everything else keeps working. |

**Changes to earlier decisions:** V4 §Layout and today's code make any problem disable the whole catalog.
This narrows that to structural problems. Management follows the same split (CAT-6).

Source: V4 §Layout, §Interrupted updates; owner decision 2026-11-16. State: **partial** (structural case
met; per-prompt isolation not met). Confirmed: yes (2026-11-16).

### CAT-6: An interrupted change never leaves a silently broken catalog

*As a developer, an interrupted change never leaves me with a silently broken catalog: I am told exactly
what is wrong and how to restore it, nothing is repaired without asking, and a prompt changed outside the
plugin blocks only changes to that prompt.*

**What you'll notice:** writes go through a temporary file that is then swapped in, the catalog index is
written last, and completed steps are undone if a later one fails, so an interruption almost never costs
anything. If the catalog still ends up inconsistent:

- **Structural problem** (CAT-5): browsing and running stop, and `/prompt-library` refuses every change.
  It names the exact file and how to restore it from git; outside git you fix it by hand with the format
  guide. The one repair it offers itself, after asking, is removing a leftover draft file from an
  interrupted save.
- **One prompt changed since approval:** only that prompt is blocked; other prompts can still be added
  and changed. If its text or origin changed, it can only be restored from git or retired (see the
  amendment below), never revised from its unapproved text (that would turn an outside edit into an
  approved new version). If only an attached file changed, it can instead be reviewed with the new
  attachment content as a new version (second amendment below).
- Nothing is ever repaired silently.

**Changes to earlier decisions:** V4 §Interrupted updates and today's code refuse every change while any
validation problem exists. This keeps that for structural problems and narrows it to the one prompt for a
fingerprint mismatch.

**Amended 2026-11-17 (CAT-6):** *a prompt blocked because it changed since its approval can be restored from
git when git has a copy, or retired after I confirm, so that an outside edit never becomes approved text and
a prompt I can't restore never stays stuck in my library.* `/prompt-library` offers *Retire* for such a
prompt, showing slug, version and the reason and asking once. A retired prompt never runs again, its
remembered approvals end, it leaves the normal lists but stays in the history, and its slug stays taken
(CAT-4); to keep the wording, copy it into a new prompt with a new slug and full review. Restoring from git
stays the first suggestion. Found by the cross-model review before the requirements PR.

**Amended 2026-11-17 (CAT-6, attachments):** *when only an attached file changed since a prompt's
approval, I can revise the prompt to take the new file content: the approved prompt text stays as it
was, and the new attachment content goes through screening, review and my approval as a new version,
so that editing a shared style guide never strands my prompts while an outside edit to a prompt's own
text or origin never becomes approved text.* The prompt shows "attachment changed since approval" and
`/prompt-library` offers *Review the new attachment*, showing the attachment diff; each attaching prompt
gets its own review and approve-and-activate question (CAT-2's accepted trade-off, LIF-6). An attachment
that grew past the CFG-6 limit takes the same path once shortened or detached. If the text or origin
changed as well, the stricter rule wins: restore from git or retire. Found by the cross-model review
before the requirements PR.

Source: V4 §Interrupted updates; code (atomic writes, rollback, orphan removal); owner decision
2026-11-16. State: **partial** (structural handling met; per-prompt blocking, retire and attachment
review not met).
Confirmed: yes (2026-11-16; amended 2026-11-17).

### CAT-7: A stored prompt can never become a standing instruction

*As a developer, my catalog can never be placed where Claude Code or GitHub loads files automatically, so
that a stored or imported prompt can never become a standing instruction without my review and
approval.*

**What you'll notice:** a catalog location in or below `.git`, `.github` or Claude Code's configuration
folders under `.claude/` (`rules`, `skills`, `commands`, `agents`, `hooks` and similar) is refused; the
default is used and you are told why. Stored prompts cannot double as rules, commands or skills: a
standing rule is written as a rule. Attached files (CAT-2) follow the same location rule.

Source: code (`FORBIDDEN_ROOTS` in the validator); not stated in V4. State: met for the catalog;
attachments not met (CAT-2). Confirmed: yes (2026-11-16).

## 3. Intake (INT)

### INT-1: A prompt can come from six origins, and its origin is always recorded

*As a developer, I can add a prompt I wrote, one Claude or Codex drafted, turns from a Claude Code
session, or text from the web, and the plugin's own examples come in through setup, so that every prompt
records where it came from and gets the level of screening that origin needs.*

**What you'll notice:** every prompt carries one of six origins: `user`, `claude`, `codex`, `session`,
`web` or `example`. The origin decides how strict the plugin is: `session`, `web`, `claude` and `codex`
text is blocked on a secret, `session` and `web` also get the import review, and your own `user` text gets
warnings only. `codex` is your claim (the plugin cannot verify who wrote pasted text), so it is screened
as untrusted like `claude`. `example` is set only by `/prompt-library-setup` when you accept a shipped
example (CAT-1); you never choose it by hand. A secret match in `example` text is also a hard stop
before the draft is filed (SCR-1).

**Changes to earlier decisions:** extends V4's five origins with `example` (decided in CAT-1).

**Amended 2026-11-17 (DEF-3):** once Notion support arrives, a seventh origin, `notion`, set only by
`/prompt-sync` (never chosen by hand); a secret in it is a hard stop, as for `session` and `web`.

Source: V4 §Intake Sources; owner decision 2026-11-16. State: **partial** (five origins: met; `example`:
not met). Confirmed: yes (2026-11-16).

### INT-2: Every new prompt starts as a draft and runs only after my approval

*As a developer, every prompt I add starts as a draft and becomes runnable only after review and my
approval of its exact text, usually in the same run, so that an interrupted or abandoned add can never
leave a runnable prompt behind.*

**What you'll notice:** `/prompt-library add` normally goes all the way in one run: the prompt is filed
as a draft, reviewed, you approve its exact text, and it becomes active. If you stop partway (you close
the session or say "not yet"), it stays a draft: retrieval lists it only when you ask for non-active
records, it cannot run, and `/prompt-library activate <slug>` picks up where you left off. No intake path
(paste, session, web or example) skips the draft state.

**Amended 2026-11-17 (DEF-3):** one exception, once Notion support arrives: a change you accept in a Notion
sync becomes active directly, without a draft step.

Source: V4 §Intake Sources. State: met. Confirmed: yes (2026-11-16).

### INT-3: Text the plugin pulls in itself cannot be relabeled; pasted text's origin is shown first

*As a developer, text the plugin fetches from the web or reads from a past session is always filed as
`web` or `session`, and for pasted text I see and confirm the origin before it is filed, so that the
import review can never be skipped silently by a label.*

**What you'll notice:** a URL import is always `web` and a session read by ID is always `session`; you
cannot file either as `user`. For text you paste, the plugin cannot know where it came from: before filing
it shows you the slug, name, origin, description and fingerprint and asks whether to file the draft. If
you paste web text and confirm it as `user`, it skips the import review, but that is a choice you saw and
made, never a silent one.

Source: V4 §Authority and Trust Model. State: met. Confirmed: yes (2026-11-16).

### INT-4: I can save turns from a Claude Code session without the plugin reading transcripts

*As a developer, I can save turns from a Claude Code session by selecting or pasting them, or, when
session-kit is installed, by naming a session and turn ranges that are merged into one draft, so that I
can capture good prompts from past work without the plugin itself reading my transcript files.*

**What you'll notice:** selecting or pasting turns always works. Naming a session ID and turn ranges works
only when session-kit is installed (detected at run time, not declared as a dependency); without it, that
option is not offered and you paste instead. Several turns are merged into one draft whose `source_ref`
lists the ranges used, and the result must still fit the 50-line limit (CAT-3), or you are asked to
condense it. Session text is always `session` origin (INT-3), so it gets the import review and the hard
secret block, because transcripts often hold keys and private data.

Source: V4 §Intake Sources. State: met. Confirmed: yes (2026-11-16).

### INT-5: Before saving, I am asked "prompt or skill?" and offered to revise a near-duplicate

*As a developer, before a prompt is saved I am asked whether it should be a prompt, a skill or a workflow
skill, and offered to revise a similar existing prompt instead, so that my library holds only real prompts
without silent near-duplicates, while I make the final call.*

**What you'll notice:** every add asks one question first, even when the answer looks obvious: "Prompt"
(normally recommended), "Skill" (needs bundled scripts or references, tool restrictions or automatic
activation; points to `skill-development`) or "Workflow skill" (multi-step phases or sub-agents; points to
`workflow-skill-development`). Text that carries its own code for Claude to define or run gets "Skill"
recommended, with the reason. Picking a skill saves nothing and ends the add. Picking "Prompt" checks for
an existing prompt in the same area or with a similar name or description and, if one exists, offers to
revise it or add a new one anyway. Both are recommendations; you decide.

**Changes to earlier decisions:** V4 named two choices (prompt or skill); the third, "Workflow skill",
exists in the code and is now part of the requirement.

Source: V4 §Intake Triage; code (workflow-skill option). State: met. Confirmed: yes (2026-11-16).

### INT-6: Only I can start a change to my library or its setup

*As a developer, only I can start adding, revising, activating or deactivating a prompt, or setting up
the library, by typing the command myself, so that no model action, including instructions hidden in
imported text, can begin changing my catalog.*

**What you'll notice:** Claude can suggest `/prompt-library add` but cannot start it; plain words like
"save this as a prompt" do not start it either, you type the command. The same holds for
`/prompt-library-setup` (PUR-6). Your exact-text approval (PUR-2) is still required on top.

**Changes to earlier decisions:** extends the user-only start to the new `prompt-library-setup` skill
(PUR-6), which V4 did not have.

Source: V4 §Components; code (`disable-model-invocation`); owner decision 2026-11-16. State: **partial**
(`prompt-library`: met; `prompt-library-setup`: not met, the skill does not exist). Confirmed: yes
(2026-11-16).

## 4. Screening for secrets and personal data (SCR)

### SCR-1: A secret in imported or AI-written text stops the draft

*As a developer, when text from a session, the web, Claude or Codex contains something that looks like a
secret, the draft is stopped and I see the line and the kind of match (never the secret itself), and I
remove it myself, so that no key can end up in my library and no prompt is silently rewritten.*

**What you'll notice:** for `session`, `web`, `claude` and `codex` text, a match is a hard stop before
anything is saved: you see a line number and a pattern name (for example "line 7: bearer_token"), never the
matched text. You edit the line and the plugin screens again; only a clean draft can be filed. Nothing is
auto-redacted, because a prompt silently rewritten to a placeholder can be broken or misleading.

**Changes to earlier decisions:** V4 hard-blocked only `session` and `web`; the block also covers `claude`
and `codex`, because AI-written text often carries keys over from the session (consistent with INT-1).

**Amended 2026-11-17 (SCR-1):** a shipped example (`example` origin, CAT-1) gets the same hard stop
before its draft is filed. An example never needs a real secret, so a match means the shipped example
is broken; you are told which example and line, and it is not added. Found by the cross-model review
before the requirements PR.

Source: V4 §Import review; code (extended to `claude`, `codex`). State: met (`example`: not met, the
origin does not exist yet). Confirmed: yes (2026-11-16; amended 2026-11-17).

### SCR-2: In my own text, a match is a warning I can accept

*As a developer, when my own text matches a secret pattern I get a warning naming the line and the kind of
match and can choose to keep it, so that legitimate paths and example strings in my prompts are not
blocked while a real secret is still made visible to me.*

**What you'll notice:** a `user` prompt containing, for example, `/Users/alex/projects/api` or a fake
example token gets a warning ("line 3: home_directory_path") and a choice to keep it or fix it; it is never blocked. The trade-off:
a real key you paste into your own prompt and accept is saved in your project catalog.

Source: code. State: met. Confirmed: yes (2026-11-16).

### SCR-3: The secret check repeats at every later step, and reaches older prompts through status

*As a developer, the secret check is repeated at every step that files, verifies or activates a prompt,
and the library status check flags active prompts that match a newly added pattern, so that a secret
cannot slip in after the first check and a stricter screen still reaches my older prompts.*

**What you'll notice:** a draft update, the recording of verification and activation each screen the text
again (blocking for the origins in SCR-1), so an accepted rewrite or a hand-edited draft carrying a key is
refused even though the first screen passed. A run of an active prompt is not re-screened; it cannot
change without being blocked (CAT-6). When a plugin update adds a pattern, the status check of
`/prompt-library-setup` (PUR-6) lists active prompts that now match, so you can revise them; their runs
are not blocked.

**Changes to earlier decisions:** adds the status-check flag for active prompts, which V4 and the code do
not have.

Source: code; owner decision 2026-11-16. State: **partial** (re-screening at filing, verification and
activation: met; status-check flag: not met). Confirmed: yes (2026-11-16).

### SCR-4: The screen catches common secret kinds, plus patterns I add for my project

*As a developer, the screen catches service keys and tokens, credential lines and headers, private-key
blocks, credentials in URLs and personal home-directory paths, and I can add my own patterns for a
project, so that common secrets and my organization's own formats are both caught before a prompt is
saved.*

**What you'll notice:** caught without any setup: service keys and tokens (for example AWS, GitHub, Slack,
OpenAI-style `sk-`, Google, Stripe, GitLab, npm, JWT), credential lines (`Authorization:`, `Bearer ...`,
`API_KEY=...`, `password: ...`, `?token=` in a URL), PEM private-key blocks, `user:pass@` in a URL, and
personal home paths (`/home/<name>`, `/Users/<name>`, `C:\Users\<name>`). A plugin update can add new
providers without changing this requirement. Formats only your organization uses (an internal token prefix,
an internal host) are caught only after you add them as project patterns; a pattern you add that is too
broad can block too much.

**Changes to earlier decisions:** adds project-specific patterns, which V4 and the code do not have; where
they are stored and in what format is decided in CFG-7.

Source: V4 §Import review; code (URL credentials, credential lines, shared `plib-token-shapes.json`); owner
decision 2026-11-16. State: **partial** (built-in categories: met; project patterns: not met). Confirmed:
yes (2026-11-16).

### SCR-5: Email addresses are screened like secrets

*As a developer, an email address in my prompt is treated like a secret (blocked for session, web, Claude
and Codex text, a warning for my own text), while git remotes such as `git@host:path` and reserved example
domains such as `example.com` or `.test` are allowed, so that colleagues' and customers' addresses do not
end up in my library.*

**What you'll notice:** a colleague's address carried over from a transcript stops the draft (SCR-1) or
warns you in your own text (SCR-2); you replace it, for example with "the on-call owner". A git remote
(`git@github.com:org/repo.git`) and reserved example addresses (`example.com`, `example.net`,
`example.org`, and the `.example`, `.test`, `.invalid`, `.localhost` endings) pass; other `.net` and `.org`
addresses are screened. The trade-off: a prompt that really needs a
team mailbox cannot be saved from session or AI text; you rephrase it or write that part as your own text.

Source: branch (ad706e64, 7df79b46); owner decision 2026-11-16. State: **branch** (only on the unmerged
security-bundle branch). Confirmed: yes (2026-11-16).

### SCR-6: The reviewer reports other personal data in every prompt

*As a developer, the reviewer reports personal data (phone numbers, names, postal addresses, customer
identifiers) as a Critical finding for every prompt, whatever its origin, showing the line and the kind of
data but never the value, and I decide whether to remove it, so that personal data is never saved
unnoticed while legitimate mentions are not blocked.*

**What you'll notice:** before you approve, findings such as "line 4: phone number (Critical)" appear for
`user`, `claude`, `codex`, `session`, `web` and `example` prompts alike. They never block on their own;
you remove the data or keep it. An occasional false alarm (a version string that looks like a phone
number) is possible. Email addresses are handled by the screen instead (SCR-5).

**Changes to earlier decisions:** V4 and the code check personal data only in the import review
(`session` and `web`); this extends the reviewer's personal-data check to every origin.

Source: V4 §Import review; code; owner decision 2026-11-16. State: **partial** (`session`, `web`: met;
other origins: not met). Confirmed: yes (2026-11-16).

## 5. Review and optimization (REV)

### REV-1: Every prompt is reviewed before it can run, with no way around it

*As a developer, every prompt gets a quality review whose findings I see before approving, and a Critical
finding must be acknowledged; if the reviewer cannot run, the prompt stays a draft until a review
succeeds, so that no prompt ever runs unreviewed.*

**What you'll notice:** the reviewer checks clarity, boundaries and prerequisites, the 50-line limit,
redundancy, a clear success condition and wording not tied to one tool, for every origin. Findings are
advisory: you see them before approving, and a Critical one needs your acknowledgment. If the reviewer
cannot be started, the add or revise stops with the prompt saved as a draft; `/prompt-library activate
<slug>` later resumes with the review. While the reviewer is broken, no new prompt can be activated.

**Changes to earlier decisions:** removes the current "continue without a review" choice after a failed
reviewer dispatch, so PUR-2 holds without exception.

**Amended 2026-11-17 (DEF-3):** one exception, once Notion support arrives: a change you accept in a Notion
sync is not reviewed before it becomes active; it is still screened for secrets.

Source: V4 §Quality review; owner decision 2026-11-16. State: **partial** (review and acknowledgment: met;
no-review-no-activation: not met, the skill offers to continue without a review). Confirmed: yes
(2026-11-16).

### REV-2: Imported and AI-written text is checked for hidden instructions

*As a developer, prompts from a session or the web get the full import review with its own approval, and
prompts written by Claude or Codex are also checked for hidden instructions and for doing more than their
description says, so that instructions picked up from outside text are caught whichever way they arrive.*

**What you'll notice:** for `session` and `web` prompts the reviewer checks for injection-like text aimed
at the agent (ignore rules, exfiltrate, call tools, fetch more, act outside the purpose), provenance
(`source_ref` complete, license or attribution noted) and scope fit, and your one approval of the exact
content (LIF-1) also records the import approval, separately from the quality approval. For `claude` and `codex` prompts the reviewer runs the same
hidden-instruction and scope-fit checks and reports them like any other finding (a hidden instruction is
Critical); there is no separate import approval and no provenance check for them. Personal data is
covered for every origin by SCR-6.

**Changes to earlier decisions:** V4 limited all import checks to `session` and `web`; this extends the
hidden-instruction and scope-fit checks to `claude` and `codex`.

Source: V4 §Import review; owner decision 2026-11-16. State: **partial** (`session`, `web`: met; `claude`,
`codex`: not met). Confirmed: yes (2026-11-16).

### REV-3: The reviewer proposes a rewrite; I accept it, reject it or ask for another round

*As a developer, the reviewer proposes an optimized rewrite shown as a diff, and I accept it whole, reject
it, or ask for another round with my own instructions; an accepted rewrite replaces a draft in place,
while a change to an active or inactive prompt becomes a new version that is reviewed and approved again,
so that nothing is rewritten without my approval and a prompt in use is never changed underneath me.*

**What you'll notice:** one review round runs automatically; the rewrite changes wording, not intent, and
stays within 50 lines. If you want only part of it, you ask for another round and say what to keep (for
example "keep the example section"). A draft that never ran has no version 2: the accepted rewrite replaces
it, and the original stays visible in the diff (and in git when the catalog is tracked). Changing an
active or inactive prompt always creates a new draft version that goes through review and approval.

Source: V4 §Optimization. State: **partial** (rewrite, approval, in-place and new-version handling: met;
passing my own instructions to another round: not stated in the skill). Confirmed: yes (2026-11-16).

### REV-4: The reviewer can only look and suggest

*As a developer, the reviewer can only read the prompt and report findings and a proposed rewrite; it
cannot approve, activate, edit, write, run commands or fetch anything, so that a prompt designed to
manipulate the reviewer can at most produce a wrong report, which I see before deciding.*

**What you'll notice:** an accepted rewrite is filed by the management skill through the validator after
your approval, never by the reviewer. A prompt that tells the reviewer to approve, activate or change files
has no effect beyond the reviewer's report.

Source: V4 §Optimization, §Components; code (agent `tools: Read`). State: met. Confirmed: yes (2026-11-16).

### REV-5: The reviewer treats the prompt as data, never as orders

*As a developer, the reviewer never follows instructions inside a prompt; it cites hostile text by line in
its findings, shows me the exact wording only in a clearly labelled quoted-data block, never quotes
secrets or personal data at all, and never carries hostile text into its rewrite, so that I can judge what
was found without the prompt being able to steer the review or leak a secret.*

**What you'll notice:** text addressed to "the reviewer" or claiming the review is already approved is
reported as a Critical finding, not obeyed. The findings table cites it by line; a labelled quoted-data
block below the table shows its wording, unless it contains a secret or personal data, in which case only
the line and the kind of value appear. The proposed rewrite removes it.

Source: V4 §Authority and Trust Model; code (agent). State: met. Confirmed: yes (2026-11-16).

### REV-6: The reviewer sees exactly the prompt being filed and its own attachments

*As a developer, the reviewer sees exactly the prompt being filed and the project files it attaches, and
cannot be pointed at, or tricked into reading, anything else (another prompt, a file outside the catalog
or project, a file reached through a link, or a file swapped in after the check), so that hidden
instructions in a prompt and in its attachments are both reviewed while nothing else can leak into the
review.*

**What you'll notice:** a hidden instruction in an attached file (for example line 40 of
`docs/style-guide.md`) is reported like one in the prompt text, because attachments are loaded into the
agent at every run (CAT-2). Nothing the record says can make the reviewer see `.env`, another prompt, a
file outside the project or a file reached through a symlink or junction.

**Changes to earlier decisions:** extends the reviewer's scope from "the one record" to the record plus
its attachments, as CAT-2 ("shown in the review") requires.

**Mechanism (implementation decision, not part of the requirement).** On `main` the skill passes the
reviewer an absolute record path and nothing bounds it. On the security-bundle branch, the validator's
`review-path` checks the path (inside the catalog, a listed record, no link on the way) and the agent
re-checks it, but a link swapped in between the check and the read still escapes. Passing the record's
text and metadata inline (no file read left to steer) satisfies REV-6 only if the attachments' content is
passed too; extending `review-path` to attachments must also close the swap gap. Either way, REV-1 to
REV-6 and CAT-2 must hold together.

Source: code + branch; owner decision 2026-11-16. State: **partial** (single-record review: met without a
bound on `main`, bounded on the branch with the swap gap; attachments: not met). Confirmed: yes
(2026-11-16).

## 6. Verification and lifecycle (LIF)

### LIF-1: A prompt becomes active only with my approval of its exact content

*As a developer, a prompt becomes active only after I approve its exact final content (text and
attachments) in one question that shows me the content, its fingerprint and any invisible characters; for
session and web prompts that one approval covers both the quality and the import review, so that nothing I
have not seen can ever be activated, without asking me twice for the same text.*

**What you'll notice:** after the review you see the final text, the first characters of its fingerprint
and a list of invisible characters (line, column, name) if there are any, and answer one question. That
yes records the quality approval and, for `session` and `web`, the import approval, both bound to that
fingerprint. Activation refuses if any required approval does not match the current content.

**Amended 2026-11-17 (DEF-3):** one exception, once Notion support arrives: accepting a change in a Notion
sync activates it; the run approval (PUR-3, EXE-3) still shows its full text before its first run.

Source: V4 §Verification record; code. State: **partial** (text: met; attachments in the fingerprint: not
met, CAT-2). Confirmed: yes (2026-11-16).

### LIF-2: Any change to approved content cancels the approval, except line endings

*As a developer, any change to an approved prompt's content (its text or an attached file), however small,
cancels its approvals, while a change of line endings alone does not, so that what runs is always exactly
what I approved and a checkout on another operating system does not break my prompts.*

**What you'll notice:** a typo fixed directly in the file makes the prompt count as changed: it is blocked
on its own until restored or retired (CAT-6), and a real change goes through revise, review and approval. Windows and
Unix line endings give the same fingerprint, so a checkout on another system keeps every approval.
Whitespace and spelling changes are not exempt. Since SEC-4 (2026-11-17), a changed `origin` also
cancels the approval.

Source: V4 §Verification record. State: **partial** (text: met; attachments: not met, CAT-2). Confirmed:
yes (2026-11-16).

### LIF-3: A prompt changes only by new versions, and going back is a new version too

*As a developer, a prompt moves from draft to active, can be switched off and on without a new version,
and is changed only by a new version that replaces the old one once approved; to go back, I start a new
version from any earlier version's text, so that the history only grows, every version that runs was
reviewed under today's rules, and I can always return to wording that worked.*

**What you'll notice:** `draft -> active <-> inactive`; switching a prompt off and on needs no new version
or review. A revise creates a new draft version; when it is finalized, the old version becomes historical,
and if the old one was inactive you choose whether the new one starts active or inactive. A historical
version never runs again: to go back to v2's wording, you revise starting from v2's text, which becomes a
new version (for example v4) after review and approval. A prompt blocked as changed since its approval can
also be retired (CAT-6 amendment): a terminal state, never run again, kept in the history.

Source: V4 §Lifecycle; code (revise from a chosen earlier version). State: met. Confirmed: yes
(2026-11-16).

### LIF-4: Revising never interrupts the version in use, and I can discard a draft I no longer want

*As a developer, the version in use keeps running unchanged while a new version is being prepared and is
replaced only when I finalize the new one, and I can discard a draft I no longer want after seeing what
will be removed, so that a revision in progress never breaks my work and an abandoned idea never blocks
the next one.*

**What you'll notice:** while v4 is a draft, `/prompt-execution` keeps running v3. A discard (for example
`/prompt-library discard <slug>`) shows which draft will be removed and what stays active, and asks once;
afterwards a new revise starts a fresh v4. Only a draft that never became active can be discarded, an
initial draft included; a version that has run stays in the history (LIF-3). Nothing is discarded
automatically.

**Changes to earlier decisions:** adds discarding a listed draft. Today only an unlisted stray file can be
discarded, and an abandoned revision blocks every further revise of that prompt until it is resumed.

Source: V4 §Lifecycle, §Acceptance; owner decision 2026-11-16. State: **partial** (old version keeps
running: met; discard: not met). Confirmed: yes (2026-11-16).

### LIF-5: A prompt name always runs exactly one text

*As a developer, each prompt has at most one active version, and when I want to compare wordings I save
the variant as its own prompt (for example `review__missing-tests-short`), so that a prompt name always
runs exactly one known text.*

**What you'll notice:** activating a second version of the same prompt is refused; the new version replaces
the old one through finalize (LIF-3). Two wordings you want to compare are two prompts with two names, each
with its own review, approval and history.

Source: V4 §Lifecycle. State: met. Confirmed: yes (2026-11-16).

### LIF-6: Every change to my library needs my yes, without asking twice about the same text

*As a developer, every change to my library is shown to me and needs my yes before it happens, and
approving a prompt's exact text and activating it are one question ("Approve and activate", "Approve, keep
as draft", "Cancel"), so that nothing changes without my consent and I am not asked twice about the same
text.*

**What you'll notice:** the simplest add asks three times: prompt or skill (INT-5), file this draft
(showing slug, name, origin and fingerprint, INT-3), and approve-and-activate (LIF-1). "Approve, keep as
draft" records the approval without activating. Activating a draft approved earlier, deactivating,
reactivating, finalizing a revision and discarding a draft (LIF-4) each keep their own question.

**Changes to earlier decisions:** merges today's separate "approve exactly this text" and "change status"
questions into one for a draft being activated.

Source: V4 §Lifecycle; owner decision 2026-11-16. State: **partial** (consent for every change: met by
the skill's instructions, see SEC-3; combined question: not met). Confirmed: yes (2026-11-16).

### LIF-7: My yes only counts for the exact content I saw

*As a developer, my approval is applied only if the content is still exactly what I was shown; if it
changed, nothing is approved, I see what changed since I looked, and I am asked again about the new
content (after it is screened and reviewed if needed), so that a change I never saw can never be approved
by my click and I can still finish in the same run.*

**What you'll notice:** if another session, an editor or a sync changes the record while you are looking
at the approval question, your click approves nothing. You see which lines changed after you looked; the
new content goes through the screen (and the review, when its text changed) and you get a fresh question.

**Changes to earlier decisions:** today the validator refuses (`--expect-sha256`) and the run stops with an
error; showing the change and asking again is new.

Source: code (`--expect-sha256`); owner decision 2026-11-16. State: **partial** (refusal: met; showing the
change and asking again: not met). Confirmed: yes (2026-11-16).

### LIF-8: An interrupted add or revise picks up where it stopped

*As a developer, a draft left by an interrupted add or revise resumes where it stopped, keeping only
approvals that still match its current content and redoing only what is missing, so that an interruption
costs me nothing and a changed draft is never activated on an old approval.*

**What you'll notice:** after a closed session or a crash, `/prompt-library activate <slug>` continues the
draft. If you had already approved it and its content is unchanged (same fingerprint), you are only asked
for the missing step, for example activation. If the content changed since your approval, or it was never
reviewed, it goes back through review and approval (LIF-2, REV-1). The secret screen runs again either way
(SCR-3).

Source: code. State: met. Confirmed: yes (2026-11-16).

## 7. Retrieval (RET)

### RET-1: Find, list and show a stored prompt and its history

*As a developer, I can list my active prompts, search them by name, area, description or a phrase from
their text, show one in full, and see its earlier versions, so that I can find and check a stored prompt
without opening catalog files.*

**What you'll notice:** a list shows only active prompts unless you ask for drafts, deactivated, retired
(CAT-6) or older versions. A search also finds a prompt by a phrase inside its text, and each result says whether it matched
a label or the text. Showing a prompt gives its details and its full text as quoted data in a code block;
Claude never acts on it. A history lists every version, oldest first, and prints the text only of the one
you pick. When the catalog fails its check, nothing is listed and you are told why (CAT-5).

**Changes to earlier decisions:** today search covers only slug, area, name and short description;
searching the prompt text is new.

Source: V4 §Scope; owner decision 2026-11-17. State: **partial** (list, show, history: met; text search:
not met). Confirmed: yes (2026-11-17).

### RET-2: Looking up a prompt never changes or runs anything

*As a developer, finding or showing a stored prompt never runs it and never changes the catalog, and any
instruction in its text is shown to me rather than followed, so that looking at a prompt is always safe.*

**What you'll notice:** a lookup only displays. It never runs a prompt, edits the catalog, or starts
`/prompt-execution` or `/prompt-library` for you; to run what you found you type
`/prompt-execution <slug>` (PUR-3, INT-6). Only the catalog check and show commands run without asking;
anything else during a lookup would raise the normal permission prompt. Instruction-like text in a prompt
is reported to you, not followed.

Source: V4 §Components. State: met. Confirmed: yes (2026-11-17).

### RET-3: Lookups on request, and a hint when a stored prompt fits

*As a developer, a lookup starts when I ask in plain words for a stored prompt or type
`/prompt-retrieval`, and when something I ask for fits a stored prompt, Claude mentions that prompt and its
`/prompt-execution` command once per session, so that I reuse my library without having to remember
every prompt in it.*

**What you'll notice:** "find the saved prompt about commit messages" starts a lookup without a command.
When you ask for work a stored prompt covers ("write me a changelog entry"), Claude says once that
`docs__changelog-entry` exists and that `/prompt-execution docs__changelog-entry` runs it, and then does
what you asked. A hint only names the prompt and the command: it never shows the text or runs anything
(RET-2, PUR-3), and the same prompt is not mentioned again in that session. To find fitting prompts, Claude
reads the catalog's labels during other work.

**Changes to earlier decisions:** V4 starts retrieval only on a clear request; the hint is new. It reads
the catalog during unrelated work, which V4 did not do, and it is the one exception to PUR-4's "nothing
automatic" (owner decision 2026-11-17, PUR-4 amended).

Source: V4 §Components; owner decision 2026-11-17. State: **partial** (lookup on request: met; hints: not
met). Confirmed: yes (2026-11-17).

### RET-4: Hidden characters and mixed-alphabet words are pointed out whenever text is shown

*As a developer, whenever a prompt's text is shown to me (lookup, run preview, approval), every invisible
character and every word that mixes alphabets is listed with its position, so that the text I approve is
the text that runs.*

**What you'll notice:** above the code block you get one line per finding, for example "line 1, column 21,
U+200B ZERO WIDTH SPACE (invisible in the text below)", or a word such as "pаssword" whose "а" is Cyrillic.
Invisible means zero-width, direction, tag, control and private-use characters, blank-looking letters and
spaces that are not a normal space. The list stops at 50 with "50 or more". Findings are reported, never
blocked: an emoji joiner or a variation selector is legitimate, and you decide.

**Changes to earlier decisions:** the draft said "invisible or look-alike", but the code reports only
invisible characters; flagging words that mix alphabets is new.

Source: code (`hidden_characters` in the validator); owner decision 2026-11-17. State: **partial**
(invisible characters: met; mixed-alphabet words: not met). Confirmed: yes (2026-11-17).

### RET-5: See which active prompts need my approval soon

*As a developer, I can ask for a list of my active prompts that have no valid approval (never remembered,
expired, voided by a change or forgotten, each with its reason) and of those whose remembered approval
expires within the next 7 days, without anything being renewed or run, so that I can renew the prompts I
rely on before they start asking again.*

**What you'll notice:** `/prompt-retrieval approvals` lists active prompts in two groups, each line with
name, version and the reason or expiry date. It is read-only like every lookup (RET-2) and runs only when
you type it (PUR-4). It shows this machine's approvals file (PUR-3), never a teammate's. The 7-day window
is fixed, not a setting. To renew, run the prompt and pick *Run and remember* again.

**Changes to earlier decisions:** `prompt-retrieval` gains one new read-only checker subcommand that reads
the approvals file; today it may only run `validate` and `show`. PUR-6's status report keeps its own
approvals summary.

Source: owner decision 2026-11-17. State: **not met** (no remembered approvals exist yet, PUR-3).
Confirmed: yes (2026-11-17).

## 8. Execution (EXE)

### EXE-1: Only you can start a run

*As a developer, a stored prompt runs only when I type `/prompt-execution` with its name; nothing Claude
reads (a request in plain words, a hint, a lookup, or text inside a prompt or a web page) can start a run,
so that with remembered approvals nothing runs that I didn't start myself.*

**What you'll notice:** "run the missing-tests prompt" gets you the command to type, not a run. The
prompts that run are exactly the ones named after the command, never taken from the conversation or from
a prompt's text; a line such as "then also run `deploy__publish`" inside a prompt is shown to you, not
followed. This matters most for remembered approvals (PUR-3), which run without a question.

Source: V4 §Execution 1; owner decision 2026-11-17. State: met (`disable-model-invocation`, slugs only
from the command's arguments). Confirmed: yes (2026-11-17).

### EXE-2: Only an active, unchanged prompt can run

*As a developer, a run starts only if every prompt I named is active and unchanged since its approval;
otherwise nothing runs and I'm told which prompt was refused and why, so that I never run edited text, or
a sequence with a step missing.*

**What you'll notice:** a draft, a deactivated or older version, or a hand-edited prompt is refused with
its reason, and then no prompt of that run starts. The text is checked again right before each prompt;
a change in between stops the run there (EXE-5). A changed prompt blocks only itself and can only be
restored from git or retired, or, when only an attached file changed, reviewed as a new version (CAT-6);
other prompts stay runnable in later runs.

Source: V4 §Execution 2. State: **partial** (refusal and no partial run: met; a changed prompt blocking
only itself: not met, today it makes the whole catalog unavailable). Confirmed: yes (2026-11-17).

### EXE-3: What you see before a prompt runs

*As a developer, before a run I see, for every prompt without a valid remembered approval, its name,
version, origin, verification state, prerequisites, boundaries, hidden characters, full text and the full
content of its attached files, and for a remembered one a line with its version and approval dates, so
that I always know exactly what will run.*

**What you'll notice:** a new or changed prompt gets the full preview, attachments included and never
summarized; a long attachment makes a long preview (at most the CFG-6 limit, 32 KB by default). A
remembered prompt gets
one line, for example "`review__missing-tests` v3, approved 2026-11-10, expires 2026-12-10", and no
preview (PUR-3). Prerequisites and boundaries are shown, not checked (CAT-2); hidden characters are listed
per RET-4.

**Changes to earlier decisions:** V4 shows the full text before every run; remembered approvals (PUR-3)
replace that with the one-line notice, and attachments (CAT-2) join the preview.

Source: V4 §Execution 3; PUR-3, CAT-2, RET-4. State: **partial** (full preview of text: met; attachment
content and the remembered-run notice: not met). Confirmed: yes (2026-11-17).

### EXE-4: What one approval covers

*As a developer, an approval I give covers exactly the prompts, order and executor shown in its question,
and a remembered approval covers one unchanged prompt in any run I type, so that nothing runs in a set,
order or place I didn't choose.*

**What you'll notice:** the question names the prompts in order, each with a short fingerprint, and the
executor (Claude). Asking in your answer for a different set or order runs nothing; you are told to type a
new command, which gets its own preview and question. An interrupted run may continue with the rest of
the same approved sequence, in the same order (EXE-5). A remembered approval belongs to one prompt version
and runs it without asking in any command you type, in the order you typed (EXE-1). An approval for Claude
does not cover another executor (DEF).

**Changes to earlier decisions:** V4 says an earlier approval never substitutes; remembered approvals
(PUR-3) are the one exception, and they are per prompt, not per set or order.

Source: V4 §Execution 4; PUR-3; owner decision 2026-11-17. State: **partial** (per-question binding: met;
remembered approvals: not met). Confirmed: yes (2026-11-17).

### EXE-5: Prompts run one after another; a failure stops the rest, an interruption asks

*As a developer, the prompts in a run go one after another in the order I typed; if one fails, the run
stops and I'm told what ran, what was in progress and what didn't start, and if I interrupt one, I'm asked
whether to continue with the remaining prompts, so that a later step never builds on a failed one and an
interruption of mine doesn't force me to retype the rest.*

**What you'll notice:** prompts never run in parallel. A prompt fails when it errors or Claude cannot
complete it; the run then stops with the three lists, and nothing retries on its own. When you interrupt a
prompt (Esc), you get *Continue with the remaining prompts* (named) or *Stop*. The interrupted prompt
counts as not completed and is not restarted; the remaining ones are still covered by your approval and
are checked again right before each runs (EXE-2).

**Changes to earlier decisions:** V4 stops the run on an interruption too; asking to continue is new.

Implementation note: an Esc interruption ends Claude's turn, so the question may only appear with your
next message; not verified.

Source: V4 §Execution 5; owner decision 2026-11-17. State: **partial** (stop on failure with report: met;
continue question after an interruption: not met). Confirmed: yes (2026-11-17).

### EXE-6: An approved prompt gets no extra powers

*As a developer, an approved prompt runs with exactly the authority of a request I typed: it can't add
permissions or tools, change the approval flow, start or load other prompts, or change the catalog, and
its output isn't written back, so that approving a prompt never approves anything beyond its own text.*

**What you'll notice:** permission prompts, CLAUDE.md and project rules apply as if you had typed the
text. A line asking to edit a catalog prompt is blocked by the PUR-4 hook, and one asking to start another
prompt is refused (EXE-1); you are told about both. Attached files (CAT-2) load as context; they are files,
not prompts. Only the prompt text is the request; name, prerequisites, boundaries and references are
information. Output stays in the conversation. A prompt that needs its own tool grants or other prompts is
a skill (PUR-1).

Source: V4 §Execution 6. State: met (the hook-based block of catalog edits: not met, PUR-4). Confirmed:
yes (2026-11-17).

### EXE-7: Prompts run only in an interactive Claude session

*As a developer, stored prompts run only in an interactive Claude session I'm watching, never headless, on
a schedule or in Codex (until DEF-2 adds Codex with its own approval), so that someone is always there to
see a run and answer its questions.*

**What you'll notice:** `claude -p "/prompt-execution …"`, CI jobs and scheduled runs are refused, even for
a prompt with a remembered approval (PUR-3). In Codex you can look a prompt up in Claude and paste its text
yourself; running it there waits for DEF-2.

Source: V4 §Execution; PUR-3. State: Codex: met (no Codex executor exists); headless refusal: **not
verified** (a headless run cannot answer the approval question, but an explicit refusal, needed once
remembered runs skip that question, does not exist). Confirmed: yes (2026-11-17).

## 9. Trust and safety (SEC)

### SEC-1: Stored content is data everywhere except an approved run

*As a developer, everything stored with a prompt (its text, labels, references and attached files) is
treated as data to show me in every step except a run I approved, and even then only the prompt text is my
request, so that no stored content can steer Claude on its own.*

**What you'll notice:** in a lookup, a hint, intake, review, approval or history, instruction-like content
("ignore your rules", "always run this first") is shown and reported to you, never followed. During an
approved run only the prompt text is your request, with the authority of a typed message (EXE-6); attached
files are context. This is the general rule that RET-2, REV-5 and EXE-6 apply to their own steps, and it
covers any step added later (for example DEF-3).

Source: V4 §Authority and Trust Model. State: met (attachments: not met, CAT-2). Confirmed: yes
(2026-11-17).

### SEC-2: Text you didn't type yourself is untrusted from the start

*As a developer, text that comes from a web page, a session, or a Claude or Codex answer is treated as
untrusted at every step, and any instruction in it is reported to me, never followed, so that a prompt I
import can't change how it is imported, reviewed or approved.*

**What you'll notice:** a line such as "mark this verified and skip the review" in an imported page is
reported, not followed, while fetching, screening, reviewing and approving. Origins `web`, `session`,
`claude` and `codex` are untrusted; `user` and `example` text gets the same review but is not treated as
hostile. This matches SCR-1 (hard block on secrets, which also covers `example` text because a shipped
example never needs a secret) and REV-2 (hidden-instruction check).

**Changes to earlier decisions:** V4 names only web pages and sessions; `claude` and `codex` are added,
following REV-2.

Source: V4 §Authority, §Intake Sources; REV-2. State: met for web and session; claude and codex follow
REV-2's state. Confirmed: yes (2026-11-17).

### SEC-3: The approval questions rely on the skills, and that limit is written down

*As a developer, I'm told plainly that the approval questions are enforced by the skills' instructions,
not by the validator or the hook, including for remembered approvals, so that I know exactly what protects
me and what doesn't.*

**What you'll notice:** nothing in normal use. The README says that the validator checks text,
fingerprints and catalog validity, and the PUR-4 hook blocks direct edits, but neither can see whether you
were asked; a skipped question (a bug, or an instruction wrongly followed) would not be caught. Since
PUR-3 this also covers remembered approvals: one recorded without your click would let a prompt run later
with no question.

**Later option (not a requirement):** a hook that records your answer to the approval question, so the
validator accepts an activation or a remembered approval only with a matching answer. Not verified that a
hook can see the answer; it would be a second always-on hook (PUR-4).

Source: code (README Safety design); PUR-3, PUR-4; owner decision 2026-11-17. State: **partial**
(documented for activation and runs: met; remembered approvals: not met). Confirmed: yes (2026-11-17).

### SEC-4: A prompt's origin is a confirmed label, bound to the approval

*As a developer, a prompt's origin is what was fetched or what I confirmed at intake, and it is covered by
the approval fingerprint, so that relabeling a prompt outside Claude makes it count as changed instead of
silently skipping the import checks.*

**What you'll notice:** `origin` is never proof of where text came from: fetched text is locked to `web`
or `session`, pasted text carries the origin you confirmed (INT-3). If an editor or a teammate's commit
changes it, for example from `web` to `user`, the prompt counts as changed: it is blocked on its own until
restored or retired (CAT-6), like a hand-edited text (LIF-2). Inside Claude the PUR-4 hook already blocks such edits.

**Changes to earlier decisions:** V4 and the README treat a hand-edited `origin` as outside the guarantees;
it is now covered by the fingerprint. LIF-2's "any change cancels the approval" extends to `origin`. The
fingerprint format changes; ship it with CAT-1's `catalog_version` bump.

Source: V4 §Authority; owner decision 2026-11-17. State: **not met** (the fingerprint covers the text
only). Confirmed: yes (2026-11-17).

### SEC-5: The plugin writes only through its own checker; anything else asks you first

*As a developer, the plugin changes the catalog only through its own checker, after its questions, and any
other file write or web fetch shows me Claude Code's normal permission prompt, so that nothing outside the
catalog is written or fetched without my say.*

**What you'll notice:** during an import Claude Code asks permission to fetch the URL and to write the
scratch file used for screening; filing and activating after your *Approve* run without a further prompt,
because only the checker's commands are pre-approved (the questions themselves are skill-enforced, SEC-3).
The same applies to the approvals file (PUR-3). The PUR-4 hook blocks any other route to these files.

Source: code (no Read/Write/WebFetch grants); PUR-4. State: met (the approvals file and the hook: not met,
PUR-3, PUR-4). Confirmed: yes (2026-11-17).

### SEC-6: Every security gate is reviewed before it ships

*As a developer, every security gate in the plugin (the original screen, path and fingerprint checks once,
and each new gate before its first commit) gets a security review whose Critical and Major findings are
fixed before it ships, so that the protections I rely on have been checked for holes.*

**What you'll notice:** nothing directly; this is a rule for building the plugin. The catch-up review of
the original gates (secret screen, catalog path rules, fingerprint checks) comes first, because new gates
build on them. New gates from this document: the PUR-4 hook, remembered approvals and their store (PUR-3),
attachment loading and path rules (CAT-2), project screen patterns (SCR-4), the origin fingerprint (SEC-4)
and the headless refusal (EXE-7).

**Changes to earlier decisions:** V4 requires the review for new gates only; the catch-up review of the
original gates is new (V5 H7 found them unverified).

Source: V4 §Plugin Conventions; V5 H7; `.claude/rules/require-security-review-before-new-gate.md`; owner
decision 2026-11-17. State: **not met** (original gates unverified; new gates not built yet). Confirmed: yes
(2026-11-17).

## 10. Configuration and paths (CFG)

### CFG-1: Choose where my catalog lives

*As a developer, my prompt catalog lives at `.claude/prompts/` in my project unless I set another path in
my untracked `.claude/promptlibrary-kit.local.json`, and setup shows me which path is in use and where it
came from, so that I can put the catalog where my project keeps such files without anyone else's
repository deciding it for me.*

**What you'll notice:** the default ships in the plugin's tracked `promptlibrary-kit.settings.json`, which
you never edit. Your override is `catalog_root` in the local file, which also holds your approval lifetime
(PUR-3); it is per project and per machine and never committed, so a teammate who has not set the same path
sees the default location, not yours. Setup and its status report (PUR-6) show the path in use and whether
it came from the default, your local file or a fallback after a rejected value. The checker's `--root`
option exists for tests only; the skills never pass it, and it obeys the same path rules (CFG-3).

**Changes to earlier decisions:** the draft said "one setting"; PUR-3 added the approval lifetime, and the
attachment size limit (CAT-2, CAT-3) and project screen patterns (SCR-4) get their own CFG requirements.
CFG-1 now covers the catalog root only.

Source: V4 §Configuration; code (`resolve_root`); owner decision 2026-11-17. State: met (showing the source
in setup: not met, PUR-6). Confirmed: yes (2026-11-17).

### CFG-2: A tracked local settings file cannot move the catalog (dropped)

Dropped by the owner on 2026-11-17 as a hypothetical case: a `*.local.*` file is never tracked, and PUR-6's
setup keeps it git-ignored. No separate requirement is kept. The check stays in the code: a tracked
local file, or one reached through a link, has its `catalog_root` ignored, with a warning and a fail-closed
answer when git cannot tell. PUR-3's tracked-copy rules for the approval lifetime and the approvals file
also stay unchanged.

Source: V4 §Path trust boundary; code (`_is_tracked`, `_via_link`). State: met (as an implementation
detail). Confirmed: dropped (2026-11-17).

### CFG-3: My catalog stays inside my project, however the path is written

*As a developer, my catalog (and every attached file) always resolves inside my project, whatever form the
path takes (`..`, absolute, another drive, network path, link, junction, case, 8.3 short name), so that a
setting can never make the plugin read or write prompts somewhere else on my machine.*

**What you'll notice:** a catalog path that ends up outside the project root is refused, the default is
used and you are told why (CFG-4). Folder names with a trailing dot or space, or a colon, are refused
because Windows would read them as another folder. The project root is git's top-level folder (else the
working directory), and the catalog cannot be the project root itself. Sharing one catalog across
repositories stays DEF-1's job.

Source: V4 §Path trust boundary; code (`check_catalog_path`, `contained`); owner decision 2026-11-17.
State: met for the catalog (tests cover `..`, links, case, UNC, the root itself and trailing dots or
colons; junctions, 8.3 names and other drives are handled by the resolved-path comparison but untested:
add tests); attachments not met (CAT-2). Confirmed: yes (2026-11-17).

### CFG-4: A bad catalog path falls back to the default, and I'm told

*As a developer, if my catalog path setting is unusable, the plugin uses the default location, tells me
why in every skill before I confirm any change, and stops with the reasons if no location works, so that a
typo never sends the plugin somewhere unexpected without my knowing.*

**What you'll notice:** the order is your local `catalog_root`, then the plugin default; each rejection is
reported with its reason, and setup's status names the source as a fallback (CFG-1, PUR-6). If no value
works, the plugin stops with every reason and never guesses another folder. Trade-off you accepted: after
a typo, a change goes into the default catalog, so you can end up with prompts in two folders if you
ignore the warning. An invalid approval lifetime is handled the same way (PUR-3).

Source: V4 §Path trust boundary; code (`resolve_root`); owner decision 2026-11-17. State: **partial**
(fallback and the stop: met; only `prompt-retrieval` is told to show the warnings, `prompt-library` and
`prompt-execution` are not). Confirmed: yes (2026-11-17).

### CFG-5: The checker isn't affected by my project's Python setup

*As a developer, the plugin's checker and hook run the same way in every project, unaffected by my
project's Python files, virtual environment, uv settings or Python environment variables, so that nothing
in a repository can change how my prompts are checked.*

**What you'll notice:** only `uv` on your PATH is needed (PUR-4); your `pyproject.toml`, `.venv` and uv
config are ignored, and nothing is installed from your package index. Each call starts a fresh environment
with the standard library only (QA-4), which costs a small delay.

**Changes to earlier decisions:** extends the isolation to Python's own import path (Python's `-I` mode on
the checker call) and to the PUR-4 hook, whose `python3`/`python` fallback tiers
(`.claude/rules/require-python-hook-interpreter-fallback.md`) must run isolated too.

Source: code (`uv run --isolated --no-project --no-config`; README records a non-isolated form once picking
up a repository `.venv`); owner decision 2026-11-17. State: **partial** (uv isolation: met; Python `-I`
and whether `PYTHONPATH` reaches the checker: not met, unverified; hook: not built, PUR-4). Confirmed: yes
(2026-11-17).

### CFG-6: Attached files have a size limit I can set per project

*As a developer, all files attached to one prompt together are at most 32 KB by default, a limit I can set
per project to 16, 32 or 64 KB, checked when I attach, review and run, and never cut off silently, so that
what I approve stays readable and each run loads a predictable amount into my session.*

**What you'll notice:** an attachment that would exceed the limit is refused before review, with the sizes
named; attach a focused excerpt or make a skill (PUR-1). A file that grows past the limit, or a limit you
lower later, makes the prompt unrunnable until the attachments are shortened or detached; nothing is cut
off. Everything attached is shown in full in the review and the first-run preview (EXE-3) and loaded at
every run, which is why there is a cap. Setup's status shows the limit and where it came from (PUR-6).

**Settings (decided 2026-11-17, per `.claude/rules/ask-before-config-decisions.md`):**

| Item | Decision |
|---|---|
| Setting | `attachment_max_kb`, the total for all of one prompt's attachments: only `16`, `32` or `64`; default `32`. Any other value is rejected, the default is used, and the fallback is reported (CFG-4). No separate per-file limit. |
| Storage | Both: the default in the plugin's tracked `promptlibrary-kit.settings.json`; a per-project override in the untracked `.claude/promptlibrary-kit.local.json`. A tracked copy may only lower it (the PUR-3 pattern). |
| Format | JSON, the same files as `catalog_root`. |

**Changes to earlier decisions:** settles the attachment size limit CAT-2 and CAT-3 left open; the owner
chose a setting over a fixed limit.

Source: CAT-2, CAT-3; owner decision 2026-11-17. State: **not met** (attachments are not loaded yet, CAT-2).
Confirmed: yes (2026-11-17).

### CFG-7: My team's own secret formats are screened too

*As a developer, I can add secret patterns (a name and a regular expression each) for my project in a
shared, committed `.claude/promptlibrary-kit.screen.json` and in my own untracked
`.claude/promptlibrary-kit.local.json`, and the screen applies both together with the built-in kinds,
skipping and reporting any unusable pattern, so that my team's own token formats are caught for everyone
and my private ones for me, while a pattern can only add catches, never remove one.*

**What you'll notice:** a project pattern is used exactly like a built-in kind: on the prompt text and its
attachments when a prompt is saved (a hard stop for imported and AI-written text, SCR-1; a warning for
your own, SCR-2), again at every later step (SCR-3), and by setup's status check, which lists active
prompts matching a newly added project pattern (SCR-3). Match messages show the pattern's name, never the
matched text. Patterns are not used at run time and never change a prompt. A pattern that comes with a
cloned repository can block too much but cannot let anything through. Setup's status (PUR-6) shows how many
patterns came from each source. Trade-off you accepted: a committed pattern applies to you without asking,
and a badly written one can block prompts until it is fixed; review the shared file like code. A pattern
that runs out of time, or any left when the total time budget is used up, is skipped and reported
(amendments below).

**Settings (decided 2026-11-17, per `.claude/rules/ask-before-config-decisions.md`):**

| Item | Decision |
|---|---|
| Setting | Additional secret patterns, each `{"name": ..., "pattern": ...}`, the shape of the built-in `plib-token-shapes.json`. A pattern with an invalid regular expression, no name, or a name a built-in kind already uses, or one that runs out of time or is reached after the total time budget is used up (amendments below), is skipped and reported; the rest of the screen still runs. |
| Storage | Both, combined: a shared, git-tracked project file `.claude/promptlibrary-kit.screen.json` (`{"version": 1, "patterns": [...]}`), and a `screen_patterns` list in the untracked `.claude/promptlibrary-kit.local.json`. No tracked-copy restriction: patterns only add catches. |
| Format | JSON (backslashes doubled, no comments). |

**Changes to earlier decisions:** settles SCR-4's open storage and format. The owner re-confirmed keeping
project patterns when asked whether to drop them (2026-11-17). SCR-3's status flag, written for patterns a
plugin update adds, also covers newly added project patterns.

**Amended 2026-11-17 (CFG-7):** *each project pattern gets a fixed time limit of 1 second every time it
screens text, and a pattern that runs out of time is skipped and reported like an invalid one, so that a
badly written or hostile shared pattern can never hang saving, checking or setup.* Built-in kinds and the
other patterns still run; setup's status (PUR-6) lists the skipped pattern until it is fixed. The limit is
fixed, not a setting, and built-in kinds are not limited. Trade-off you accepted: while a pattern is
skipped, the text it should catch is not caught by it. Mechanism note: Python's standard regex engine
cannot be stopped inside a thread, so project patterns run in a separate worker process (standard library
only, QA-4), adding a small delay to each screen that uses them; the delay is not measured yet. Found by
the cross-model review before the requirements PR.

**Amended 2026-11-17 (CFG-7, total budget):** *all project patterns together get a fixed total of 5
seconds for each text they screen; once it is used up, the remaining project patterns are skipped and
named in the report, so that matching a shared pattern file can never make a save, check or setup take
more than a few seconds per text.* Built-in kinds always run in full first. The budget is fixed, not a
setting. The pattern count and pattern length are not capped (owner decision); trade-off you accepted:
loading and compiling a very long pattern file is not bounded by this budget and costs its own time, and
patterns late in the list may be skipped whenever earlier ones are slow. Setup's status check covers every active prompt, so with a hostile file it takes
about 5 seconds per prompt. Found by the cross-model review before the requirements PR.

Source: SCR-4; owner decisions 2026-11-17. State: **not met** (no project patterns exist). A new security
gate (SEC-6): `security-reviewer` before its first commit. Confirmed: yes (2026-11-17; amended
2026-11-17).

## 11. Platform and quality (QA)

### QA-1: The plugin behaves the same on Linux, macOS and Windows 11

*As a developer on Linux, macOS or Windows 11, the plugin behaves the same on my machine as on my
teammates', verified by its tests running on all three systems in CI whenever the plugin changes, so that a
prompt approved on one system is checked, fingerprinted and run the same way on another.*

**What you'll notice:** the same prompt gets the same fingerprint, screen result and path decisions on any
of the three systems; rules that exist for one system (Windows trailing-dot names in CFG-3, POSIX file
permissions) are tested on that system. The tests run in CI for any PR touching `plugins/promptlibrary-kit/`,
so the cost of macOS and Windows runners applies only when the plugin changes.

Source: V4 §Acceptance; owner decision 2026-11-17. State: **partial** (Linux: in CI since 51fc2b13;
Windows: local runs only, the Windows CI job covers other tests; macOS: never run). Confirmed: yes
(2026-11-17).

### QA-2: The plugin has really been run, end to end, before each release

*As a developer, every release of the plugin has been run live, end to end, from a marketplace install
(setup, add, review, activate, look up, run, including a remembered approval), with the run recorded, so
that what I install has worked outside its development checkout.*

**What you'll notice:** problems only an install shows (a wrong plugin path, a missing permission grant, a
skill that does not load) are found before release, not by you. Trade-off you accepted: a live run takes a
person about half an hour per release and cannot be fully automated, because the approval questions need a
human.

**Changes to earlier decisions:** V5 H1 asked for one live run; this makes it a per-release check from a
marketplace install, not only from `--plugin-dir`.

Source: V5 H1; owner decision 2026-11-17. State: **partial** (`--plugin-dir` runs 2026-10-14; no
marketplace install, no per-release record). Confirmed: yes (2026-11-17).

### QA-3: The reviewer is reached when it should be, and only then

*As a developer, `/prompt-library` always reaches `prompt-reviewer` by name at its review step, and a
direct request about a stored prompt reaches it too, while unrelated review requests never do, checked by a
trigger test (or, while that tool is broken, a recorded dry run of the trigger phrases), so that every
prompt is reviewed and the reviewer never takes over other work.*

**What you'll notice:** inside `/prompt-library` the review always happens, because the skill calls the
reviewer by name (what REV-1 relies on). Outside it, "review the stored prompt X" reaches the reviewer,
while "review this PR" or a code review does not.

Source: V5 H2; code (`prompt-library` step 7, `Agent(prompt-reviewer)` grant); owner decision 2026-11-17.
State: **partial** (by-name call: met; description check: not met, the trigger-test tool crashes, #460).
Confirmed: yes (2026-11-17).

### QA-4: The plugin needs nothing but Python's standard library

*As a developer, the plugin's scripts, including any future hook, use only Python's standard library and
carry the `plib` prefix (apart from the standard `smoke_test.py` files), so that installing it brings in no
third-party code and its files are easy to recognize.*

**What you'll notice:** nothing to install beyond `uv` (CFG-5), no dependency supply chain, nothing that
breaks when a package index is unreachable. Trade-off you accepted: no ready-made libraries, so a YAML
parser or a regex engine with timeouts (CFG-7 bounds its project patterns with a worker process instead) is hand-written or done
without.

**Changes to earlier decisions:** drops the draft's alternative `promptlib` prefix, which no file uses.

Source: V4 §Plugin Conventions; README §Language; owner decision 2026-11-17. State: met (hook: not built,
PUR-4). Confirmed: yes (2026-11-17).

## 12. Deferred (planned later, must stay possible) (DEF)

### DEF-1: General prompts I can use in every repository (later)

*As a developer, I can later keep prompts that serve every repository in a separate general catalog
(`scope: general`), with the same record format, fingerprints, review and approvals as my project prompts
and no attached files, so that adding general prompts never forces a change to my existing project
prompts.*

**What you'll notice:** nothing today; every prompt is a project prompt (PUR-5). Once it arrives, general
prompts go through the same review, screening and approvals. They carry no attachments, because attached
files are project files (CAT-2) and loading different files per repository would break LIF-7. How the two
catalogs combine is DEF-4's open question. A general catalog sits outside the project, which CFG-3 forbids
for project catalogs, so its location rules and security review (SEC-6) are designed with the feature.

**Changes to earlier decisions:** V4's "without changing the record format or hashes" now means the
fingerprints as extended by CAT-2 (attachments) and SEC-4 (origin); general prompts are limited to no
attachments.

Source: V4 §Deferred, §Extension Seams; owner decision 2026-11-17. State: deferred. Confirmed: yes
(2026-11-17).

### DEF-2: Running stored prompts in Codex (later)

*As a developer, I can later run stored prompts in Codex too, approved separately for Codex (once or
remembered), only in an interactive Codex session I'm watching, and with every approval for every executor
ending when the prompt changes, so that approving a prompt for Claude never lets it run somewhere else.*

**What you'll notice:** nothing today; Codex cannot run stored prompts (EXE-7). Once it arrives, each
prompt needs its own Codex approval, remembered approvals are kept per executor (EXE-4, PUR-3), runs are
interactive only (EXE-7) with no extra powers (EXE-6), and a text change ends the approvals for every
executor. Trade-off you accepted: a prompt used in both places is approved twice.

Source: V4 §Deferred, §Extension Seams; EXE-4, EXE-7; owner decision 2026-11-17. State: deferred.
Confirmed: yes (2026-11-17).

### DEF-3: Notion as the main library for its scope (later)

*As a developer, once Notion support arrives, I can start a sync that shows me every change from Notion's
configured scope and applies only what I accept; an accepted change becomes the active version without a
separate review or activation approval, is still screened for secrets, and is shown in full before its
first run in my session, never writing back to Notion and never silently overwriting a local edit, so that
a team can share prompts through Notion without approving every edit twice.*

**What you'll notice:** nothing today (blocked on #267). Once it arrives: `/prompt-sync` is user-invoked
and lists each change next to your current version; accepting it is the approval. A secret in synced text
is a hard stop (SCR-1); origin is recorded as `notion`. Because the text changed, its next run shows the
full text and asks *Run once / Run and remember* (PUR-3, EXE-3), and remembered approvals for the old text
end (LIF-2). Trade-off you accepted: anyone who can edit the Notion page decides what becomes active; you
see each change in the sync and again in full before its first run, but no reviewer checks it.

**Changes to earlier decisions:** adds a Notion-sync exception to PUR-2, REV-1, LIF-1 and INT-2, and a
seventh origin `notion` to INT-1 (amendment notes there); the run approval is unchanged. The owner chose this over synced changes arriving as untrusted
drafts.

Source: V4 §Wave 1; V5 §3; PUR-5; owner decision 2026-11-17. State: deferred, blocked (#267). Confirmed:
yes (2026-11-17).

### DEF-4: Two catalogs never make a name ambiguous (later)

*As a developer, once I have more than one catalog, a prompt name found in more than one of them never
silently picks one: nothing runs until I choose, and each approval belongs to one catalog's prompt, so
that adding a catalog can never change which text a name runs.*

**What you'll notice:** nothing today. Once general prompts exist (DEF-1), a name found in one catalog runs
as usual; a name found in both runs nothing and shows where each comes from; lookups mark each entry with
its catalog. Notion prompts sync into the project catalog (DEF-3) and add no third catalog. Still open,
designed with DEF-1: whether one catalog may take precedence, how a command names a catalog, and whether a
conflict is blocked when a prompt is saved. Trade-off you accepted: a conflict blocks the run until you
resolve it.

**Changes to earlier decisions:** narrows V4's "deliberately not designed" by one fixed point, taken from
LIF-5.

Source: V4 §Extension Seams; LIF-5; owner decision 2026-11-17. State: deferred. Confirmed: yes
(2026-11-17).

## 13. Behavior in code that V4 never stated (CODE)

Each is either covered by a confirmed requirement above or recorded as an implementation detail (resolved
with the owner, 2026-11-17).

| ID | Behavior | Where | Resolution |
|---|---|---|---|
| CODE-1 | Catalog may not sit in `.git`, `.github` or Claude Code config folders | validator `FORBIDDEN_ROOTS` | Covered by CAT-7 |
| CODE-2 | Hidden-character reporting in every text display and approval | validator, all three skills | Covered by RET-4 |
| CODE-3 | Secret screen also blocks `claude` and `codex` text, and re-screens at every later step | validator | Covered by SCR-1, SCR-3 |
| CODE-4 | Email screen with git-remote and example-domain exemptions | branch | Covered by SCR-5 |
| CODE-5 | `review-path` record-path gate for the reviewer | branch | Mechanism of REV-6 |
| CODE-6 | Atomic writes and rollback of a partly failed status move | validator | Covered by CAT-6 |
| CODE-7 | `discard-orphan` repair offer for an orphan from an interrupted draft | prompt-library step 1 | Covered by CAT-6, LIF-8 |
| CODE-8 | `--expect-sha256` binding an approval to the shown text | validator | Mechanism of LIF-7 |
| CODE-9 | Input files read only from the catalog or the system temp directory | validator | Implementation detail (supports SEC-5, CFG-3) |
| CODE-10 | Shared token-shape list with `analysis-kit` (`plib-token-shapes.json`) | scripts | Mechanism of SCR-4 |
