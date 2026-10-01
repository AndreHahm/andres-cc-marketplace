# Reference Chains (R14 extension)

Full detail for R14's second clause. `SKILL.md` carries the rule's statement and a pointer here. ADVISORY and
forward-looking, like R28-R30: checked on newly-created or modified reference files.

## What is checked

R14 keeps `references/` one level deep in directory terms. This clause covers the same idea at the content
level: a `references/` file that **requires** the reader to load a second `references/` file before it can be
used. That forces an unplanned second context load on any agent that already opened the first file (issue #382).

## Chain versus cross-reference

Most pointers between reference files are ordinary cross-references, and a script cannot tell the two apart. A
count over this repo found 96 of 351 reference files pointing at another reference file (262 pointers across 26
skills), so only the judgment below separates a finding from the normal case.

- **Chain (ADVISORY):** the first file cannot be used without the second — "read X first", "load Y before
  applying this", or a procedure whose steps live in the other file.
- **Cross-reference (not a finding):** "see also X", a pointer to related detail, or an index entry. The reader
  can finish the task with the first file alone.

## Not covered

- `SKILL.md` pointing at a reference file: that is the intended design.
- A catalog or index file whose job is to list the others (`skill-file-catalog.md`).
- A pointer to a file in another skill's folder: that is R34's domain.

## Severity

ADVISORY, never blocking. State which sentence you judged to be a load requirement, so the maintainer can
disagree.

## Fix

Inline the part of the second file the first one needs, or merge the two files, or restate the pointer as an
optional "see also". Do not nest the files into subdirectories: R14's directory clause forbids that.
