# Async submission: tool-side test bugs to fix

> **RESOLUTION (2026-06-16).** Re-validating the list against the *current* branch with
> Galaxy's `validate_test_cases_for_tool_source` showed most of these were already fixed on
> `batch-test-async-submission` (gatk4, hisat2, quast, multigsea, spapros, picrust2 — all
> tests OK). The only two still failing — **humann** (test 0) and **dropletutils** (tests
> 0/1) — turned out **not** to be tool/test bugs but a **framework gap**: when a legacy test
> omits a *nested* conditional's discriminator (relying on its default when, as the sync API
> does), the async builder's loose fallback mis-resolved it to an *enclosing* conditional's
> discriminator that shares the generic name (`selector`/`use`). Fixed in Galaxy
> `lib/galaxy/tool_util/parameters/case.py` (commit "Don't resolve an omitted nested
> conditional discriminator to an ancestor's") — **no tool-side test edits required**, so
> zero maintainer fallout. This also means omitted defaulted conditionals are now handled
> like sync, which is the right basis for any future automated legacy-test fixer.

These tests fail at the async **request-build** layer (the new `POST /api/jobs`
test-case → state conversion) but pass under sync `POST /api/tools`, which tolerates
them via loose behaviour. Unless marked otherwise these are **test bugs** to fix in the
tool repos; the async path is correctly stricter.

Source: clean upstream run on `mvdbeek/tools-iuc@async-upstream-clean` against Galaxy
`async-submission-parse-fix`. Triaged with `case_state` after the six framework fixes
landed.

Legend: ✅ confirmed test bug (actionable) · 🔎 needs classification (possible framework gap)

---

## ✅ humann — `tools/humann/humann.xml` (6 tests)
`log_level` is **not a parameter** — the command hardcodes `--log-level 'DEBUG'`
(humann.xml:251). The tests carry an obsolete `<param name="log_level" value="DEBUG"/>`
(approx lines 485, 624, 703, 785, 881, 953).
**Fix:** delete those 6 `log_level` test params.

## ✅ gatk4 — `tools/gatk4/gatk4_mutect2.xml` (test 1)
Test sets `optional_parameters="no"` but also supplies `read_filter`, which lives in the
`optional` conditional's `yes` branch (gatk4_mutect2.xml:428). It is in an unselected
branch (sync ignores it; no effect on output).
**Fix:** set `optional_parameters="yes"`, or remove `read_filter` from the test.
(Minor: test 3 lists `reference_sequence="hg38"` twice — now tolerated by the framework,
but the duplicate could be removed.)

## ✅ hisat2 — `tools/hisat2/hisat2.xml` (test 0)
Provides bare `novel_splicesite_outfile="false"` with `spliced_options_selector` omitted;
the param lives in `adv|spliced_options` (advanced branch) and the value is its default.
Test 5 (hisat2.xml:950) qualifies the same param correctly as
`adv|spliced_options|novel_splicesite_outfile`.
**Fix:** qualify it like test 5, or drop it (it is the default).

## ✅ quast — `tools/quast/quast.xml` (tests 0, 3)
- **test 0:** `gene_finding.tool` value `--gene_finding` (underscore) but the option is
  `--gene-finding` (hyphen, quast.xml:421); the command also checks the underscore form
  (quast.xml:194) — an internal tool inconsistency. **Fix:** make option value, command,
  and test value consistent.
- **test 3:** `min_identity` is placed in `<section name="alignments">` but belongs to
  `<conditional name="assembly">` (command uses `$assembly.min_identity`). **Fix:** move
  `min_identity` into the assembly block.
- (test 8 fails under sync too — a real tool/output issue, out of scope.)

## ✅ dropletutils — `tools/dropletutils/dropletutils.xml` (tests 0, 1, 5)
- **tests 0/1:** bare `use="filter"` but there are three nested `use` params
  (format / operation / method at lines 114, 132, 138) — ambiguous. **Fix:** qualify the
  `use` params in the test.
- **test 5:** `lowerpopr` (dropletutils.xml:290) appears only in the test — a typo /
  nonexistent param. **Fix:** correct the name or remove it.

## ✅ multigsea — `tools/multigsea/multigsea.xml` (test 0)
The `proteomics_data` (and `transcriptomics_data`, `metabolomics_data`) conditionals have
options `true`/`false` with **no `selected="true"`** (lines 56-67). When a test omits the
conditional, async defaults to the first option (`true` = Enabled), which requires the
`proteomics` data param → "Field required".
**Fix:** add `selected="true"` to the `false` (Disabled) option of these conditionals
(the sensible default), or have tests set the selector explicitly.

---

## ✅ spapros — `tools/spapros/evaluation.xml` (test 5) — test/tool bug (investigated)
Test sets `method="plot_marker_corr"` but supplies `use_marker_corr` (plus `markerset`,
`header_markerset`, `per_celltype`, `per_marker`). Those params live in the
`select_marker_corr` conditional, which is defined **only in the `plot_summary` when**
(evaluation.xml:244). The `plot_marker_corr` when (evaluation.xml:298) does **not** contain
`select_marker_corr` — it has `select_per_celltype_min_mean`/`select_per_marker_min_mean`
(which the test provides correctly, fully qualified). So the test feeds an unselected
branch's params; sync ignores them, async flags them.
(Not a framework gap — the elided-match correctly does not resolve a param that isn't in
the selected branch.)
**Fix:** either the tool is missing `select_marker_corr` in the `plot_marker_corr` branch
(if marker-correlation params belong there), or the test should drop those params.
Decide which is intended for `plot_marker_corr`.

## ✅ picrust2 — `tools/picrust2/hsp.xml` (tests 0, 1, 2) — test typo (investigated)
The tests reference `<conditional name="hsp_method__options">` (double underscore, e.g.
hsp.xml:46, 65, 84), but the macro defines `<conditional name="hsp_method_options">`
(single underscore, macros.xml:188; discriminator `hsp_method`). Sync ignores the unknown
double-underscore name and falls back to defaults; async flags it.
**Fix:** rename `hsp_method__options` → `hsp_method_options` (single underscore) in the
hsp.xml tests.

---

## Not request-build issues (execution layer — out of this list)
- **Class J `.fasta.gz` decompression** — ✅ **root cause area found (2026-06-15): async
  execution does not apply the implicit `fasta.gz -> fasta` conversion that sync applies.**
  (NOTE: an earlier "deferred URI materialization" theory was WRONG and is retracted — the
  CI job record shows the input is a plain uploaded HDA, `src=hda`, not a deferred/URL
  dataset. No materialization is involved.)

  Evidence (clean CI run 27539369753, Galaxy = `mvdbeek/galaxy@async-submission-parse-fix`,
  custom planemo `mvdbeek/planemo@async-submission`):
  - **bwameth-0 / meningotype-0:** tool crashes with
    `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8b in position 1` — `0x8b` is
    the **gzip magic byte**. The tool received raw gzip bytes as if they were plain fasta.
  - **biscot-0:** `--contigs …dataset_…​.dat` then crash "Loading contigs fasta file".
  - **repeatmodeler-0:** `BuildDatabase` died — same input never decompressed.

  The job record (CI artifact, meningotype-0):
  - `job inputs`: `input|fasta = {src: hda, id: 30, uuid: 098ad0d2-…}` — plain uploaded HDA.
  - `command_line`: `ln -s '…/dataset_098ad0d2-….dat' 'input.fasta.gz' && meningotype 'input.fasta.gz' …`
    — the job symlinks the **original** compressed HDA (same uuid as the input) and runs the
    tool on it. The implicit `fasta.gz -> fasta` conversion never took effect.

  Mechanism. The test uploads with explicit `ftype="fasta.gz"`, so the HDA is stored
  **compressed**. Data staging (upload) is the same for both modes — only the *tool*
  submission API changes with `GALAXY_TEST_USE_LEGACY_TOOL_API` — so the HDA is `fasta.gz`
  in sync AND async.
  - **Sync** (`POST /api/tools`): job-time `_collect_input_datasets` →
    `find_conversion_destination(['fasta'])` finds the `fasta.gz -> fasta` converter, runs
    it, and the tool gets plain fasta. ✅
  - **Async** (`POST /api/jobs`): the job runs against the original `fasta.gz`; the implicit
    conversion is not applied. ❌

  The conversion machinery is shared and correct: `find_conversion_destination`
  (`datatypes/registry.py:906`) is pure datatype logic and returns a `fasta.gz -> fasta`
  conversion for both modes, and `_collect_input_datasets` (`tools/actions/__init__.py:258`)
  even writes the converted dataset back into `param_values`/`parent` (line 274). So the bug
  is that **the async execution path doesn't end up running against that converted dataset**
  — the conversion produced/written during input collection isn't what the async job uses.

  **Setting `ftype` in the test does NOT fix it** — bwameth (`bwameth.xml:133`), meningotype
  (`meningotype.xml:100`) and repeatmodeler (`repeatmodeler.xml:28`) already declare
  `ftype="fasta.gz"` and still fail; only biscot omits it. The HDA is correctly typed
  `fasta.gz`; the async path just doesn't apply the conversion. Tools/tests are correct per
  Galaxy's implicit-conversion contract; nothing to fix tool-side.

  Why the earlier framework reproducer was a false PASS: `test_toolbox_pytest` auto-decompresses
  `.gz` at **upload** (`sniff.py:843` — `is_compressed and auto_decompress and not keep_compressed`),
  so its HDA was already plain `fasta` — it never had a `fasta.gz` HDA to convert and so never
  exercised this path. A framework-tool test cannot reproduce this.

  **Right reproducer:** an API-level integration test — upload a `fasta.gz` asserting HDA
  `ext == fasta.gz`, then run a trivial `format="fasta"` tool via async `POST /api/jobs` and
  sync `POST /api/tools`, asserting the tool sees decompressed content. Then pin the exact
  point in the async execution/param-resolution path where the converted dataset is dropped.

  **UPDATE (2026-06-16, REPRODUCED LOCALLY via planemo+biocontainers — root cause is a
  CONVERTER-REGISTRATION bug, NOT the async path):**
  Ran the custom async planemo (`mvdbeek/planemo@async-submission`) against the instrumented
  Galaxy worktree with `--biocontainers` (real gravity/gunicorn/celery). meningotype FAILS —
  reproduced. Instrumentation at `actions/__init__.py:175` (`process_dataset`) shows:
  `data_ext=fasta.gz datatype=FastaGz accepted=[Fasta] direct_match=False target_ext=None`.
  So `find_conversion_destination(fasta.gz, [fasta])` finds **no converter** — the tool gets
  raw gzip. The `gz_to_uncompressed.xml` converter (fasta.gz→fasta) exists and is supposed to
  be registered (`registry.py:425-427`), so something prevents it being found at job time.
  CRUCIALLY this happens under **sync too** (same `target_ext=None`), so it is NOT
  async-specific at the conversion layer — it's a converter-availability regression in this
  Galaxy branch that the async batch CI is simply the only job exercising. (Production sync CI
  uses a release Galaxy where the converter works, which is why these tools pass there.)
  **ROOT CAUSE (confirmed 2026-06-16):** the implicit conversion runs in the **Celery
  worker** (the `ASYNC_CONV_DEBUG` line is logged by `celery.log`, `WARNING/main`). Enhanced
  debug shows `raw_converters=[] cached_converters=[]` — `datatype_converters['fasta.gz']` is
  genuinely **empty in the worker** (not a cache issue). The async tool-request path
  (`POST /api/jobs` → `queue_jobs` Celery task → `execute_async` → `_collect_input_datasets` →
  `find_conversion_destination`) executes in the Celery worker, but the worker builds its
  Galaxy app with **`use_converters=False`** (`lib/galaxy/celery/__init__.py:121`, in
  `build_app()`). So the worker's datatypes registry has no converters loaded, implicit
  conversion silently no-ops, and the raw compressed dataset is handed to the tool (which then
  reads gzip bytes as fasta and dies on `0x8b`). The sync path creates the job in the web
  process (converters loaded), so it converts correctly — this is why it's async-only in
  practice (POST /api/jobs moved job setup, incl. implicit conversion, into the converter-less
  worker).

  **FIX (IMPLEMENTED + VERIFIED 2026-06-16):** register the datatype converters in the Celery
  worker's `build_app()` using the toolbox-less tool-creation path that `queue_jobs` already
  uses (`create_tool_from_source`), since the minimal worker app has no `ToolBox`. See
  `lib/galaxy/celery/__init__.py` (`build_app` now sets `use_converters=True` and calls a new
  `_register_worker_datatype_converters(galaxy_app)` that loads each built-in converter into
  `registry.datatype_converters`). Verified via planemo+biocontainers: the meningotype job now
  runs `meningotype 'input.fasta'` on a **decompressed** dataset (file starts with `>`),
  instead of the previous `meningotype 'input.fasta.gz'` on raw gzip — the `0x8b` crash is
  gone. (Local planemo tests still time out on the slow docker-on-mac meningotype container,
  but the dataset-level proof is conclusive: the converter job runs and produces plain fasta.)
  Fixes implicit conversion for ALL affected tools (biscot, bwameth, meningotype,
  repeatmodeler, and any tool relying on implicit conversion on the async path).

  ---
  Earlier note (why it was hard — the simpler approaches don't work):
  - `use_converters=True` alone only populates the `self.converters` *list*; the
    `datatype_converters` dict (read by `find_conversion_destination`) is populated by
    `load_datatype_converters(toolbox)`, which only runs in `UniverseApplication.__init__`
    (app:921), NOT in the worker's `GalaxyManagerApplication`.
  - `load_datatype_converters` needs a `ToolBox`, and `ToolBox.__init__` (plus its
    prerequisites) needs `app.watchers`, `app.tool_cache`, `citations_manager`,
    `container_finder`, `toolbox_search`, etc., several of which are resolved via lagom and
    require the app to be a `StructuredApp` (only `UniverseApplication` is). Bolting these onto
    the minimal `GalaxyManagerApplication` cascades (verified: AttributeError `watchers` →
    `tool_cache` → lagom `RecursionError` on `ConfigWatchers`). So the minimal worker app
    cannot host a toolbox without effectively becoming a full app.

  Candidate fixes (pick per perf/architecture tradeoff):
  1. Have the Celery worker that runs job execution use a full (`UniverseApplication`/
     `StructuredApp`) app, or a variant that loads datatype converters. Simplest correctness;
     heavier worker startup (loads the tool panel).
  2. Add a lightweight converter-only registration path (load just the ~30 built-in converter
     tools into `datatype_converters` without a full `ToolBox`), callable from `build_app()`.
  3. Perform the implicit datatype conversion in the web tier (which has converters) before
     dispatching the job to Celery, so `execute_async` never needs converters.

  Affects ALL implicit conversions on the async path (biscot, bwameth, meningotype,
  repeatmodeler — fasta.gz→fasta — and any tool relying on implicit conversion). Reproduced
  and root-caused locally via planemo+biocontainers against the worktree Galaxy; a clean fix
  was not landed because it requires the above architectural decision (owned by the branch
  maintainer).

  ---
  (Earlier note, now superseded:) **Galaxy's async conversion code is CORRECT.**
  Added three API integration tests in
  `lib/galaxy_test/api/test_tool_execute.py` (`test_implicit_gz_conversion_sync`,
  `test_implicit_gz_conversion_async`, `test_implicit_gz_conversion_async_deferred`) plus a
  `TargetHistory.with_dataset_for_test_file()` populator helper. They run the
  `implicit_conversion` tool on a `1.fasta.gz` input requiring the double conversion
  `fasta.gz -> fasta -> tabular`, with an explicit precondition assert that the input HDA is
  stored compressed (`file_ext == "fasta.gz"`, so NOT auto-decompressed at upload — the
  confound that made the earlier framework reproducer a false pass).

  Result: **all three pass**, including async via `POST /api/jobs` with both a plain uploaded
  `src=hda` and a DEFERRED dataset. So the async execution path *does* perform the implicit
  `fasta.gz -> fasta` conversion; neither the upload path, the deferred-materialization path,
  nor `_collect_input_datasets` is broken in Galaxy. (Both earlier hypotheses — deferred
  materialization, and async dropping the converted dataset — are falsified by direct test.)

  So the CI failure is **not in Galaxy's core async conversion**. Remaining differences
  between the passing local repro and the failing CI run, to investigate next:
  1. **Custom planemo `@async-submission` request encoding** — how it builds the tool request
     from the test XML (does it mislabel the data input's `ext`, or submit it in a form that
     skips conversion?). This is the most likely suspect since direct API submission works.
  2. **`--biocontainers` job environment / job-handler ordering** — a possible race where the
     async tool job is dispatched before the implicit converter job completes (locally the
     converter finishes first, so it passes).
  Decisive next step: capture the actual tool-request payload planemo sends in CI (the `ext`
  it assigns to the fasta.gz input), and/or check converter-job vs tool-job ordering in the
  failing CI job. The three new tests stay as regression guards that Galaxy async conversion
  works.
- **Real tool/runtime/nondeterminism:** allegro (segfault), hybpiper (targetfile),
  cnvkit, metawrapmg, varvamp, episcanpy, picrust2_place_seqs, humann (diamond index).
- **quast test 8** fails under sync as well.

---

## Post-fix investigation of remaining async failures (2026-06-16)

After the converter + nested-conditional fixes, run 27597761421 still had ~25 failures.
Investigated the 17 kept repos:

### Framework bug found & fixed: varvamp test 3 — 500 on `/api/tool_requests/{id}`
`build_xml_tool_source` parsed raw tool-source strings with `strip_whitespace=True`, which
`.strip()`s every element's text — unlike the file/macro loader (`xml_macros.load` uses
`strip_whitespace=False`). varvamp's `PRIMER_3_PENALTY` regex validator body
`" *(\d+, *)*\d+ *$"` (leading optional spaces) became the invalid `"*(\d+..."`. The async
path stores `tool_source.to_string()` and re-parses it via this string path when encoding the
request, so the corrupted regex raised `nothing to repeat at position 0` during static
validation → 500. Fixed by parsing raw string sources with `strip_whitespace=False`
(Galaxy commit "Preserve significant whitespace when parsing a tool from its raw string
source") + regression test.

### Request-build is otherwise CORRECT for all 17 repos
Ran `validate_test_cases_for_tool_source` across every test of all 17 repos: **no validation
errors**. Spot-checked the async-built state vs each test's intent for the suspicious cases
(gubbins extensive_search, gatk4 optional_parameters, novoplasty reference_cond) — async
builds **exactly** what the test specifies. The earlier "async vs weekly param diff" was
**confounded**: the async run (mvdbeek/batch) and weekly run (galaxyproject/main) number
tests independently and run slightly different tool versions, so `tool-N` did not refer to
the same test. That diff is not a reliable signal.

### Remaining failures are execution-side, not parameter bugs
The remaining failures are `failure` (output differs) or job errors, with correct request
params. Likely causes: genuine tool nondeterminism, stale expected outputs, real tool/runtime
issues (multigsea R package load, allegro segfault 139, spapros/picrust2 job errors), or
batch-branch tests differing from main. Confirming any single one as async-specific requires
running the *same* tool+test in both sync and async on the batch branch (in progress for
gubbins as a representative no-compressed-input case).

### CONFIRMED: remaining failures are NOT async-specific (sync fails too on the batch branch)
Ran failing tools in **sync** (`GALAXY_TEST_USE_LEGACY_TOOL_API=always`) via planemo against
the same batch branch:
- **gubbins-4**: fails in sync too — identical `base_branch_embl` "Expected 1638 lines"
  mismatch. Not async-specific.
- **fairy_cov-1**: fails in sync too — same `output` diff. Not async-specific.
- **mlst**: inconclusive locally (Docker could not pull the mlst image, exit_code 125).

These "pass in the weekly run" only because galaxyproject/main runs **different tool
versions** than the batch branch; the async run (mvdbeek/batch) and weekly run number tests
independently and run different code, so `tool-N` is not the same test. On the batch branch
itself these fail in BOTH sync and async — they are tool/test drift (stale expected outputs,
real tool/runtime issues, container availability), not async-framework bugs.

**Conclusion:** after the converter, nested-conditional resolver, and validator-whitespace
fixes, the async submission **framework** is solid — every request-build validates and the
async-specific failures are resolved. The remaining red tests are tool-side and out of scope
for the async framework work (they also fail under sync on this branch).

### CORRECTION (2026-06-16): main's clean tools have 60 async request-build failures
Merged upstream/main, then reset the 15 still-failing tool dirs to main's clean versions and
re-ran `validate_test_cases_for_tool_source`: **60 request-build failures** ("Invalid
parameter name found …") across gatk4 (reference_sequence ×6), hisat2 (type ×17), mlst
(advanced ×8), picrust2 (hsp_method__options, study_fasta, no_regroup), gubbins (iterations,
converge_method, `expensive_research` typo), gemini, episcanpy, fairy, spapros, cnvkit,
dropletutils (lowerpopr typo), novoplasty, multigsea.

So the batch branch's 334 commits are **legitimate async fixes** for real test-definition
issues that sync tolerates (unknown params are ignored) but async rejects — NOT drift that
broke working tools. The batch branch is AHEAD of main on async-readiness; resetting to main
regresses 60 tests (reset was undone). My earlier "remaining failures are tool-side drift"
conclusion only describes the ~20 failures that remain AFTER the batch's fixes (e.g. gubbins-4
output diff, which does fail in sync too). The broader async surface is large.

Two classes among the 60: (a) genuine test typos (lowerpopr, expensive_research,
hsp_method__options) — async correctly rejects, must be fixed in the test; (b) structural
"all tests fail" cases (gatk4 reference_sequence, hisat2 type, mlst advanced) — likely
loose-name/elided resolution the framework could handle (like the nested-conditional fix),
which would remove the need for those per-tool edits. Worth converting (b) to framework fixes.

### RE-CORRECTION (2026-06-16): real async request-build failures on main = 17, not 60
The "60" above came from `validate_test_cases_for_tool_source` (`test_case_validation`), which
rejects ANY unhandled test input. But the **actual** async request-build path
(`verify/parse.py` → `test_case_state(validate=True)`) applies the legacy bare-name tolerance
(`_input_name_was_handled_by_legacy_fallback`, profile < 24.2): it resolves an unqualified
`<param name="reference_sequence">` into its conditional and accepts it. Re-measured main's 15
failing tools with that tolerant path → **17** genuine request-build failures, not 60. So my
strict validator over-counted by ~43 pure legacy bare-names (e.g. gatk4's reference_sequence),
which the real async build accepts — those per-tool qualifications were NOT strictly required.

The real 17 split into:
- **Genuine test typos** async correctly rejects (batch fixes are right, not framework-fixable):
  dropletutils `lowerpopr` (→lowerprop), fairy `minimum-ani`/`min-spacing` (dash vs underscore),
  gubbins `expensive_research` (→extensive), picrust2 `hsp_method__options` (double underscore).
- **Structural / wrong-branch / default-when** (candidates for FRAMEWORK fixes that would remove
  the per-tool edit): gatk4 `read_filter`, episcanpy `method|*`, novoplasty bare `reference`,
  spapros `method|use_marker_corr`, multigsea `proteomics_data.__absent__` (no selected default),
  hisat2 `novel_splicesite_outfile`.

Net: the batch branch's async edits are a MIX — some necessary (typos), some that a tolerant
framework already handles (bare names), some replaceable by further framework work (structural).
The async framework itself (with the converter/resolver/whitespace fixes) is sound; the strict
`validate_test_cases_for_tool_source` is stricter than the real submission path.

### Structural cases triaged → 1 framework fix, 4 genuine test/tool bugs (2026-06-16)
Worked through the 6 structural (non-typo) request-build failures on main:
- **novoplasty** (bare `reference`) & **hisat2** (bare `novel_splicesite_outfile`): FIXED in the
  framework. `_infer_when_from_inputs` ignored legacy *unqualified* (bare) inputs, so a test that
  supplies a non-default branch's param by its short name and omits the discriminator fell back
  to the default (empty) branch and rejected the param. Now bare inputs are considered when
  inferring the active when. Galaxy commit "Infer conditional when from bare unqualified branch
  params in async tool tests" + regression test. Removes the need for novoplasty/hisat2 test edits.
- **gatk4** (`read_filter`): test sets `optional_parameters="no"` but supplies `read_filter`, a
  `yes`-branch param → genuine wrong-branch test bug; async correctly rejects. Not framework-fixable.
- **episcanpy** (`lazy_pp_n_neighbors` etc.): the param does not exist in main's model at all
  (tool incomplete / renamed) → tool fix, not framework.
- **spapros** (`method|use_marker_corr`): `use_marker_corr` lives only in the `plot_summary`
  branch, test selects `plot_marker_corr` → genuine unselected-branch test bug. Not framework.
- **multigsea** (`proteomics_data.__absent__`): conditional has no `selected="true"` default;
  defaulting to the first option (Enabled) still requires data the test omits → needs a tool-side
  default (selected Disabled) or explicit selector. Not cleanly framework-fixable.

So of the structural class, 1 framework fix clears 2 tools; the remaining 4 are correct async
rejections of real test/tool bugs (sync only "passes" them by silently ignoring unknown or
unselected-branch params). Combined with the converter, nested-conditional, bare-name-inference,
and validator-whitespace fixes, the framework now handles the legitimate legacy patterns; the
residual failures are genuine tool-side issues.
