testing

## Task 1

Analysis of `nyc-311-2025-november.csv.gz`. Every answer below was computed with pandas and independently verified by streaming the gzipped CSV with Python's `csv` module (see `answers.py`).

**Rows and columns:** 304,905 rows × 44 columns.

- Check: `zcat nyc-311-2025-november.csv.gz | wc -l` = 304,906 lines = 1 header + 304,905 rows; the header has 44 fields.

**Distinct `Problem (formerly Complaint Type)` values:** 174 (no blank values).

**`Created Date` range:** earliest `2025-11-01 00:00:04`, latest `2025-11-30 23:59:52`.

- Parsed with `%m/%d/%Y %I:%M:%S %p`; all 304,905 values parsed successfully.

**Rows with no `Closed Date`:** 4,136.

- Check: 4,136 rows have an empty raw `Closed Date` field.

Their `Status` values:

| Status | Rows |
|---|---|
| In Progress | 3,402 |
| Open | 300 |
| Pending | 199 |
| Assigned | 168 |
| Started | 65 |
| Closed | 2 |

Note: the 2 rows marked `Status = Closed` with no `Closed Date` (Unique Keys `66937975` and `66784599`) are a quirk of the source data, not a parsing error.
