"""
Fetch NOAA CPC ENSO Strength Probabilities table.

URL:    https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php
Cadence: monthly, 2nd Thursday with the ENSO Diagnostic Discussion.

The page renders an HTML table with one row per 3-month season and
one column per RONI strength bin. pandas.read_html parses it cleanly.

Expected payload:
  issued: ISO date of latest CPC update (parse from page header)
  table:  dict[season_label] -> dict[bin_label] -> int (percent)

Implementation TODO:
  1. fetch via http_get
  2. extract issuance date from the page (typically "Updated: YYYY-MM-DD")
  3. tables = pd.read_html(html); pick the strength table by header signature
  4. normalize column names to match sources.CPC_STRENGTH_RONI bin labels
  5. return FetchResult(source='cpc_strength', ok=True, issued=..., payload={'table': ...})
"""

from ._common import FetchResult, http_get, now_iso

URL = "https://cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths.php"


def fetch() -> FetchResult:
    # TODO: implement HTML parse. For now, return ok=False so the
    # orchestrator falls back to cached/seeded values.
    return FetchResult(
        source="cpc_strength",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; see fetchers/cpc_strength.py docstring",
    )
