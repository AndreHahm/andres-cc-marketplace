# TaskCreate/TaskUpdate Patterns & Best Practices

Use this guide when writing a skill or agent whose own body should instruct Claude to use `TaskCreate`/`TaskUpdate` to track its work. This is about authoring components that correctly *invoke* these tools — not about how Claude Code itself schedules tasks.

## When to Instruct TaskCreate

**Use for:**
- Tasks with 3+ distinct steps
- Multi-file or multi-component work
- Sequential dependencies between steps
- Workflows where the user benefits from visible progress

**Don't use for:**
- Single-file edits
- 1-2 step operations
- Pure research/reading with no state to track
- Conversational responses

A skill that instructs `TaskCreate` for every trivial operation trains Claude to over-instrument simple work — reserve it for genuinely multi-step components.

## Core Requirements

### 1. Dual-Form Naming

Every task needs both forms — `subject` (imperative: what to do) and `activeForm` (present continuous: doing it now):

```
TaskCreate:
- subject: "Run tests"
- activeForm: "Running tests"
- description: "Execute test suite and verify all tests pass"
```

Missing `activeForm` is the most common mistake — the spinner has nothing to show while the task is `in_progress`.

### 2. Real-Time, Sequential Updates

- Mark `in_progress` **before** starting work, `completed` **immediately after** finishing — never batch updates ("do steps 1-3, then update all three").
- Exactly **one** task `in_progress` at a time.
- Only mark `completed` when the work is **fully** done. If blocked or failed, leave the task `in_progress` and create a new task for the resolution — don't mark a stalled task complete to make the list look finished.

## Instructing This in a Skill or Agent Body

**Command/skill body:**
```markdown
**Use TaskCreate tool** to track the following phases:
1. Scan plugin structure
2. Validate components
3. Generate report

Use TaskUpdate tool to mark each phase as in_progress before starting and completed after finishing.
```

**Agent system prompt:**
```markdown
**Use TaskCreate tool** at the start to create tasks for multi-step workflows.
Use TaskUpdate tool to mark each task as in_progress before starting, completed immediately after finishing.
```

Name `TaskCreate`/`TaskUpdate` explicitly in body prose ("**Use TaskCreate tool**...") rather than describing the tracking implicitly — an implicit description ("track progress through the phases") leaves Claude free to skip the tool entirely, since nothing names which mechanism to use.

## Common Mistakes

**Wrong — missing `activeForm`:**
```
TaskCreate:
- subject: "Run tests"
- description: "Execute test suite"
```

**Right — both forms present:**
```
TaskCreate:
- subject: "Run tests"
- description: "Execute test suite and verify all tests pass"
- activeForm: "Running tests"
```

**Wrong — multiple tasks `in_progress` simultaneously:**
```
TaskUpdate: {taskId: "1", status: "in_progress"}
TaskUpdate: {taskId: "2", status: "in_progress"}
```

**Right — one at a time:**
```
TaskUpdate: {taskId: "1", status: "completed"}
TaskUpdate: {taskId: "2", status: "in_progress"}
```

**Wrong — batched updates:** do Task 1, Task 2, Task 3, then mark all three complete at the end.
**Right — sequential updates:** do Task 1, mark it complete, do Task 2, mark it complete, and so on.

## Quick Decision Tree

```
Is this 3+ steps?
  NO  -> Don't instruct TaskCreate
  YES -> Multiple files/components?
           NO  -> Probably don't need it
           YES -> Sequential dependencies?
                    NO  -> Maybe don't need it
                    YES -> Instruct TaskCreate
```
