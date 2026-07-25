# Trigger Judgment

**User prompt:** "improve this plugin based on the retro"

## (1) Would this description trigger the skill?

**Yes.**

The description's "Use when..." clause lists this exact phrase, verbatim, as a trigger example:

> Use when the user asks to **"improve this plugin based on the retro"**, "enhance this plugin compared to X", ...

Since the user prompt is a literal, word-for-word match of one of the explicitly enumerated trigger phrases, this is as strong a semantic match as a description can produce — no inference or generalization is required. Additionally, the broader framing reinforces the match: the skill is described as "Orchestrates ongoing maintenance for an already-built plugin through three workflows — retro-driven improvement...", and the prompt's reference to "the retro" aligns directly with a retrospective/retro-driven-improvement intent. The description also mentions wanting to "act on findings from analyzing-sessions ... rather than just reading a report," which matches the implied intent of "improve ... based on the retro" (i.e., take action on retro findings, not just review them).

## (2) Which workflow matches?

**`improve-a-plugin.md` (retro-driven improvement).**

Reasoning:
- The skill explicitly maps its three workflows to three trigger categories: retro-driven improvement, comparison-driven enhancement, and dev-rules/docs-modernization.
- "based on the retro" directly signals the retrospective/analyzing-sessions source of findings, not a comparison against another plugin (`enhance-a-plugin.md`, which is comparison-driven and triggers on phrasing like "enhance this plugin compared to X") and not the docs-modernization workflow (`self-upstream-plugin-devkit.md`, which triggers on phrasing like "check plugin-devkit's rules against upstream docs" or "keep plugin-devkit current with the platform docs").
- The description's own example ordering pairs "improve this plugin based on the retro" with the first-listed workflow, "retro-driven improvement," confirming the mapping to `improve-a-plugin.md`.
