#!/usr/bin/env python3
"""Task 2: profile one borough (Staten Island), then compare it with Queens.

Counts here are 311 calls, not residents. The script also checks whether a
single address dominates the borough's top complaint.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # save figures without needing a display
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

BOROUGH_COL = "Borough"
PROBLEM_COL = "Problem (formerly Complaint Type)"
ADDRESS_COL = "Incident Address"

PRIMARY = "STATEN ISLAND"
SECONDARY = "QUEENS"
TOP_N = 10


def load_data() -> pd.DataFrame:
    return pd.read_csv(
        DATA,
        encoding="utf-8",
        encoding_errors="replace",
        low_memory=False,
    )


def top_problems(df: pd.DataFrame, borough: str):
    sub = df[df[BOROUGH_COL] == borough]
    total = len(sub)
    counts = sub[PROBLEM_COL].value_counts()
    return sub, total, counts


def print_top_five(borough: str, total: int, counts: pd.Series) -> None:
    print(f"\n{borough.title()} — {total:,} total 311 calls")
    print(f"{'#':>2}  {'Problem (formerly Complaint Type)':<36} {'Calls':>7}  {'Share':>6}")
    print("-" * 66)
    for rank, (problem, n) in enumerate(counts.head(5).items(), start=1):
        label = problem if len(problem) <= 36 else problem[:35] + "…"
        print(f"{rank:>2}. {label:<36} {n:>7,}  {n / total:>5.1%}")


def plot_top_ten(borough: str, total: int, counts: pd.Series) -> Path:
    top = counts.head(TOP_N)
    labels = top.index[::-1]
    values = top.values[::-1]

    fig, ax = plt.subplots(figsize=(10, 6.5))
    bars = ax.barh(labels, values, color="#3b6ea5", edgecolor="white", linewidth=1.5)
    ax.set_xlabel("Number of 311 calls", fontsize=11)
    ax.set_ylabel("Problem (formerly Complaint Type)", fontsize=11)
    ax.set_title(
        f"{borough.title()}: top 10 311 problems, November 2025",
        fontsize=14,
        loc="left",
        pad=14,
    )
    ax.bar_label(bars, labels=[f"{v:,}" for v in values], padding=3, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.grid(True, alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.01,
        "Counts measure calls, not residents.",
        fontsize=8,
        color="dimgray",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    out = HERE / f"fig-borough-{borough.lower().replace(' ', '-')}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def address_check(sub: pd.DataFrame, total: int, counts: pd.Series) -> None:
    """Report whether one address dominates the borough's top complaint."""
    problem = counts.index[0]
    n = counts.iloc[0]
    rows = sub[sub[PROBLEM_COL] == problem]
    addresses = rows[ADDRESS_COL].dropna().value_counts()

    print(f"\nAddress trap — top problem: {problem!r}")
    print(f"  {n:,} calls ({n / total:.1%} of all {total:,} calls in the borough).")
    if addresses.empty:
        print("  No usable address values for this problem.")
        return

    top_address, top_count = addresses.index[0], addresses.iloc[0]
    top_share = top_count / n
    print(f"  Most-reported address: {top_address} — {top_count:,} calls "
          f"({top_share:.1%} of this problem's calls).")
    if top_share >= 0.10:
        print("  One address dominates this complaint; treat it as a hotspot, "
              "not as a borough-wide pattern.")
    else:
        print("  No single address dominates this complaint; the calls are spread out.")

    top_two = addresses.head(2)
    if len(top_two) > 1:
        two_share = top_two.sum() / n
        print(f"  Two busiest addresses together: {top_two.sum():,} calls "
              f"({two_share:.1%}).")


def comparison_paragraph(
    primary_total: int,
    primary_counts: pd.Series,
    secondary_total: int,
    secondary_counts: pd.Series,
    secondary_sub: pd.DataFrame,
) -> str:
    q_top = secondary_counts.index[0]
    p_top = primary_counts.index[0]
    q_rows = secondary_sub[secondary_sub[PROBLEM_COL] == q_top]
    q_addresses = q_rows[ADDRESS_COL].dropna().value_counts()
    addr_text = ""
    if len(q_addresses) >= 2:
        a1, a2 = q_addresses.index[0], q_addresses.index[1]
        n1, n2 = int(q_addresses.iloc[0]), int(q_addresses.iloc[1])
        addr_text = (
            f" Within Queens' top category, two addresses — {a1} ({n1:,} calls) "
            f"and {a2} ({n2:,} calls) — account for "
            f"{(n1 + n2) / len(q_rows):.1%} of the calls, so part of that total "
            f"reflects repeated reports about a few locations."
        )

    def share(counts, n, problem):
        return counts[problem] / n

    q_items = list(secondary_counts.head(5).items())
    p_items = list(primary_counts.head(5).items())
    q_line = ", ".join(f"{name} ({n / secondary_total:.1%})" for name, n in q_items[1:])
    p_extra = [name for name, _ in p_items if name not in dict(q_items)]
    p_extra_text = " and ".join(p_extra[:2])

    sentences = [
        f"Queens recorded {secondary_total:,} calls in November 2025 — about "
        f"{secondary_total / primary_total:.1f} times Staten Island's "
        f"{primary_total:,} — and its top problem is also {q_top}, but it accounts "
        f"for {share(secondary_counts, secondary_total, q_top):.1%} of Queens "
        f"calls versus {share(primary_counts, primary_total, p_top):.1%} on Staten Island.",
        f"The rest of Queens' top five leans toward housing and neighborhood noise "
        f"— {q_line} — whereas Staten Island's top five also includes "
        f"{p_extra_text}.",
        "A plausible hypothesis is that Queens' denser, more mixed housing stock "
        "and heavier curbside demand generate more parking, heat, and noise calls "
        "per resident, while Staten Island's lower density and different housing "
        "and infrastructure mix give water and streetlight problems a larger share "
        "of its much smaller call base." + addr_text,
        "None of this proves the why: the dataset counts calls, not people, and "
        "reporting habits can differ from borough to borough.",
    ]
    return " ".join(sentences)


def main() -> None:
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    df = load_data()
    print(f"Loaded {len(df):,} rows × {len(df.columns)} columns from {DATA.name}")

    primary_sub, primary_total, primary_counts = top_problems(df, PRIMARY)
    secondary_sub, secondary_total, secondary_counts = top_problems(df, SECONDARY)

    print_top_five(PRIMARY, primary_total, primary_counts)
    print_top_five(SECONDARY, secondary_total, secondary_counts)

    figure = plot_top_ten(PRIMARY, primary_total, primary_counts)
    print(f"\nSaved chart: {figure.name}")

    address_check(primary_sub, primary_total, primary_counts)
    address_check(secondary_sub, secondary_total, secondary_counts)

    print("\nQueens compared with Staten Island (3–5 sentences):")
    print(comparison_paragraph(
        primary_total,
        primary_counts,
        secondary_total,
        secondary_counts,
        secondary_sub,
    ))


if __name__ == "__main__":
    main()
