"""
Fetch IRI ENSO Quick Look 3-category probabilities.

URL:    https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
Cadence: monthly, around the 19th-20th.

History: until ~April 2026 IRI rendered the 3-category probability
table (La Niña / Neutral / El Niño) directly as HTML. Around the
May 19, 2026 issuance the page was reorganized: the HTML table was
removed and the same data now appears only as embedded PNG images
(figure1.png and figure3.png). The text of the page, however, still
states the headline probability range in prose.

This fetcher parses the prose to recover the three-category split.
The trade-off vs the old table parse:

- We retain the headline probability (El Niño / Neutral / La Niña
  split) and the issued date, which is all the brief actually uses.
- We lose the per-season variation across the 9 rows. IRI's own
  prose typically describes the forecast as "consistently maintained
  within a remarkably high and narrow X-Y% range", so the
  per-season variation is small (1-2 percentage points) by IRI's
  own framing. We populate all 9 season labels with the same
  (la_nina, neutral, el_nino) tuple, computed from the upper bound
  of the parsed range.

The parser walks the page text looking for:
  1. A range like "97-98%" near words like "range", "narrow",
     "El Niño", or "probabilities". The upper bound is used as
     the El Niño percent for all 9 seasons.
  2. If no range matches, a single peak like "peaking at 98%" or
     "98% probability". Used directly as the El Niño percent.

Neutral is computed as 100 - El Niño. La Niña is set to 0 (IRI's
forecasts at the moderate-to-super lead almost always show 0% La
Niña; any nonzero La Niña would need a separate parse).

Year resolution for each row label works the same way as CPC
strengths: the first row's first month equals the issuance month
(May issuance starts MJJ), each subsequent row shifts forward by
one month, NDJ/DJF cross-year trigrams get the "YYYY-YY" suffix.

Expected payload:
  issued:              ISO date from "Published: ..." banner
  three_cat:           dict[season] -> (la_pct, neu_pct, en_pct)
                       (all 9 seasons populated with same tuple)
  qualitative_summary: short string capturing IRI's framing
"""

from __future__ import annotations

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

# Probability range like "97-98%", "97 - 98 %", "97 to 98 %", including
# Unicode en-dash and em-dash. Bounds checked against [50, 100] later.
_RANGE_RE = re.compile(
    r"(\d{1,3})\s*(?:[\-–—]|to)\s*(\d{1,3})\s*%",
    re.IGNORECASE,
)

# Single-value peak like "peaking at 98%" or "reaching 98 %".
_PEAK_RE = re.compile(
    r"(?:peak(?:s|ing)?|reach(?:es|ing)?)\s+(?:at\s+)?(\d{1,3})\s*%",
    re.IGNORECASE,
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


def _extract_three_cat_from_prose(page_text: str) -> tuple[int, int, int] | None:
    """Return (la_nina, neutral, el_nino) from IRI page narrative, or None.

    Prefers a probability range with relevant context ("range", "narrow",
    "El Niño", "probabilities") and uses the upper bound. Falls back to a
    single peak value. Both bounds are sanity-checked against [50, 100]
    (anything outside that is almost certainly not the ENSO category
    probability we are looking for).
    """
    context_words = ("range", "narrow", "el niño", "el nino",
                     "probabilit", "outlook", "forecast")

    candidates = []
    for m in _RANGE_RE.finditer(page_text):
        lo, hi = int(m.group(1)), int(m.group(2))
        if not (50 <= lo <= 100 and 50 <= hi <= 100 and lo <= hi):
            continue
        ctx_lo = max(0, m.start() - 80)
        ctx_hi = min(len(page_text), m.end() + 80)
        ctx = page_text[ctx_lo:ctx_hi].lower()
        if any(w in ctx for w in context_words):
            candidates.append((m.start(), lo, hi))

    if candidates:
        # Use the first (earliest in document) qualifying range, which is
        # typically the headline statement.
        candidates.sort(key=lambda c: c[0])
        _, _, hi = candidates[0]
        el_nino = hi
        return (0, 100 - el_nino, el_nino)

    for m in _PEAK_RE.finditer(page_text):
        v = int(m.group(1))
        if 50 <= v <= 100:
            return (0, 100 - v, v)

    return None


def _extract_qualitative_summary(page_text: str) -> str:
    """Return a short string summarising IRI's framing, for the brief."""
    # Look for a sentence containing a probability range
    sent_re = re.compile(
        r"[^.!?]*\b\d{1,3}\s*(?:[\-–—]|to)\s*\d{1,3}\s*%[^.!?]*[.!?]",
        re.IGNORECASE,
    )
    for m in sent_re.finditer(page_text):
        s = m.group(0).strip()
        if any(w in s.lower() for w in ("range", "narrow", "el ni",
                                         "probabilit", "outlook")):
            # Trim and collapse whitespace
            return " ".join(s.split())[:300]
    return ""


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=30)
        soup = BeautifulSoup(r.text, "lxml")
        page_text = soup.get_text(" ", strip=True)

        m = _PUBLISHED_RE.search(page_text)
        if not m:
            return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                               error="'Published: <Month> <Day>, <Year>' banner not found")
        month_name, day_str, year_str = m.group(1), m.group(2), m.group(3)
        issued = date(int(year_str), _MONTH_NAMES[month_name], int(day_str)).isoformat()
        issued_year, issued_month = int(year_str), _MONTH_NAMES[month_name]

        triple = _extract_three_cat_from_prose(page_text)
        if triple is None:
            return FetchResult(
                source="iri", ok=False, fetched_at=now_iso(),
                error=("3-category prose not parseable; IRI may have "
                       "changed page format again."),
            )

        # Populate all 9 overlapping seasons with the same tuple. IRI's
        # prose describes a "narrow range" across the forecast horizon,
        # so per-season variation is within ~1-2 ppt and is not worth
        # attempting to recover from prose alone.
        three_cat: dict = {}
        for i in range(9):
            three_cat[_season_label(issued_year, issued_month, i)] = triple

        qualitative = _extract_qualitative_summary(page_text)

        return FetchResult(
            source="iri",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={
                "three_cat": three_cat,
                "qualitative_summary": qualitative,
            },
        )
    except Exception as e:
        return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
