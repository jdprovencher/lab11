testing

## Task 1

| Question | Answer |
|---|---|
| How many rows and columns? | **304,905 rows × 44 columns** |
| How many distinct values does `Problem (formerly Complaint Type)` have? | **174** |
| Earliest `Created Date` | **2025-11-01 00:00:04** |
| Latest `Created Date` | **2025-11-30 23:59:52** |
| How many rows have no `Closed Date`? | **4,136** |

Source: `nyc-311-2025-november.csv.gz`. Each answer was computed with pandas and then independently verified by streaming the gzipped CSV with Python's `csv` module; see `answers.py`.

### Verification

- **Rows:** `zcat nyc-311-2025-november.csv.gz | wc -l` = 304,906 lines = 1 header + 304,905 rows. The header has 44 fields.
- **Distinct Problem:** pandas `nunique()` = 174; a set built from the raw CSV = 174. No blank values.
- **Created Date:** parsed with `%m/%d/%Y %I:%M:%S %p`; all 304,905 values parsed, and an independent `datetime.strptime` pass gives the same earliest and latest.
- **No Closed Date:** pandas `isna()` = 4,136; rows whose raw `Closed Date` field is `""` = 4,136.

### Status of rows with no `Closed Date`

| Status | Rows |
|---|---|
| In Progress | 3,402 |
| Open | 300 |
| Pending | 199 |
| Assigned | 168 |
| Started | 65 |
| Closed | 2 |

Note: the 2 rows marked `Status = Closed` with no `Closed Date` (Unique Keys `66937975` and `66784599`) are a quirk of the source data, not a parsing error.
