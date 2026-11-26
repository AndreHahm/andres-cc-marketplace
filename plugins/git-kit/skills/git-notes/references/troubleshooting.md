# Git Notes Troubleshooting

Common git notes mistakes and their fixes.

| Mistake | Fix |
|---------|-----|
| Notes not showing in log | Specify ref: `git log --notes=reviews` or configure `notes.displayRef` |
| Notes lost after rebase | Prevent it: add each ref to copy, which has no default, with `git config --add notes.rewriteRef refs/notes/<name>`, and keep `git config notes.rewrite.rebase true`. Recover a note already lost: find the pre-rebase commit with `git log -g`, then `git notes --ref=<name> copy <old-sha> <new-sha>`, re-checking any review, test or audit verdict first |
| Notes not on remote | Push explicitly: `git push origin refs/notes/commits` |
| "Note already exists" error | Use `-f` to overwrite or `append` to add |
