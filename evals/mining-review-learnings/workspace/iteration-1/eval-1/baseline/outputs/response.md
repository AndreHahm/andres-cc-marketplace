# Review-Learnings Mining — PR #172 (explicit-PR-list mode)

## Task

Cross-check GitHub's real review history for PR #172 (AndreHahm/andres-cc-marketplace, merged
2026-08-28, `feat(git-kit): add github-issue-lifecycle skill for freestanding issue work`) against
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s existing content, and determine whether there is a new,
generalizable pattern-learning candidate for PR #172 that isn't already captured there.

## Method

- Fetched PR #172's full review history via `gh api repos/AndreHahm/andres-cc-marketplace/pulls/172/reviews`
  and `.../pulls/172/comments` (paginated).
- Read `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` in full (1204 lines), including its existing
  `## PR #172` section (lines 1011-1042) and the Master pre-push checklist (lines 1045-1204).
- Grepped the whole document for keywords tied to each real PR #172 finding (`substring`, `manifest`,
  `version bump`, `body-file`, `duplicate-of`, `Write.*grant`, `open-question`, etc.) to check for
  coverage elsewhere in the document, not just inside its own PR #172 section.

## Real review findings on PR #172 (from GitHub, not from the doc)

Reviewers: `devin-ai-integration[bot]` (no issues found), `coderabbitai[bot]` (1 actionable comment),
`chatgpt-codex-connector[bot]` (2 review rounds, on commits `2c12b9f4c2` and `de364938ed`). All findings
below were real and fixed by `AndreHahm` in commits `de36493` (round 1) and `30352d7` (round 2 follow-up).

1. **CodeRabbit** — `.agents/skills/github-issue-lifecycle/scripts/smoke_test.py:33` (and 2 mirror
   copies): `"name:" in fm` / `"description:" in fm` frontmatter checks match substrings like
   `skill-name:`/`long-description:`, so the smoke test can pass even when the real `name`/`description`
   key is absent. Fixed by anchoring to `^name:\s*\S`/`^description:\s*\S` non-comment YAML lines.
2. **Codex P1** — `.claude-plugin/marketplace.json:27`: PR adds a release-worthy skill but leaves both
   `plugins/git-kit/.claude-plugin/plugin.json` and the marketplace entry at `1.0.0-alpha.3`, which (per
   this repo's own `versioning-and-distribution.md:102-109,157-159`) means `claude plugin update` treats
   the code as unchanged and existing installs never receive it. Fixed by bumping both to
   `1.0.0-alpha.4`.
3. **Codex P1** — `plugins/git-kit/skills/github-issue-lifecycle/workflows/work-an-existing-issue.md:62`:
   generated comment/title/search text interpolated inside a Bash double-quoted `gh` argument is a
   shell-injection surface (`$(...)`/backticks aren't neutralized by double quotes). Fixed by switching
   to `gh issue comment -F/--body-file` from a scratchpad file across all 3 mirrors, plus the same swap
   in `resolve-an-issue.md`.
4. **Codex P2** — `plugins/git-kit/skills/github-issue-lifecycle/workflows/resolve-an-issue.md:12`: a
   direct "resolve issue #N" entry routes straight to Workflow 3, but Workflow 3's own open-question gate
   never fetches fresh issue comments (`gh issue view --comments`) — only Workflow 2 did, so the gate can
   fire against stale/absent state on this entry path. Fixed by making the `--comments` fetch Workflow 3's
   own Step 1.
5. **Codex P2** — `plugins/git-kit/skills/github-issue-lifecycle/workflows/resolve-an-issue.md:23`: a
   "duplicate" Declined reason was folded into the generic `not planned` close path, discarding GitHub's
   native duplicate-issue link. Fixed with a dedicated `--reason duplicate --duplicate-of <canonical>`
   branch.
6. **Codex P2** (round 2, on commit `de364938ed`, i.e. a *regression from round 1's own fix*) —
   `plugins/git-kit/skills/github-issue-lifecycle/SKILL.md:14`: after round 1 switched Workflows 2/3 to
   `--body-file`, the skill's `allowed-tools` still omitted `Write` and its own Boundaries section still
   claimed "this skill holds no Write grant" — an unexpected permission escalation that blocks headless/
   default-deny use. Fixed by adding `Write` to `allowed-tools` and correcting the now-stale Boundaries
   prose, across all 3 mirrors.

## Cross-check against the existing document

`THIRD_PARTY_REVIEW_LEARNINGS.md` already has a `## PR #172` section (lines 1011-1042, "Codex, 2 rounds")
covering exactly **2 of these 6 findings**:

- Finding 5 (duplicate-of) → documented as "Pattern: `gh issue close` has a dedicated reason/flag for each
  closure type, not just one generic path" (lines 1013-1028).
- Finding 3 (shell-injection / `--body-file`) → documented as "Pattern: untrusted issue/comment text in a
  Bash double-quoted `gh` argument is a shell-injection surface, not a style nit" (lines 1030-1041).

The other 4 real findings are absent from the PR #172 section. Checking each against the *rest* of the
1204-line document (not just its own section) to see if they're recurrences of an already-named pattern:

- **Finding 1 (frontmatter substring match)** — not a new *shape*. The document already has a broader,
  well-developed theme that "a substring/membership check (`X in string`) is unsound for a structural or
  security decision" — most explicitly PR #88's headline pattern ("a substring-matching security carve-out
  is not a defensible boundary," lines 848-878) and PR #55's checklist item 6 ("don't scan the whole
  trailing argument blob for a signal... split into real argument boundaries first," line 224). Finding 1
  is a milder, non-adversarial instance of the same root cause (unanchored substring match → false
  positive/negative), just applied to YAML frontmatter validation instead of a security carve-out or regex
  scope. Recurrence, not new.
- **Finding 4 (stale-state gate on an alternate entry path)** — not a new shape. This is a direct instance
  of the already-documented PR #79 pattern: "when a new mandatory gate is inserted... don't stop at fixing
  the one path that motivated the gate — enumerate every entry path that can reach Y" (lines 695-717). Here
  the "gate" is the open-question check and the "entry path" is direct-invocation-of-Workflow-3 vs.
  Workflow-2-then-3. Recurrence, not new.
- **Finding 6 (Write-grant regression from round 1's own fix)** — not a new shape. This is a direct
  instance of PR #54's already-documented "Pattern 4: A tool grant added mid-edit needs to be checked in
  the same edit, not a later pass" (lines 95-103), reinforced by the Master checklist's own item "Every new
  `Bash(...)`/`Skill(...)` call added: is its exact matching grant already in `allowed-tools`, checked in
  this same edit?" (line 1142). It also compounds with the already-documented "stale prose in another
  section of the same file after a behavior change" theme (PR #54 Pattern 6, PR #79's "Confirms" section).
  Recurrence (worth noting the checklist item's own wording only names `Bash(...)`/`Skill(...)` grants, not
  `Write`, but that's a wording-completeness nit, not a new pattern).
- **Finding 2 (missing plugin/marketplace manifest version bump)** — genuinely absent. I grepped the whole
  document for `manifest`, `version bump`, `plugin.json.*version`, `claude plugin update`, `installation`,
  and the only hits are unrelated (`installed_plugins.json` appears once, in PR #54's Pattern 7, about
  querying install state for a *different* purpose — detecting whether a plugin is enabled, not whether a
  manifest version was bumped). No pattern anywhere in the document addresses: shipping a release-worthy
  component change without bumping the plugin's own `plugin.json` version (and its marketplace-entry
  mirror), which silently prevents `claude plugin update` from delivering the change to existing
  installations. This is a distinct, generalizable, and consequential lesson — it isn't a "does the code
  work" bug, it's a "does the fix actually reach anyone who already installed the plugin" release-hygiene
  gap, a category the document doesn't cover at all yet.

## Conclusion

**Yes — there is one new, generalizable pattern-learning candidate for PR #172 that is not yet captured in
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`: the missing plugin/marketplace manifest version bump.**

Evidence (PR #172, Codex P1 review comment on `.claude-plugin/marketplace.json:27`, commit `2c12b9f4c2`):

> "This adds a release-worthy skill while leaving both `plugins/git-kit/.claude-plugin/plugin.json` and
> this marketplace entry at `1.0.0-alpha.3`. The repository's versioning guide at
> `plugins/plugin-devkit/skills/plugin-development/references/versioning-and-distribution.md:102-109`
> states that an explicit unchanged version makes `claude plugin update` treat changed code as unchanged,
> so existing git-kit installations will not receive this feature. Bump the version in both manifests as
> required by that guide's lines 157-159."

Confirmed real and fixed (`AndreHahm`'s reply on the same thread, commit `de36493`): "Bumped
`plugins/git-kit/.claude-plugin/plugin.json` and this marketplace entry to `1.0.0-alpha.4`... verified
against its real git history: alpha.1 -> alpha.2 -> alpha.3 across prior releases."

**Proposed pattern write-up (for a maintainer to add to the document, not applied by this task):**

> ### Pattern: a release-worthy change needs its plugin manifest version bumped, or existing installs never
> receive it
>
> **What happened:** PR #172 added a brand-new skill (`github-issue-lifecycle`) to `git-kit` but left both
> `plugins/git-kit/.claude-plugin/plugin.json` and the mirroring `marketplace.json` entry at the same
> version (`1.0.0-alpha.3`) they had before the change. Per this repo's own
> `versioning-and-distribution.md`, `claude plugin update` compares the manifest version to decide whether
> there's anything new to pull — an unchanged version means an already-installed copy of `git-kit` silently
> never receives the new skill, even though the code shipped and merged correctly.
>
> **Rule:** any PR that adds/changes a shippable plugin component (a skill, agent, command, or hook a user
> would expect to receive via `claude plugin update`) must also bump that plugin's own `plugin.json`
> version and its `marketplace.json` mirror, in the same PR — not as a follow-up. Check this explicitly
> before finalizing any plugin-devkit change that adds or materially changes a component, the same way
> `plugin-rulebook-enforcement.md`'s R20 already checks for other kinds of stale-mirror drift.

The other 3 findings absent from the PR #172 section (frontmatter substring match, stale-state gate on an
alternate entry path, Write-grant regression from round 1's own fix) are all real, but each is a
recurrence of an already-documented pattern elsewhere in the file (PR #88's substring-matching theme, PR
#79's multi-entry-path gate theme, and PR #54's Pattern 4 / grant-added-mid-edit theme, respectively) —
not new pattern-learning candidates in their own right.
