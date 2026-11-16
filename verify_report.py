#!/usr/bin/env python3
"""Independent second pass over every headline number in report.md.

The task scripts compute their answers with pandas.  This script recomputes the
same answers from the gzipped CSV using only ``csv``, ``gzip``, ``Counter``,
``statistics``, and plain arithmetic, then compares the two routes.  It is the
"second way" behind the Verify columns in the report.

Run from the repository root:

    python3 verify_report.py
"""
import csv
import gzip
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "nyc-311-2025-november.csv.gz"

FMT = "%m/%d/%Y %I:%M:%S %p"
PROBLEM = "Problem (formerly Complaint Type)"
NOISE = "Noise - Residential"
HEAT = "HEAT/HOT WATER"

POPULATIONS = {
    "BRONX": 1_472_654,
    "BROOKLYN": 2_736_074,
    "MANHATTAN": 1_694_251,
    "QUEENS": 2_405_464,
    "STATEN ISLAND": 495_747,
}

failures = []


def check(label, got, expected, note=""):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}: got {got!r}, expected {expected!r} {note}".rstrip())
    if not ok:
        failures.append(label)


def close(label, got, expected, tolerance=5e-5):
    ok = abs(got - expected) <= tolerance
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}: got {got:.6f}, expected {expected:.6f} "
          f"(tolerance {tolerance})")
    if not ok:
        failures.append(label)


def main():
    if not DATA.exists():
        raise SystemExit(f"Data file not found: {DATA}")

    rows = 0
    columns = None
    problems = set()
    open_rows = 0
    open_statuses = Counter()
    unique_keys = set()
    duplicate_keys = 0
    earliest = latest = None

    borough_calls = Counter()
    si_problems = Counter()
    queens_problems = Counter()
    si_parking_addresses = Counter()
    queens_parking_addresses = Counter()

    noise_by_hour = Counter()
    heat_by_hour = Counter()
    brooklyn_noise_by_hour = Counter()
    brooklyn_heat_by_hour = Counter()
    noise_cells = Counter()          # (date, hour) -> calls
    noise_dates = set()
    noise_one_am_by_day = Counter()
    noise_anomaly_addresses = Counter()
    noise_anomaly_boroughs = set()
    nov12_addresses = Counter()

    agency_total = Counter()
    agency_open = Counter()
    agency_negative = Counter()
    durations = defaultdict(list)
    longest = None

    heat_open = Counter()
    heat_durations = defaultdict(list)

    unspecified = 0
    unspecified_agency = Counter()
    unspecified_problem = Counter()
    unspecified_address_type = Counter()
    unspecified_facility = Counter()
    unspecified_present = Counter()
    unspecified_cities = Counter()
    unspecified_zips = Counter()

    with gzip.open(DATA, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = len(reader.fieldnames)

        for row in reader:
            rows += 1
            problem = row[PROBLEM]
            if problem:
                problems.add(problem)
            if row["Closed Date"] == "":
                open_rows += 1
                open_statuses[row["Status"]] += 1
            if row["Unique Key"] in unique_keys:
                duplicate_keys += 1
            else:
                unique_keys.add(row["Unique Key"])

            created = datetime.strptime(row["Created Date"], FMT)
            if earliest is None or created < earliest:
                earliest = created
            if latest is None or created > latest:
                latest = created

            borough = row["Borough"]
            agency = row["Agency"]
            borough_calls[borough] += 1
            agency_total[agency] += 1

            if borough == "STATEN ISLAND":
                si_problems[problem] += 1
                if problem == "Illegal Parking":
                    si_parking_addresses[row["Incident Address"]] += 1
            elif borough == "QUEENS":
                queens_problems[problem] += 1
                if problem == "Illegal Parking":
                    queens_parking_addresses[row["Incident Address"]] += 1

            if problem == NOISE:
                noise_by_hour[created.hour] += 1
                noise_cells[(created.date(), created.hour)] += 1
                noise_dates.add(created.date())
                if created.hour == 1:
                    noise_one_am_by_day[created.date()] += 1
                if created.date().isoformat() == "2025-11-02" and created.hour == 1:
                    noise_anomaly_addresses[row["Incident Address"]] += 1
                    noise_anomaly_boroughs.add(borough)
                if created.date().isoformat() == "2025-11-12":
                    nov12_addresses[row["Incident Address"]] += 1
                if borough == "BROOKLYN":
                    brooklyn_noise_by_hour[created.hour] += 1

            if problem == HEAT:
                heat_by_hour[created.hour] += 1
                if borough == "BROOKLYN":
                    brooklyn_heat_by_hour[created.hour] += 1
                if row["Closed Date"] == "":
                    heat_open[borough] += 1
                else:
                    closed = datetime.strptime(row["Closed Date"], FMT)
                    hours = (closed - created).total_seconds() / 3600
                    if hours >= 0:
                        heat_durations[borough].append(hours)

            if borough == "Unspecified":
                unspecified += 1
                unspecified_agency[agency] += 1
                unspecified_problem[problem] += 1
                unspecified_address_type[row["Address Type"]] += 1
                if row["Facility Type"]:
                    unspecified_facility[row["Facility Type"]] += 1
                for field in ("Incident Zip", "Incident Address", "City"):
                    if row[field]:
                        unspecified_present[field] += 1
                if row["Incident Zip"]:
                    unspecified_zips[row["Incident Zip"]] += 1
                if row["City"]:
                    unspecified_cities[row["City"]] += 1
                if row["Latitude"] and row["Longitude"]:
                    unspecified_present["both coordinates"] += 1

            if row["Closed Date"] == "":
                agency_open[agency] += 1
                continue
            closed = datetime.strptime(row["Closed Date"], FMT)
            hours = (closed - created).total_seconds() / 3600
            if hours < 0:
                agency_negative[agency] += 1
                continue
            durations[agency].append(hours)
            if longest is None or hours > longest[0]:
                longest = (hours, row["Unique Key"], agency, problem,
                           row["Created Date"], row["Closed Date"])

    print("Task 1 — shape, distinct problems, date range, open rows")
    check("rows", rows, 304_905)
    check("columns", columns, 44)
    check("distinct problem types", len(problems), 174)
    check("Rows with no `Closed Date`", open_rows, 4_136)
    check("Status counts on open rows", dict(open_statuses),
          {"In Progress": 3_402, "Open": 300, "Pending": 199,
           "Assigned": 168, "Started": 65, "Closed": 2})
    check("duplicate Unique Keys", duplicate_keys, 0)
    check("earliest Created Date", earliest,
          datetime(2025, 11, 1, 0, 0, 4))
    check("latest Created Date", latest,
          datetime(2025, 11, 30, 23, 59, 52))

    print("\nTask 2 — Staten Island and Queens profile")
    check("Staten Island calls", si_problems.total(), 9_871)
    check("Queens calls", queens_problems.total(), 69_617)
    close("Queens / Staten Island ratio",
          queens_problems.total() / si_problems.total(), 7.052680, 1e-5)
    expected_si = [("Illegal Parking", 1_323), ("Noise - Residential", 768),
                   ("Water System", 604), ("Street Light Condition", 418),
                   ("Blocked Driveway", 392)]
    expected_queens = [("Illegal Parking", 14_779), ("HEAT/HOT WATER", 6_907),
                       ("Blocked Driveway", 6_591), ("Noise - Residential", 5_844),
                       ("Noise - Street/Sidewalk", 3_303)]
    check("Staten Island top five", si_problems.most_common(5), expected_si)
    check("Queens top five", queens_problems.most_common(5), expected_queens)
    check("Staten Island Illegal Parking top address",
          si_parking_addresses.most_common(1)[0], ("555 JOHNSTON TERRACE", 17))
    close("Staten Island top-address share",
          si_parking_addresses.most_common(1)[0][1] / 1_323, 0.012850, 1e-6)
    check("Queens Illegal Parking top address",
          queens_parking_addresses.most_common(1)[0], ("5-47 50 AVENUE", 465))
    close("Queens top-address share",
          queens_parking_addresses.most_common(1)[0][1] / 14_779, 0.031464, 1e-6)

    print("\nTask 3 — population normalization")
    check("five-borough population total", sum(POPULATIONS.values()), 8_804_190)
    check("Unspecified rows dropped", borough_calls["Unspecified"], 196)
    check("rows retained", rows - borough_calls["Unspecified"], 304_709)
    expected_calls = {"BRONX": 74_674, "BROOKLYN": 88_591,
                      "MANHATTAN": 61_956, "QUEENS": 69_617,
                      "STATEN ISLAND": 9_871}
    expected_rates = {"BRONX": 50.7071, "BROOKLYN": 32.3789,
                      "MANHATTAN": 36.5684, "QUEENS": 28.9412,
                      "STATEN ISLAND": 19.9114}
    for borough, population in POPULATIONS.items():
        check(f"{borough.title()} calls", borough_calls[borough],
              expected_calls[borough])
        close(f"{borough.title()} calls per 1,000",
              borough_calls[borough] / population * 1_000,
              expected_rates[borough], 1e-4)
    close("Bronx plain-calculator rate", 74_674 / 1_472_654 * 1_000,
          50.7071, 1e-4)

    print("\nTask 4 — hourly rhythms and night matrix")
    check("Noise peak hour", noise_by_hour.most_common(1)[0], (22, 3_878))
    check("Heat peak hour", heat_by_hour.most_common(1)[0], (9, 2_799))
    check("Brooklyn noise peak", brooklyn_noise_by_hour.most_common(1)[0],
          (22, 910))
    check("Brooklyn heat peak", brooklyn_heat_by_hour.most_common(1)[0],
          (9, 845))
    check("Noise day count", len(noise_dates), 30)
    check("Night matrix cell total", sum(noise_cells.values()), 43_928)
    max_cell = max(noise_cells.items(), key=lambda item: item[1])
    check("Night matrix maximum cell", max_cell,
          ((datetime(2025, 11, 2).date(), 1), 308))
    other_one_am = [n for day, n in noise_one_am_by_day.items()
                    if day.isoformat() != "2025-11-02"]
    median_one_am = statistics.median(other_one_am)
    check("Median 01:00 calls on other nights", median_one_am, 40)
    close("01:00 anomaly ratio", 308 / median_one_am, 7.7, 1e-9)
    check("Number of addresses in anomaly cell",
          len(noise_anomaly_addresses), 248)
    check("Number of boroughs in anomaly cell",
          len(noise_anomaly_boroughs), 5)
    check("Busiest anomaly address calls",
          noise_anomaly_addresses.most_common(1)[0][1], 10)
    check("Nov 12 noise calls", sum(nov12_addresses.values()), 2_817)
    check("Nov 12 busiest address", nov12_addresses.most_common(1)[0],
          ("655 EAST  230 STREET", 2_139))
    close("Nov 12 busiest-address share", 2_139 / 2_817, 0.759318, 1e-6)

    print("\nTask 5 — response times")
    check("open cases dropped", open_rows, 4_136)
    check("closed-before-created rows", sum(agency_negative.values()), 98)
    check("usable closed cases", sum(len(v) for v in durations.values()),
          300_671)
    expected_medians = {
        "NYPD": 1.250556, "HPD": 53.836528, "DSNY": 38.556389,
        "DOT": 83.75, "DEP": 39.583333, "DOB": 182.537361,
    }
    expected_counts = {
        "NYPD": 139_751, "HPD": 86_032, "DSNY": 20_149,
        "DOT": 14_119, "DEP": 13_608, "DOB": 8_318,
    }
    expected_open = {
        "NYPD": 0, "HPD": 215, "DSNY": 213, "DOT": 368, "DEP": 126, "DOB": 0,
    }
    expected_negative = {
        "NYPD": 68, "HPD": 0, "DSNY": 1, "DOT": 29, "DEP": 0, "DOB": 0,
    }
    for agency, expected in expected_medians.items():
        check(f"{agency} open dropped", agency_open[agency],
              expected_open[agency])
        check(f"{agency} invalid dropped", agency_negative[agency],
              expected_negative[agency])
        check(f"{agency} closed rows", len(durations[agency]),
              expected_counts[agency])
        close(f"{agency} median hours", statistics.median(durations[agency]),
              expected, 5e-5)
    check("longest case key", longest[1], "66705910")
    check("longest case agency", longest[2], "DPR")
    check("longest case problem", longest[3], "Overgrown Tree/Branches")
    close("longest case hours", longest[0], 8_995.713889, 5e-5)
    close("longest case days", longest[0] / 24, 374.821412, 5e-5)
    dpr = durations["DPR"]
    check("DPR case count", len(dpr), 5_468)
    close("DPR mean hours", statistics.mean(dpr), 917.515092, 5e-5)
    close("DPR median hours", statistics.median(dpr), 186.691944, 5e-5)
    close("DPR mean / median", statistics.mean(dpr) / statistics.median(dpr),
          4.914594, 5e-5)
    close("DPR mean excluding longest",
          statistics.mean([value for value in dpr if value != longest[0]]),
          916.037463, 5e-5)

    print("\nTask 6 — same job, different boroughs")
    check("HEAT/HOT WATER rows",
          sum(len(v) for v in heat_durations.values()) + sum(heat_open.values()),
          47_946)
    check("HEAT/HOT WATER open cases", sum(heat_open.values()), 34)
    expected_heat = {
        "STATEN ISLAND": 27.744028, "BRONX": 30.815,
        "MANHATTAN": 34.159444, "BROOKLYN": 37.725556,
        "QUEENS": 42.84,
    }
    expected_heat_counts = {
        "STATEN ISLAND": 348, "BRONX": 16_663, "MANHATTAN": 11_425,
        "BROOKLYN": 12_569, "QUEENS": 6_907,
    }
    for borough, expected in expected_heat.items():
        check(f"{borough.title()} HEAT closed rows",
              len(heat_durations[borough]), expected_heat_counts[borough])
        close(f"{borough.title()} HEAT median",
              statistics.median(heat_durations[borough]), expected, 5e-5)
    queens = statistics.median(heat_durations["QUEENS"])
    staten = statistics.median(heat_durations["STATEN ISLAND"])
    close("Queens - Staten Island gap hours", queens - staten, 15.095972, 5e-5)
    close("Queens / Staten Island ratio", queens / staten, 1.544116, 5e-5)

    print("\nTask 7 — Unspecified-borough anomaly")
    check("Unspecified rows", unspecified, 196)
    check("top agency", unspecified_agency.most_common(1)[0], ("TLC", 70))
    check("DOT rows", unspecified_agency["DOT"], 59)
    check("DSNY rows", unspecified_agency["DSNY"], 30)
    check("top-three agency rows", sum(n for _, n in unspecified_agency.most_common(3)),
          159)
    check("top problem", unspecified_problem.most_common(1)[0],
          ("Ferry Inquiry", 29))
    check("Taxi Complaint rows", unspecified_problem["Taxi Complaint"], 24)
    check("Derelict Vehicles rows", unspecified_problem["Derelict Vehicles"], 23)
    check("For Hire Vehicle Complaint rows",
          unspecified_problem["For Hire Vehicle Complaint"], 20)
    check("missing Incident Zip", 196 - unspecified_present["Incident Zip"], 176)
    check("missing Incident Address",
          196 - unspecified_present["Incident Address"], 163)
    check("missing City", 196 - unspecified_present["City"], 179)
    check("rows with zip", unspecified_present["Incident Zip"], 20)
    check("distinct zips", len(unspecified_zips), 15)
    check("rows with city", unspecified_present["City"], 17)
    check("distinct cities", len(unspecified_cities), 14)
    check("rows with both coordinates",
          unspecified_present["both coordinates"], 13)
    check("intersection rows", unspecified_address_type["INTERSECTION"], 42)
    check("DSNY garage rows", unspecified_facility["DSNY Garage"], 12)

    print("\n" + "=" * 64)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED: {failures}")
        raise SystemExit(1)
    print("All second-method checks passed.")


if __name__ == "__main__":
    main()
