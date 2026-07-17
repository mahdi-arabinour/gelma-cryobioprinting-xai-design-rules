# From Prediction to Design Rules: Explainable Machine Learning Analysis of Cryoprotectant Effects in GelMA-Based Cryobioprinting Bioinks

[![DOI](https://zenodo.org/badge/1303640160.svg)](https://doi.org/10.5281/zenodo.21407415)

# Repository overview

Reproducibility package for the manuscript:

**From Prediction to Design Rules: Explainable Machine Learning Analysis of Cryoprotectant Effects in GelMA-Based Cryobioprinting Bioinks**

## Scope

This repository contains the curated data reconstruction, data-preparation code, leakage-safe machine-learning workflow, explainability analysis, stability metrics, multi-objective ranking, sensitivity analysis, and generalization tests used in the manuscript.

The study is a secondary analysis of the GelMA-HUVEC cryobioprinting dataset reported by Qiao et al. The extracted rules are local, data-supported formulation hypotheses within the published design space. They are not causal claims or universal cryoprotectant principles.

## Repository structure

```text
.
├── data/
│   ├── source_reconstruction/
│   │   └── qiao_2023_s2_reconstructed_wide.csv
│   ├── processed/
│   │   ├── qiao_2023_gelma_huvec_viability_100_formulations.csv
│   │   └── missing_expected_formulations.csv
│   ├── DATA_DICTIONARY.md
│   ├── DATA_LICENSE.md
│   ├── README.md
│   └── SHA256SUMS.txt
├── docs/
│   ├── DATA_PROVENANCE.md
│   ├── EXPECTED_RESULTS.md
│   └── REPRODUCIBILITY_CHECKLIST.md
├── notebooks/
│   └── Cryobioprinting_XAI_Reproducible_Notebook.ipynb
├── scripts/
│   ├── prepare_data.py
│   ├── run_pipeline.py
│   └── validate_dataset.py
├── CITATION.cff
├── LICENSE
├── MANIFEST.csv
├── RUN_ORDER.md
├── environment.yml
└── requirements.txt
```

## Data summary

The reconstructed dataset contains:

- 100 unique formulations
- 300 time-resolved viability observations after long-format conversion
- two permeable CPAs: ethylene glycol (EG) and glycerol (GL)
- three sugar CPAs: raffinose (RA), lactose (LA), and trehalose (TR)
- no-sugar controls
- viability measurements at Day 1, Day 7, and Day 15

A complete factorial interpretation of the stated design space contains 104 formulations. Four EG-raffinose conditions with 20% raffinose were not present in the reconstructed numerical dataset and were not imputed.

The public processed file uses `NoSugar` rather than `None` for no-sugar controls. This avoids accidental conversion of the category into a missing value by common CSV readers. The analysis script maps `NoSugar` back to the manuscript display label `None` so generated tables remain consistent with the manuscript.

## Reproduce the analysis

Create the tested environment:

```bash
conda env create -f environment.yml
conda activate cryobioprinting-xai
```

Or install the pinned Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Then run:

```bash
python scripts/prepare_data.py
python scripts/validate_dataset.py
python scripts/run_pipeline.py
```

Detailed instructions are provided in `RUN_ORDER.md`.

## Main model specification

- model: `RandomForestRegressor`
- trees: 500
- minimum samples per leaf: 2
- validation: five-fold `GroupKFold`
- grouping variable: `formulation_id`
- target: cell viability (%)
- final features: permeable CPA identity, sugar CPA identity, permeable CPA concentration, sugar concentration, and storage day
- random seed: 42

## Generated outputs

The pipeline creates:

- validated input and engineered datasets
- feature-set ablation results
- grouped cross-validation and baseline comparisons
- bootstrap confidence intervals
- SHAP global and directional summaries
- formulation-level multi-objective rankings
- sensitivity-analysis outputs
- cross-domain generalization tests
- manuscript-ready tables and figures
- serialized final model and model metadata
- export manifest and compressed output archive

Generated files are written under `outputs/`. The directory is intentionally excluded from version control because it can be rebuilt from the included data and code.

## Data provenance and rights

The numerical values were reconstructed from the supplementary numerical data associated with:

Qiao, Q., et al. *The use of machine learning to predict the effects of cryoprotective agents on the GelMA-based bioinks used in extrusion cryobioprinting.* Bio-Design and Manufacturing, 2023, 6(4), 464-477.

No missing formulations were imputed and no unreported viability values were inferred. See `docs/DATA_PROVENANCE.md` and `data/DATA_LICENSE.md` before reusing the data.

## Citation

Citation metadata are provided in `CITATION.cff`. The GitHub repository URL and Zenodo DOI should be added only after the public repository and versioned Zenodo record have been created.
