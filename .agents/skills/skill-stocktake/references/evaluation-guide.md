# Evaluation Guide

Detailed guidance for writing high-quality verdict reasons in skill-stocktake evaluations.

## Reason Quality Rules

The `reason` field in `results.json` must be **self-contained and decision-enabling** — a reader must be able to act on it without opening the skill file.

- Never write "unchanged" or "superseded" alone — restate the concrete evidence
- Name specific sections, line ranges, or overlapping skills
- For Retire/Merge: name what alternative covers the same need

## Bad vs. Good Examples by Verdict

### Retire

- Bad: `"Superseded"`
- Good: `"disable-model-invocation: true already set; superseded by continuous-learning-v2 which covers all the same patterns plus confidence scoring. No unique content remains."`

### Merge

- Bad: `"Overlaps with X"`
- Good: `"42-line thin content; Step 4 of chatlog-to-article already covers the same workflow. Integrate the 'article angle' tip as a note in that skill."`

### Improve

- Bad: `"Too long"`
- Good: `"276 lines; Section 'Framework Comparison' (L80–140) duplicates ai-era-architecture-principles; delete it to reach ~150 lines."`

### Keep (mtime-only change in Quick Scan)

- Bad: `"Unchanged"`
- Good: `"mtime updated but content unchanged. Unique Python reference explicitly imported by rules/python/; no overlap found."`
