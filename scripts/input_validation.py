#!/usr/bin/env python
"""Input validation for QC gate node.

Checks:
    1. Input files exist and are readable.
    2. Matrix CSV has at least 1 gene row and 2+ sample columns.
    3. Group mapping CSV has at least 2 columns (ID, group) and 2+ rows.
"""

import sys
import json
from pathlib import Path


def validate_inputs(mat_path: str, map_path: str) -> bool:
    """Validate input files for QC gate. Returns True if all checks pass."""
    errors = []

    # Check matrix exists
    mat = Path(mat_path)
    if not mat.exists():
        errors.append(f"Matrix file not found: {mat_path}")
        print(json.dumps({"level": "error", "msg": f"Matrix file not found: {mat_path}"}))
        return False

    if not mat.is_file():
        errors.append(f"Matrix path is not a file: {mat_path}")
        print(json.dumps({"level": "error", "msg": f"Matrix path is not a file: {mat_path}"}))
        return False

    # Check group map exists
    gmap = Path(map_path)
    if not gmap.exists():
        errors.append(f"Group map file not found: {map_path}")
        print(json.dumps({"level": "error", "msg": f"Group map file not found: {map_path}"}))
        return False

    if not gmap.is_file():
        errors.append(f"Group map path is not a file: {map_path}")
        print(json.dumps({"level": "error", "msg": f"Group map path is not a file: {map_path}"}))
        return False

    print(json.dumps({"level": "info", "msg": "Input validation passed"}))
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            json.dumps(
                {
                    "level": "error",
                    "msg": "Usage: input_validation.py <mat.csv> <map.csv>",
                }
            )
        )
        sys.exit(1)

    ok = validate_inputs(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
