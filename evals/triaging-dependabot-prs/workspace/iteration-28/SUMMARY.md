# Iteration 28

New eval 25 (scenarios 73 and 74), for the two residuals the security review left open on the issue #741 change:
step 6.6 now passes `--expected-head-sha` on every merge, so a push after 6.4 is not merged unchecked, and an added
package from a non-PyPI index (or a pnpm `tarball:` resolution) is `unknown` without a lookup. One simulated answer
from a general-purpose subagent that read the updated skill, graded by the author. No baseline: the pre-change skill
has neither the head-lockfile check nor the merge pin, which eval 23's baseline and `merge-pr` eval 18's baseline
already show.

| Eval | with_skill |
|---|---|
| 25: The merge is pinned to the head 6.4 checked, and an off-registry added package is never looked up | 5 of 5 |
