#!/usr/bin/env python3
"""Create the standardized modeling table from the reconstructed Qiao et al. S2 table.

No missing formulations are imputed. The script only maps the source-style indicator
columns into explicit formulation variables and preserves the reported Day 1, Day 7,
and Day 15 viability values.
"""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "source_reconstruction"
    / "qiao_2023_s2_reconstructed_wide.csv"
)
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "qiao_2023_gelma_huvec_viability_100_formulations.csv"
)

SOURCE_COLUMNS = {
    "EG",
    "EGP",
    "GL",
    "GLP",
    "RA",
    "RAP",
    "LA",
    "LAP",
    "TR",
    "TRP",
    "Day1",
    "Day7",
    "Day15",
}

OUTPUT_COLUMNS = [
    "formulation_id",
    "permeable_cpa",
    "permeable_conc_pct",
    "sugar_cpa",
    "sugar_conc_pct",
    "viability_day1_pct",
    "viability_day7_pct",
    "viability_day15_pct",
    "has_sugar",
    "is_no_sugar_control",
    "is_ra_group",
]


def _as_int(value: str) -> int:
    return int(float(value))


def standardize_row(row: dict[str, str]) -> dict[str, object]:
    if _as_int(row["EG"]) == 1 or _as_int(row["EGP"]) > 0:
        permeable_cpa = "EG"
        permeable_conc = _as_int(row["EGP"])
    elif _as_int(row["GL"]) == 1 or _as_int(row["GLP"]) > 0:
        permeable_cpa = "GL"
        permeable_conc = _as_int(row["GLP"])
    else:
        raise ValueError("Each row must contain either an EG or GL formulation.")

    sugar_cpa = "NoSugar"
    sugar_conc = 0
    sugar_flags = []
    for sugar, flag_col, conc_col in (
        ("RA", "RA", "RAP"),
        ("LA", "LA", "LAP"),
        ("TR", "TR", "TRP"),
    ):
        present = _as_int(row[flag_col]) == 1 or _as_int(row[conc_col]) > 0
        if present:
            sugar_flags.append((sugar, _as_int(row[conc_col])))

    if len(sugar_flags) > 1:
        raise ValueError("A row contains more than one sugar CPA.")
    if sugar_flags:
        sugar_cpa, sugar_conc = sugar_flags[0]

    formulation_id = (
        f"{permeable_cpa}_{permeable_conc}_{sugar_cpa}_{sugar_conc}"
    )

    return {
        "formulation_id": formulation_id,
        "permeable_cpa": permeable_cpa,
        "permeable_conc_pct": permeable_conc,
        "sugar_cpa": sugar_cpa,
        "sugar_conc_pct": sugar_conc,
        "viability_day1_pct": row["Day1"],
        "viability_day7_pct": row["Day7"],
        "viability_day15_pct": row["Day15"],
        "has_sugar": int(sugar_cpa != "NoSugar"),
        "is_no_sugar_control": int(sugar_cpa == "NoSugar"),
        "is_ra_group": int(sugar_cpa == "RA"),
    }


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Source reconstruction not found: {SOURCE_PATH}")

    with SOURCE_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing_columns = SOURCE_COLUMNS.difference(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "Source reconstruction is missing columns: "
                + ", ".join(sorted(missing_columns))
            )
        standardized = [standardize_row(row) for row in reader]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(standardized)

    print(f"Wrote {len(standardized)} formulations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
