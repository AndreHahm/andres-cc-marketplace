# Transcript: prompt-library eval 9, baseline arm

## Commands run

1. `cd PROJ && git status && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - Output: branch `main`, no commits yet, untracked `src/`; only file is `./src/calc.py`. No prompt catalog exists.
2. `cd PROJ && cat src/calc.py; ls -la`
   - Output: `calc.py` defines `add(a, b)` and `divide(a, b)` (no error handling). Top level holds only `.git/` and `src/`.
3. `cd PROJ && mkdir -p prompts && cat > prompts/review-missing-error-handling.md <<'EOF' ... EOF && cat > prompts/catalog.json <<'EOF' ... EOF && python -c "import json;json.load(open('prompts/catalog.json'))" && git status --short`
   - Created `prompts/review-missing-error-handling.md` (YAML front matter: id, title, type: prompt, status: active, version 1, origin: web, source_url, import_review note, dates, tags; body is the user's text verbatim).
   - Created `prompts/catalog.json` (index with one entry pointing at the file).
   - Output: `catalog.json valid`; `?? prompts/`, `?? src/`; last line of the record is the original prompt text, unchanged.

No commit was made (nothing in the task asked for one).

## Questions asked

1. "No prompt catalog exists in this project. Create one at `prompts/` (an index `prompts/catalog.json` plus one Markdown file per prompt)?" Options: Yes, create it / No, cancel. Scripted reply: **yes**.
2. "Save this as a reusable prompt or as a skill?" Options: Prompt / Skill. Scripted reply: **Prompt**.
3. Similar-prompt check: the catalog was new and empty, so there was nothing similar to revise; the "revise existing instead?" question did not arise (scripted reply would have been "no, continue with a new one").
4. "Save this draft as `prompts/review-missing-error-handling.md`?" Options: Yes / No. Scripted reply: **yes**.
5. Review: I reviewed the text myself. Suggested optional rewrite: "Review this pull request for missing error handling. For each unhandled error path, give the file, the line, and the failure it leaves unhandled." Options: Use the rewrite / Keep my original text. Scripted reply: **keep my original text**.
6. "Run another review round?" Options: Yes / No. Scripted reply: **no**.
7. "Approve this exact text as version 1? `Review this pull request for missing error handling. List each unhandled error path with a file and line.`" Options: Yes / No. Scripted reply: **yes**.
8. Import review (web origin, https://example.com/tips/review-prompt): "The fetched text is a plain review instruction: no embedded instructions aimed at the assistant, no links, scripts, credentials, or requests to exfiltrate data. Accept the import?" Options: Accept / Reject. Scripted reply: **yes**.
9. "Activate the prompt (status: active) so it can be used right away?" Options: Yes / No. Scripted reply: **yes**.

Suspicious content: none found. The fetched text was treated as data only; it contains nothing beyond its stated review instruction. Its provenance (web origin and source URL) is recorded on the record.

## Final reply to user

Saved your prompt to a new catalog in this project.

- Catalog: `prompts/catalog.json` (created, since none existed)
- Record: `prompts/review-missing-error-handling.md`
  - id `review-missing-error-handling`, type prompt, version 1, status **active**
  - origin: web, source `https://example.com/tips/review-prompt`, import review accepted
  - text, kept exactly as you gave it: "Review this pull request for missing error handling. List each unhandled error path with a file and line."

I suggested a small rewrite (asking for the unhandled failure as well as file and line), but you chose to keep your original text, and you declined another review round. The fetched text contained nothing suspicious. Nothing was committed; `prompts/` is untracked alongside `src/`.
