#!/usr/bin/env python3
"""Validate the standardized GelMA-HUVEC formulation table before analysis."""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "qiao_2023_gelma_huvec_viability_100_formulations.csv"
)

REQUIRED_COLUMNS = [
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

EXPECTED_MISSING = {
    "EG_5_RA_20",
    "EG_10_RA_20",
    "EG_15_RA_20",
    "EG_20_RA_20",
}


def expected_formulations() -> set[str]:
    expected: set[str] = set()
    for permeable in ("EG", "GL"):
        for pconc in (5, 10, 15, 20):
            expected.add(f"{permeable}_{pconc}_NoSugar_0")
            for sugar in ("RA", "LA", "TR"):
                for sconc in (5, 10, 15, 20):
                    expected.add(f"{permeable}_{pconc}_{sugar}_{sconc}")
    return expected


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    with DATA_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = set(REQUIRED_COLUMNS).difference(fieldnames)
        if missing_columns:
            raise AssertionError(
                "Missing required columns: " + ", ".join(sorted(missing_columns))
            )
        rows = list(reader)

    if len(rows) != 100:
        raise AssertionError(f"Expected 100 rows; found {len(rows)}.")

    ids = [row["formulation_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError("Duplicate formulation_id values were found.")

    for row_number, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if row[column] == "":
                raise AssertionError(
                    f"Blank value at CSV row {row_number}, column {column}."
                )

        permeable = row["permeable_cpa"]
        sugar = row["sugar_cpa"]
        pconc = int(float(row["permeable_conc_pct"]))
        sconc = int(float(row["sugar_conc_pct"]))

        if permeable not in {"EG", "GL"}:
            raise AssertionError(f"Unexpected permeable CPA at row {row_number}.")
        if sugar not in {"NoSugar", "RA", "LA", "TR"}:
            raise AssertionError(f"Unexpected sugar CPA at row {row_number}.")
        if pconc not in {5, 10, 15, 20}:
            raise AssertionError(f"Unexpected permeable concentration at row {row_number}.")
        if sugar == "NoSugar" and sconc != 0:
            raise AssertionError(f"NoSugar row has nonzero sugar concentration at row {row_number}.")
        if sugar != "NoSugar" and sconc not in {5, 10, 15, 20}:
            raise AssertionError(f"Unexpected sugar concentration at row {row_number}.")

        expected_id = f"{permeable}_{pconc}_{sugar}_{sconc}"
        if row["formulation_id"] != expected_id:
            raise AssertionError(
                f"formulation_id mismatch at row {row_number}: "
                f"{row['formulation_id']} != {expected_id}"
            )

        expected_has_sugar = int(sugar != "NoSugar")
        expected_no_sugar = int(sugar == "NoSugar")
        expected_ra = int(sugar == "RA")
        if int(row["has_sugar"]) != expected_has_sugar:
            raise AssertionError(f"has_sugar mismatch at row {row_number}.")
        if int(row["is_no_sugar_control"]) != expected_no_sugar:
            raise AssertionError(f"is_no_sugar_control mismatch at row {row_number}.")
        if int(row["is_ra_group"]) != expected_ra:
            raise AssertionError(f"is_ra_group mismatch at row {row_number}.")

        for column in (
            "viability_day1_pct",
            "viability_day7_pct",
            "viability_day15_pct",
        ):
            value = float(row[column])
            if not 0 <= value <= 100:
                raise AssertionError(
                    f"Viability outside 0-100 at row {row_number}, column {column}."
                )

    observed = set(ids)
    expected = expected_formulations()
    missing = expected.difference(observed)
    extra = observed.difference(expected)

    if missing != {
        item.replace("_None_", "_NoSugar_") for item in EXPECTED_MISSING
    }:
        raise AssertionError(f"Unexpected missing design-space conditions: {sorted(missing)}")
    if extra:
        raise AssertionError(f"Unexpected extra formulations: {sorted(extra)}")

    print("Dataset validation passed.")
    print(f"Rows: {len(rows)}")
    print(f"Unique formulations: {len(observed)}")
    print(f"Expected full design space: {len(expected)}")
    print(f"Missing conditions: {len(missing)}")
    for item in sorted(missing):
        print(f"  - {item}")


if __name__ == "__main__":
    main()
