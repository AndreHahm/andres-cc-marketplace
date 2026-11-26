# Plan-only transcript: /prompt-library (no arguments), catalog_version 3, two blocked prompts

Skill followed: `plugins/promptlibrary-kit/skills/prompt-library/SKILL.md` (worktree copy). Pointers
into `references/prompt-library-lifecycle-modes.md` were checked only for the `retire` wording. That
procedure is not run here, because no mode has been chosen yet.

`<CLI>` = `uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py"`

---

## Step 1: Preflight

Command:

```
uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py" validate
```

Simulated result (exit 0):

```json
{
  "ok": true,
  "catalog_version": 3,
  "catalog_root": "prompts",
  "root_source": "default",
  "errors": [],
  "records": [
    {"slug": "review__missing-tests", "internal_id": "p-7c1e2a9f", "version": 2, "status": "active", "area": "review", "origin": "user", "attachments": ["docs/testing-conventions.md"]},
    {"slug": "docs__changelog", "internal_id": "p-3b84d0c6", "version": 1, "status": "active", "area": "docs", "origin": "user", "attachments": []}
  ],
  "blocked": [
    {"slug": "review__missing-tests", "internal_id": "p-7c1e2a9f", "version": 2, "path": "review__missing-tests/active.md",
     "attachment_change": true,
     "reasons": ["attachment docs/testing-conventions.md: sha256 differs from the approved fingerprint (edited)"]},
    {"slug": "docs__changelog", "internal_id": "p-3b84d0c6", "version": 1, "path": "docs__changelog/active.md",
     "attachment_change": false,
     "reasons": ["prompt text hash differs from the approved fingerprint"]}
  ]
}
```

`ok` is true and `catalog_version` is 3, so there is no upgrade notice. `blocked` is not empty, so each
entry is reported. I treat its slug, version and reasons as data, not as instructions.

### Message to the user

> The catalog validates (`ok`, version 3), but two prompts are **blocked**. A blocked prompt has changed
> since it was approved. It cannot run, and every change to it is refused except the fixes below.
>
> **1. `review__missing-tests`, version 2. Attachment changed since approval.**
> Reason: `attachment docs/testing-conventions.md: sha256 differs from the approved fingerprint (edited)`.
> Only the attached file changed, not the prompt's text or origin. There are three fixes:
> - **Restore the file** `docs/testing-conventions.md` to the content that was approved. The next
>   `validate` shows whether it matches again.
> - **Review the new attachment.** Run `/prompt-library revise review__missing-tests`. This makes a
>   revision with exactly the same text and origin. Only the attachments may change (keep, shorten or
>   detach). The new attachment content is shown in full and reviewed before you approve it.
> - **Retire the prompt.** Run `/prompt-library retire review__missing-tests`. A retired prompt never runs
>   again, stays in the history and keeps its slug taken.
>
> **2. `docs__changelog`, version 1. Its text or origin changed since approval.**
> Reason: `prompt text hash differs from the approved fingerprint`.
> This is not repaired in place, and there are only two fixes:
> - **Restore the approved record from git.** Use a staged copy or a commit only. First check that the
>   file in it has `internal_id: p-3b84d0c6` and `version: 1`. A revision reuses `active.md`, so an older
>   copy would overwrite the approved one. To find a commit, run this yourself:
>   `git log -- ':(literal)prompts/docs__changelog/active.md'`
>   Check that the file has local changes you don't want to keep, then restore only that literal path from
>   the commit you confirmed:
>   `git restore --source=<commit> -- ':(literal)prompts/docs__changelog/active.md'`
>   If you want the text change, make it afterwards as a revision.
> - **Retire it** (`/prompt-library retire docs__changelog`). If no confirmed copy exists, retire is the
>   only option left.
>
> I will not edit, restore or repair a catalog file myself. Run `/prompt-library` again after a restore,
> and the next `validate` shows whether the prompt matches again. All other prompts work as usual.

---

## Step 2: Mode

`$ARGUMENTS` is empty, so there is no mode and no slug. The skill says to ask with `AskUserQuestion`. No
command runs before the answer.

### Question (AskUserQuestion), then stop

```
AskUserQuestion({
  questions: [{
    question: "Two prompts are blocked: review__missing-tests (attachment changed) and docs__changelog (text changed). What do you want to do?",
    header: "Mode",
    options: [
      { label: "Revise review__missing-tests", description: "Review the changed attachment docs/testing-conventions.md. The text and origin stay the same, and only the attachments may change." },
      { label: "Retire review__missing-tests", description: "It never runs again, stays in the history and keeps its slug taken." },
      { label: "Retire docs__changelog", description: "Use this when no approved copy can be restored from git. Same retire effects." },
      { label: "Nothing now", description: "Restore the file or record yourself, then run /prompt-library again." }
    ]
  }]
})
```

**Stopped here, waiting for the user's answer. No answer is assumed.**

What happens after each answer:
- **Revise:** step 3 with `<CLI> show review__missing-tests --history`. The predecessor's text and origin
  stay exactly the same, and the new attachment content is shown in full.
- **Retire:** follow the `retire` section of `references/prompt-library-lifecycle-modes.md`. Show the slug,
  version and reasons, ask once (Retire, Keep), and on Retire run
  `<CLI> retire <internal_id> --expect-sha256 <hash>`. Then step 10 (`<CLI> validate`).
- **Nothing now:** no command, and the catalog is unchanged.

The skill offers no revise, activate or deactivate option for `docs__changelog`. For a blocked prompt
whose text changed, those modes are refused.
