# Special Scenarios

## Binary Files in Conflict

Binary files cannot be merged. Choose one version:

```bash
git checkout --ours path/to/binary    # keep our version
# or
git checkout --theirs path/to/binary  # keep their version
```

## Mass Rename/Refactoring Conflicts

If one branch renamed/refactored many files while another modified them:

1. Accept the rename/refactoring (structural change)
2. Apply the modifications to the new structure
3. Use backups from `handle-deleted-modified.sh` to guide the application
