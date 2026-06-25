#!/usr/bin/env python
"""Output validation for QC gate node.

Checks that output files exist and contain expected content.
"""

import sys
import json
from pathlib import Path


def validate_outputs(outdir: str) -> bool:
    """Validate QC gate output files. Returns True if all checks pass."""
    out = Path(outdir)
    errors = []

    for fname in ["validated_matrix.csv", "validated_groups.csv", "confirm.yaml"]:
        fpath = out / fname
        if not fpath.exists():
            errors.append(f"Missing output file: {fpath}")
        elif fpath.stat().st_size == 0:
            errors.append(f"Empty output file: {fpath}")

    if errors:
        for e in errors:
            print(json.dumps({"level": "error", "msg": e}))
        return False

    print(json.dumps({"level": "info", "msg": "Output validation passed"}))
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "level": "error",
                    "msg": "Usage: output_validation.py <outdir>",
                }
            )
        )
        sys.exit(1)

    ok = validate_outputs(sys.argv[1])
    sys.exit(0 if ok else 1)
