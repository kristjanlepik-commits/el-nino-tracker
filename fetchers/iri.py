"""
Fetch IRI ENSO Quick Look 3-category probabilities.

URL:    https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
Cadence: monthly, around the 19th-20th.

The page renders the 3-category probability table (La Niña, Neutral,
El Niño) directly as HTML at the top of the Quick Look. Header row is
['Season', 'La Niña', 'Neutral', 'El Niño'] and there are 9 data rows
(overlapping 3-month seasons) with trigrams in the first cell, no year.

Issued date is taken from the page's "Published: <Month> <Day>, <Year>"
banner.

Year resolution for each row works the same way as CPC strengths: the
first row's first month equals the issuance month (IRI starts AMJ in
the April issue, MJJ in May, etc.), each subsequent row shifts forward
by one month, and NDJ/DJF cross-year trigrams get the "YYYY-YY" suffix.

Expected payload:
  issued: ISO date from "Published: ..." banner
  three_cat: dict[season_label] -> (la_nina_pct, neutral_pct, el_nino_pct)
"""

import re
from datetime import date

from bs4 import BeautifulSoup

from ._common import FetchResult, http_get, now_iso

URL = "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/"

_MONTH_NAMES = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}

_TRIGRAM_BY_FIRST_MONTH = {
    1: "JFM", 2: "FMA", 3: "MAM", 4: "AMJ", 5: "MJJ", 6: "JJA",
    7: "JAS", 8: "ASO", 9: "SON", 10: "OND", 11: "NDJ", 12: "DJF",
}
_CROSS_YEAR_TRIGRAMS = {"NDJ", "DJF"}

_PUBLISHED_RE = re.compile(
    r"Published:\s*(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{1,2}),\s*(\d{4})"
)


def _season_label(issued_year: int, issued_month: int, row_index: int) -> str:
    """First row's first month = issued month; each row shifts +1 month."""
    first_abs = issued_year * 12 + (issued_month - 1) + row_index
    first_year = first_abs // 12
    first_month = (first_abs % 12) + 1
    trigram = _TRIGRAM_BY_FIRST_MONTH[first_month]
    if trigram in _CROSS_YEAR_TRIGRAMS:
        return f"{trigram} {first_year}-{(first_year + 1) % 100:02d}"
    return f"{trigram} {first_year}"


def _pick_three_cat_table(soup: BeautifulSoup):
    """Return the <table> whose header row is Season / La Niña / Neutral / El Niño."""
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        if (len(header) >= 4
                and header[0].lower().startswith("season")
                and "Niña" in header[1]
                and "Neutral" in header[2]
                and "Niño" in header[3]):
            return t
    return None


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=30)
        soup = BeautifulSoup(r.text, "lxml")

        m = _PUBLISHED_RE.search(soup.get_text(" ", strip=True))
        if not m:
            return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                               error="'Published: <Month> <Day>, <Year>' banner not found")
        month_name, day_str, year_str = m.group(1), m.group(2), m.group(3)
        issued = date(int(year_str), _MONTH_NAMES[month_name], int(day_str)).isoformat()
        issued_year, issued_month = int(year_str), _MONTH_NAMES[month_name]

        table = _pick_three_cat_table(soup)
        if table is None:
            return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                               error="3-category table not found on page")

        rows = table.find_all("tr")[1:]
        three_cat: dict = {}
        for i, row in enumerate(rows):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 4:
                continue
            try:
                la, neu, en = int(cells[1]), int(cells[2]), int(cells[3])
            except ValueError:
                return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                                   error=f"row {i} non-integer probabilities: {cells}")
            label = _season_label(issued_year, issued_month, i)
            three_cat[label] = (la, neu, en)

        if len(three_cat) != 9:
            return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                               error=f"expected 9 seasons, got {len(three_cat)}")

        return FetchResult(
            source="iri",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={"three_cat": three_cat},
        )
    except Exception as e:
        return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
