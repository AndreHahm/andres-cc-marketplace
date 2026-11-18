BASELINE. Notes docs/ci.md routes findings to resolving-analysis-findings but does not use it.
Plan: 1. curl api/issues/search for the issue (approval). 2. read file, curl api/rules/show. 3. ask: mark false positive / accept / fix code / cancel; ask for reason.
4. `curl -X POST (token as basic auth) https://sonarcloud.io/api/issues/do_transition -d issue=<full key> -d transition=falsepositive` and api/issues/add_comment (approval). 5. re-check.
Nothing run.
