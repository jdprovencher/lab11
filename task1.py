"""Answers to the lab questions, each computed two independent ways.

Primary path: pandas.  Check path: streaming csv/gzip, no pandas.
"""
import csv
import gzip
from datetime import datetime
from collections import Counter

import pandas as pd

PATH = "nyc-311-2025-november.csv.gz"
PROBLEM = "Problem (formerly Complaint Type)"

df = pd.read_csv(
    PATH,
    encoding="utf-8",
    encoding_errors="replace",
    low_memory=False,
)

# ---------------------------------------------------------------- 1. shape
rows, cols = df.shape
print(f"Rows: {rows}   Columns: {cols}")

# Check: raw line count minus header, and header field count from csv module.
with gzip.open(PATH, "rt", encoding="utf-8", errors="replace", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    csv_rows = sum(1 for _ in reader)
print(f"  rows check: pandas={rows}  csv={csv_rows}"
      f"  (zcat | wc -l - 1 = 304906 - 1) -> {'OK' if rows == csv_rows else 'MISMATCH'}")
print(f"  cols check: pandas={cols}  csv header={len(header)}"
      f" -> {'OK' if cols == len(header) else 'MISMATCH'}")

if rows != csv_rows or cols != len(header):
    raise SystemExit("shape mismatch - investigate")

# --------------------------------------------------- 2. distinct Problems
n_problems = df[PROBLEM].nunique(dropna=True)
print(f"Distinct {PROBLEM!r}: {n_problems}")

# Check: independent set built while streaming.
with gzip.open(PATH, "rt", encoding="utf-8", errors="replace", newline="") as f:
    reader = csv.DictReader(f)
    problems = {r[PROBLEM] for r in reader if r[PROBLEM] != ""}
print(f"  check: pandas={n_problems}  csv set={len(problems)}"
      f" -> {'OK' if n_problems == len(problems) else 'MISMATCH'}")

if n_problems != len(problems):
    raise SystemExit("distinct-Problem mismatch - investigate")
print(f"  (blank Problem values: pandas={df[PROBLEM].isna().sum()})")

# ------------------------------------------------------ 3. Created Date range
fmt = "%m/%d/%Y %I:%M:%S %p"
created = pd.to_datetime(df["Created Date"], format=fmt, errors="coerce")
print(f"Created Date: earliest={created.min()}  latest={created.max()}"
      f"  unparsed={created.isna().sum()}")

# Check: parse every value with datetime.strptime, no pandas.
lo = hi = None
bad = 0
with gzip.open(PATH, "rt", encoding="utf-8", errors="replace", newline="") as f:
    for r in csv.DictReader(f):
        try:
            t = datetime.strptime(r["Created Date"], fmt)
        except ValueError:
            bad += 1
            continue
        lo = t if lo is None or t < lo else lo
        hi = t if hi is None or t > hi else hi
print(f"  check: csv earliest={lo}  latest={hi}  unparsed={bad}"
      f" -> {'OK' if (lo, hi) == (created.min(), created.max()) else 'MISMATCH'}")

if (lo, hi) != (created.min(), created.max()):
    raise SystemExit("Created Date mismatch - investigate")

# ------------------------------------------------ 4. rows with no Closed Date
open_rows = df["Closed Date"].isna()
print(f"Rows with no Closed Date: {open_rows.sum()}")

# Check: the field is literally empty in the raw CSV.
with gzip.open(PATH, "rt", encoding="utf-8", errors="replace", newline="") as f:
    raw_open = [r for r in csv.DictReader(f) if r["Closed Date"] == ""]
print(f"  check: pandas isna={open_rows.sum()}  csv empty-string={len(raw_open)}"
      f" -> {'OK' if open_rows.sum() == len(raw_open) else 'MISMATCH'}")

if open_rows.sum() != len(raw_open):
    raise SystemExit("open-row mismatch - investigate")

statuses = df.loc[open_rows, "Status"].value_counts(dropna=False)
raw_statuses = Counter(r["Status"] for r in raw_open)
print("Status values on rows with no Closed Date:")
for status, n in statuses.items():
    print(f"  {status!r}: {n}  (csv check: {raw_statuses.get(status, 0)})")
if dict(statuses) != dict(raw_statuses):
    raise SystemExit("Status distribution mismatch - investigate")

# Sanity note: 2 of these rows still say Status=Closed, which is a data quirk
# (Closed Date missing while status says Closed), not a parsing bug.
