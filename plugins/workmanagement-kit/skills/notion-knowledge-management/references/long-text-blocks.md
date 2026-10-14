# Long Text as Page-Content Blocks

Procedure for the second rule in SKILL.md's "Long Text and Page-Content Blocks" section: a record whose
`body`, `findings` or `context` would exceed 2,000 characters keeps only a short note in that property,
and the full text goes into the page as blocks of at most 2,000 characters.

## Steps

1. **Write the full text to a generated file** in the session scratchpad, named like
   `wmgt-body-<timestamp>.md`. Never build the name from record content, and never use the repository
   root. This file is the only thing the splitter is ever pointed at. It holds the unredacted body, so
   do not copy it anywhere else.
2. **Split it:** `${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_split_blocks.py split "<that file>" --start <i>`.
   The result gives `total` (the block count) and ten blocks at a time; continue with `--start` set to
   the result's `next_start` while `has_more` is true. `--count` and `--max` are optional (`--max` must
   be at least 2), and a bad command line comes back as the same JSON failure (exit 1). A leading
   byte-order mark in the file is ignored. Splitting prefers a blank line, then a line break, then a
   space or tab, and cuts hard only where there is no whitespace. Line endings are normalized to LF,
   and the whitespace character at a cut is dropped.
3. **Preview for approval.** State the block count, say that a cut inside a paragraph reads as a
   paragraph break after reassembly, and say so when the text contains a markdown table or code fence
   (the splitter does not understand them, so a split can land inside one). The preview also covers the
   file's text for credentials or personal data, like any other captured content.
4. **After approval,** create the page with the first blocks joined by blank lines as its content, then
   append the remaining pages of blocks with `notion-update-page`'s `insert_content` at the end.
5. **If an append fails midway,** report the page ID and the last block written. Re-read the page, then
   resume from the next block. Never re-create the page.

## Read-back

The read-back returns Markdown with one line per paragraph, so a block count cannot be observed. A live
split write in the test environment on 2026-10-13 confirmed this: six paragraphs written as three
splitter blocks came back as six lines, intact and in order. Confirm instead that the paragraph count
equals the source's and that the last paragraph ends with the source's closing sentence.
