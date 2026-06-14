# Async Framework Bugs Exposed by Tool Reverts

All tool-side workarounds listed here have been reverted. Each section names the tool,
shows the original workaround commit, describes the framework behavior that caused it,
and states what the framework needs to fix.

---

## 1. `selected="true"` defaults applied when test supplies explicit value

**Tools:** `tools/multigsea`, `tools/hybpiper`, `tools/deseq2`, `tools/varvamp`  
**Commits reverted:** `847134f07`, `cb5b3b675`, `868d16c6a`

### multigsea
`<param name="databases" type="select" multiple="true">` has `selected="true"` on kegg,
reactome, wikipathways and pathbank. Tests set `value="kegg"` (one database). In the async
path `fill_static_defaults` / `_fill_default_for` fills *all* `selected="true"` options as
defaults, so all four databases run instead of one.

Workaround applied: removed `selected="true"` from three options.  
**Framework fix needed:** when the async request includes an explicit value for a
multi-select, `fill_static_defaults` must not overlay `selected="true"` defaults on top.

### hybpiper
`stats_type_select` and `sequence_type_select` multi-select params have `selected="true"`
on `gene` and `dna` options. An `expect_failure` test does not supply these params. Async
fills the selected defaults, making the test "pass" when it should fail.

Workaround applied: added `value_json="[]"` in the test to force empty selection.  
**Framework fix needed:** same as multigsea; don't fill multi-select defaults when the
caller has omitted the param entirely in a context where absence is intentional.

### deseq2
`output_selector` multi-select in section `output_options` has `selected="true"` items.
Tests that omit `output_selector` get those defaults applied by the async path and produce
extra outputs.

Workaround applied: added `<section name="output_options"><param name="output_selector"
value_json="[]"/></section>` to every affected test.  
**Framework fix needed:** same root cause.

### varvamp
Four optional multi-select output params (`scheme_outputs`, `aln_cons_outputs`,
`plot_outputs`, `misc_outputs`) have `selected="true"` items. Test 4 sets them to
`value_json="null"` to produce one output. The async path ignores `null` for optional
multi-selects and applies the selected defaults, producing 8 outputs instead of 1.

Workaround applied: changed `expect_num_outputs="1"` → `"8"` and removed the four null
overrides.  
**Framework fix needed:** honour an explicit `null` value for an optional multi-select (i.e.
treat it as "no selection") rather than overwriting it with `selected="true"` defaults.

---

## 2. Absent conditional: async picks wrong when-branch instead of `selected="true"` default

**Tools:** `tools/quast`, `tools/humann`, `tools/allegro`, `tools/gemini`  
**Commits reverted:** `815547719`, `1c1a5c327`, `0ad19ab6d`, `41229a6c7`

### quast
Tests 06 and 07 omit the `assembly` conditional. The `use_ref` param inside it has
`selected="true"` on `false`. Async picks the *first* option (`true`) instead of the
selected default, generating extra reference-based outputs.

Workaround applied: added explicit `<conditional name="assembly"><param name="type"
value="genome"/><conditional name="ref"><param name="use_ref" value="false"/></conditional>
</conditional>` to both tests.  
**Framework fix needed:** when a conditional is absent from the request, initialise it with
the `selected="true"` default value (equivalent to what `fill_static_defaults` should do
for conditionals whose test param has a default when).

### humann
A `wf` conditional is omitted from one test. Without an explicit discriminator, async
cannot determine the active when-branch.

Workaround applied: added `<conditional name="wf"><param name="selector" value="none"/>
</conditional>`.  
**Framework fix needed:** same as quast.

### allegro
`cond_haplotypes` and `cond_steps` conditionals were missing explicit discriminator params
in two tests.

Workaround applied: added `<param name="opt_haplotypes" value="no"/>` and
`<param name="extra_steps_type" value="STEPS"/>`.  
**Framework fix needed:** same as quast.

### gemini (gemini_query)
`mutation_status` conditional was missing an explicit discriminator.

Workaround applied: added `<conditional name="mutation_status"><param name="status_select"
value="Somatic"/></conditional>`.  
**Framework fix needed:** same as quast.

---

## 3. Duplicate `<section>` blocks in the same test: only first is merged

**Tool:** `tools/novoplasty`  
**Commit reverted:** `847134f07`

Test 1 for novoplasty had two separate `<section name="assembly_options">` blocks:

```xml
<!-- first block (genome range, type) -->
<section name="assembly_options"> ... </section>
<!-- other sections -->
<section name="assembly_options">
    <param name="extend_seed_directly" value="no"/>
    <param name="kmer" value="40"/>
</section>
```

`_merge_into_state()` initialises the section dict on the first encounter. The second block
is never merged, so `extend_seed_directly=no` and `kmer=40` are silently dropped (tool runs
with default `kmer=39`).

Workaround applied: moved `extend_seed_directly` and `kmer` into the first section block.  
**Framework fix needed:** `_merge_into_state()` in `lib/galaxy/tool_util/parameters/case.py`
must merge all sibling blocks with the same section name instead of ignoring subsequent ones.

---

## 4. `_input_for` short-name fallback picks wrong match for ambiguous names

**Tool:** `tools/spapros`  
**Commit reverted:** `868d16c6a`

`celltypes` appears both as `analysis.celltypes` and as a parameter inside
`figure_options_masked_dotplot.celltypes`. `_input_for()` falls back to short-name lookup
when the prefixed name is not found; it returns the *first* match — in this case the wrong
`analysis.celltypes` — instead of the intended `figure_options_masked_dotplot.celltypes`.

Workaround applied: moved `<param name="celltypes">` inside a
`<section name="figure_options_masked_dotplot">` wrapper in the test.  
**Framework fix needed:** `_input_for()` in `lib/galaxy/tool_util/parameters/case.py` should
prefer an exact prefixed match and only fall back to short-name as a last resort; when
multiple params share a short name, the fallback should not be used.

---

## 5. `filter` expressions with `is True` / `is true` fail against string truevalues

**Tool:** `tools/hybpiper`, `tools/picrust2/place_seqs`  
**Commits reverted:** `815547719`

### hybpiper (heatmap output filter)
The original filter:
```xml
<filter>job_conditional['hybpiper_job'] == 'stats' and job_conditional['heatmap'] and job_conditional['heatmap'] is true</filter>
```
In the async path `job_conditional['heatmap']` holds the string `"true"` (the truevalue),
not the Python singleton `True`, so `is true` evaluates to `False` and the heatmap output
is suppressed even when the user selected it.

Additionally, the `heatmap` param had no `truevalue`/`falsevalue`, which caused the async
path to store the string `"false"` (truthy) when unchecked. `truevalue="true" falsevalue=""`
was added to fix this, which is a valid falsevalue pattern but was paired with the wrong
filter.

**Reverted param change:** removed `truevalue="true" falsevalue=""` (back to no explicit
truevalue/falsevalue — defaults are `"true"` and `"false"`).  
**Reverted filter change:** restored `is true` check.  
**Framework fix needed:** filters that reference boolean parameters should receive the Python
`True`/`False` object, not the truevalue/falsevalue string. Alternatively,
`populate_state_async` must call `to_python()` on boolean values to normalise them before
storing in state, so filter expressions see consistent types.

### picrust2/place_seqs (intermediate_check output filter)
Same issue: `intermediate_check is True` fails because the async path stores the string
`"intermediate_check"` (the truevalue) rather than Python `True`.

**Reverted change:** restored `intermediate_check is True`.  
**Framework fix needed:** same as hybpiper — boolean params in state must hold Python
`True`/`False`, not their truevalue string.

---

## 6. `format=` additions (accepted format widening)

**Tools:** `tools/bwameth`, `tools/meningotype`, `tools/metawrapmg`, `tools/repeatmodeler`  
**Commit reverted:** `e056c3ac8`

The async path fails when a test supplies a `.fasta.gz` file to a param declared
`format="fasta"` because the file extension does not match. The workaround widened the
accepted formats to `"fasta,fasta.gz"`. Instead:

- Tests must supply the correct `ftype=` attribute so the async path knows the intended
  format. These `ftype=` attributes were added and are kept.
- The `format=` attribute on the param definition must not be changed — if the tool truly
  does not accept gzipped FASTA, the test data should use plain FASTA files.

**Reverted:** `format="fasta,fasta.gz"` → `format="fasta"` on all four param definitions.  
**Framework fix needed / test note:** if the tool really does accept `.fasta.gz` input, a
PR to each repository should widen the format with proper testing, not as a side-effect of
an async compatibility fix.

---

## 7. `falsevalue="false"` → `falsevalue=""` (biscot)

**Tool:** `tools/biscot`  
**Commit reverted:** `e056c3ac8`

`log_file` boolean param had `falsevalue="false"`. The async path was storing the string
`"false"` (truthy in Python) so `<filter>log_file</filter>` produced a log output even when
unchecked. The workaround changed `falsevalue` to `""` (empty string, falsy).

**Reverted:** `falsevalue=""` → `falsevalue="false"`.  
**Framework fix needed:** same as §5 — boolean params in state must hold Python `True`/
`False`, not their truevalue/falsevalue string, so filter expressions behave consistently.

---

## 8. Tool restructurings (param renames, command changes)

These are changes that altered the public tool API to remove ambiguity that confused the
async parameter parsing.

### hisat2 — repeat renamed `read_groups` → `rg_tags` (commit `41229a6c7`)
The repeat named `read_groups` lived inside a conditional also named `read_groups`,
creating path `adv|sam_options|read_groups|read_groups`. `is_in_state()` in
`lib/galaxy/util/permutations.py` has a missing `return` on recursive calls (see
`async-submission-tool-test-bugs.md`), which causes the nested repeat to be silently
dropped. The workaround renamed the repeat to `rg_tags`.

**Reverted:** repeat name and all command/test references restored to `read_groups`.  
**Framework fix needed:** add missing `return` in `is_in_state()`.

### mlst — param `scheme` renamed to `scheme_manual`; command split (commit `41229a6c7`)
The `scheme` text param inside the `manual` when-branch had the same short name as
`set_scheme` (the conditional discriminator), causing `_input_for()` short-name fallback to
pick the wrong param. The workaround renamed it to `scheme_manual` and split the `list or
manual` elif branch.

**Reverted:** param name and command restored to original.  
**Framework fix needed:** same as §4 (short-name fallback must not fire on ambiguous names).

### gatk4 (Mutect2) — `tumor` param hoisted out of conditional (commit `1c1a5c327`)
`tumor` was a data param inside both `tumor_only` and `somatic` when-branches. The async
path could not find it because the test was not fully specifying the conditional context.
The workaround moved `tumor` to the top level and simplified the command.

**Reverted:** `tumor` is back inside both when-branches; command restored.  
**Framework fix needed:** the async path must correctly resolve data params inside
conditionals when the conditional context is provided in the request.

---

## 9. picrust2/pathway_pipeline — `intermediate_check` removed from test

**Commit reverted:** `cb5b3b675`

`<param name="intermediate_check" value="false"/>` was removed from test 2. This masked
the same boolean filter bug (§5) — with the value absent the filter expression
`intermediate_check` evaluated as falsy (VISITOR_UNDEFINED or None), which happened to
give the same result as `False`. Restoring the explicit `value="false"` will expose the bug.

**Framework fix needed:** same as §5.
