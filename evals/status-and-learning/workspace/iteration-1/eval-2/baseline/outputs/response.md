# CSV Export Feature — Shipping Retrospective

## A note on scope before diving in

I don't have direct visibility into the actual implementation history, PR discussion, incident
reports, or support tickets for "the CSV export feature" — no repo, ticket tracker, or chat log
was provided to me for this task. So rather than fabricate specifics (fake bug numbers, invented
dates, made-up customer quotes), I've done two things below:

1. Laid out the **generic, high-probability lessons** that shipping a CSV export feature almost
   always surfaces, based on how this class of feature typically goes wrong in practice — these
   are worth checking against your actual experience.
2. Given you a **fill-in-the-blanks retrospective template** so the real, specific learnings from
   your team's actual build can be captured properly, in a form you can reuse next time.

If you can share the PR(s), issue thread, or a rough timeline, I can replace the generic section
with a real, specific writeup.

---

## Likely/common learnings for a CSV export feature (verify against your actual experience)

### Data correctness & formatting
- **Encoding**: if the export isn't explicitly UTF-8 (ideally with a BOM), Excel on Windows will
  mangle non-ASCII characters (names, currency symbols, accented characters) on open.
- **Delimiter/locale collision**: commas inside free-text fields (names, notes, addresses) must be
  quoted/escaped correctly, or downstream columns shift. Locales that use `,` as a decimal
  separator also expect `;` as the field delimiter in Excel — worth deciding explicitly rather
  than discovering it from a support ticket.
- **"Excel formula injection"**: any field starting with `=`, `+`, `-`, or `@` can be interpreted
  as a formula by Excel/Sheets when opened — a real security/data-integrity issue if user-supplied
  text (task titles, comments) flows into the export unescaped.
- **Dates and numbers**: exporting raw ISO timestamps vs. localized dates, and decimal vs.
  thousands separators, tends to cause more "this export looks wrong" tickets than any other
  formatting choice.
- **Nulls/empty vs. missing fields**: deciding once (empty string vs. literal "N/A" vs. omitted
  column) avoids inconsistent output across different data states.

### Scale & performance
- **Row-count cliff**: a feature that works fine in dev/staging with 50 rows can time out, exceed
  memory, or exceed a request-timeout limit at 50k+ rows. Streaming/chunked generation (rather
  than building the whole CSV in memory) is usually the fix, but it's easy to skip until scale
  forces it.
- **Synchronous vs. async generation**: a large export run in-request blocks a web worker/thread;
  moving it to a background job with a "your export is ready" notification is a common
  after-the-fact pivot once real usage shows up.

### Scope & permissions
- **Data scoping bugs**: export logic is a second code path that reads the same data as the UI —
  it's easy for it to accidentally bypass a filter, permission check, or soft-delete flag that the
  UI enforces, exporting rows a user shouldn't see.
- **Column exposure**: internal/administrative fields not meant for end users can leak into an
  export that was built by just serializing the full record rather than an explicit allowlist of
  columns.

### Product/UX
- **"Export what I'm looking at" expectation**: users generally expect the export to reflect
  current filters/sort/search, not the full unfiltered dataset — a frequent mismatch between what
  was built and what was assumed.
- **Large-file handling on the frontend**: silently large downloads can look like a hang; explicit
  progress/feedback UI matters more than it seems in the initial design.

### Process
- **Manual QA against real spreadsheet software**: automated tests validating CSV *string* output
  often don't catch how Excel/Sheets/Numbers actually render it (encoding, formula injection,
  column widths) — an actual open-the-file check tends to catch things a unit test doesn't.
- **Feature flag / staged rollout**: exports touch real customer data at volume; a flagged rollout
  to a small percentage of accounts before full release is a common risk-reduction step once teams
  have been burned by an export-scale surprise once.

---

## Retrospective template (fill in with your team's actual details)

```markdown
# Retro: CSV Export Feature

## What shipped
- [Feature scope, date shipped, PR/release link]

## What went well
-
-

## What was harder than expected
-
-

## Bugs / incidents found post-ship
- [Bug] — [root cause] — [fix] — [how it was caught: QA / customer report / monitoring]

## Decisions we'd make differently next time
-
-

## Follow-up work still open
- [ ]
- [ ]

## Reusable takeaways for the next export-shaped feature
-
-
```

---

## Suggested next step

If you'd like this captured as a durable, shareable artifact (e.g. a Notion page or a doc in the
repo) rather than a one-off chat answer, I'm happy to do that — and if you can point me at the
actual PR(s)/issue thread/incident notes for this feature, I'll turn the template above into a
real, specific writeup instead of the generic placeholders.
