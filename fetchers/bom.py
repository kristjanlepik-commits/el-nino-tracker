"""
Fetch BoM ENSO Outlook alert status and short summary.

URL:    https://www.bom.gov.au/climate/enso/
Cadence: fortnightly.
Data:   HTML page with alert level (e.g., "Watch", "Alert") in a known
        DOM location. Plain text summary in the lead paragraph.

Expected payload:
  issued: ISO date stamped on page ("Issued on:")
  alert_status: str
  summary: str (first paragraph of the bulletin)

Implementation TODO:
  1. fetch and parse with bs4
  2. extract the alert level pill or heading
  3. extract issuance date and summary
  4. return FetchResult(source='bom', ok=True, ...)
"""

from ._common import FetchResult, http_get, now_iso

URL = "https://www.bom.gov.au/climate/enso/"


def fetch() -> FetchResult:
    # TODO: implement bs4 parse
    return FetchResult(
        source="bom",
        ok=False,
        fetched_at=now_iso(),
        error="not implemented; see fetchers/bom.py docstring",
    )
