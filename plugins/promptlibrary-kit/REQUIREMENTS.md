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
    back through review and approval.
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
size limit (value still open, see CAT-2), and are still reviewed, fingerprinted and previewed.

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
| **One prompt:** its text (or, per CAT-2, an attached file) no longer matches its approval fingerprint | Only that prompt is unavailable, shown as "changed since approval" with the reason; everything else keeps working. |

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
  and changed. The affected prompt can only be restored from git, never revised from its unapproved text
  (that would turn an outside edit into an approved new version).
- Nothing is ever repaired silently.

**Changes to earlier decisions:** V4 §Interrupted updates and today's code refuse every change while any
validation problem exists. This keeps that for structural problems and narrows it to the one prompt for a
fingerprint mismatch.

Source: V4 §Interrupted updates; code (atomic writes, rollback, orphan removal); owner decision
2026-11-16. State: **partial** (structural handling met; per-prompt blocking not met). Confirmed: yes
(2026-11-16).

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
example (CAT-1); you never choose it by hand.

**Changes to earlier decisions:** extends V4's five origins with `example` (decided in CAT-1).

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

Source: V4 §Import review; code (extended to `claude`, `codex`). State: met. Confirmed: yes (2026-11-16).

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
they are stored and in what format is decided in Area 10 (CFG).

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
(`git@github.com:org/repo.git`) and reserved example addresses (`example.com`, `.net`, `.org`, and the
`.example`, `.test`, `.invalid`, `.localhost` endings) pass. The trade-off: a prompt that really needs a
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

Source: V4 §Quality review; owner decision 2026-11-16. State: **partial** (review and acknowledgment: met;
no-review-no-activation: not met, the skill offers to continue without a review). Confirmed: yes
(2026-11-16).

### REV-2: Imported and AI-written text is checked for hidden instructions

*As a developer, prompts from a session or the web get the full import review with its own approval, and
prompts written by Claude or Codex are also checked for hidden instructions and for doing more than their
description says, so that instructions picked up from outside text are caught whichever way they arrive.*

**What you'll notice:** for `session` and `web` prompts the reviewer checks for injection-like text aimed
at the agent (ignore rules, exfiltrate, call tools, fetch more, act outside the purpose), provenance
(`source_ref` complete, license or attribution noted) and scope fit, and you approve the import review
separately from the quality review. For `claude` and `codex` prompts the reviewer runs the same
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

Source: V4 §Verification record; code. State: **partial** (text: met; attachments in the fingerprint: not
met, CAT-2). Confirmed: yes (2026-11-16).

### LIF-2: Any change to approved content cancels the approval, except line endings

*As a developer, any change to an approved prompt's content (its text or an attached file), however small,
cancels its approvals, while a change of line endings alone does not, so that what runs is always exactly
what I approved and a checkout on another operating system does not break my prompts.*

**What you'll notice:** a typo fixed directly in the file makes the prompt count as changed: it is blocked
on its own until restored (CAT-6), and a real change goes through revise, review and approval. Windows and
Unix line endings give the same fingerprint, so a checkout on another system keeps every approval.
Whitespace and spelling changes are not exempt.

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
new version (for example v4) after review and approval.

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

**What you'll notice:** a list shows only active prompts unless you ask for drafts, deactivated or older
versions. A search also finds a prompt by a phrase inside its text, and each result says whether it matched
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
the catalog during unrelated work, which V4 did not do.

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
