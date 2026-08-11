# Git Notes Troubleshooting

Common git notes mistakes and their fixes.

| Mistake | Fix |
|---------|-----|
| Notes not showing in log | Specify ref: `git log --notes=reviews` or configure `notes.displayRef` |
| Notes lost after rebase | Enable: `git config notes.rewrite.rebase true` |
| Notes not on remote | Push explicitly: `git push origin refs/notes/commits` |
| "Note already exists" error | Use `-f` to overwrite or `append` to add |
