# Git Notes Configuration

Git config options for notes display, merge strategy, and rewrite preservation.

## Git Config

```bash
# Set default notes ref
git config notes.displayRef refs/notes/reviews

# Display multiple notes refs (--add appends rather than overwriting)
git config --add notes.displayRef refs/notes/testing

# Set merge strategy for notes
git config notes.mergeStrategy union

# Set merge strategy for specific namespace
git config notes.reviews.mergeStrategy theirs

# Preserve notes during rebase
git config notes.rewrite.rebase true

# Preserve notes during amend
git config notes.rewrite.amend true

# Set rewrite mode
git config notes.rewriteMode concatenate
```

## Sample .gitconfig

```gitconfig
[notes]
    displayRef = refs/notes/reviews
    displayRef = refs/notes/testing
    mergeStrategy = union

[notes "reviews"]
    mergeStrategy = theirs

[notes.rewrite]
    rebase = true
    amend = true
```
