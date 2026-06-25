---
name: qc-gate
description: >
  Quality control gate — validates merged expression data, confirms group
  assignments (control vs treatment), cleans whitespace and formatting issues,
  and outputs validated data files with a pass/fail decision. Applicable to
  any merged gene expression matrix with group metadata. Preconditions:
  expression matrix has been merged from one or more datasets; group mapping
  file is available.
type: standard

inputs:
  - name: matrix.csv
    format: csv
    semantic_type: expression_matrix
    description: >
      Gene expression matrix (genes x samples). First column is gene IDs,
      subsequent columns are sample IDs with expression values.
  - name: groups.csv
    format: csv
    semantic_type: group_mapping
    description: >
      Sample-to-group assignment table. Must contain at minimum a sample ID
      column and a group assignment column.

outputs:
  - name: validated_matrix.csv
    format: csv
    semantic_type: expression_matrix
    description: >
      Cleaned expression matrix with normalized sample IDs (spaces removed,
      hyphens normalized to dots). Always produced.
  - name: validated_groups.csv
    format: csv
    semantic_type: group_mapping
    description: >
      Validated group mapping with columns: ID, group, color. Color assignment
      uses matplotlib defaults (#1f77b4 for control, #d62728 for treatment).
      Always produced.
  - name: confirm.yaml
    format: yaml
    semantic_type: qc_confirm
    description: >
      QC confirmation metadata: control name, treat name, sample counts,
      dataset name, raw and display names. Always produced.

entry: scripts/main.py

parameters:
  - name: run
    type: choice
    required: true
    bind: static
    description: Subcommand — execute QC gate validation.

  - name: --mat
    type: file
    required: true
    bind: upstream
    description: Path to input expression matrix CSV file.

  - name: --map
    type: file
    required: true
    bind: upstream
    description: Path to input group mapping CSV file.

  - name: --control-name
    type: string
    required: true
    bind: config
    description: >
      Name of the control group as it appears in the group mapping file.

  - name: --treat-name
    type: string
    required: false
    default: ""
    bind: config
    description: >
      Name of the treatment group. If empty, auto-detected from the group
      mapping (first non-control group).

  - name: --data-set-name
    type: string
    required: false
    default: "Merged Dataset"
    bind: config
    description: >
      Human-readable dataset name written into the confirm output.

  - name: --color1
    type: string
    required: false
    default: "#1f77b4"
    bind: static
    description: Color for the control group in output group mapping.

  - name: --color2
    type: string
    required: false
    default: "#d62728"
    bind: static
    description: Color for the treatment group in output group mapping.

  - name: --outdir
    type: file_out
    required: true
    bind: framework
    description: Output directory for validated files.

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

file_layout: flat
file_discovery: pattern
---

# Node Function

Perform quality control validation on an expression matrix and its group mapping. The gate confirms that:
1. The input files exist and are readable CSV files.
2. The group mapping contains exactly 2 groups (one control, one treatment).
3. Sample IDs are consistent between the matrix and group map.
4. All sample IDs are cleaned (spaces removed, hyphens normalized to dots).

On success, outputs validated and cleaned versions of the matrix, group map, and a confirm metadata file in YAML format.

# Expected Input

- **Expression matrix CSV**: Genes as rows, samples as columns. First column contains gene identifiers. Expression values must be numeric.
- **Group mapping CSV**: At minimum, column 1 contains sample IDs, column 2 contains group names. Additional columns are ignored.
- **Control name**: The exact string matching a group label in the mapping file.
- **Treatment name (optional)**: If not provided, auto-detected as the non-control group.

# Exceptions

- **FileNotFoundError (exit 1)**: Input matrix or group map does not exist or is not readable. Action: halt pipeline.
- **Group count != 2 (exit 2)**: The group mapping contains fewer or more than 2 distinct groups. QC gate only supports binary comparisons. Action: skip with warning.
- **Control name mismatch**: If the configured control_name is not found among the group labels, the node auto-detects groups and emits a warning in stdout NDJSON. This is NOT a hard error.

# Reporting Requirements

Output to stdout must follow the NDJSON format:
```json
{"level": "info", "msg": "<progress message>"}
{"level": "result", "status": "pass", "decision": "qc_pass", "metrics": {"control": "<name>", "control_num": N, "treat": "<name>", "treat_num": N, "total_num": N}}
```

Gate nodes include the `decision` field in the result line. Valid decisions: `qc_pass`, `qc_fail`.

# Hardware Requirements

Minimal. Single-core CPU, less than 1 GB memory. Runtime is sub-minute for typical expression matrices (< 100k genes, < 1000 samples).
