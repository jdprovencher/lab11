#!/usr/bin/env python3
"""Task 3: normalize November 311 calls by 2020 Census borough population.

The Census API key is read from the CENSUS_API_KEY environment variable and is
never written to this file:

    CENSUS_API_KEY=... python3 task3.py
"""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

BOROUGH_COL = "Borough"
PROBLEM_COL = "Problem (formerly Complaint Type)"

CENSUS_URL = "https://api.census.gov/data/2020/dec/pl"
FIPS_TO_BOROUGH = {
    "36005": "Bronx",
    "36047": "Brooklyn",
    "36061": "Manhattan",
    "36081": "Queens",
    "36085": "Staten Island",
}
BOROUGH_NAMES = {
    "BRONX": "Bronx",
    "BROOKLYN": "Brooklyn",
    "MANHATTAN": "Manhattan",
    "QUEENS": "Queens",
    "STATEN ISLAND": "Staten Island",
}


def fetch_populations() -> pd.DataFrame:
    """Fetch P1_001N (total population) for New York's five borough counties."""
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "Set CENSUS_API_KEY in the environment, e.g.\n"
            "  CENSUS_API_KEY=... python3 task3.py"
        )

    query = urlencode({
        "get": "NAME,P1_001N",
        "for": "county:*",
        "in": "state:36",
        "key": key,
    })
    with urlopen(f"{CENSUS_URL}?{query}", timeout=60) as response:
        payload = json.load(response)

    header, *rows = payload
    records = [dict(zip(header, row)) for row in rows]
    populations = {}
    names = {}
    for record in records:
        fips = record["state"] + record["county"]
        if fips in FIPS_TO_BOROUGH:
            populations[FIPS_TO_BOROUGH[fips]] = int(record["P1_001N"])
            names[FIPS_TO_BOROUGH[fips]] = record["NAME"]

    missing = set(FIPS_TO_BOROUGH.values()) - set(populations)
    if missing:
        raise SystemExit(f"Census response missing boroughs: {sorted(missing)}")

    table = pd.DataFrame(
        {
            "Borough": list(FIPS_TO_BOROUGH.values()),
            "County": [names[b] for b in FIPS_TO_BOROUGH.values()],
            "Population": [populations[b] for b in FIPS_TO_BOROUGH.values()],
        }
    ).sort_values("Borough")

    total = int(table["Population"].sum())
    print(f"Census 2020 populations fetched; five-borough total = {total:,}")
    if not 8_700_000 <= total <= 8_900_000:
        raise SystemExit(
            f"Population sanity check failed: {total:,} is not roughly 8.8 million"
        )
    return table


def complaint_counts(df: pd.DataFrame):
    counts = df[BOROUGH_COL].value_counts()
    counts.index = counts.index.map(BOROUGH_NAMES)
    unspecified = int(counts[counts.index.isna()].sum())
    counts = counts[counts.index.notna()]
    counts = counts.rename_axis("Borough").rename("Complaints").reset_index()
    return counts, unspecified


def per_1000_table(populations: pd.DataFrame, counts: pd.DataFrame):
    merged = populations.merge(counts, on="Borough", how="left", validate="one_to_one")
    merged["Complaints"] = merged["Complaints"].fillna(0).astype(int)

    # Plain-calculator check (Bronx): 74,674 calls / 1,472,654 residents * 1,000
    # = 50.71 calls per 1,000 residents. The table below prints 50.7.
    merged["Per1000"] = merged["Complaints"] / merged["Population"] * 1_000

    merged["RankRaw"] = merged["Complaints"].rank(
        ascending=False, method="min"
    ).astype(int)
    merged["RankRate"] = merged["Per1000"].rank(
        ascending=False, method="min"
    ).astype(int)
    return merged.sort_values("Complaints", ascending=False)


def print_table(table: pd.DataFrame) -> None:
    print(
        f"\n{'Borough':<14}{'Population':>12}{'Complaints':>12}"
        f"{'Per 1,000':>11}{'Raw rank':>10}{'Rate rank':>11}"
    )
    print("-" * 70)
    for row in table.itertuples(index=False):
        print(
            f"{row.Borough:<14}{row.Population:>12,}{row.Complaints:>12,}"
            f"{row.Per1000:>11.1f}{row.RankRaw:>10}{row.RankRate:>11}"
        )


def bar_chart(
    table: pd.DataFrame,
    value_col: str,
    xlabel: str,
    title: str,
    filename: str,
    value_format: str,
) -> Path:
    data = table.sort_values(value_col)
    values = data[value_col].to_numpy()
    labels = data["Borough"].to_list()

    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh(labels, values, color="#3b6ea5", edgecolor="white", linewidth=1.5)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel("Borough", fontsize=11)
    ax.set_title(title, fontsize=14, loc="left", pad=14)
    ax.bar_label(bars, labels=[value_format.format(v) for v in values],
                 padding=4, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.grid(True, alpha=0.25)
    ax.set_axisbelow(True)
    ax.margins(x=0.12)
    fig.text(
        0.01,
        0.01,
        "Counts are 311 calls, not residents. Population: 2020 Census.",
        fontsize=8,
        color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    out = HERE / filename
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def writeup(table: pd.DataFrame) -> str:
    rows = {r.Borough: r for r in table.itertuples(index=False)}
    return (
        f"Yes: Brooklyn falls from first in raw calls ({rows['Brooklyn'].Complaints:,}) "
        f"to third per 1,000 residents ({rows['Brooklyn'].Per1000:.1f}), while the Bronx "
        f"rises from second to first ({rows['Bronx'].Per1000:.1f}) and Manhattan jumps "
        f"from fourth to second ({rows['Manhattan'].Per1000:.1f}); Queens slips from "
        f"third to fourth ({rows['Queens'].Per1000:.1f}), and Staten Island stays fifth "
        f"({rows['Staten Island'].Per1000:.1f}). "
        "Brooklyn and Queens are large, relatively lower-density outer boroughs with "
        "more low-rise, owner-occupied neighborhoods, so their big raw totals mostly "
        "track population size rather than a higher rate of calling 311. "
        "Manhattan's high rate is plausibly explained by dense rental housing, older "
        "buildings, and a huge daytime population of workers and visitors who can call "
        "311 but are not counted in the resident denominator. "
        "The Bronx's leading rate is consistent with dense, older housing stock and more "
        "housing-condition complaints, though the data cannot tell us whether that "
        "reflects greater need, greater willingness to report, or both. "
        "Even the per-1,000 measure is only a rough correction, because the denominator "
        "counts residents while the numerator counts calls that anyone can make."
    )


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    populations = fetch_populations()
    print("\nTwo-column population table:")
    print(populations[["Borough", "Population"]].to_string(index=False))

    df = pd.read_csv(
        DATA,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    )
    counts, unspecified = complaint_counts(df)
    print(
        f"\nDropped {unspecified:,} rows with Borough='Unspecified' "
        f"({unspecified / len(df):.2%} of {len(df):,} rows); "
        "they have no population to normalize against."
    )
    print(f"Rows retained for normalization: {int(counts['Complaints'].sum()):,}")

    table = per_1000_table(populations, counts)
    print_table(table)

    raw_path = bar_chart(
        table,
        "Complaints",
        "Number of 311 calls",
        "NYC 311 calls by borough, November 2025",
        "fig-borough-raw.png",
        "{:,.0f}",
    )
    rate_path = bar_chart(
        table,
        "Per1000",
        "311 calls per 1,000 residents",
        "NYC 311 calls per 1,000 residents, November 2025",
        "fig-borough-per1000.png",
        "{:.1f}",
    )
    print(f"\nSaved charts: {raw_path.name}, {rate_path.name}")

    print("\n3c — write-up (3–5 sentences):")
    print(writeup(table))


if __name__ == "__main__":
    main()
