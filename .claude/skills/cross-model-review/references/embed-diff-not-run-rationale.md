# Why Codex must never be told to run `git diff` itself

Extracted from SKILL.md's Phase 1 (Codex's pass) per plugin-rulebook's R13 (SKILL.md grew past the
500-line Critical threshold). Both Phase 1 and Phase 2 embed the diff as plain text and point here for
why — SKILL.md keeps only the actual instruction (embed the content, don't ask Codex to fetch it).

A confirmed, live Windows-specific issue (issue #78) makes Codex's own large-output shell-execution
path fail outright (`CreateProcessAsUserW` / Windows error 1920) on some machines, while a
small-output command from the same dispatch succeeds fine. The failure is about anticipated output
size, not the sandbox profile — it isn't specific to the danger-full-access Step 2 path either; the
same failure shape can hit the sandboxed Step 1 path too.

Embedding the diff as plain text in the instruction file, rather than instructing Codex to run
`git diff` (or any other command expected to produce large output) itself, sidesteps the whole failure
class on every platform, with no reliability cost — Codex still receives the exact same diff content
either way, just handed to it directly instead of fetched.
