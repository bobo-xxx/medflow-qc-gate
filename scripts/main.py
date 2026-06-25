#!/usr/bin/env python
"""
QC Gate — validate merged expression data, confirm group assignments,
clean data, and output validated files with pass/fail decision.

Subcommands:
    run    Execute QC gate validation.
"""

import sys
import json
import logging
import argparse
from pathlib import Path

import pandas as pd
import yaml


logger = logging.getLogger("qc_gate")


def ndjson_info(msg: str, **kwargs) -> None:
    """Emit an info-level NDJSON line to stdout."""
    line = {"level": "info", "msg": msg, **kwargs}
    print(json.dumps(line, ensure_ascii=False), flush=True)


def ndjson_result(status: str, **kwargs) -> None:
    """Emit a result NDJSON line to stdout."""
    line = {"level": "result", "status": status, **kwargs}
    print(json.dumps(line, ensure_ascii=False), flush=True)


def make_dir(path: Path) -> None:
    """Create directory if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def read_file(path: Path, **kwargs) -> pd.DataFrame:
    """Read a CSV file into a DataFrame. Raises FileNotFoundError."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return pd.read_csv(path, **kwargs)


def normalize_id(value: str) -> str:
    """Normalize a sample ID: strip spaces, replace hyphens with dots."""
    return str(value).replace(" ", "").replace("-", ".")


def validate_groups(
    group_df: pd.DataFrame,
    control_name: str,
    treat_name: str,
    color1: str,
    color2: str,
) -> tuple[pd.DataFrame, str, str, int, int]:
    """
    Validate group mapping: confirm exactly 2 groups, match control/treatment
    names, and produce a normalized group DataFrame with color assignments.

    Returns:
        (group2, control_name, treat_name, c_num, t_num)
    """
    # Normalize all string columns
    for col in group_df.columns:
        group_df[col] = group_df[col].astype(str).apply(normalize_id)

    # Column 0 = sample IDs, Column 1 = group names
    id_col = group_df.columns[0]
    group_col = group_df.columns[1]

    # Build mapping: group_name -> [sample_ids]
    mapping = group_df.groupby(group_col, sort=False)[id_col].agg(list).to_dict()
    groups = list(mapping.keys())

    if len(groups) != 2:
        raise ValueError(
            f"QC gate only supports binary comparisons (control vs treatment). "
            f"Found {len(groups)} group(s): {', '.join(groups)}. "
            f"group count is not 2"
        )

    control_name_norm = normalize_id(control_name)

    if control_name_norm in groups:
        treat_name_detected = [g for g in groups if g != control_name_norm][0]
        ndjson_info(
            "Control/treatment groups confirmed",
            control=control_name_norm,
            treatment=treat_name_detected,
        )
    else:
        logger.warning(
            "Control name '%s' not found in group labels %s. "
            "Auto-detecting groups.",
            control_name_norm,
            groups,
        )
        ndjson_info(
            "Control name not matched — auto-detecting groups",
            configured_control=control_name_norm,
            available_groups=groups,
        )
        control_name_norm, treat_name_detected = groups[0], groups[1]

    # If user provided treat_name, use it if it matches
    if treat_name and normalize_id(treat_name) in groups:
        treat_name_detected = normalize_id(treat_name)

    c_num = len(mapping.get(control_name_norm, []))
    t_num = len(mapping.get(treat_name_detected, []))

    group2 = pd.DataFrame(
        {
            "ID": mapping.get(control_name_norm, [])
            + mapping.get(treat_name_detected, []),
            "group": [control_name_norm] * c_num + [treat_name_detected] * t_num,
            "color": [color1] * c_num + [color2] * t_num,
        }
    )

    return group2, control_name_norm, treat_name_detected, c_num, t_num


def run_qc(args: argparse.Namespace) -> None:
    """Execute the QC gate validation."""
    ndjson_info("Starting QC gate validation")

    # --- Read inputs ---
    ndjson_info("Reading input files", mat=str(args.mat), map=str(args.map))
    try:
        mat = read_file(Path(args.mat), index_col=0)
    except FileNotFoundError as e:
        ndjson_info("Input matrix not found", error=str(e))
        raise

    try:
        group = read_file(Path(args.map))
    except FileNotFoundError as e:
        ndjson_info("Input group map not found", error=str(e))
        raise

    ndjson_info(
        "Input shapes",
        mat_shape=list(mat.shape),
        group_shape=list(group.shape),
    )

    # --- Normalize sample IDs ---
    mat.columns = [normalize_id(str(c)) for c in mat.columns]
    mat.index = [normalize_id(str(i)) for i in mat.index]

    # --- Validate groups ---
    try:
        group2, control_name, treat_name, c_num, t_num = validate_groups(
            group,
            control_name=args.control_name,
            treat_name=args.treat_name or "",
            color1=args.color1,
            color2=args.color2,
        )
    except ValueError as e:
        ndjson_info("Group validation failed", error=str(e))
        ndjson_result(
            "fail",
            decision="qc_fail",
            metrics={"error": str(e)},
        )
        sys.exit(2)

    # --- Filter and align matrix ---
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    out_mat_path = outdir / "validated_matrix.csv"
    out_map_path = outdir / "validated_groups.csv"
    out_confirm_path = outdir / "confirm.yaml"

    # Keep only samples present in both matrix and group map
    common_samples = [s for s in group2["ID"].tolist() if s in mat.columns]
    if not common_samples:
        ndjson_info(
            "No common samples between matrix and group map",
            matrix_samples=mat.columns.tolist(),
            group_samples=group2["ID"].tolist(),
        )
        ndjson_result(
            "fail",
            decision="qc_fail",
            metrics={"error": "No common samples between matrix and group map"},
        )
        sys.exit(2)

    mat_filtered = mat[common_samples]
    make_dir(out_mat_path)
    mat_filtered.to_csv(out_mat_path)

    make_dir(out_map_path)
    group2.to_csv(out_map_path, index=False)

    # --- Build confirm ---
    data_set_name = args.data_set_name or "Merged Dataset"
    confirm = {
        "control": control_name,
        "control_num": str(c_num),
        "treat": treat_name,
        "treat_num": str(t_num),
        "total_num": str(c_num + t_num),
        "control_raw": control_name,
        "treat_raw": treat_name,
        "control_cn_raw": control_name,
        "treat_cn_raw": treat_name,
        "data_set_name": data_set_name,
        "data_set_name_raw": data_set_name,
    }

    make_dir(out_confirm_path)
    with open(out_confirm_path, "w") as f:
        yaml.dump(confirm, f, default_flow_style=False, allow_unicode=True)

    ndjson_info(
        "QC gate validation complete",
        control=control_name,
        control_num=c_num,
        treat=treat_name,
        treat_num=t_num,
    )

    ndjson_result(
        "success_matrix",
        decision="qc_pass",
        metrics={
            "control": control_name,
            "control_num": c_num,
            "treat": treat_name,
            "treat_num": t_num,
            "total_num": c_num + t_num,
            "dataset": data_set_name,
        },
        files=[
            str(out_mat_path),
            str(out_map_path),
            str(out_confirm_path),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QC Gate — validate merged expression data.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Execute QC gate validation")
    run_parser.add_argument(
        "--mat", type=str, required=True, help="Path to input expression matrix CSV"
    )
    run_parser.add_argument(
        "--map", type=str, required=True, help="Path to input group mapping CSV"
    )
    run_parser.add_argument(
        "--control-name",
        type=str,
        required=True,
        help="Name of the control group",
    )
    run_parser.add_argument(
        "--treat-name",
        type=str,
        default="",
        help="Name of the treatment group (auto-detected if empty)",
    )
    run_parser.add_argument(
        "--data-set-name",
        type=str,
        default="Merged Dataset",
        help="Human-readable dataset name",
    )
    run_parser.add_argument(
        "--color1",
        type=str,
        default="#1f77b4",
        help="Color for control group (default: #1f77b4)",
    )
    run_parser.add_argument(
        "--color2",
        type=str,
        default="#d62728",
        help="Color for treatment group (default: #d62728)",
    )
    run_parser.add_argument(
        "--outdir",
        type=str,
        required=True,
        help="Output directory path",
    )

    args = parser.parse_args()

    if args.subcommand == "run":
        run_qc(args)


if __name__ == "__main__":
    main()
