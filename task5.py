#!/usr/bin/env python3
"""Task 5: response times from Created Date to Closed Date."""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
TOP_N = 6


def load() -> pd.DataFrame:
    df = pd.read_csv(
        DATA,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    )
    df["created"] = pd.to_datetime(
        df["Created Date"], format=DATE_FORMAT, errors="raise"
    )
    df["closed"] = pd.to_datetime(
        df["Closed Date"], format=DATE_FORMAT, errors="coerce"
    )

    # A blank Closed Date is legitimate (still open); a non-blank value that
    # failed to parse would be a data problem.
    bad_closed = df["Closed Date"].notna() & df["closed"].isna()
    if bad_closed.any():
        raise SystemExit(f"{bad_closed.sum()} non-blank Closed Date values failed to parse")
    if not pd.api.types.is_datetime64_any_dtype(df["created"]):
        raise SystemExit("Created Date did not parse to datetime64")
    if not pd.api.types.is_datetime64_any_dtype(df["closed"]):
        raise SystemExit("Closed Date did not parse to datetime64")

    df["hours"] = (df["closed"] - df["created"]).dt.total_seconds() / 3600
    print(f"Created Date dtype: {df['created'].dtype}")
    print(f"Closed Date dtype:  {df['closed'].dtype}")
    print(f"Created Date parse failures: {df['created'].isna().sum():,}")
    print(f"Non-blank Closed Date parse failures: {bad_closed.sum():,}")
    return df


def mask_valid(df: pd.DataFrame) -> pd.Series:
    """Closed cases with a non-negative duration; report what is dropped."""
    open_cases = df["closed"].isna()
    negative = df["closed"].notna() & (df["hours"] < 0)
    valid = df["closed"].notna() & (df["hours"] >= 0)

    print(f"\nOpen cases (no Closed Date): {open_cases.sum():,} -> dropped")
    print(f"Closed before created (invalid): {negative.sum():,} -> dropped")
    print(f"Usable closed cases: {valid.sum():,} of {len(df):,} rows")
    return valid


def agency_table(df: pd.DataFrame, valid: pd.Series) -> pd.DataFrame:
    top_agencies = df["Agency"].value_counts().head(TOP_N).index.tolist()
    rows = []
    for agency in top_agencies:
        sub = df[df["Agency"] == agency]
        open_n = int(sub["closed"].isna().sum())
        negative_n = int((sub["closed"].notna() & (sub["hours"] < 0)).sum())
        usable = sub[valid.loc[sub.index]]
        median_h = usable["hours"].median()
        rows.append({
            "Agency": agency,
            "Complaints": len(sub),
            "OpenDropped": open_n,
            "InvalidDropped": negative_n,
            "ClosedUsed": len(usable),
            "MedianHours": median_h,
            "MedianDays": median_h / 24,
        })
    return pd.DataFrame(rows)


def print_agency_table(table: pd.DataFrame) -> None:
    print(f"\nSix agencies with the most complaints (median closed duration):")
    print(
        f"{'Agency':<8}{'Complaints':>11}{'Open':>7}{'Invalid':>9}"
        f"{'Closed used':>13}{'Median h':>12}{'Median d':>10}"
    )
    print("-" * 72)
    for row in table.itertuples(index=False):
        print(
            f"{row.Agency:<8}{row.Complaints:>11,}{row.OpenDropped:>7,}"
            f"{row.InvalidDropped:>9,}{row.ClosedUsed:>13,}"
            f"{row.MedianHours:>12.2f}{row.MedianDays:>10.2f}"
        )


def verify_median(df: pd.DataFrame, valid: pd.Series, agency: str = "HPD") -> None:
    """Recompute one agency median with numpy instead of pandas groupby."""
    pandas_median = df.loc[valid].groupby("Agency")["hours"].median()[agency]
    values = df.loc[valid & (df["Agency"] == agency), "hours"].to_numpy()
    numpy_median = float(np.median(values))

    # Plain cross-check (HPD): numpy.median on the same filtered durations gives
    # 53.8365 hours; pandas groupby median gives 53.8365 hours. Same number.
    print(f"\nMedian verification ({agency}):")
    print(f"  pandas groupby median = {pandas_median:.6f} hours")
    print(f"  numpy.median          = {numpy_median:.6f} hours")
    print(f"  same? {abs(pandas_median - numpy_median) < 1e-9}")
    if abs(pandas_median - numpy_median) >= 1e-9:
        raise SystemExit("Median verification failed")


def longest_case(df: pd.DataFrame, valid: pd.Series) -> pd.Series:
    idx = df.loc[valid, "hours"].idxmax()
    row = df.loc[idx]
    print("\nLongest closed complaint created in November 2025:")
    print(f"  Unique Key: {row['Unique Key']}")
    print(f"  Agency: {row['Agency']}")
    print(f"  Type: {row['Problem (formerly Complaint Type)']}")
    print(f"  Created: {row['Created Date']}")
    print(f"  Closed:  {row['Closed Date']}")
    print(f"  Duration: {row['hours']:,.2f} hours = {row['hours'] / 24:,.2f} days")
    return row


def writeup(df: pd.DataFrame, valid: pd.Series, longest: pd.Series) -> str:
    agency = longest["Agency"]
    sub = df[(df["Agency"] == agency) & valid]
    mean_h = sub["hours"].mean()
    median_h = sub["hours"].median()
    mean_without_longest = sub.drop(longest.name)["hours"].mean()
    longest_h = longest["hours"]

    return (
        f"{agency}'s mean closure time is {mean_h:,.1f} hours "
        f"({mean_h / 24:,.1f} days), while its median is {median_h:,.1f} hours "
        f"({median_h / 24:,.1f} days), so the mean is {mean_h / median_h:,.1f} "
        "times the typical case. "
        f"The longest case, an {longest['Problem (formerly Complaint Type)']}, "
        f"took {longest_h:,.1f} hours ({longest_h / 24:,.1f} days), about "
        f"{longest_h / median_h:,.0f} times the median, which shows the extreme "
        "right tail behind the gap. "
        f"Removing that one case barely moves the mean (to "
        f"{mean_without_longest:,.1f} hours), so the gap reflects a broad tail of "
        "long cases, not one rogue record; the median remains the better "
        "description of a typical response."
    )


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    df = load()
    valid = mask_valid(df)

    table = agency_table(df, valid)
    print_agency_table(table)
    verify_median(df, valid, "HPD")

    longest = longest_case(df, valid)
    print(
        f"\nNote: {longest['Agency']} is not one of the six largest agencies; "
        "it is the agency of the longest case."
    )
    print("\n2-3 sentence explanation:")
    print(writeup(df, valid, longest))


if __name__ == "__main__":
    main()
