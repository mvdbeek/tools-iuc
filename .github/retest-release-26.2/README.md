This branch reruns the 12 tool tests plausibly fixed by galaxyproject/galaxy#24535,
merged into release_26.2 on 2026-10-29. Tool wrappers and fixtures remain at the
original tools-iuc revision 689ea0f9138e069fcf0df9d862f2fe3c43769a44.

`previous-failures.json` contains only the IDs, status, tool/version and index
fields from the failing reports in upstream run 40652176226. Explicit wrapper
paths select exactly those 12 cases; the final check requires all 12 cases to be
present exactly once and successful across the four jobs.
No unrelated test definitions are deleted or altered.

The action-level previous-run-id support was merged in planemo-ci-action#69 and
is available in v1.0.32, but tools-iuc's weekly workflow does not expose it.
That helper downloads the same-numbered chunk artifact from the current repo.
There is also a functional limitation in Planemo 0.75.47: BaseEngine.test filters
--failed against tc._test_id/tc.index, but embedded XML tool tests are
ExternalGalaxyToolTestCase instances without _test_id. They are all dropped.
This was reproduced with the actual failed Velvet report and unchanged wrapper:
Planemo reported "No tests were executed" without starting Galaxy.

This fork run therefore passes explicit XML paths directly to planemo test,
using the same action to install the same dependencies and the same test flags.
The small checked-in selection from the upstream report verifies coverage;
it does not rely on the broken --failed filter or artifact chunk layout.

The older fork experiment also exists on branch batch-test-async-submission as
.github/workflows/async-submission-test.yaml. It used a hard-coded repository
subset, not a generally exposed subset/retest input in the upstream weekly CI.

Push to ci/retest-release-26.2-compatibility to trigger this workflow on
mvdbeek/tools-iuc only. It also declares workflow_dispatch. The Galaxy revision
and action revision are pinned in the workflow; update GALAXY_REVISION to a new
release_26.2 SHA for subsequent checks. TMPDIR uses RUNNER_TEMP to keep Planemo's
Galaxy instance on disk on Ubuntu 26 runners. Per-test timeout is 900 seconds.
