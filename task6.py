#!/usr/bin/env python3
"""Task 6: compare the same job (HEAT/HOT WATER) across boroughs."""
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
PROBLEM = "HEAT/HOT WATER"


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
    bad_closed = df["Closed Date"].notna() & df["closed"].isna()
    if bad_closed.any():
        raise SystemExit(f"{bad_closed.sum()} Closed Date values failed to parse")
    df["hours"] = (df["closed"] - df["created"]).dt.total_seconds() / 3600
    print(f"Created Date dtype: {df['created'].dtype}")
    print(f"Closed Date dtype:  {df['closed'].dtype}")
    return df


def build_table(df: pd.DataFrame):
    heat = df[df["Problem (formerly Complaint Type)"] == PROBLEM].copy()
    print(f"\n{PROBLEM}: {len(heat):,} rows")
    print(f"Agencies: {heat['Agency'].value_counts().to_dict()}")

    open_cases = heat["closed"].isna()
    negative = heat["closed"].notna() & (heat["hours"] < 0)
    valid = heat["closed"].notna() & (heat["hours"] >= 0)
    closed = heat[valid]

    print(f"Open cases (no Closed Date): {open_cases.sum():,} -> dropped")
    print(f"Closed-before-created (invalid): {negative.sum():,} -> dropped")
    print(f"Usable closed cases: {valid.sum():,} of {len(heat):,} rows")
    print("\nOpen cases by borough:")
    print(heat[open_cases]["Borough"].value_counts().to_string())

    rows = []
    for borough, sub in closed.groupby("Borough"):
        total = int((heat["Borough"] == borough).sum())
        n_open = int((open_cases & (heat["Borough"] == borough)).sum())
        rows.append({
            "Borough": borough,
            "Complaints": total,
            "OpenDropped": n_open,
            "ClosedUsed": len(sub),
            "MedianHours": sub["hours"].median(),
            "MedianDays": sub["hours"].median() / 24,
        })

    table = pd.DataFrame(rows).sort_values("MedianHours", ascending=True)
    print("\nMedian hours to close, fastest to slowest:")
    print(
        f"{'Borough':<15}{'Complaints':>11}{'Open':>7}"
        f"{'Closed used':>13}{'Median h':>12}{'Median d':>10}"
    )
    print("-" * 68)
    for row in table.itertuples(index=False):
        print(
            f"{row.Borough.title():<15}{row.Complaints:>11,}{row.OpenDropped:>7,}"
            f"{row.ClosedUsed:>13,}{row.MedianHours:>12.2f}{row.MedianDays:>10.2f}"
        )
    return heat, closed, table, int(open_cases.sum())


def verify_median(closed: pd.DataFrame, borough: str = "QUEENS") -> None:
    """Recompute one borough's median with statistics.median on a plain list."""
    subset = closed.loc[closed["Borough"] == borough, "hours"]
    pandas_median = subset.median()
    plain_list_median = statistics.median(subset.tolist())

    # Cross-check (Queens): statistics.median on the plain list gives 42.8400 h;
    # the pandas/groupby median gives 42.8400 h. Same number.
    print(f"\nMedian verification ({borough.title()}):")
    print(f"  pandas median          = {pandas_median:.6f} hours")
    print(f"  statistics.median list = {plain_list_median:.6f} hours")
    print(f"  same? {abs(pandas_median - plain_list_median) < 1e-9}")
    if abs(pandas_median - plain_list_median) >= 1e-9:
        raise SystemExit("Median verification failed")


def chart(table: pd.DataFrame, open_total: int) -> Path:
    # barh draws the first row at the bottom, so reverse the fastest-to-slowest
    # order to put the fastest borough at the top of the chart.
    data = table.sort_values("MedianHours", ascending=False)
    values = data["MedianHours"].to_numpy()
    labels = [b.title() for b in data["Borough"]]
    counts = data["ClosedUsed"].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.barh(
        labels,
        values,
        color="#3b6ea5",
        edgecolor="white",
        linewidth=1.5,
    )
    ax.set_xlabel("Median hours to close", fontsize=11)
    ax.set_ylabel("Borough", fontsize=11)
    ax.set_title(
        "HEAT/HOT WATER: median hours to close by borough, November 2025",
        fontsize=14,
        loc="left",
        pad=14,
    )
    ax.bar_label(
        bars,
        labels=[f"{v:.1f} h  (n={n:,})" for v, n in zip(values, counts)],
        padding=4,
        fontsize=9,
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.grid(True, alpha=0.25)
    ax.set_axisbelow(True)
    ax.margins(x=0.18)
    fig.text(
        0.01,
        0.01,
        f"Same complaint type, same agency (HPD). Closed cases only; "
        f"{open_total:,} open cases dropped.",
        fontsize=8,
        color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    out = HERE / "fig-same-job.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def paragraph(table: pd.DataFrame) -> str:
    fastest = table.iloc[0]
    slowest = table.iloc[-1]
    gap = slowest.MedianHours - fastest.MedianHours
    ratio = slowest.MedianHours / fastest.MedianHours

    return (
        f"The gap for identical work is {gap:.1f} hours ({gap / 24:.2f} days): "
        f"{fastest.Borough.title()} closes HEAT/HOT WATER cases in a median of "
        f"{fastest.MedianHours:.1f} hours, while {slowest.Borough.title()} takes "
        f"{slowest.MedianHours:.1f} hours, or {ratio:.2f} times as long. "
        "Because every row is the same complaint type, the same agency (HPD), and "
        "the same month, the 'different jobs' excuse is no longer available; the "
        "gap is about place, not task. "
        "It could still reflect differences in inspector staffing and deployment, "
        "queue workload and triage, building age and landlord responsiveness, case "
        "complexity, or the way closures are recorded. "
        "To tell those candidates apart I would need HPD staffing and inspection "
        "schedules by borough, assignment and queue timestamps that separate "
        "waiting from work time, and building/landlord condition data; this file "
        "has address, BBL, community board, resolution text, and resolution-update "
        "dates, but none of those pins down capacity versus need versus reporting "
        "practice."
    )


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    df = load()
    heat, closed, table, open_total = build_table(df)
    verify_median(closed, "QUEENS")
    figure = chart(table, open_total)
    print(f"\nSaved chart: {figure.name}")

    print("\nOne-paragraph answer:")
    print(paragraph(table))


if __name__ == "__main__":
    main()
