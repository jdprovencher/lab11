#!/usr/bin/env python3
"""Task 4: hourly rhythms, a borough check, and a night-by-hour heat map."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

PROBLEM_COL = "Problem (formerly Complaint Type)"
BOROUGH_COL = "Borough"
DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"

NOISE = "Noise - Residential"
HEAT = "HEAT/HOT WATER"
CHECK_BOROUGH = "BROOKLYN"


def load() -> pd.DataFrame:
    df = pd.read_csv(
        DATA,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    )
    print(f"Created Date dtype before parsing: {df['Created Date'].dtype}")
    df["created"] = pd.to_datetime(
        df["Created Date"], format=DATE_FORMAT, errors="raise"
    )
    print(f"Created Date dtype after parsing:  {df['created'].dtype}")
    if not pd.api.types.is_datetime64_any_dtype(df["created"]):
        raise SystemExit("Created Date did not parse to a datetime dtype")
    if df["created"].isna().any():
        raise SystemExit(f"{df['created'].isna().sum()} Created Date values failed to parse")

    df["hour"] = df["created"].dt.hour
    df["date"] = df["created"].dt.date
    if not df["hour"].between(0, 23).all():
        raise SystemExit("Parsed hour outside 0-23")
    print(f"Created Date parse failures: {df['created'].isna().sum():,}")
    return df


def hourly(df: pd.DataFrame, problem: str, borough: str | None = None) -> pd.Series:
    sub = df[df[PROBLEM_COL] == problem]
    if borough is not None:
        sub = sub[sub[BOROUGH_COL] == borough]
    return sub.groupby("hour").size().reindex(range(24), fill_value=0)


def peak(hourly_counts: pd.Series) -> tuple[int, int]:
    return int(hourly_counts.idxmax()), int(hourly_counts.max())


def peak_check(df: pd.DataFrame, problem: str) -> tuple[int, int]:
    """Check the plotted peak against value_counts() and a table-like groupby."""
    sub = df[df[PROBLEM_COL] == problem]
    vc_peak = int(sub["hour"].value_counts().idxmax())
    table_peak = int(sub.groupby("hour").size().idxmax())
    counts = hourly(df, problem)
    plotted_peak, plotted_count = peak(counts)
    assert plotted_peak == vc_peak == table_peak, (
        f"{problem}: plot={plotted_peak}, value_counts={vc_peak}, table={table_peak}"
    )
    print(
        f"  {problem:<22} peak={plotted_peak:02d}:00  "
        f"count={plotted_count:,}  value_counts={vc_peak:02d}  table={table_peak:02d}"
    )
    return plotted_peak, plotted_count


def line_chart(df: pd.DataFrame) -> tuple[Path, str]:
    noise = hourly(df, NOISE)
    heat = hourly(df, HEAT)
    noise_peak, noise_peak_n = peak(noise)
    heat_peak, heat_peak_n = peak(heat)

    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    ax.plot(
        noise.index,
        noise.values,
        marker="o",
        linewidth=2.2,
        markersize=4,
        color="#c0392b",
        label=NOISE,
    )
    ax.plot(
        heat.index,
        heat.values,
        marker="o",
        linewidth=2.2,
        markersize=4,
        color="#2c6fbb",
        label=HEAT,
    )

    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(-0.5, 23.5)
    ax.set_xlabel("Hour of day (0 = midnight)", fontsize=11)
    ax.set_ylabel("Number of 311 calls in November 2025", fontsize=11)
    ax.set_title(
        "Noise and heat complaints peak at different hours",
        fontsize=14,
        loc="left",
        pad=12,
    )
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")

    for x, y, label, color in [
        (noise_peak, noise_peak_n, f"{NOISE}\npeak {noise_peak:02d}:00", "#c0392b"),
        (heat_peak, heat_peak_n, f"{HEAT}\npeak {heat_peak:02d}:00", "#2c6fbb"),
    ]:
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(x, y + 600),
            ha="center",
            fontsize=8,
            color=color,
            arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
        )

    claim_one = (
        f"{NOISE} peaks at {noise_peak:02d}:00 with {noise_peak_n:,} calls, while "
        f"{HEAT} peaks at {heat_peak:02d}:00 with {heat_peak_n:,} calls."
    )
    claim_two = (
        "That is consistent with a morning rhythm for heat problems and a "
        "late-night rhythm for noise complaints."
    )
    fig.text(
        0.5,
        0.015,
        claim_one + " " + claim_two,
        ha="center",
        va="bottom",
        fontsize=9,
        wrap=True,
        color="#333333",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    out = HERE / "fig-hours.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out, claim_one + " " + claim_two


def borough_check(df: pd.DataFrame) -> None:
    print(f"\nBorough split check ({CHECK_BOROUGH.title()} only):")
    for problem in (NOISE, HEAT):
        counts = hourly(df, problem, CHECK_BOROUGH)
        b_peak, b_count = peak(counts)
        all_peak, _ = peak(hourly(df, problem))
        print(
            f"  {problem:<22} all={all_peak:02d}:00  "
            f"{CHECK_BOROUGH.title()}={b_peak:02d}:00 ({b_count:,} calls)"
            f"  {'same' if b_peak == all_peak else 'DIFFERENT'}"
        )


def nights_table(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    noise = df[df[PROBLEM_COL] == NOISE]
    dates = list(pd.date_range("2025-11-01", "2025-11-30", freq="D").date)
    nights = pd.crosstab(noise["date"], noise["hour"])
    nights = nights.reindex(index=dates, columns=range(24), fill_value=0)
    if nights.shape != (30, 24):
        raise SystemExit(f"Expected a 30x24 table, got {nights.shape}")
    if int(nights.values.sum()) != len(noise):
        raise SystemExit("Night table does not add up to the filtered row count")
    print(f"\nDay x hour table: {nights.shape[0]} rows x {nights.shape[1]} columns")
    print(f"  cell total={int(nights.values.sum()):,}  noise rows={len(noise):,}")
    return nights, dates


def heatmap(nights: pd.DataFrame, dates: list) -> Path:
    row, col = np.unravel_index(np.argmax(nights.values), nights.shape)
    max_value = int(nights.values[row, col])
    max_date = dates[row]

    fig, ax = plt.subplots(figsize=(13, 8))
    image = ax.imshow(
        nights.values,
        aspect="auto",
        cmap="magma",
        interpolation="nearest",
    )
    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=8)
    ax.set_yticks(range(len(dates)))
    ax.set_yticklabels([d.strftime("%b %d") for d in dates], fontsize=8)
    ax.set_xlabel("Hour of day (0 = midnight)", fontsize=11)
    ax.set_ylabel("Night (calendar date)", fontsize=11)
    ax.set_title(
        f"{NOISE}: calls by night and hour, November 2025",
        fontsize=14,
        loc="left",
        pad=12,
    )
    colorbar = fig.colorbar(image, ax=ax, pad=0.015)
    colorbar.set_label("Number of calls", fontsize=10)

    ax.add_patch(
        Rectangle(
            (col - 0.5, row - 0.5),
            1,
            1,
            fill=False,
            edgecolor="cyan",
            linewidth=2.0,
        )
    )
    ax.annotate(
        f"{max_date:%b} {max_date.day}, {col:02d}:00\n{max_value} calls",
        xy=(col, row),
        xytext=(col + 3, row + 5),
        color="white",
        fontsize=9,
        fontweight="bold",
        ha="left",
        va="center",
        bbox={"boxstyle": "round", "facecolor": "black", "alpha": 0.55,
              "edgecolor": "none"},
        arrowprops={"arrowstyle": "->", "color": "white", "lw": 1.2},
    )
    fig.tight_layout()

    out = HERE / "fig-nights.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def anomaly_checks(df: pd.DataFrame) -> None:
    sub = df[df[PROBLEM_COL] == NOISE]
    target = sub[
        (sub["date"] == pd.Timestamp("2025-11-02").date()) & (sub["hour"] == 1)
    ]
    one_am = sub[sub["hour"] == 1].groupby("date").size()
    top_address = target["Incident Address"].value_counts()
    top_n = int(top_address.iloc[0])
    top_share = top_n / len(target)

    nov12 = sub[sub["date"] == pd.Timestamp("2025-11-12").date()]
    nov12_top = nov12["Incident Address"].value_counts()
    nov12_addr = nov12_top.index[0]
    nov12_addr_n = int(nov12_top.iloc[0])

    print("\nAnomaly checks for 2025-11-02 01:00 (Noise - Residential):")
    print(f"  cell count={len(target):,}; median 01:00 on other nights="
          f"{one_am.drop(pd.Timestamp('2025-11-02').date()).median():.0f}")
    print(f"  bad rows: duplicate Unique Keys={df['Unique Key'].duplicated().sum():,}, "
          f"fully duplicated rows={df.duplicated().sum():,}, "
          f"NaT Created Date={df['created'].isna().sum():,}")
    print(f"  burst check: {len(target):,} rows, "
          f"{target['Incident Address'].nunique():,} addresses, "
          f"{target[BOROUGH_COL].nunique()} boroughs; "
          f"busiest address={top_n} calls ({top_share:.1%})")
    print(f"  separate Nov 12 cluster: {len(nov12):,} noise calls, "
          f"{nov12_addr_n:,} from {nov12_addr} ({nov12_addr_n / len(nov12):.1%})")


def writeup(df: pd.DataFrame) -> str:
    sub = df[df[PROBLEM_COL] == NOISE]
    target = sub[
        (sub["date"] == pd.Timestamp("2025-11-02").date()) & (sub["hour"] == 1)
    ]
    one_am = sub[sub["hour"] == 1].groupby("date").size()
    median_one_am = one_am.drop(pd.Timestamp("2025-11-02").date()).median()
    nov12 = sub[sub["date"] == pd.Timestamp("2025-11-12").date()]
    nov12_top = nov12["Incident Address"].value_counts()
    nov12_addr = nov12_top.index[0]
    nov12_addr_n = int(nov12_top.iloc[0])

    return (
        "No: most nights share a late-night peak, but Nov 12 is elevated all day "
        "and Nov 2 has a sharp 1 a.m. spike. "
        f"The largest single cell is 2025-11-02 at 01:00, with {len(target):,} "
        f"Noise - Residential calls — about "
        f"{len(target) / median_one_am:.1f} times the median 01:00 count on other "
        f"nights ({median_one_am:.0f}). "
        "I think that 1 a.m. spike is the end of daylight saving time at 2:00 a.m. "
        "that morning, which made 1:00-1:59 occur twice and collapsed two clock "
        "hours into one timestamp bucket, probably amplified by Saturday-night and "
        "Halloween-weekend reporting. "
        "Check one ruled out bad rows and duplicated records: all 304,905 Created "
        "Date values parsed to datetime64[ns] with zero NaT, zero duplicate Unique "
        "Keys, and zero fully duplicated rows. "
        f"Check two ruled out a localized burst behind that cell: its {len(target):,} "
        f"calls span five boroughs and {target['Incident Address'].nunique():,} "
        "addresses, with the busiest address contributing only 10 calls (3.2%); "
        f"Nov 12's separate {len(nov12):,}-call cluster at {nov12_addr} "
        f"({nov12_addr_n:,} calls) is a real one-address burst, not the cause of "
        "the 1 a.m. spike."
    )


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    df = load()

    print("\nPeak-hour verification against value_counts() and groupby-table:")
    peak_check(df, NOISE)
    peak_check(df, HEAT)

    figure, claim = line_chart(df)
    print(f"\nSaved line chart: {figure.name}")
    print(f"Claim: {claim}")

    borough_check(df)

    nights, dates = nights_table(df)
    heatmap_path = heatmap(nights, dates)
    print(f"Saved heat map: {heatmap_path.name}")

    anomaly_checks(df)

    print("\nNight-by-night analysis (5 sentences):")
    print(writeup(df))


if __name__ == "__main__":
    main()
