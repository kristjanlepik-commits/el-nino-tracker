"""
Fetch NOAA CPC ENSO Strength Probabilities table.

URL:    https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php
Cadence: monthly, 2nd Thursday alongside the ENSO Diagnostic Discussion.

The page renders one HTML table with 9 rows (overlapping 3-month seasons)
and 9 RONI strength bin columns. The header text on the page is "Issued
<Month> <Year>" (no day), so we set the issued date to the 2nd Thursday
of that month, matching CPC's regular issuance day.

Bin label normalization (page header to canonical key in sources.py):
  "Index <= -2.0 C"           ->  "<=-2.0"
  "-1.5 C >= Index > -2.0 C"  ->  "-2.0to-1.5"
  "-1.0 C >= Index > -1.5 C"  ->  "-1.5to-1.0"
  "-0.5 C >= Index > -1.0 C"  ->  "-1.0to-0.5"
  "-0.5 C < Index < 0.5 C"    ->  "neutral"
  "0.5 C <= Index < 1.0 C"    ->  "0.5to1.0"
  "1.0 C <= Index < 1.5 C"    ->  "1.0to1.5"
  "1.5 C <= Index < 2.0 C"    ->  "1.5to2.0"
  "Index >= 2.0 C"            ->  ">=2.0"

Season labels are derived from row index + issued month/year. The first
row's central month equals the issued month (CPC publishes the current
month as the first overlapping season). Cross-year trigrams (NDJ, DJF)
get a "YYYY-YY" suffix to match the canonical labels in sources.py.

Expected payload:
  issued: ISO date (2nd Thursday of the issued month)
  table:  dict[season_label] -> dict[bin_label] -> int (percent)
"""

import io
import re
from datetime import date, timedelta

import pandas as pd

from ._common import FetchResult, http_get, now_iso

URL = "https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php"

_MONTH_NAMES = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

# trigram first-month -> trigram letters
_TRIGRAM_BY_FIRST_MONTH = {
    1: "JFM", 2: "FMA", 3: "MAM", 4: "AMJ", 5: "MJJ", 6: "JJA",
    7: "JAS", 8: "ASO", 9: "SON", 10: "OND", 11: "NDJ", 12: "DJF",
}
_CROSS_YEAR_TRIGRAMS = {"NDJ", "DJF"}

_ISSUED_RE = re.compile(
    r"Issued\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{4})"
)


def _second_thursday(year: int, month: int) -> date:
    d = date(year, month, 1)
    # Mon=0 .. Sun=6 ; Thursday=3
    first_thu = d + timedelta(days=(3 - d.weekday()) % 7)
    return first_thu + timedelta(days=7)


def _normalize_bin_header(h: str) -> str:
    """Map a CPC column header to a canonical bin label, or empty string."""
    s = " ".join(h.split())
    # Convert Unicode comparison operators to ASCII
    s = s.replace("≤", "<=").replace("≥", ">=")
    # Strip degree-C variants
    s = s.replace("°C", "").replace("°", "").replace(" C", "")
    s = s.replace(" ", "")
    # s now looks like "Index<=-2.0", "-0.5<Index<0.5", "0.5<=Index<1.0", etc.
    # Closed-tail bins
    if re.fullmatch(r"Index<=-2\.?0?", s):
        return "<=-2.0"
    if re.fullmatch(r"Index>=2\.?0?", s):
        return ">=2.0"
    # Neutral
    if re.fullmatch(r"-0\.5<Index<0\.5", s):
        return "neutral"
    # Negative descending bins: "-1.5>=Index>-2.0" -> "-2.0to-1.5"
    m = re.fullmatch(r"(-?\d+\.\d+)>=Index>(-?\d+\.\d+)", s)
    if m:
        upper, lower = m.group(1), m.group(2)
        return f"{lower}to{upper}"
    # Positive ascending bins: "0.5<=Index<1.0" -> "0.5to1.0"
    m = re.fullmatch(r"(-?\d+\.\d+)<=Index<(-?\d+\.\d+)", s)
    if m:
        lower, upper = m.group(1), m.group(2)
        return f"{lower}to{upper}"
    return ""


_CANONICAL_BINS = {"<=-2.0", "-2.0to-1.5", "-1.5to-1.0", "-1.0to-0.5",
                   "neutral", "0.5to1.0", "1.0to1.5", "1.5to2.0", ">=2.0"}


def _season_label(issued_year: int, issued_month: int, row_index: int) -> str:
    """Derive the canonical season label for the i-th row in the strength table."""
    # central_abs counts months since year 0, month 1
    central_abs = issued_year * 12 + (issued_month - 1) + row_index
    first_abs = central_abs - 1
    first_year = first_abs // 12
    first_month = (first_abs % 12) + 1
    trigram = _TRIGRAM_BY_FIRST_MONTH[first_month]
    if trigram in _CROSS_YEAR_TRIGRAMS:
        return f"{trigram} {first_year}-{(first_year + 1) % 100:02d}"
    return f"{trigram} {first_year}"


def _pick_strength_table(html: str):
    """Return the dataframe whose normalized columns cover all 9 canonical bins."""
    tables = pd.read_html(io.StringIO(html))
    best = None
    best_hits = 0
    for t in tables:
        if "Season" not in [str(c) for c in t.columns]:
            continue
        norm_cols = {_normalize_bin_header(str(c)) for c in t.columns}
        hits = len(norm_cols & _CANONICAL_BINS)
        if hits > best_hits:
            best_hits = hits
            best = t
    if best is None or best_hits < len(_CANONICAL_BINS):
        raise ValueError(
            f"strength table not found; best matched {best_hits}/9 canonical bins"
        )
    return best


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=30)

        m = _ISSUED_RE.search(r.text)
        if not m:
            return FetchResult(source="cpc_strength", ok=False, fetched_at=now_iso(),
                               error="'Issued <Month> <Year>' header not found on page")
        issued_month = _MONTH_NAMES[m.group(1)]
        issued_year = int(m.group(2))
        issued_iso = _second_thursday(issued_year, issued_month).isoformat()

        df = _pick_strength_table(r.text)
        col_map = {col: _normalize_bin_header(str(col)) for col in df.columns
                   if str(col) != "Season"}
        # Build the table dict.
        table: dict[str, dict[str, int]] = {}
        for i, row in df.iterrows():
            label = _season_label(issued_year, issued_month, i)
            bins = {}
            for raw_col, canon in col_map.items():
                if not canon:
                    continue
                bins[canon] = int(row[raw_col])
            if set(bins) != _CANONICAL_BINS:
                return FetchResult(source="cpc_strength", ok=False, fetched_at=now_iso(),
                                   error=f"row {i} bins {set(bins)} != canonical")
            table[label] = bins

        if len(table) != 9:
            return FetchResult(source="cpc_strength", ok=False, fetched_at=now_iso(),
                               error=f"expected 9 seasons, got {len(table)}")

        return FetchResult(
            source="cpc_strength",
            ok=True,
            issued=issued_iso,
            fetched_at=now_iso(),
            payload={"table": table},
        )
    except Exception as e:
        return FetchResult(source="cpc_strength", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
