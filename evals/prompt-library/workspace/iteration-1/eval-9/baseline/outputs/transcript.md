# Baseline transcript (eval-9)

## Commands
1. `cd <proj> && pwd && ls -la && find . -maxdepth 3 -not -path './.git/*'` -> project has only .git and src/calc.py (add, divide). No prompt library, no prompts dir.
2. `cd <proj> && find . -not -path './.git/*' -type f; ls -a; cat src/calc.py | head -20` -> confirmed no existing convention.
3. `cd <proj> && mkdir -p prompts && cat > prompts/review-error-handling.md <<EOF ... EOF; cat prompts/review-error-handling.md` -> file created:

```
---
name: review-error-handling
source: https://example.com/tips/review-prompt
added: 2026-10-04
---

Review this pull request for missing error handling. List each unhandled error path with a file and line.
```
4. `mkdir -p <outputs>; ls <outputs>` (created this directory)

## Questions / assumed replies
- Q: No prompt library exists and no "/prompt-library" tool is available; OK to create `prompts/` with one markdown file per prompt? A (assumed): yes.

## Final reply
I saved the prompt to `prompts/review-error-handling.md` in your project. There was no existing prompt library, so I created the `prompts/` folder and used one markdown file per prompt.

The file holds the prompt text exactly as you gave it, with a small header recording its name (`review-error-handling`), the source URL (https://example.com/tips/review-prompt) and today's date.

I didn't run anything against the prompt or check the URL. I saved only the text you pasted.
