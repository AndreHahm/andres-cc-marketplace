# Troubleshooting

## "Both Added" Conflicts (AA)

Both branches added a new file with the same name but different content:

1. Review both versions
2. If they serve the same purpose, merge their content
3. If they serve different purposes, rename one

## Persistent Conflict Markers

If validation shows conflict markers but you think you resolved them:

1. Search for the exact marker strings using the `Grep` tool (pattern: `^<<<<<<<`) -- not a raw
   `Bash(git grep:*)` grant, since `git grep` accepts `-O`/`--open-files-in-pager=<cmd>`, which runs
   an arbitrary command rather than searching
2. Some markers might be in strings or comments - resolve those too
3. Check for hidden characters or encoding issues

## Tests Fail After Resolution

1. Test each branch individually to confirm they pass
2. The failure is likely from interaction between the merged changes
3. Debug the interaction issue, not the individual changes
4. Update code to make both changes work together
