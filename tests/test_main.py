"""Tests for QC gate main.py entry point."""

import sys
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
MAIN = Path(__file__).parent.parent / "scripts" / "main.py"


def run_qc(mat, map_csv, control_name, treat_name="", data_set_name="Test",
           color1="#1f77b4", color2="#d62728", outdir=None):
    """Helper to run main.py and capture stdout/stderr/exit code."""
    if outdir is None:
        outdir = tempfile.mkdtemp()

    cmd = [
        sys.executable, str(MAIN), "run",
        "--mat", str(mat),
        "--map", str(map_csv),
        "--control-name", control_name,
        "--treat-name", treat_name,
        "--data-set-name", data_set_name,
        "--color1", color1,
        "--color2", color2,
        "--outdir", outdir,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result, outdir


def parse_ndjson(stdout):
    """Parse NDJSON stdout lines into list of dicts."""
    lines = []
    for line in stdout.strip().split("\n"):
        if line.strip():
            lines.append(json.loads(line))
    return lines


class TestQCGateValidInput:
    """Tests with valid input."""

    def test_valid_input_produces_pass(self):
        """Valid 2-group input produces qc_pass decision."""
        result, outdir = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="Control",
        )

        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"

        lines = parse_ndjson(result.stdout)
        assert lines, "Expected NDJSON output"

        # Last line should be result
        last_line = lines[-1]
        assert last_line["level"] == "result"
        assert last_line["decision"] == "qc_pass"
        assert "metrics" in last_line
        assert last_line["status"] == "success_matrix"

    def test_output_files_exist(self):
        """Output files are created."""
        result, outdir = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="Control",
        )

        assert (Path(outdir) / "validated_matrix.csv").exists()
        assert (Path(outdir) / "validated_groups.csv").exists()
        assert (Path(outdir) / "confirm.yaml").exists()

    def test_validated_matrix_has_expected_samples(self):
        """Output matrix contains only matched samples."""
        result, outdir = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="Control",
        )

        import pandas as pd
        out_mat = pd.read_csv(Path(outdir) / "validated_matrix.csv", index_col=0)
        # Sample IDs should be normalized (spaces removed, hyphens to dots)
        # Original: "Sample1", " Sample2", "Sample3 ", "Sample4"
        # Normalized: "Sample1", "Sample2", "Sample3", "Sample4"
        assert sorted(out_mat.columns.tolist()) == ["Sample1", "Sample2", "Sample3", "Sample4"]

    def test_ndjson_info_lines(self):
        """Info lines precede the result line."""
        result, _ = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="Control",
        )

        lines = parse_ndjson(result.stdout)
        info_lines = [l for l in lines if l["level"] == "info"]
        result_lines = [l for l in lines if l["level"] == "result"]

        assert len(info_lines) >= 3, f"Expected at least 3 info lines, got {len(info_lines)}"
        assert len(result_lines) == 1


class TestQCGateAutoDetect:
    """Tests for automatic group detection."""

    def test_auto_detect_when_control_not_in_map(self):
        """When control_name not found, auto-detects groups."""
        result, outdir = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="NonexistentGroup",
        )

        # Should still pass — auto-detection emits warning but succeeds
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"

        lines = parse_ndjson(result.stdout)
        warnings = [l for l in lines if "auto-detecting" in str(l.get("msg", "")).lower()
                    or "auto" in str(l.get("msg", "")).lower()]
        assert len(warnings) >= 1, "Expected auto-detection warning"

    def test_auto_detect_produces_valid_output(self):
        """Auto-detection still produces correct output files."""
        result, outdir = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="WrongName",
        )

        assert (Path(outdir) / "validated_matrix.csv").exists()
        assert (Path(outdir) / "confirm.yaml").exists()

        import yaml
        with open(Path(outdir) / "confirm.yaml") as f:
            confirm = yaml.safe_load(f)
        assert "control" in confirm
        assert "treat" in confirm


class TestQCGateErrors:
    """Tests for error conditions."""

    def test_wrong_group_count_exits_2(self):
        """Non-binary group count exits with code 2."""
        result, _ = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map_3groups.csv",
            control_name="Control",
        )

        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
        assert "group count is not 2" in result.stdout or "qc_fail" in result.stdout

    def test_single_group_exits_2(self):
        """Single group exits with code 2."""
        result, _ = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "test_map_1group.csv",
            control_name="OnlyGroup",
        )

        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"

    def test_missing_matrix_file(self):
        """Missing matrix file exits with code 1."""
        result, _ = run_qc(
            mat=FIXTURES / "nonexistent.csv",
            map_csv=FIXTURES / "test_map.csv",
            control_name="Control",
        )

        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"

    def test_missing_map_file(self):
        """Missing map file exits with code 1."""
        result, _ = run_qc(
            mat=FIXTURES / "test_matrix.csv",
            map_csv=FIXTURES / "nonexistent.csv",
            control_name="Control",
        )

        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
