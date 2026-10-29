This branch reruns the 12 tool tests plausibly fixed by galaxyproject/galaxy#24535,
merged into release_26.2 on 2026-10-29. Tool wrappers and fixtures remain at the
original tools-iuc revision 689ea0f9138e069fcf0df9d862f2fe3c43769a44.

`previous-failures.json` contains only the IDs, status, tool/version and index
fields from the failing reports in upstream run 40652176226. Planemo's shipped
`--failed --failed_json` feature selects those cases; the final check requires
all 12 cases to be present exactly once and successful across the four jobs.
No unrelated test definitions are deleted or altered.

The action-level previous-run-id support was merged in planemo-ci-action#69 and
is available in v1.0.32, but tools-iuc's weekly workflow does not expose it.
That helper downloads the same-numbered chunk artifact from the current repo.
This fork run instead supplies a small checked-in selection from the upstream
report, so it does not depend on same-repository artifact access or chunk layout.

The older fork experiment also exists on branch batch-test-async-submission as
.github/workflows/async-submission-test.yaml. It used a hard-coded repository
subset, not a generally exposed subset/retest input in the upstream weekly CI.

Push to ci/retest-release-26.2-compatibility to trigger this workflow on
mvdbeek/tools-iuc only. It also declares workflow_dispatch. The Galaxy revision
and action revision are pinned in the workflow; update GALAXY_REVISION to a new
release_26.2 SHA for subsequent checks. TMPDIR uses RUNNER_TEMP to keep Planemo's
Galaxy instance on disk on Ubuntu 26 runners. Per-test timeout is 900 seconds.
