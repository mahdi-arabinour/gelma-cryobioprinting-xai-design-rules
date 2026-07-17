# Expected key results

A successful run should reproduce the manuscript-level numerical summaries within ordinary floating-point precision.

## Dataset

- observed formulations: 100
- expected complete design space: 104
- missing formulations: 4
- long-format observations: 300

## Final grouped Random Forest model

Approximate five-fold grouped cross-validation results:

- MAE: 4.842%
- RMSE: 6.106%
- R2: 0.649

Approximate bootstrap 95% confidence intervals:

- MAE: 4.418-5.274%
- R2: 0.585-0.710

## Main design-rule outputs

- highest-ranked individual formulation: `GL_15_RA_15`
- strongest average CPA family: EG with trehalose
- most favorable concentration region: 15% permeable CPA with 15% sugar CPA
- cross-transfer between EG and GL domains: approximately 12% MAE with negative R2 values

Small differences in the last decimal place may occur across operating systems or dependency builds. Larger differences indicate a data-loading, environment, or validation problem.
