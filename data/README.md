# Data directory

This directory separates the source-style numerical reconstruction from the standardized modeling table.

## Files

### `source_reconstruction/qiao_2023_s2_reconstructed_wide.csv`

A 100-row reconstruction of the supplementary numerical formulation table using the source-style indicator and concentration columns:

`EG`, `EGP`, `GL`, `GLP`, `RA`, `RAP`, `LA`, `LAP`, `TR`, `TRP`, `Day1`, `Day7`, and `Day15`.

This is not raw instrument data. It is a reconstruction of the published supplementary numerical dataset used for the secondary analysis.

### `processed/qiao_2023_gelma_huvec_viability_100_formulations.csv`

The standardized formulation-level table used by the analysis pipeline. It contains explicit CPA identities, concentrations, viability values, formulation identifiers, and categorical flags.

The no-sugar category is encoded as `NoSugar`, not `None`, to prevent CSV readers such as pandas from interpreting the category as a missing value.

### `processed/missing_expected_formulations.csv`

The four formulation conditions expected from a complete factorial interpretation of the stated design space but not present in the reconstructed numerical dataset. These values were not imputed.

### `DATA_DICTIONARY.md`

Definitions, units, allowed values, and provenance status for every field.

### `SHA256SUMS.txt`

SHA-256 checksums for the CSV files in this directory.

## Rebuild and validate

From the repository root:

```bash
python scripts/prepare_data.py
python scripts/validate_dataset.py
```

The preparation script preserves the reported Day 1, Day 7, and Day 15 viability values and only standardizes the formulation descriptors.
