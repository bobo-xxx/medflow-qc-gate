# Proposal: Wrap qc-gate Reference Implementation into IRE Node Package

## Problem

The `original/` directory contains reference implementation code for a QC gate node (`check_confirm.py`, `check_rgs.py`, `check_tcga.py`, plus orchestration rules). This code is tightly coupled to an internal rules-based DAG framework (MyRule, RuleSet, Cache classes) and is not yet packaged as a standalone IRE node conforming to the IRE node package protocol.

## Goals

- Extract core QC gate logic from `original/` into a standalone, protocol-compliant IRE node package
- Implement `SKILL.md` with v2 frontmatter contract (inputs, outputs, parameters, exceptions, hardware)
- Implement `env.yaml` declaring conda dependencies (Python + pandas + pyyaml)
- Implement `scripts/main.py` as the single entry point with CLI argument parsing
- Implement `scripts/input_validation.py` and `scripts/output_validation.py`
- Write tests under `tests/`
- Output NDJSON to stdout per the CLI contract
- Produce Apache 2.0 LICENSE and README.md

## Scope

- **In scope**: Extract group validation logic from `check_confirm.py`, data cleaning logic, confirm file generation; package as standalone node
- **Out of scope**: The internal rules-based DAG framework (MyRule, RuleSet, Cache, ColorAssigner); TCGA-specific data validation (check_tcga.py); GEO data downloading (check.py orchestration); RGS file processing (check_rgs.py - simple whitespace cleaning); Snakemake/rule-engine integration

## Non-goals

- Replicating the full Snakemake rules engine
- Supporting TCGA-specific data types (this is a general QC gate)
- Downloading GEO datasets

## Core Acceptance Scenarios

1. **Valid input**: Expression matrix + group map with exactly 2 groups (control + treatment) -- validates, cleans, outputs confirmed files, reports pass
2. **Wrong group count**: Matrix with 1 or 3+ groups -- raises data_mismatch exception
3. **Control name mismatch**: control_name not found in group map -- warns but continues with auto-detected groups
4. **Missing input file**: Input matrix or map file not found -- FileNotFoundError with data_insufficient nature
