## Summary
On Windows, `git-review-fix-diff.py`'s time limit fires but the call returns only when a child process holding git's output pipe exits, so a stalled git can outlast the limit by far

## Environment
- **Product/Service**: git-kit review helper `plugins/git-kit/scripts/git-review-fix-diff.py` (`_show`) and its test `tests/marketplace_ci/test_git_review_fix_diff_script.py`
- **Region/Version**: after the issue 655 branch; Git for Windows 2.56.0.windows.2, Python 3.13, uv
- **Browser/OS**: Windows 11

## Reproduction Steps
1. On native Windows, create a `git.cmd` in a temporary directory that runs the absolute path of `ping.exe` with `-n 31 127.0.0.1`. The `ping` child process keeps the output pipe open for about 30 seconds.
2. Load the script as a module, set `_TIMEOUT_SECONDS` to 1 and call `module._show(str(stalled), "a" * 40)`, where `stalled` is the `git.cmd` from step 1.
3. Time the call. The same shape is in `test_a_stalled_git_is_stopped_at_the_time_limit`, which uses a `#!/bin/sh` git running `sleep 30` on POSIX.

## Expected Behavior
The call raises `TimeoutError` within about the limit (1 second here) and ends or abandons the child. The script's own docs say the limit must not depend on `SIGALRM`, which Windows lacks, and must also end a git whose child process keeps the output pipe open.

## Actual Behavior
`TimeoutError` is raised, so `pytest.raises(TimeoutError)` is satisfied, but the call returns only after about 30 seconds (measured 30.6 s against an `elapsed < 15` assertion). The time limit fires, yet the call is held up until the child exits.

## Error Details
~~~
assert (48336.629076 - 48306.0634133) < 15
AssertionError
~~~

## Impact
**Medium** - On Windows a review helper can take far longer than its documented time limit when a stalled git leaves a child holding the pipe. No known user-facing incident. Only a `.cmd` stand-in was tested, not a real `git.exe` child such as a fsmonitor or hook process.

## Additional Context
- Likely cause (unverified): killing the `cmd.exe` wrapper does not kill its child, so reading the pipe blocks until the child exits.
- Current status: the Windows run of that test is skipped with this reason in its skip text (issue 655 branch). The POSIX run is unchanged.
- Suggested directions: kill the whole process tree on timeout (for example `taskkill /T` or a Windows job object), or stop waiting on the pipe after the limit.
- Related: #655.
