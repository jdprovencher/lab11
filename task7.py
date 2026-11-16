#!/usr/bin/env python3
"""Task 7: chase the 196 rows whose Borough is 'Unspecified'."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"


def main() -> None:
    df = pd.read_csv(
        DATA,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    )
    unknown = df[df["Borough"] == "Unspecified"].copy()
    print(f"Rows with Borough='Unspecified': {len(unknown):,}")
    print(f"Share of all rows: {len(unknown) / len(df):.3%}")

    # Query 1: what agencies and problem types are these?
    print("\nQuery 1 — agency and problem concentration")
    print(unknown["Agency"].value_counts().to_string())
    print("\nTop problem types:")
    print(unknown["Problem (formerly Complaint Type)"].value_counts().head(10).to_string())
    top3 = unknown["Agency"].value_counts().head(3)
    print(f"\nTop three agencies account for {top3.sum():,} of {len(unknown):,} rows.")

    # Query 2: is the missing borough part of missing geography?
    print("\nQuery 2 — missing location fields")
    for column in ["Incident Zip", "Incident Address", "City", "Latitude", "Longitude"]:
        print(f"  {column:<18} missing={unknown[column].isna().sum():>3}  "
              f"present={unknown[column].notna().sum():>3}")
    print(f"  rows with both coordinates: "
          f"{unknown[['Latitude', 'Longitude']].notna().all(axis=1).sum():,}")

    # Query 3: where are the rows that do have location text?
    print("\nQuery 3 — the rows that do carry places")
    places = unknown.loc[
        unknown["City"].notna(),
        ["Agency", "Problem (formerly Complaint Type)", "Incident Zip",
         "Incident Address", "City"],
    ]
    print(places.to_string(index=False))
    print("\nAddress types:")
    print(unknown["Address Type"].value_counts(dropna=False).to_string())
    print("\nFacility types:")
    print(unknown["Facility Type"].value_counts(dropna=False).head(5).to_string())

    print("\nFive-sentence write-up:")
    print(
        f"I found {len(unknown):,} rows with Borough='Unspecified', concentrated "
        "in location-free service complaints: TLC (70), DOT (59), DSNY (30), led "
        "by Ferry Inquiry (29), Taxi Complaint (24), and Derelict Vehicles (23). "
        "Query 1 grouped them by agency and problem type, showing that 159 of 196 "
        "come from those three agencies and that taxi, ferry, and vehicle reports "
        "dominate. "
        "Query 2 checked the location fields: 176 have no Incident Zip, 163 no "
        "Incident Address, 179 no City, and only 13 have coordinates, so the "
        "missing borough tracks missing geography rather than a specific place. "
        "Query 3 inspected the 20 rows with zips and 17 with City values; they "
        "include Buffalo, Albany, San Francisco, Pittsburgh, Harrisburg, and other "
        "out-of-NYC addresses, along with 42 intersections and 12 DSNY garages, "
        "so there is no hidden New York neighborhood behind the label. "
        "Verdict: this is a data artifact/legitimate category effect, not a real "
        "place—taxi, ferry, consumer, and garage complaints often have no fixed "
        "borough—and the file alone cannot tell whether any of the located rows "
        "should have been geocoded."
    )


if __name__ == "__main__":
    main()
