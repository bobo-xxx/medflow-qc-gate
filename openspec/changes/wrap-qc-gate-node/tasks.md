# Tasks: Wrap qc-gate Reference Implementation

## Implementation Checklist

### 1. Create env.yaml
- [ ] Create `envs/env-py.yaml` with channels (conda-forge) and dependencies (python, pandas, pyyaml)
- [ ] Create or symlink `env.yaml` pointing to envs/env-py.yaml

### 2. Implement SKILL.md
- [ ] Write SKILL.md with v2 frontmatter contract
- [ ] Declare inputs, outputs, parameters with bind annotations
- [ ] Declare exceptions, hardware requirements
- [ ] Write body sections: Node Function, Expected Input, Exceptions, Reporting Requirements

### 3. Implement scripts/main.py
- [ ] Parse CLI arguments (argparse)
- [ ] Read input matrix and group map
- [ ] Validate exactly 2 groups exist
- [ ] Match control/treatment names (auto-detect if not specified)
- [ ] Clean data (replace spaces, normalize hyphens to dots in sample IDs)
- [ ] Write validated output files (matrix, groups, confirm YAML)
- [ ] Report QC gate decision via NDJSON stdout

### 4. Implement validation scripts
- [ ] Create `scripts/input_validation.py` — check input files exist, are readable, have required columns
- [ ] Create `scripts/output_validation.py` — verify output files are valid

### 5. Write tests
- [ ] Test: valid input with matching control/treatment groups
- [ ] Test: auto-detection of groups when control_name not in map
- [ ] Test: error when group count != 2
- [ ] Test: error when input file missing
- [ ] Test: NDJSON stdout format

### 6. Verify
- [ ] Run verify checklist: file_layout, file_discovery, conditional outputs, defaults, exceptions, hardware, entry point, bind fields, LICENSE, NDJSON
- [ ] All tests pass
