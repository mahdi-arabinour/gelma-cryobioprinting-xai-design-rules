# Reproducibility checklist

## Data integrity

- [ ] `data/source_reconstruction/qiao_2023_s2_reconstructed_wide.csv` is present.
- [ ] `python scripts/prepare_data.py` completes without error.
- [ ] `python scripts/validate_dataset.py` reports 100 unique formulations.
- [ ] The validator reports exactly four missing conditions.
- [ ] No missing condition has been imputed.
- [ ] SHA-256 checksums match `data/SHA256SUMS.txt` before any intentional data edit.

## Environment

- [ ] The environment was created from `environment.yml` or `requirements.txt`.
- [ ] Python and package versions were recorded.
- [ ] The analysis was launched from the repository root.

## Validation and modeling

- [ ] Day 1, Day 7, and Day 15 observations from the same formulation remain in the same validation fold.
- [ ] Five-fold `GroupKFold` uses `formulation_id` as the group.
- [ ] The final model uses the five stated formulation-time variables.
- [ ] The final model is compared with global-mean and time-specific mean baselines.
- [ ] SHAP is applied to the final selected model.
- [ ] Generalization tests include EG-to-GL, GL-to-EG, leave-one-sugar-out, and leave-one-concentration-out analyses.

## Outputs

- [ ] Tables are written to `outputs/tables/`.
- [ ] Figures are written to `outputs/figures/`.
- [ ] The final model and metadata are written to `outputs/models/`.
- [ ] `outputs/EXPORT_MANIFEST.csv` is present.
- [ ] `outputs_package.zip` is created.
- [ ] Key metrics agree with `docs/EXPECTED_RESULTS.md` within floating-point tolerance.

## Release preparation

- [ ] Repository URL has been added to `CITATION.cff` only after the GitHub repository exists.
- [ ] Version is tagged as `v1.0.0` only after the final files are verified.
- [ ] Zenodo DOI is added only after the GitHub release has been archived.
- [ ] The manuscript and Supplementary Information use the final real links, not placeholder links.
