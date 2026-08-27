# Conception Classification — Auto-Generate README on Every Commit

Applying `plugin-conception`'s Entry Route A (from-scratch suggestion) normalize → classify → shallow-overlap process.

## Step 1: Normalize Intent and Evidence

- **Problem or opportunity (as stated):** plugin READMEs can drift out of date as a plugin's components
  change; the requester wants README content regenerated automatically so it never goes stale.
- **Target user and scenario:** a plugin-devkit maintainer who commits a change to a plugin's
  skills/agents/commands/hooks and wants the plugin's README to reflect that change without a separate,
  remembered manual step.
- **Desired outcome:** the README stays accurate relative to the plugin's actual current component set,
  with no manual trigger required.
- **Proposed mechanism (not the need itself):** a new plugin-devkit feature that regenerates the README on
  every `git commit`.
- **Constraints/non-goals:** not stated by the requester; not yet explored, since Step 2's classification
  makes that exploration unnecessary (see below).

**Assumption labeled:** the requester is treating "auto-generate on every commit" as the solution, not as
the underlying need. The underlying need is "README accuracy stays current with the plugin's real state,"
which is a narrower thing than "something runs on every commit regardless of whether docs need it."

## Step 2 + Step 3: Classify, Then Verify Against Current Repository State

Per this skill's rule, I did not trust the requester's framing or an unverified assumption of a gap — I
re-checked `plugins/plugin-devkit/skills/plugin-documentation/SKILL.md` (this worktree's current copy)
directly rather than reasoning from memory.

**What actually exists today**, confirmed by reading the file:

- `plugin-documentation` already authors and updates a plugin's README (and other human-facing docs) from
  the plugin's actual current `plugin.json` + component frontmatter as the sole source of truth (Step 2 of
  that skill), explicitly to avoid invented or stale claims.
- Its own "When to Use" section already names the exact trigger the requester is asking for: *"Updating an
  existing human-facing doc after components were added, removed, or changed (a stale skill/agent/command
  count, a missing new capability, an outdated example)"* and *"after building or modifying plugin
  components when their docs need to reflect the change."*
- It has a **delta-check flow** purpose-built for the "small, enumerable change" case (Step 4): for a count
  bump, a new table row, or a single capability added/removed, it runs a cheap, targeted re-verification of
  just the changed claims (via `human-doc-reviewer` in delta mode) instead of a full whole-surface review —
  the same shape as "regenerate the README to reflect what just changed."
- It is already wired into the pipeline: `plugin-lifecycle-downstream`'s Document phase invokes it
  automatically with a changed-claim list after fixes are applied, so documentation updates already happen
  as a matter of course after a component change moves through the existing lifecycle, not only on a
  standalone ad hoc request.
- Its own Gotchas explicitly protect against the failure mode a naive "regenerate on every commit" hook
  would introduce: *"Don't overwrite human-added content on an update pass... A full silent rewrite is a
  worse outcome than a slightly-stale doc."* An unconditional every-commit regeneration is exactly the kind
  of blind full-rewrite trigger this existing skill was deliberately designed to avoid.

**Overlap check (repository-metadata depth, per Step 3):**

| Candidate / neighbor | Location | Relationship | Overlap | Required action |
|---|---|---|---|---|
| `plugin-documentation` | `plugins/plugin-devkit/skills/plugin-documentation/SKILL.md` | Same capability domain (README currency) | **Full** | Stop |
| `plugin-lifecycle-downstream` Document phase | `plugins/plugin-devkit/skills/plugin-lifecycle-downstream/` | Existing lifecycle owner that already invokes `plugin-documentation` post-fix | Full | Stop |

No partial gap survives: the requested outcome (README stays current) is already delivered by an existing,
already-integrated component, and delivered more safely than the proposed mechanism (it targets only actual
changed claims and preserves human-added content, rather than blindly regenerating on every commit
including commits that touch nothing documentation-relevant).

## Classification: **Retain**

> Current behavior is adequate; no implementation is justified.

**Rationale:** The proposed feature is a mechanism (auto-run on every commit), not a validated gap in
outcome. The underlying need — README content tracking the plugin's real current state — is already met by
`plugin-documentation`'s existing author/update flow and its delta-check mode, invoked either directly or
automatically via `plugin-lifecycle-downstream`'s Document phase after component changes. Building a new
plugin-devkit feature to force README regeneration on *every* commit would (a) duplicate an existing,
already-integrated capability, and (b) be strictly worse than what exists today, since an unconditional
every-commit trigger has no way to distinguish "a commit that changed a component's public surface" from
"a commit that didn't," and risks the exact silent-overwrite failure mode `plugin-documentation` already
guards against.

If there is a real residual gap, it is narrower than what was proposed: *"nothing currently fires
`plugin-documentation` automatically outside the `plugin-lifecycle-downstream` pipeline — a standalone
commit made outside that pipeline doesn't trigger a doc-currency check."* That is a much smaller, different
question (should `commit`/`git-kit` gate on doc-currency the way it already gates on behavior-change
testing?) than "auto-generate READMEs on every commit," and isn't evidenced here — no friction or
occurrence of a stale README from a standalone commit was reported. Per this skill's Step 1 rule, no
evidence should be fabricated to manufacture a gap that wasn't actually reported.

## Step 7: Decision and Stop

Per the classification table, **Retain → stop; no downstream hand-off.** Per Testing & Validation scenario
7 ("Retain/no-work outcome"), this stops cleanly with stated rationale and **no Conception Brief is
written** — a Retain outcome doesn't warrant the ceremony of Steps 4-6 (Scope/Baseline/Implementation
Plan), since there is no implementation to plan.

**Recommendation to the requester:** if the actual pain point is "a standalone commit outside the guided
pipeline can leave docs stale," that's worth raising as its own, narrower candidate — most plausibly an
Enhance against `commit`/`git-kit` (an optional doc-currency prompt, mirroring its existing
behavior-change-test gate) rather than a new plugin-devkit auto-generation feature. That would need its own
classification pass with real evidence of the gap, not bundled into this one.
