# Splitting Commits Into Ordered Waves

When a feature touches multiple files, implement in **waves**. Each wave is one logical concern, one standalone commit, ordered by dependency. This creates a clean git history that reviewers can audit one commit at a time.

> **Related**: See the main `standalone-commits` skill for making each wave reviewable and auditable, and git-kit's `commit` skill for commit message conventions and PR guidelines.

## Relationship To Standalone Commits

This reference decides commit *order*. The main `standalone-commits` skill decides whether each commit *boundary* is good.

Use this reference to plan the sequence:

```
foundation -> implementation -> consumers -> cleanup
```

Then use `standalone-commits`'s acceptance checks to test each wave:

```
Can this commit be reviewed, verified, and reverted as one coherent unit?
```

If a planned wave fails that test, change the wave boundary before committing.

## The Pattern

This reference uses the same 4-wave numbering as `standalone-commits`' own "Wave Planning" section — it doesn't introduce a separate numbering, only expands what typically belongs in each wave:

```
Wave 1: Foundation — types, interfaces, contracts/APIs (the shape everything else builds on)
  ↓
Wave 2: Implementation — factories/builders, infrastructure, and anything that satisfies the Wave 1 contract
  ↓
Wave 3: Consumers — apps, UI, integrations that adopt the new implementation
  ↓
Wave 4: Cleanup — remove old paths once no consumers depend on them
```

Not every change needs all four waves. A simple bugfix might be one standalone commit. A cross-cutting refactor might need all four, with Wave 1 or Wave 2 split into multiple commits if either one is too large to review as a single unit.

## Wave Characteristics

Each wave must be:

| Property      | Description                                    |
| ------------- | ---------------------------------------------- |
| **Atomic**    | One logical concern per wave                   |
| **Buildable** | Code compiles after this wave (run type-check) |
| **Focused**   | Changes relate to ONE layer/concern            |
| **Complete**  | No half-done work within a wave                |
| **Auditable** | Reviewers can inspect this wave without waiting for a later wave |

## Real Example: Schema Refactor

This feature moved metadata from workspace to tables. It needed five commits — Wave 1 (Foundation) and Wave 2 (Implementation) each split into two, since each half was independently reviewable and didn't depend on its sibling. Note the actual landing order interleaves the sub-waves (1a, 2a, 1b, 2b, 3) rather than finishing all of Wave 1 before starting Wave 2 — that's fine, since dependency order only requires each commit to come after what it actually depends on, not after every commit in an earlier-numbered wave:

### Wave 1a: Types (Foundation)

```
feat(schema): add IconDefinition, CoverDefinition, and FieldMetadata types

- Add IconDefinition discriminated union (emoji | external)
- Add CoverDefinition discriminated union (external)
- Add FieldMetadata with optional name/description to all field types
- Update TableDefinition to use icon/cover instead of emoji/order
```

Files: `types.ts` only. Foundation for everything else.

### Wave 2a: Factories (Implementation)

```
feat(schema): add optional name/description to field factory functions

All factory functions (id, text, richtext, integer, real, boolean, date,
select, tags, json) now accept optional name and description parameters.
```

Files: `factories.ts` only. Uses types from Wave 1a.

### Wave 1b: Contracts (Foundation)

```
feat(schema): remove emoji and description from WorkspaceSchema

Workspace is now just a container with guid, id, name, tables, and kv.
Visual metadata (icon, cover, description) now lives on TableDefinition.
```

Files: `contract.ts` only. API change using new types.

### Wave 2b: Infrastructure (Implementation)

```
feat(schema): use slugify for human-readable SQL column names

- Add @sindresorhus/slugify dependency
- Add toSqlIdentifier() helper using slugify with '_' separator
- SQLite columns now use field.name (or derived from key) instead of key
```

Files: `to-drizzle.ts`, `package.json`. Utility that uses field metadata.

### Wave 3: Consumers

```
feat(schema): update app to use TablesWithMetadata

- WorkspaceSchema now accepts TablesSchema | TablesWithMetadata
- Export new types from package index
- Update app to create proper TableDefinition with metadata
```

Files: App files that consume the new types.

## The Workflow

1. **Plan waves before coding**
   - List files that need changes
   - Group by layer/concern
   - Order by dependency (foundations first)
   - Define the standalone claim each wave will prove

2. **Implement one wave**
   - Make changes for that wave only
   - Resist temptation to "fix one more thing"

3. **Verify the wave**
   - Run the project's type-check/build/test command
   - Re-read `git diff --staged` against the wave claim
   - Ensure no errors introduced

4. **Commit the wave**
   - Use conventional commit format
   - Message describes what this wave accomplishes
   - Body can list specific changes

5. **Repeat for next wave**

## When to Use Waves

| Scenario                 | Waves? | Why                        |
| ------------------------ | ------ | --------------------------- |
| Single file bugfix       | No     | One change, one commit     |
| Add new type + factory   | Maybe  | Could be 1-2 waves         |
| Refactor across 5+ files | Yes    | Need logical grouping      |
| Breaking API change      | Yes    | Types → API → Consumers    |
| Add dependency + use it  | Yes    | Infra wave then usage wave |

## Anti-Patterns

### Giant Commit

```
refactor: update schema system

- Add new types
- Update factories
- Change contracts
- Add slugify
- Update app
```

Problem: One monolithic commit. Can't bisect, can't revert partially, no story.

### Micro Commits

```
feat: add IconDefinition type
feat: add CoverDefinition type
feat: add FieldMetadata type
feat: update IdFieldSchema
feat: update TextFieldSchema
...
```

Problem: Too granular. 20 commits for one logical change. Noise.

### Wrong Order

```
Wave 1: Update app to use new types  ❌
Wave 2: Add the types                 ❌
```

Problem: Wave 1 won't compile. Bottom-up, not top-down.

## Dependency Order Heuristic

When deciding wave order, ask: "What does this file import?"

```
types.ts         → imports nothing (foundation)
factories.ts     → imports types.ts
contract.ts      → imports types.ts
converters.ts    → imports types.ts, may add deps
app/             → imports everything above
```

Files that import nothing come first. Files that import everything come last.

## Branch Strategy

For multi-wave work:

```bash
# Create the feature branch first via Skill(git-kit:starting-work) -- raw
# `git checkout -b` is hard-blocked by git-kit's branch-creation guard outside it.

# Wave 1
# ... make changes ...
# (each wave's commit goes through this skill's own Staging Workflow step 6,
# which writes the marker git-kit's commit guard requires)
git add <files> && git commit -m "feat(scope): wave 1 description"

# Wave 2
# ... make changes ...
git add <files> && git commit -m "feat(scope): wave 2 description"

# ... continue waves ...

# When done, all waves are individual commits on the branch
# PR shows clean history of how the feature evolved
```

## Quick Reference

Before starting:

- [ ] List all files that need changes
- [ ] Group by layer (types, factories, contracts, infra, consumers)
- [ ] Order by dependency

For each wave:

- [ ] Change only files in this wave
- [ ] Run type-check
- [ ] Commit with descriptive message
- [ ] Move to next wave

After all waves:

- [ ] Final type-check
- [ ] Run tests if applicable
- [ ] Create PR with clean commit history
