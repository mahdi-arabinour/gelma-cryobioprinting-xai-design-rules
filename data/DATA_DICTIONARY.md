# Data dictionary

## Processed modeling table

File: `processed/qiao_2023_gelma_huvec_viability_100_formulations.csv`

| Column | Type | Unit or allowed values | Definition |
|---|---|---|---|
| `formulation_id` | string | structured identifier | Unique identifier formatted as `<permeable CPA>_<permeable concentration>_<sugar CPA>_<sugar concentration>`. |
| `permeable_cpa` | categorical | `EG`, `GL` | Permeable cryoprotective agent: ethylene glycol or glycerol. |
| `permeable_conc_pct` | integer | 5, 10, 15, 20 | Reported permeable CPA concentration in percent. |
| `sugar_cpa` | categorical | `NoSugar`, `RA`, `LA`, `TR` | Sugar CPA identity: no-sugar control, raffinose, lactose, or trehalose. |
| `sugar_conc_pct` | integer | 0, 5, 10, 15, 20 | Reported sugar CPA concentration in percent. `0` is used only for no-sugar controls. |
| `viability_day1_pct` | numeric | percent | Reported cell viability at Day 1. |
| `viability_day7_pct` | numeric | percent | Reported cell viability at Day 7. |
| `viability_day15_pct` | numeric | percent | Reported cell viability at Day 15. |
| `has_sugar` | binary integer | 0, 1 | `1` for sugar-containing formulations and `0` for no-sugar controls. |
| `is_no_sugar_control` | binary integer | 0, 1 | `1` for no-sugar controls and `0` otherwise. |
| `is_ra_group` | binary integer | 0, 1 | `1` for raffinose-containing formulations and `0` otherwise. |

## Source-style reconstruction

File: `source_reconstruction/qiao_2023_s2_reconstructed_wide.csv`

| Column | Type | Unit or allowed values | Definition |
|---|---|---|---|
| `EG` | binary integer | 0, 1 | Indicator for ethylene glycol. |
| `EGP` | numeric | percent | Ethylene glycol concentration. |
| `GL` | binary integer | 0, 1 | Indicator for glycerol. |
| `GLP` | numeric | percent | Glycerol concentration. |
| `RA` | binary integer | 0, 1 | Indicator for raffinose. |
| `RAP` | numeric | percent | Raffinose concentration. |
| `LA` | binary integer | 0, 1 | Indicator for lactose. |
| `LAP` | numeric | percent | Lactose concentration. |
| `TR` | binary integer | 0, 1 | Indicator for trehalose. |
| `TRP` | numeric | percent | Trehalose concentration. |
| `Day1` | numeric | percent | Reported cell viability at Day 1. |
| `Day7` | numeric | percent | Reported cell viability at Day 7. |
| `Day15` | numeric | percent | Reported cell viability at Day 15. |

## Missing conditions

The following conditions were not present in the reconstructed source table and were not imputed:

- `EG_5_RA_20`
- `EG_10_RA_20`
- `EG_15_RA_20`
- `EG_20_RA_20`
