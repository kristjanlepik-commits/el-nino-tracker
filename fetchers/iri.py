"""
Fetch IRI ENSO Quick Look 3-category probabilities.

URL:    https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
Data:   IRI publishes a JSON feed for the Quick Look probabilities.
        The exact JSON URL changes occasionally; check the page source
        for the current data endpoint. Fallback is parsing the PDF
        accompanying the plume image.
Cadence: monthly, ~19th of the month.

Expected payload:
  issued: ISO date of latest IRI release
  three_cat: dict[season_label] -> [pct_la_nina, pct_neutral, pct_el_nino]

Implementation TODO:
  1. fetch JSON if endpoint is stable; else parse PDF with pdfplumber
  2. extract per-season probabilities for AMJ through DJF target year
  3. return FetchResult(source='iri', ok=True, ...)
"""

from ._common import FetchResult, http_get, now_iso

PAGE_URL = "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/"


def fetch() -> FetchResult:
    # TODO: implement; check page source for JSON endpoint first
    return FetchResult(
        source="iri",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; see fetchers/iri.py docstring",
    )
