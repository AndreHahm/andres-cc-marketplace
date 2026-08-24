## Issues found

**1. Description doesn't follow required format (Validation Rules table)**
`description: reviews documentation for accuracy` fails the spec: descriptions must "start with 'Use this agent when...'" and read as one clear sentence describing trigger conditions. This one is a bare noun-phrase fragment with no trigger language, so nothing tells the dispatcher *when* to invoke it (vs. just what it does). Should be something like: `Use this agent when documentation has been created or changed and needs an accuracy review.`

**2. Tool scoping violates least-privilege for a read-only reviewer (`tools` field)**
The skill states explicitly: *"Read-only reviewer/analysis agents must not receive Bash, Write, or Edit — restrict to Read, Grep, Glob unless there is a specific, justified need."* This agent's own system prompt describes exactly that role — "Read the docs and report accuracy issues" — yet its `tools` list includes both `Write` and `Bash`:
```yaml
tools: ["Read", "Grep", "Glob", "Write", "Bash"]
```
Neither `Write` nor `Bash` is justified by the stated job. This is the "unnecessary tool permissions" anti-pattern the skill's Best Practices section calls out directly ("DON'T: Unnecessary tool permissions"). Correct scoping should be `["Read", "Grep", "Glob"]`.

**3. Scope creep in the system prompt drives the over-broad tools grant**
The body instructs the agent to write its review to `./outputs/review.md`, "save all outputs to ./outputs/", and fabricate a `./timing.json` containing `total_tokens`, `duration_ms`, and `model`. This is why `Write`/`Bash` were added — but it's outside the agent's one-sentence job ("reviews documentation for accuracy"), violating "One agent, one job." It's also asking the agent to report metadata (its own total token count, wall-clock duration) that a system-prompt-driven agent has no reliable way to know — it can only fabricate those numbers, which is a bad instruction regardless of tool scoping.

**4. Relative output paths (repo-root scratch-file risk)**
`./outputs/review.md`, `./outputs/`, and `./timing.json` are bare relative paths with no directory validation. Per this repo's own scratch-file conventions, a relative path like this resolves to whatever the agent's cwd happens to be — frequently the repo root — producing untracked clutter outside any gitignored location. Even setting aside whether this agent should be writing files at all, the paths as written aren't safe.

**5. Fields that do pass validation**
- `name: doc-checker` — valid (lowercase, hyphenated, 11 chars).
- `model: inherit` — valid.
- `color: blue` — valid (one of the 8 allowed values).

## Recommended fix
- Rewrite `description` to start with "Use this agent when..." and state the trigger condition.
- Drop `Write` and `Bash` from `tools`, leaving `["Read", "Grep", "Glob"]`.
- Remove the "Write your review to ./outputs/review.md", "save outputs", and "create ./timing.json" instructions from the body entirely — a reviewer agent should return its findings as its response, not write files or self-report fabricated usage metrics. If output-to-file is genuinely needed, that's a separate, justified design decision requiring an explicit absolute/gitignored path and a corresponding tool grant — not the default.
