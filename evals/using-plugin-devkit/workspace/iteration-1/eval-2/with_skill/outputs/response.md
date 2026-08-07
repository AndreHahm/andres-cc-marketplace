# Task

User request: "Run plugin-lifecycle-upstream to build a new skill for handling CSV validation."

Skill under test: `using-plugin-devkit` (guided front door for plugin-devkit).

# Step 0: Does `using-plugin-devkit` even apply here?

Before running Phase 1, I checked whether this skill's own scope covers this request at all — its frontmatter and body both address this directly.

From the frontmatter description:
> "Not for requests that already name a specific skill or pipeline, or a single already-known fix — those skip this front door and go straight to the named skill."

From the "When NOT to Use" section:
> "**Already know the exact skill or pipeline** — invoking it directly (e.g. `Skill(skill-development)`, `Skill(plugin-lifecycle-upstream)`) skips this extra confirmation gate"

The user's request explicitly names the pipeline: "Run **plugin-lifecycle-upstream**..." This is not a vague "help me build a plugin" or "where do I start" — it is a request that already names the specific pipeline by its exact skill name. The skill's own documentation uses `Skill(plugin-lifecycle-upstream)` as its literal example of the case that should bypass this front door.

Also relevant: the "When to Use" section requires "The request names no specific plugin-devkit skill or pipeline" — which is false here, since `plugin-lifecycle-upstream` is named.

**Conclusion: `using-plugin-devkit` does not apply to this request.** Its entire job is to help a user pick between three lifecycle pipelines (or a lighter alternative) when they haven't already named one. Here that selection work is already done by the user. Running Phase 1's `AskUserQuestion` picker ("Build something new / QA or audit / Fix or improve / Not sure") would be redundant theater — asking the user to re-derive an answer they already gave in their own request — and Phase 2's confirmation gate exists specifically to catch a *wrong* pipeline choice made *by this skill's own Phase 1 logic*, which never ran here since Phase 1 itself is skipped.

# What I would do instead

Per the skill's own instruction, this request skips the front door and goes straight to the named skill. The correct action is to invoke `Skill(plugin-lifecycle-upstream)` directly, passing through the user's actual request ("build a new skill for handling CSV validation") as its argument.

**This is the point where I would invoke `Skill(plugin-lifecycle-upstream)`** with argument roughly: "build a new skill for handling CSV validation." I am not actually invoking it per the test instructions — stopping here.

One secondary note, not part of `using-plugin-devkit`'s own logic but worth flagging since it surfaced during the check: `plugin-lifecycle-upstream`'s own description says "For a single already-known component, use the matching Design skill directly instead of this pipeline" (i.e., `skill-development` for a single skill). Whether "a new skill for handling CSV validation" counts as a single already-known component (skip to `skill-development`) or genuinely needs Ideate/Plan/Design/Build/Test is a judgment call that belongs to `plugin-lifecycle-upstream` itself once invoked, not to `using-plugin-devkit` — the user's request explicitly said "Run plugin-lifecycle-upstream," so that pipeline (and any internal redirect it chooses to make) is the right place for that decision, not this front door.

# Answer to give the user

Since the user already named the exact pipeline, no `AskUserQuestion` call from `using-plugin-devkit` is warranted (per its own "When NOT to Use" rule). I would tell the user:

"Your request already names the pipeline (`plugin-lifecycle-upstream`), so `using-plugin-devkit`'s picker doesn't apply here — going straight to `plugin-lifecycle-upstream` as requested, to build the CSV-validation skill."

No `AskUserQuestion` was called, in Phase 1 or Phase 2, because both phases are gated behind first confirming the front door applies, and it does not.
