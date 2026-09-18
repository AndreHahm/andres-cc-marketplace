## Summary
context-kit: audit-context.sh spawns one `wc` process per scanned file, exceeding 90s on a large skills tree

## Environment
- **Product/Service**: context-kit plugin, `context-audit` skill (this marketplace)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
N/A — a performance/scalability finding, not a reproducible bug. Found by CodeRabbit during review of
PR #353 (context-kit wave-4 QA), `plugins/context-kit/skills/context-audit/scripts/audit-context.sh:91`.

## Expected Behavior
The static inventory scan completes in a reasonable time even against a large skills tree (this
repository's own `.claude/skills/` currently has 135+ entries).

## Actual Behavior
`file_words_and_size()` starts one `wc -w -c` subprocess per scanned file (every `SKILL.md`,
`references/*.md`, `rules/*.md`, CLAUDE.md, and auto-memory file). A large skills tree therefore
performs hundreds of serial process starts. This skill's own documentation already discloses that this
can exceed 90 seconds (`SKILL.md`'s "Known limitation" note under `### 1. Static Inventory`).

**Suggested fix (CodeRabbit's own suggestion):** batch metric collection per scan phase (e.g. one `wc
-w -c file1 file2 ...` call per phase instead of one call per file, correlating `wc`'s per-file output
lines back to filenames positionally), or use a streaming/single-pass approach — while preserving safe
filename handling (a filename containing a literal newline or unusual character must not break the
correlation between `wc`'s output lines and the files being measured).

## Error Details
~~~
N/A — no error output; this is a performance characteristic, not a failure.
~~~

## Visual Evidence
N/A

## Impact
**Medium-High** — not incorrect output, but a real usability problem: the primary `context-audit`
command becomes slow-to-unusable on a large, real skills tree. Rated "Major / Heavy lift" by
CodeRabbit's own severity assessment — a full batching/streaming rewrite is a genuine architectural
change to the scanning loop, not a small fix, and risks introducing a new filename-correlation bug if
rushed.

## Additional Context
This gap is already disclosed in `plugins/context-kit/skills/context-audit/SKILL.md`'s own "Static
Inventory" section as a known, tracked limitation. This issue exists to track the actual follow-up
work; filing it (rather than attempting a rushed rewrite) was a deliberate decision to defer a "Heavy
lift" architectural change to a follow-up pass rather than risk a new bug in the wave-4 QA PR.
