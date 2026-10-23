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

    # Tier 3 (added 2026-07-20 after the June 22 issuance dropped both the
    # range phrasing and the "peaking at" phrasing, e.g. "El Niño
    # probabilities are assigned at 100% from JJA through SON"): scan
    # sentence by sentence for standalone percentages in an El Niño /
    # probability context and take the maximum. Sentences mentioning the
    # IOD are excluded; the page also carries Indian Ocean Dipole
    # percentages ("~97% positive IOD") that must not be mistaken for
    # ENSO numbers.
    best = None
    for sm in re.finditer(r"[^.!?]*\d{1,3}\s*%[^.!?]*[.!?]", page_text):
        s = sm.group(0)
        sl = s.lower()
        if "iod" in sl or "dipole" in sl:
            continue
        if not any(w in sl for w in ("el niño", "el nino", "probabilit")):
            continue
        for pm in re.finditer(r"(\d{1,3})\s*%", s):
            v = int(pm.group(1))
            if 50 <= v <= 100 and (best is None or v > best):
                best = v
    if best is not None:
        return (0, 100 - best, best)

    return None


_SEASON_CODES = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
                 "JJA", "JAS", "ASO", "SON", "OND", "NDJ")
_SEASON_RE = "(" + "|".join(_SEASON_CODES) + ")"


def _three_cat_by_season(page_text: str, labels: list) -> tuple[dict, dict]:
    """{season label: (la, neu, en)} for the seasons IRI's prose states,
    and {label: basis}. Three sentence shapes, all from the 2026-10-19
    issue: "X% from AAA through BBB", "X% in AAA", and "By AAA, neutral
    ... N%, while the El Niño probability drops to E%". Where only the El
    Niño share is stated, La Niña is taken as 0, the same convention as
    the flat fill. Codes are matched to the issue's nine labels by code,
    which is unique inside one forecast window."""
    by_code = {lab.split()[0]: lab for lab in labels}
    order = [lab.split()[0] for lab in labels]
    out, basis = {}, {}
    for sm in re.finditer(r"[^.!?]*\d{1,3}\s*%[^.!?]*[.!?]", page_text):
        s = " ".join(sm.group(0).split())
        sl = s.lower()
        if "iod" in sl or "dipole" in sl or not re.search(r"\b" + _SEASON_RE + r"\b", s):
            continue
        for m in re.finditer(r"(\d{1,3})\s*%\s*from\s+" + _SEASON_RE + r"(?:\s+\d{4})?\s+(?:through|to|until)\s+"
                             + _SEASON_RE, s):
            v, a, b = int(m.group(1)), m.group(2), m.group(3)
            if a in order and b in order and order.index(a) <= order.index(b):
                for code in order[order.index(a):order.index(b) + 1]:
                    out[by_code[code]] = (0, 100 - v, v)
                    basis[by_code[code]] = f"stated: {m.group(0)}"
        for m in re.finditer(r"(\d{1,3})\s*%\s*in\s+" + _SEASON_RE + r"\b", s):
            v, code = int(m.group(1)), m.group(2)
            if code in by_code and ("el niño" in sl or "el nino" in sl):
                out[by_code[code]] = (0, 100 - v, v)
                basis[by_code[code]] = f"stated: {m.group(0)}"
        bm = re.search(r"\bBy\s+" + _SEASON_RE + r"\b", s)
        neu = re.search(r"neutral[^%]{0,60}?(\d{1,3})\s*%", s, re.IGNORECASE)
        en = re.search(r"El Ni[ñn]o[^%]{0,60}?(\d{1,3})\s*%", s)
        if bm and neu and en and bm.group(1) in by_code:
            n, e = int(neu.group(1)), int(en.group(1))
            if n + e <= 100:
                out[by_code[bm.group(1)]] = (100 - n - e, n, e)
                basis[by_code[bm.group(1)]] = f"stated: neutral {n}%, El Niño {e}%"
    return out, basis


def _extract_qualitative_summary(page_text: str) -> str:
    """Return a short string summarising IRI's framing, for the brief."""
    # Prefer a sentence containing a probability range; fall back to any
    # non-IOD El Niño sentence with a percentage (the June 2026 phrasing).
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
    for m in re.finditer(r"[^.!?]*\d{1,3}\s*%[^.!?]*[.!?]", page_text):
        s = m.group(0).strip()
        sl = s.lower()
        if "iod" in sl or "dipole" in sl:
            continue
        if any(w in sl for w in ("el niño", "el nino", "probabilit")):
            return " ".join(s.split())[:300]
    return ""


def _pick_three_cat_table(soup: BeautifulSoup):
    """Return the table whose header row is Season / La Niña / Neutral /
    El Niño, or None. IRI has oscillated between publishing this table
    (pre-May 2026), removing it (May), and re-adding decorative tables
    (June: a strength-definitions legend that this filter correctly
    skips). Kept as tier 0 so the fetcher self-heals if the real
    probability table returns."""
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


def _parse_three_cat_table(table, issued_year: int, issued_month: int):
    """Parse the 3-category table into {season: (la, neu, en)}, or None."""
    rows = table.find_all("tr")[1:]
    three_cat: dict = {}
    for i, row in enumerate(rows):
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 4:
            continue
        try:
            la, neu, en = int(cells[1]), int(cells[2]), int(cells[3])
        except ValueError:
            return None
        three_cat[_season_label(issued_year, issued_month, i)] = (la, neu, en)
    return three_cat if len(three_cat) == 9 else None


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

        # Tier 0: if the real 3-category probability table is back on the
        # page, use it directly (per-season detail, no flat-fill).
        table = _pick_three_cat_table(soup)
        if table is not None:
            table_cats = _parse_three_cat_table(table, issued_year, issued_month)
            if table_cats:
                return FetchResult(
                    source="iri", ok=True, issued=issued,
                    fetched_at=now_iso(),
                    payload={"three_cat": table_cats,
                             "qualitative_summary":
                                 _extract_qualitative_summary(page_text)},
                )

        triple = _extract_three_cat_from_prose(page_text)
        if triple is None:
            return FetchResult(
                source="iri", ok=False, fetched_at=now_iso(),
                error=("3-category prose not parseable; IRI may have "
                       "changed page format again."),
            )

        # PER SEASON FROM THE PROSE, NOT ONE VALUE COPIED INTO ALL NINE.
        # This filled every season with the prose's highest percentage, on
        # the reasoning that IRI's seasons differed by 1-2 points. True all
        # summer; false from the 2026-10-19 issue, which reads "100% from
        # OND 2026 through MAM 2027, then ease to 92% in AMJ and 60% in MJJ
        # 2027. By JJA 2027, ENSO-neutral ... 51%, while the El Niño
        # probability drops to 37%". The flat fill stored 100 for all three.
        # Now each season gets what the prose states for it; a season it
        # does not state is left out rather than invented. DJF is the one
        # season read downstream (run_brief, snapshot diff), so if the prose
        # does not reach it, it keeps the old flat value and says so.
        three_cat: dict = {}
        basis: dict = {}
        labels = [_season_label(issued_year, issued_month, i) for i in range(9)]
        try:
            three_cat, basis = _three_cat_by_season(page_text, labels)
        except Exception:
            three_cat, basis = {}, {}
        if not three_cat:
            for lab in labels:
                three_cat[lab] = triple
                basis[lab] = "flat fill: prose maximum, no per-season statement parsed"
        djf = next((lab for lab in labels if lab.startswith("DJF ")), None)
        if djf and djf not in three_cat:
            three_cat[djf] = triple
            basis[djf] = "flat fill: prose maximum, DJF not stated"

        qualitative = _extract_qualitative_summary(page_text)

        return FetchResult(
            source="iri",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={
                "three_cat": three_cat,
                "three_cat_basis": basis,
                "qualitative_summary": qualitative,
            },
        )
    except Exception as e:
        return FetchResult(source="iri", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
