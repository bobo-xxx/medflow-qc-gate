# Design: Wrap qc-gate Reference Implementation

## Architecture

Single Python entry point (`scripts/main.py`) that:
1. Parses CLI arguments (--mat, --map, --control-name, --treat-name, --outdir, --confirm)
2. Reads input matrix (CSV) and group map (CSV)
3. Validates group structure (exactly 2 groups)
4. Matches control/treatment names
5. Cleans data (replace spaces, normalize hyphens to dots)
6. Writes validated matrix, group map, and confirm YAML
7. Reports gate decision (pass/fail) via NDJSON stdout

## SKILL.md v2 Frontmatter Design

```yaml
name: qc-gate
description: Quality control gate — validates merged expression data, confirms group assignments, detects outliers, outputs pass/fail decision.

inputs:
  - name: matrix.csv
    format: csv
    semantic_type: expression_matrix
    description: Gene expression matrix (genes x samples)
  - name: groups.csv
    format: csv
    semantic_type: group_mapping
    description: Sample-to-group assignment mapping

outputs:
  - name: validated_matrix.csv
    format: csv
    semantic_type: expression_matrix
    description: Cleaned expression matrix
  - name: validated_groups.csv
    format: csv
    semantic_type: group_mapping
    description: Validated group mapping with color assignment
  - name: confirm.yaml
    format: yaml
    semantic_type: qc_confirm
    description: QC confirmation metadata (group names, sample counts, dataset name)

entry: scripts/main.py

parameters:
  - name: --mat
    type: file
    required: true
    bind: upstream
    description: Input expression matrix CSV
  - name: --map
    type: file
    required: true
    bind: upstream
    description: Input group mapping CSV
  - name: --control-name
    type: string
    required: true
    bind: config
    description: Name of the control group
  - name: --treat-name
    type: string
    required: false
    default: ""
    bind: config
    description: Name of the treatment group (auto-detected if empty)
  - name: --data-set-name
    type: string
    required: false
    default: ""
    bind: config
    description: Human-readable dataset name for confirm output
  - name: --outdir
    type: file_out
    required: true
    bind: framework
    description: Output directory

exceptions:
  - exit_code: 1
    pattern: "FileNotFoundError"
    nature: data_insufficient
    action: halt
  - exit_code: 2
    pattern: "group count is not 2"
    nature: data_mismatch
    action: skip_with_warning

hardware:
  memory_gb: 1
  cpu: 1
  gpu: false
  runtime: "< 1 minute"
```

## Data Flow

```
Input Matrix (CSV)  ─┐
                      ├─> main.py ──> validated_matrix.csv
Input Groups (CSV)  ─┘              ──> validated_groups.csv
                                    ──> confirm.yaml
                                    ──> stdout: NDJSON (info + result)
```

## Environment

Python 3.9+ with pandas and pyyaml. Declared in `envs/env-py.yaml`.
