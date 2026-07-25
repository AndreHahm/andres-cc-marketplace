# Promotion Algorithm

## Step 5: Promote .local.md Patterns to Principles

For each normalized category (e.g., `languages/typescript`, `frameworks/rails-controllers`):

1. Collect `## Project-specific patterns` from all projects — from `.local.md` files and from hybrid `.md` files containing this section (see Step 2 in SKILL.md)
2. **Deduplicate against existing Principles**: Exclude patterns whose description semantically matches an existing principle name in the corresponding `.md` output (from Step 4). Use AI judgment for semantic equivalence (case-insensitive, synonyms). Prevents self-amplification when `.local.md` contains previously promoted patterns
3. Match remaining patterns by inline code signature (backtick portion before ` - `)
   - Use AI judgment for semantic equivalence (e.g., `useAuth()` and `useAuth() → { user, login, logout }` refer to the same pattern)
4. Count occurrences per pattern across projects
5. Calculate threshold: pattern must appear in more than `len(projects) * promote_threshold` projects (strict majority when threshold = 0.5)
6. **Convert to Principles format** and append to `## Principles` in the corresponding normalized `.md` output:
   - Signature format: `` `signature` - description `` → Principles format: `Description (simplified signature)`
   - The description becomes the principle name; the function/type name from the signature becomes the hint
   - Examples:
     - `` `useAuth() → { user, login, logout }` - auth hook interface `` → `Auth hook interface (useAuth)`
     - `` `clean_bracket_params(:keyword)` - bracket removal for WAF `` → `Bracket removal for WAF (clean_bracket_params)`
     - `` `RefOrNull<T extends { id: string }> = T | { id: null }` - nullable refs `` → `Nullable refs (RefOrNull<T>)`
   - Apply Step 4's principle deduplication to converted principles (skip if same name already exists)
7. Patterns below threshold → discard (listed in report for reference)

## Step 5.5: Merge Examples (.examples.md)

For each normalized `.examples.md` file group:

1. Collect all versions from projects that have this file (including normalized variants)
2. **Principles Examples**: Merge by section heading (e.g., `### FP only`)
   - Same principle heading across projects → adopt the most detailed example, or merge Good/Bad from different projects
   - If Good/Bad contrast exists in one project but not another → adopt from the project that has it
   - Deduplicate identical examples
3. **Promoted pattern examples**: For patterns promoted in Step 5, include their examples under `## Principles Examples`
   - Use the same semantic equivalence judgment as Step 5 to link `###` example headings to promoted patterns — do not rely solely on exact heading match
   - `###` title uses the converted Principle name (from Step 5), not the original signature
   - Include the full original signature as a Good example showing usage
   - Discard examples for patterns below threshold (same as the pattern itself)

See `references/output-formats.md` for the `.examples.md` file structure.
