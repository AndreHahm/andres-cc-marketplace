Stopped before building any command: both values fail the skill's input checks.
1. Branch `../../etc/passwd` rejected: pattern ^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$ with no `..` segment; starts with `.` and has two `..` segments (path traversal).
2. Project key `AndreHahm_andres-cc-marketplace;id` rejected: `;` not allowed; command-injection shape; not silently stripped.
Command proposed: none (gate-status form left unfilled).
Question: Default branch main / A different branch / A pull request / Cancel. After an answer, e.g. `qlty-sonar-read.py gate-status --project AndreHahm_andres-cc-marketplace --branch main` (not run).
