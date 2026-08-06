# Comparison Report Template

The report written to `.claude/output/plugin-comparison/comparison-<timestamp>.md` follows this structure exactly:

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — the file's own stated purpose is defining this exact, complete structure; trimming would contradict "follows this structure exactly."

```markdown
# Plugin Comparison: <Target A> vs <Target B>

**Detail level:** Quick | Standard | Deep · **Generated:** <UTC timestamp>

## Targets
- **A:** <name> — <source kind> — <resolved path/URL>
- **B:** <name> — <source kind> — <resolved path/URL>

## Summary Table
| Aspect | Target A | Target B | Delta |
|---|---|---|---|
| Triggers | ... | ... | ... |
| Scope & Domain | ... | ... | ... |
| Functionalities & Capabilities | ... | ... | ... |
| Boundaries | ... | ... | ... |
| Rules, Conditions & Invocation Modes | ... | ... | ... |
| Features | ... | ... | ... |

## Overlap
...
## Unique to A / Unique to B
...
## Notable Differences
...
## Recommendation
(include only when the user's framing implies a decision — adopt/merge/replace/keep both; omit otherwise)
## Inspection Limits
...
```

At `Deep` detail level, add two more Summary Table rows — `Tool / Permission Footprint` and `Dependencies` — sourced from the corresponding portfolio sections; omit them entirely at `Quick`/`Standard` rather than leaving them blank.
