# Merge Rules Report — Sample Format

```
# Merge Rules Report

## Sources
- frontend-app (3 files)
- backend-api (2 files)
- shared-lib (4 files)

## File Name Normalization
- `rails-controller.md` + `rails-controllers.md` → `rails-controllers.md`
- `rails-model.md` + `rails-models.md` → `rails-models.md`

## Merge Results
| File | Sources | Principles | Promoted to Principles | Examples |
|------|---------|------------|------------------------|----------|
| languages/typescript.md | 3/3 | 5 | 2 | 7 |
| frameworks/react.md | 2/3 | 3 | 1 | 4 |
| integrations/rails-inertia.md | 2/3 | 2 | 0 | 2 |

**Principles** = total including promoted. **Examples** = total `###` entries in the output `.examples.md`.

## Promoted to Principles
- `useAuth()` → Auth hook interface (useAuth) - 3/3 projects
- `pathFor() + url()` → Path helpers (pathFor, url) - 2/3 projects

## Below Threshold (reference)
- `useCustomHook()` (typescript) - 1/3 (frontend-app only)
- `ApiClient.create()` (typescript) - 1/3 (backend-api only)

## Skipped
- project.md x3 (project-specific, skipped)
```
