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
```

### Rewrite preservation (rebase, amend)

`notes.rewriteRef` has no default, so nothing is copied without it. A copied review or test note still
describes the pre-rewrite commit: narrow the glob or re-check it.

```bash
# Choose which notes refs a rewrite copies
git config notes.rewriteRef 'refs/notes/*'

# Preserve notes during rebase (defaults to true; set it so a false elsewhere can't switch it off)
git config notes.rewrite.rebase true

# Preserve notes during amend
git config notes.rewrite.amend true

# Set rewrite mode
git config notes.rewriteMode concatenate
```

## Sample .gitconfig

```gitconfig
[notes]
    rewriteRef = refs/notes/*
    displayRef = refs/notes/reviews
    displayRef = refs/notes/testing
    mergeStrategy = union

[notes "reviews"]
    mergeStrategy = theirs

[notes.rewrite]
    rebase = true
    amend = true
```
