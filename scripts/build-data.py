#!/usr/bin/env python3
"""Build public/data/sp500-top-weights.json from local raw files.

Sources (no network):
  - data/raw/sp500-weightings-1979-2023.xlsx  (Zenodo, Shvets, CC BY 4.0)
  - data/raw/spy-holdings/YYYY.csv            (SPY annual holdings, 2000–2025)

Year coverage:
  1994–1999  year-end snapshot from Zenodo
  2000–2025  SPY holdings CSVs (preferred when both exist)
  2026       carry-forward of 2025, marked approximate
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
EXCEL_EPOCH = datetime(1899, 12, 30)
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
XLSX = RAW / "sp500-weightings-1979-2023.xlsx"
SPY_DIR = RAW / "spy-holdings"
OUT = ROOT / "public" / "data" / "sp500-top-weights.json"
TOP_N = 25
START_YEAR = 1994
END_YEAR = 2026


def excel_date(serial: float) -> datetime:
    return EXCEL_EPOCH + timedelta(days=float(serial))


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = ET.parse(zf.open("xl/sharedStrings.xml")).getroot()
    strings: list[str] = []
    for si in root.findall("m:si", NS):
        strings.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return strings


def cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    v = cell.find("m:v", NS)
    if v is None or v.text is None:
        return None
    if cell.get("t") == "s":
        return shared[int(v.text)]
    return v.text


def col_index(ref: str) -> int:
    letters = "".join(c for c in ref if c.isalpha())
    n = 0
    for c in letters:
        n = n * 26 + (ord(c) - 64)
    return n


def parse_zenodo() -> dict[int, list[dict]]:
    if not XLSX.exists():
        print(f"skip zenodo: missing {XLSX}")
        return {}

    zf = zipfile.ZipFile(XLSX)
    shared = load_shared_strings(zf)
    sheet = ET.parse(zf.open("xl/worksheets/sheet1.xml")).getroot()
    rows = list(sheet.find("m:sheetData", NS).findall("m:row", NS))

    header_cells = rows[1].findall("m:c", NS)
    dates: list[tuple[int, datetime]] = []
    for cell in header_cells:
        ref = cell.get("r") or ""
        col = col_index(ref)
        raw = cell_value(cell, shared)
        if col < 4 or raw in (None, "", "Ticker", "ISIN Code", "Company Name"):
            continue
        try:
            dates.append((col, excel_date(float(raw))))
        except ValueError:
            continue

    year_col: dict[int, tuple[datetime, int]] = {}
    for idx, dt in dates:
        if START_YEAR <= dt.year <= 2022:
            existing = year_col.get(dt.year)
            if existing is None or dt > existing[0]:
                year_col[dt.year] = (dt, idx)
    year_to_idx = {year: idx for year, (_dt, idx) in year_col.items()}

    by_year: dict[int, list[tuple[str, str, float]]] = {y: [] for y in year_to_idx}

    for row in rows[2:]:
        values: dict[int, str | None] = {}
        for cell in row.findall("m:c", NS):
            ref = cell.get("r") or ""
            values[col_index(ref)] = cell_value(cell, shared)
        ticker = (values.get(1) or "").strip()
        name = (values.get(3) or ticker).strip()
        if not ticker:
            continue
        for year, col in year_to_idx.items():
            raw = values.get(col)
            if raw in (None, ""):
                continue
            try:
                weight = float(raw) * 100.0
            except ValueError:
                continue
            if weight <= 0:
                continue
            by_year[year].append((ticker, name, weight))

    out: dict[int, list[dict]] = {}
    for year, rows_y in by_year.items():
        rows_y.sort(key=lambda r: r[2], reverse=True)
        out[year] = [
            {"rank": i, "ticker": t, "name": n, "weight": round(w, 3)}
            for i, (t, n, w) in enumerate(rows_y[:TOP_N], start=1)
        ]
    print(f"zenodo years: {sorted(out)}")
    return out


def clean_ticker(company: str, ticker: str, used: set[str]) -> str:
    t = (ticker or "").strip().upper()
    company_l = company.lower()
    if "alphabet" in company_l and "class a" in company_l:
        t = "GOOGL"
    elif "alphabet" in company_l and "class c" in company_l:
        t = "GOOG"
    elif t in ("", "DELISTED", "NAN", "N/A", "NULL"):
        slug = re.sub(r"[^A-Z0-9]", "", company.upper())[:8] or "UNK"
        t = slug
    if t in used:
        suffix = re.sub(r"[^A-Z0-9]", "", company.upper())[:4]
        t = f"{t}-{suffix}" if suffix else f"{t}X"
    used.add(t)
    return t


def parse_spy() -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    if not SPY_DIR.exists():
        print(f"skip spy: missing {SPY_DIR}")
        return out

    for path in sorted(SPY_DIR.glob("*.csv")):
        year = int(path.stem)
        used: set[str] = set()
        rows: list[tuple[str, str, float]] = []
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for rec in reader:
                name = (rec.get("Company") or "").strip()
                ticker_raw = (rec.get("Ticker") or "").strip()
                try:
                    weight = float(rec.get("Weight") or 0)
                except ValueError:
                    continue
                if weight <= 0 or not name:
                    continue
                ticker = clean_ticker(name, ticker_raw, used)
                rows.append((ticker, name, weight))
        rows.sort(key=lambda r: r[2], reverse=True)
        out[year] = [
            {"rank": i, "ticker": t, "name": n, "weight": round(w, 3)}
            for i, (t, n, w) in enumerate(rows[:TOP_N], start=1)
        ]
    print(f"spy years: {sorted(out)}")
    return out


def compare_overlap(zenodo: dict, spy: dict) -> None:
    overlap = sorted(set(zenodo) & set(spy))
    if not overlap:
        return
    print("overlap ticker match (top 10):")
    for year in (overlap[0], overlap[len(overlap) // 2], overlap[-1]):
        z = {r["ticker"] for r in zenodo[year][:10]}
        s = {r["ticker"] for r in spy[year][:10]}
        print(f"  {year}: shared {sorted(z & s)} zenodo-only {sorted(z - s)} spy-only {sorted(s - z)}")


def main() -> None:
    zenodo = parse_zenodo()
    spy = parse_spy()
    compare_overlap(zenodo, spy)

    by_year: dict[str, list[dict]] = {}
    sources_by_year: dict[str, str] = {}

    for year in range(START_YEAR, END_YEAR + 1):
        if year in spy:
            by_year[str(year)] = spy[year]
            sources_by_year[str(year)] = "SPY annual holdings (ETF proxy for S&P 500 weights)"
        elif year in zenodo:
            by_year[str(year)] = zenodo[year]
            sources_by_year[str(year)] = "Zenodo S&P 500 component weightings (year-end)"
        elif year == 2026 and "2025" in by_year:
            by_year["2026"] = spy[2025]
            sources_by_year["2026"] = "Carried forward from 2025 SPY holdings (approximate)"

    missing = [y for y in range(START_YEAR, END_YEAR + 1) if str(y) not in by_year]
    if missing:
        raise SystemExit(f"missing years: {missing}")

    payload = {
        "years": list(range(START_YEAR, END_YEAR + 1)),
        "byYear": by_year,
        "sourcesByYear": sources_by_year,
        "meta": {
            "topNStored": TOP_N,
            "approxYears": [2026],
            "sources": [
                "Shvetsov, Nikita. U.S. & Global Stock Indices Constituents & Changes Database. Zenodo. https://doi.org/10.5281/zenodo.7789601 (CC BY 4.0)",
                "SPDR S&P 500 ETF (SPY) annual holdings compiled as Kaggle dataset 'S&P 500 Holdings and Weights (09/30/2000-2024)' plus 2025 snapshot",
            ],
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes), years={payload['years'][0]}-{payload['years'][-1]}")


if __name__ == "__main__":
    main()
