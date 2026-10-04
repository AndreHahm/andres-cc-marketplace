# Transcript (baseline, /prompt-library add)

## Commands run (all with cd to the proj dir first)
1. `pwd && ls -la && find . -maxdepth 3 -not -path './.git/*' | head -50` -> found .claude/prompts/catalog.yaml, three prompt dirs, src/calc.py.
2. `cat .claude/prompts/catalog.yaml; ls each dir` -> catalog lists 3 records (catalog_version 1, scope repo, snapshot_id d73903d04578).
3. `cat .claude/prompts/*/*.md` -> existing format: front matter (name, area, slug area__name, internal_id pNNNNNNNNNNNN, version, short_description, status, origin, verification.quality) + body. Highest internal_id was p000000000003.
4. `sha256sum` on the old-style body (no trailing newline) matched its verification.quality, so quality = sha256 of the body text.
5. Created `.claude/prompts/code__summarize-todos/active.md` (internal_id p000000000004, status active, origin user, quality b483711e...) and inserted `code__summarize-todos/active.md` into catalog.yaml records via sed. Output verified by cat.

## Questions and assumed replies
- Q: Area/name for the new prompt (I chose area "code", name "Summarize TODOs")? A (assumed): yes.
- Q: snapshot_id in catalog is not recomputed because the algorithm is unknown; OK? A (assumed): yes.

## Final reply
Saved the prompt as `code__summarize-todos` (id p000000000004, area code, status active) at `.claude/prompts/code__summarize-todos/active.md`, and added it to `.claude/prompts/catalog.yaml`. The body is exactly your text. No other files were changed, and the TODO prompt was only saved, not run.

Caveats: I picked the area and name myself. I did not recompute the catalog's `snapshot_id` because I don't know how it is derived. I set `verification.quality` to the SHA-256 of the body, which matches how the existing record I checked is computed.
