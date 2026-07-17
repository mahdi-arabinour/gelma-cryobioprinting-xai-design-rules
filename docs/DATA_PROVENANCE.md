# Data provenance

## Source

The analysis uses the GelMA-HUVEC cryobioprinting formulation and viability data reported by Qiao et al. in the supplementary numerical dataset associated with:

Qiao, Q., et al. *The use of machine learning to predict the effects of cryoprotective agents on the GelMA-based bioinks used in extrusion cryobioprinting.* Bio-Design and Manufacturing, 2023, 6(4), 464-477.

## Reconstruction

The source-style table contains the CPA indicator columns, CPA concentration columns, and Day 1, Day 7, and Day 15 viability values used in the secondary analysis. The separate supplementary materials and instruments information described in the manuscript was used only to document experimental context and was not used as a numerical modeling dataset.

The standardized table was created by mapping:

- `EG` and `EGP` to permeable CPA identity and concentration;
- `GL` and `GLP` to permeable CPA identity and concentration;
- `RA` and `RAP` to raffinose identity and concentration;
- `LA` and `LAP` to lactose identity and concentration;
- `TR` and `TRP` to trehalose identity and concentration; and
- rows without a sugar indicator to the explicit `NoSugar` category.

The reported viability values were copied without numerical transformation. No missing formulation was imputed and no unreported value was inferred.

## Design-space reconciliation

A complete factorial interpretation of the stated formulation space contains 104 conditions. The reconstructed numerical table contains 100 unique formulations. The four absent conditions are:

- `EG_5_RA_20`
- `EG_10_RA_20`
- `EG_15_RA_20`
- `EG_20_RA_20`

These conditions are listed in `data/processed/missing_expected_formulations.csv` and excluded from all analyses.

## Categorical encoding safeguard

The public processed table uses `NoSugar` because some CSV readers treat the literal string `None` as a missing-value token. The analysis script reads the file with default missing-value conversion disabled and maps `NoSugar` to the manuscript display label `None` after loading.
