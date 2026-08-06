"""Fetch daily station data from Meteo-France via data.gouv.fr.

Open, no key, CSV by department. The current-period file per department is
under a megabyte, and history comes from ECA&D, so a city costs almost nothing.

TWO TRAPS, both hit and both about station identity rather than data:
  - Departments are administrative, not geographic-intuitive. ORLY is in
    department 91 (Essonne), not 75 (Paris) or 94.
  - A city has several stations and the nearest is often not ECA&D's. Lyon
    returns LYON-BRON, LYON TETE D'OR and LYON-ST EXUPERY; only the last
    matches the historical series. Matching loosely joins two different
    thermometers, which is the composition problem this pipeline exists to
    avoid. Match the station name EXACTLY and verify against ECA&D.

Verified: all five cities returned 173/173 days identical to their ECA&D
twins. Lag 2 days.
"""
import csv
import gzip
import io
import json
import subprocess

DATASET = ("https://www.data.gouv.fr/api/1/datasets/"
           "donnees-climatologiques-de-base-quotidiennes/")

# city -> (department, EXACT station name, ECA&D staid)
CITIES = {
    "Marseille":   ("13", "MARIGNANE", 39),
    "Nice":        ("06", "NICE", 757),
    "Montpellier": ("34", "MONTPELLIER-AEROPORT", 2207),
    "Lyon":        ("69", "LYON-ST EXUPERY", 37),
    "Paris":       ("91", "ORLY", 11249),
}


def _resource_url(dep, period="2025-2026"):
    meta = json.loads(subprocess.run(
        ["curl", "-sS", "--max-time", "60", DATASET],
        capture_output=True).stdout)
    for r in meta.get("resources", []):
        t = r.get("title", "")
        if f"_{dep}_" in t and f"periode_{period}_RR-T-Vent" in t:
            return r["url"]
    return None


def fetch(city, year="2026"):
    dep, exact, staid = CITIES[city]
    url = _resource_url(dep)
    if not url:
        raise RuntimeError(f"no current resource for department {dep}")
    blob = subprocess.run(["curl", "-sS", "--max-time", "180", url],
                          capture_output=True).stdout
    text = gzip.decompress(blob).decode("latin-1")
    rows = []
    for r in csv.DictReader(io.StringIO(text), delimiter=";"):
        if (r.get("NOM_USUEL") or "").strip().upper() != exact:
            continue
        d = r.get("AAAAMMJJ", "")
        if not d.startswith(year):
            continue
        tn, tx = r.get("TN", "").strip(), r.get("TX", "").strip()
        rows.append((f"{d[:4]}-{d[4:6]}-{d[6:]}",
                     float(tn) if tn else None,
                     float(tx) if tx else None))
    return sorted(rows)


if __name__ == "__main__":
    for c in CITIES:
        rows = fetch(c)
        trop = sum(1 for _, tn, _ in rows if tn is not None and tn >= 20.0)
        print(f"{c:12s} {len(rows):3d} days, {trop:2d} tropical, to {rows[-1][0]}")
