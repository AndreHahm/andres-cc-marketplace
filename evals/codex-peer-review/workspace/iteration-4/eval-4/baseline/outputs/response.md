**Routing decision: not codex-peer-review.**

The request is a second-opinion review of the working diff before a PR is opened. The skill's own text sends that to git-kit's `cross-model-review`, not to this skill:

- Scope line: "For a two-vendor review of the working diff before a PR, use git-kit's cross-model-review instead."
- When NOT to Use: "A two-vendor review of the working diff as a gate before a PR is created or a draft is flipped to ready → git-kit's `cross-model-review`."
- Tie-break: "a diff, branch or PR named with no Codex-only ask goes to `cross-model-review`." Your request names a diff and no Codex-only question, so it falls under this rule.

This skill is a Codex-only check of Claude's own position. It does not perform the diff gate, even when code changes are attached.

**Where it should go:** `cross-model-review` (git-kit). In this session only codex-kit is installed, so that target is unavailable. The skill text gives no fallback for a missing `cross-model-review`. Its only explicit fallback is for decision-kit's `consulting-decision-model`, and there it says the skill "still does not take it on." The same reasoning applies here: codex-peer-review should not take on the diff gate as a substitute. Report that the pre-PR diff review cannot be run here, and install git-kit to get `cross-model-review`.

**What this skill would do instead:** only a Codex-only question about a position Claude has formed (a design, analysis or recommendation), dispatched through a subagent. A pure "review my diff" request does not qualify.
