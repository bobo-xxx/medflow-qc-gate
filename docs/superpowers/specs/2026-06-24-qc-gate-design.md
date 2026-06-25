---
comet_change: wrap-qc-gate-node
role: technical-design
canonical_spec: openspec
---

# QC Gate Node Technical Design

Date: 2026-06-24

## Technical Approach

Extract the core validation logic from `original/scripts/check_confirm.py` into a standalone Python CLI script. Strip out the internal rules-based framework (MyRule, RuleSet, Cache, ColorAssigner).

### Architecture

Single-file entry point `scripts/main.py` with argparse-based CLI:

```
Input: --mat (expression matrix CSV), --map (group mapping CSV)
Config: --control-name, --treat-name, --data-set-name
Framework: --outdir (output directory)
Output: validated_matrix.csv, validated_groups.csv, confirm.yaml
Stdout: NDJSON lines (info + result)
```

### Key Design Decisions

1. **Drop TCGA-specific logic**: The original `check_tcga.py` handles TCGA-specific file types (counts, FPKM, TPM, clinical). This is not a general QC gate concern. The IRE node only does generic expression matrix + group map validation.

2. **Drop RGS processing**: `check_rgs.py` is simple whitespace cleaning -- merge into main flow.

3. **Drop rules framework**: `original/rules/check.py` and `original/rules/common.py` are Snakemake-adjacent DAG orchestration. The IRE node is a single atomic step.

4. **Default colors**: Use hardcoded control/treatment colors (#1f77b4/#d62728) matching matplotlib defaults.

5. **Python only**: No R dependency. pandas + pyyaml are sufficient.

6. **Single subcommand**: `main.py run` (the run subcommand pattern provides forward compatibility for future subcommands).

### Data Flow

```
--mat (CSV) ─────────────────┐
--map (CSV) ─────────────────┤
                             ├─> validate_groups() ─> exactly 2 groups?
--control-name ──────────────┤                       ├─ match control/treat
--treat-name ────────────────┤                       └─ count samples
--data-set-name ─────────────┤
                             ├─> clean_data() ─> strip spaces, normalize IDs
                             │
                             ├─> write_outputs()
                             │   ├─ validated_matrix.csv
                             │   ├─ validated_groups.csv (with colors)
                             │   └─ confirm.yaml
                             │
                             └─> stdout: NDJSON
```

### Trade-offs and Risks

- The original code has extensive GEO/TCGA data pipeline integration that we're stripping out. This is intentional -- the IRE framework handles data sourcing through separate nodes.
- Auto-detection of groups when control_name is missing is a convenience but could produce unexpected results. Mitigated by warning in NDJSON output.
- No batch effect detection -- that's a separate node concern.

### Testing Strategy

Unit tests with pytest:
- test_valid_input: matching control/treatment groups produce pass decision
- test_auto_detect: control_name not found triggers auto-detection with warning
- test_wrong_group_count: 1 or 3+ groups raises ValueError with data_mismatch
- test_missing_file: FileNotFoundError with data_insufficient
- test_ndjson_output: stdout lines are valid JSON with correct level fields
