"""
Fetch BoM ENSO summary headline and lead text.

URL:    https://www.bom.gov.au/climate/enso/
Cadence: roughly fortnightly.
Data:   The page wraps the latest summary in <div class="wrapup">. Inside,
        a <time datetime="YYYY-MM-DD"> carries the issuance date, an <h2>
        carries the qualitative status headline (e.g., "Increased chance
        of El Niño later in 2026"), and the body is a <ul> of <li> bullets.

        BoM dropped the discrete Watch/Alert pill some time before mid-2026.
        We use the H2 as alert_status (same semantic role: a one-line
        categorical state) and pick the first <li> that mentions ENSO or
        Niño or Niña as the summary.

Expected payload:
  issued: ISO date from <time datetime>
  alert_status: text of the H2 inside div.wrapup
  summary: first ENSO-relevant <li> body inside div.wrapup
"""

import re

from bs4 import BeautifulSoup

from ._common import FetchResult, http_get, now_iso

URL = "https://www.bom.gov.au/climate/enso/"

_ENSO_RE = re.compile(r"(ENSO|Niño|Niña|Nino|Nina)", re.IGNORECASE)


def fetch() -> FetchResult:
    try:
        r = http_get(URL, timeout=30)
        soup = BeautifulSoup(r.text, "lxml")
        wrapup = soup.find("div", class_="wrapup")
        if wrapup is None:
            return FetchResult(source="bom", ok=False, fetched_at=now_iso(),
                               error="div.wrapup not found; BoM page layout may have changed")

        time_el = wrapup.find("time")
        if time_el is None or not time_el.get("datetime"):
            return FetchResult(source="bom", ok=False, fetched_at=now_iso(),
                               error="<time datetime=...> not found inside div.wrapup")
        issued = time_el["datetime"]

        h2 = wrapup.find("h2")
        if h2 is None:
            return FetchResult(source="bom", ok=False, fetched_at=now_iso(),
                               error="<h2> headline not found inside div.wrapup")
        alert_status = " ".join(h2.get_text(strip=True).split())

        summary = None
        for li in wrapup.find_all("li"):
            text = " ".join(li.get_text(strip=True).split())
            if _ENSO_RE.search(text):
                summary = text
                break
        if summary is None:
            return FetchResult(source="bom", ok=False, fetched_at=now_iso(),
                               error="no ENSO-relevant <li> found inside div.wrapup")

        return FetchResult(
            source="bom",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload={"alert_status": alert_status, "summary": summary},
        )
    except Exception as e:
        return FetchResult(source="bom", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")
