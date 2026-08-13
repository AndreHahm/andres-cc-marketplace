# Double-Check Evaluation Framework

Shared evaluation methodology for codex-kit's task/review skills. Every skill reads this after receiving Codex output.

## Peer AI Evaluation

Treat Codex as a peer, not an authority. For each finding, classify into exactly one of five categories:

- **Agree**: Confirm with additional context if useful
- **Disagree**: Explain why with evidence — read the actual code first
- **Nuance**: Add context Codex may have missed
- **False Positive (hallucination)**: the cited file/function/line does not exist in the current source tree
- **Uncited — verification deferred**: the finding has no concrete citation to check against

### Rules

- Do NOT blindly agree. Codex can hallucinate file paths, line numbers, and function names.
- Always read the actual code to verify claims about specific files before agreeing or disagreeing.
- In Phase 4, read only what Codex cited — never whole files "for context".
- If you genuinely disagree, present both perspectives and let the user decide.
- Preserve Codex output verbatim. Claude's evaluation comes AFTER, not instead of.
- Frame disagreements as peer discussion, not correction.

## Self-Bias Awareness

When reviewing code that Claude authored earlier in the session:
- Explicitly acknowledge: "Note: I authored some of this code, so I may have blind spots."
- Be extra honest about Codex's findings. Don't rationalize away valid catches.
- Default to treating Codex findings as valid unless you can prove otherwise with code evidence.

## Agreement Level

After evaluating all findings, report a one-line agreement summary:

| Level | Criteria |
|-------|---------|
| **High** | >80% findings agreed, no critical disagreements |
| **Partial** | 50-80% agreed, or disagreements on non-critical items |
| **Disagreement** | <50% agreed, or disagreement on critical findings |

Include in the summary: `Agreement: High (5/6 findings agreed)`

## Cross-Model Comparison

If Claude already analyzed the same scope earlier in the conversation:

| Finding | Claude | Codex | Agreement |
|---------|--------|-------|-----------|
| [issue] | Found  | Found | Both      |
| [issue] | Missed | Found | Codex only |
| [issue] | Found  | Missed | Claude only |

## No Auto-Fix Rule

After presenting results, **do not automatically fix or modify code**. The user must explicitly request changes.

Correct flow: present findings → wait for user → fix only what they ask for.

## Save Results

Write combined output to `${CLAUDE_PLUGIN_DATA}/reviews/<type>-<YYYYMMDD-HHMMSS>.md`.

Types: `review`, `adversarial`, `rescue`, `verify`, `research`.

Create `${CLAUDE_PLUGIN_DATA}/reviews/` if it doesn't exist: `mkdir -p ${CLAUDE_PLUGIN_DATA}/reviews`

Default format for `review`/`adversarial` (which follow it as-is):

    # Codex <Type> — <date>

    ## Scope
    <what was analyzed>

    ## Codex Output
    <preserved verbatim>

    ## Claude's Evaluation

    ### Agreed
    - [finding]: [additional context]

    ### Disputed
    - [finding]: [why, with evidence]

    ### Additional Findings
    - [things Codex missed]

    ## Summary
    - Agreement: <High|Partial|Disagreement> (N/M findings agreed)
    - Codex findings: N | Agreed: N | Disputed: N | Claude additional: N

**`rescue`/`verify`/`research` each define their own report structure instead** (an unstructured task/output/diff/evaluation/verdict list for rescue, a PASS/FAIL verdict with P1/P2 sections for verify, a Topic/Findings/Synthesis/Agreement/Takeaways structure for research) — this is intentional, not drift: each domain's output shape doesn't map cleanly onto the generic Agreed/Disputed template above. All five still write to the same `${CLAUDE_PLUGIN_DATA}/reviews/<type>-<YYYYMMDD-HHMMSS>.md` path convention and the same success/failure split; only the body's internal section structure varies per skill.
