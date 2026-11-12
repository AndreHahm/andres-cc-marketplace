---
name: Missing tests review
area: review
slug: review__missing-tests
internal_id: p3d4e5f6a7b8
version: 1
short_description: Find changes in the current diff that lack tests.
status: draft
origin: user
prerequisites: A diff against the default branch is available.
boundaries: Read-only; do not edit files.
---

Review the current diff against the default branch.
List each changed function or behavior that no test covers, with its file and line.
For each gap, name the test file where a test would belong.
You are done when every changed behavior is either covered or listed.
