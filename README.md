# medflow-qc-gate

Quality control gate node for the IRE agentic bioinformatics workflow framework.

Validates merged expression data, confirms group assignments (control vs treatment), cleans whitespace and formatting issues, and outputs validated data files with a QC pass/fail decision.

## Usage

```bash
python scripts/main.py \
  --mat input_expression_matrix.csv \
  --map group_info.csv \
  --control-name "Control" \
  --treat-name "Diabetic Foot Ulcer" \
  --confirm confirm.yaml \
  --outdir ./output
```

## Input

- Expression matrix (CSV, genes x samples)
- Group mapping (CSV, sample ID -> group assignment)

## Output

- Validated expression matrix (CSV)
- Validated group map (CSV)  
- Confirm file (YAML) with QC metadata
- NDJSON stdout reporting with QC decision

## License

Apache 2.0
