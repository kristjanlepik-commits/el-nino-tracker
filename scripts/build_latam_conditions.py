"""Emit the Latin America regional conditions payload for the LatAm page.

D-030 SEAM. This channel fetches, owns that the numbers are
methodologically correct, and emits validated JSON. Design renders it.
Nothing here draws anything.

WHAT IT IS. Seven regions of South America, each with the state of its
land surface now and the calendar window in which El Nino's teleconnection
reaches it. The point of the page element is that the windows are
STAGGERED: each region has one season that matters and they do not
coincide, so a map of current conditions alone implies the trouble is
where it is now, which is false.

WHAT IT IS NOT, AND THIS MUST SURVIVE INTO THE RENDER. It is not a fire
forecast or any other outcome forecast. Measured against 27 years of INPE
data, the best available predictor of Amazon dry-season fire explains 18%
of the variance; the other 82% is ignition, which is human. The payload
carries `skill_caveat` for exactly this reason and the renderer should
show it rather than dropping it as boilerplate.

BASELINE CHOICE, stated because it differs from the obvious one. Ranks are
computed against PRIOR years only, 1991-2025, never including the year
being reported. That matches the crops channel's convention
(`current_year_in_baseline: false`) so a percentile means the same thing
across the site. Including the current year would compress every rank
toward the middle by one observation and make cross-channel comparison
quietly wrong.

Run:
    .venv/bin/python scripts/build_latam_conditions.py

Writes data/latam_conditions.json. Reads a cached ERA5 monthly-means pull
(one small CDS request, cached on disk) so re-running is free.
"""

import calendar
import glob
import re
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "latam_conditions.json"
CACHE = Path(tempfile.gettempdir()) / "tls_latam_conditions"
PAYLOAD_VERSION = "0.1"
BASE_FIRST, BASE_LAST = 1991, 2025

# lat_s, lat_n, lon_w, lon_e
# signal_months: when the DRIVER is active. window_months: when the
# consequence can be OBSERVED. Aftereffects' distinction, and it matters:
# Nordeste's drying signal runs from September but a failed rainy season
# cannot be seen until March, and a reader told "Mar-May" will assume
# nothing is happening there until then.
REGIONS = [
    ("pampas",    "Argentine Pampas",          -39.0, -31.0, -65.0, -57.0,
     "wet", [9, 10, 11, 12, 1, 2], [11, 12, 1], [9, 10, 11, 12, 1, 2], True,
     "an agricultural upside for water-limited rainfed systems"),
    ("rio_grande", "Rio Grande do Sul",        -33.8, -27.0, -57.6, -49.7,
     "wet", [9, 10, 11, 12, 1, 2], [11, 12, 1], [9, 10, 11, 12, 1, 2], True,
     "floods. Precedent May 2024: about 181 deaths and USD 15bn, the worst "
     "in 80 years"),
    ("n_amazon",  "N Amazon / Roraima",          0.0,   5.0, -64.0, -58.0,
     "dry", [12, 1, 2, 3, 4], [1, 2, 3], [7, 8, 9, 10, 11, 12, 1, 2, 3, 4], True,
     "fire"),
    ("venezuela", "Venezuela / Guianas",         2.0,  10.0, -75.0, -64.0,
     "dry", [12, 1, 2, 3, 4], [1, 2, 3], [7, 8, 9, 10, 11, 12, 1, 2, 3, 4], True,
     "fire"),
    ("coastal_pe", "Coastal Ecuador / N Peru",   -6.0,   2.0, -81.5, -78.0,
     "wet", [1, 2, 3, 4], [2, 3, 4], [11, 12, 1, 2, 3, 4], True,
     "floods. 1997-98 about USD 2bn and 5.9% of GDP; 1982-83 about USD 2.4bn "
     "and 8.1% of GDP"),
    ("nordeste",  "Nordeste",                  -15.0,  -4.0, -45.0, -35.0,
     "dry", [3, 4, 5], [3, 4, 5], [9, 10, 11, 12, 1, 2, 3, 4, 5], True,
     "drought in its only rainy season"),
    ("s_amazon",  "S Amazon arc",              -12.0,  -5.0, -70.0, -46.0,
     "dry", [], [], [], True,
     "fire, but its window is Jul-Oct 2027 and falls outside this period"),
    ("altiplano", "Altiplano",                 -22.0, -14.0, -70.0, -62.0,
     "dry", [12, 1, 2], [], [12, 1, 2], False,
     "its wet season fails. MEASURED BUT NOT RENDERED: no impact precedent "
     "exists in the damage ledger, and the teleconnection is described in "
     "the literature as weak but significant. Research only."),
]


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "sa.nc"
    if not p.exists():
        import cdsapi
        cdsapi.Client(quiet=True, progress=False).retrieve(
            "reanalysis-era5-single-levels-monthly-means",
            {
                "product_type": ["monthly_averaged_reanalysis"],
                "variable": ["volumetric_soil_water_layer_3",
                             "total_precipitation", "2m_temperature"],
                "year": [str(y) for y in range(BASE_FIRST, 2027)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "time": ["00:00"],
                "data_format": "netcdf",
                "download_format": "unarchived",
                "area": [13, -82, -40, -34],
            },
            str(p),
        )
    return p


def open_vars(p):
    import xarray as xr
    out = {}
    if zipfile.is_zipfile(p):
        d = str(p) + ".x"
        if not os.path.isdir(d):
            with zipfile.ZipFile(p) as z:
                z.extractall(d)
        members = sorted(glob.glob(os.path.join(d, "*.nc")))
    else:
        members = [str(p)]
    for m in members:
        ds = xr.open_dataset(m)
        for v in ds.data_vars:
            out[v] = ds[v]
    return out


def series(da, box):
    s, n, w, e = box
    x = da.sel(latitude=slice(n, s), longitude=slice(w, e)).mean(
        dim=["latitude", "longitude"])
    o = {}
    for y, m, v in zip(x.valid_time.dt.year.values,
                       x.valid_time.dt.month.values, x.values):
        o.setdefault(int(y), {})[int(m)] = float(v)
    return o


def pctl(hist, cur):
    """Percentile of `cur` among PRIOR observations only. Low = dry."""
    return round(100.0 * sum(1 for h in hist if h < cur) / len(hist))


def validate(payload):
    """Refuse to write a payload whose numbers travel without their qualifiers.

    Eight findings crossed three desks on 2026-08-30 and every one was the
    same shape: a number quoted without the thing that qualifies it. A
    mis-dated ratio without its observation date. A box average without the
    extent of the field averaged. A ratio without its base. A rank labelled
    "on record" without its window. A month asserted as though measured.

    No check can tell whether a percentile is CORRECT. This checks only that
    the payload says what its percentiles are percentiles OF, which is the
    precondition for anyone catching the rest. It moves the failure from
    invisible-until-someone-asks to visible at write time.

    Raises rather than warns. A payload that cannot explain itself should
    not reach a renderer.
    """
    faults = []

    b = payload.get("baseline") or {}
    if not b.get("means"):
        faults.append("baseline.means missing: nothing says what a percentile "
                      "is measured against")
    if "current_year_in_baseline" not in b:
        faults.append("baseline.current_year_in_baseline missing: a reader "
                      "cannot tell whether a year inflates its own rank")

    legend = payload.get("instrument_legend") or {}
    numeric = set()
    for r in payload.get("regions", []):
        for k, v in r.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric.add(k)
            elif (isinstance(v, list) and v and
                  all(isinstance(x, (int, float)) and not isinstance(x, bool)
                      for x in v)):
                numeric.add(k)   # list-of-numbers needs a legend entry too
    # Month lists are documented in the `windows` block rather than the
    # instrument legend, because they are calendar identifiers rather than
    # measurements. Named explicitly so the exemption is visible instead of
    # being a hole in the rule.
    documented_in_windows = {"window_months", "peak_months", "signal_months",
                             "season_months"}
    if documented_in_windows & numeric and not (payload.get("windows") or {}).get("means"):
        faults.append("windows.means missing: month lists are exempted from "
                      "the instrument legend on the grounds that windows "
                      "documents them, and it does not")
    for k in sorted(numeric - set(legend) - documented_in_windows):
        faults.append(f"instrument_legend has no entry for numeric field "
                      f"'{k}': it would be rendered with nothing saying what "
                      f"it measures or which direction is bad")

    if any(r.get("series") for r in payload.get("regions", [])):
        sd = payload.get("series_declaration") or {}
        for need in ("means", "percentile_basis", "incomplete_seasons"):
            if not sd.get(need):
                faults.append(f"series present but series_declaration.{need} "
                              f"missing")

    w = payload.get("windows") or {}
    if not w.get("source"):
        faults.append("windows.source missing: the seasonality would read as "
                      "ours rather than cited")
    if not w.get("peak_months_provenance"):
        faults.append("windows.peak_months_provenance missing: nothing "
                      "distinguishes a month taken from a citation from a "
                      "month that is a judgement")

    # PROSE. Aftereffects' finding: every number in their payload sat inside
    # a string, so a schema-level check passed a file carrying six
    # unqualified ratios. A general numbers-in-prose scan is useless (487
    # hits on this file, almost all years and version numbers), but the
    # narrow shape is checkable: a COMPARATIVE (ratio, percentage, ordinal
    # rank, percentile) stated in a sentence that never says what it is
    # measured against. `unit` fields are exempt because naming the bare unit
    # is what they are for.
    comparative = re.compile(
        r"(\b\d+(?:\.\d+)?\s*x\b|\b\d+(?:\.\d+)?\s*%"
        r"|\b\d+(?:st|nd|rd|th)\b|\brank(?:ed)?\s+\d+"
        r"|\b\d+(?:\.\d+)?\w*\s+percentile)", re.I)
    # Qualifier words must NAME A COMPARISON BASE. An earlier version
    # included "year" and "season", which appear in nearly every sentence
    # this channel writes and so suppressed the flag universally: the check
    # caught one bare comparative in four and looked like it worked.
    qualifier = re.compile(
        r"\b(of|against|vs\.?|compared|baseline|mean|median|average|prior|"
        r"n\s*=|out of|relative to|its own|same (?:month|dekad|week|date|calendar))\b",
        re.I)

    def strings(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from strings(v, f"{path}.{k}" if path else k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from strings(v, f"{path}[{i}]")
        elif isinstance(o, str):
            yield path, o

    for path, text in strings(payload):
        if path.endswith(".unit"):
            continue
        # Checked per FIELD, not per sentence. A base very often sits in the
        # sentence before the number ("explains 18% of the variance. The
        # other 82% is ignition"), and a field is the unit that travels when
        # someone quotes this file, so the field is the right scope.
        found = comparative.findall(text)
        if found and not qualifier.search(text):
            faults.append(
                f"{path}: states {found} with nothing in the field saying "
                f"what it is measured against. Quoted out of this file the "
                f"number would travel without its base. Text: "
                f"\"{text.strip()[:90]}\"")

    sc = payload.get("skill_caveat") or {}
    if not sc.get("render_required"):
        faults.append("skill_caveat.render_required is not true: a renderer "
                      "could drop the one field that stops this reading as a "
                      "forecast")

    if faults:
        raise SystemExit(
            "REFUSING TO WRITE: this payload's numbers would travel without "
            "their qualifiers.\n\n  " + "\n  ".join(faults) +
            "\n\nSee validate() for why this raises rather than warns.")
    return len(numeric)


def main():
    V = open_vars(fetch())
    tname = "valid_time"
    last = V["swvl3"][tname].values[-1]
    obs_year = int(str(last)[:4])
    obs_month = int(str(last)[5:7])

    regions = []
    for (key, name, s, n, w, e, sign, window, peak, signal, render,
         hazard) in REGIONS:
        box = (s, n, w, e)
        SM = series(V["swvl3"], box)
        P = series(V["tp"], box)
        T = series(V["t2m"], box)
        days = calendar.monthrange(obs_year, obs_month)[1]

        sm_hist = [SM[y][obs_month] for y in range(BASE_FIRST, BASE_LAST + 1)]
        p_hist = [P[y][obs_month] * 1000 * days
                  for y in range(BASE_FIRST, BASE_LAST + 1)]
        t_clim = np.mean([T[y][obs_month] for y in range(BASE_FIRST, 2021)])

        # Seasonal series: the region's OWN window months, by year, with a
        # percentile against every other year of the same season. Heat asked
        # for this: a page wants "where this season sits in the record", not
        # "where it sits today". Cross-year windows are labelled by the year
        # the season OPENS.
        season_months = window or [7, 8, 9, 10]
        opens_prev_year = season_months[0] > season_months[-1]
        season = {}
        for y in range(BASE_FIRST + 1, obs_year + 1):
            sm_v, p_v, ok = [], [], True
            for m in season_months:
                yy = y if (not opens_prev_year or m >= season_months[0]) else y + 1
                if m not in SM.get(yy, {}) or m not in P.get(yy, {}):
                    ok = False
                    break
                sm_v.append(SM[yy][m])
                p_v.append(P[yy][m] * 1000 * calendar.monthrange(yy, m)[1])
            if ok:
                season[y] = (float(np.mean(sm_v)), float(sum(p_v)))
        season_series = []
        for y in sorted(season):
            others_sm = [v[0] for k, v in season.items() if k != y]
            others_p = [v[1] for k, v in season.items() if k != y]
            label = f"{y}-{str(y+1)[2:]}" if opens_prev_year else str(y)
            season_series.append({
                "season": label,
                "soil": round(season[y][0], 4),
                "rain_mm": round(season[y][1], 1),
                "soil_pctl": pctl(others_sm, season[y][0]),
                "rain_pctl": pctl(others_p, season[y][1]),
            })

        trail = []
        for back in (2, 1, 0):
            m = obs_month - back
            yy = obs_year if m >= 1 else obs_year - 1
            m = m if m >= 1 else m + 12
            h = [SM[y][m] for y in range(BASE_FIRST, BASE_LAST + 1)]
            trail.append(pctl(h, SM[obs_year][m]))

        regions.append({
            "key": key,
            "name": name,
            "box": {"lat_s": s, "lat_n": n, "lon_w": w, "lon_e": e},
            "sign": sign,
            "hazard": hazard,
            "window_months": window,
            "peak_months": peak,
            "signal_months": signal,
            "window_in_period": bool(window),
            "render": render,
            "soil_pctl": pctl(sm_hist, SM[obs_year][obs_month]),
            "rain_pctl": pctl(p_hist, P[obs_year][obs_month] * 1000 * days),
            "temp_anomaly_c": round(float(T[obs_year][obs_month] - t_clim), 2),
            "soil_pctl_trail": trail,
            "season_months": season_months,
            "season_is_cross_year": opens_prev_year,
            "series": season_series,
        })

    payload = {
        "_generated_from": "ERA5 monthly means via CDS, cached; no live fetch at render time",
        "_generator": "scripts/build_latam_conditions.py",
        "payload_version": PAYLOAD_VERSION,
        "observation_month": f"{obs_year}-{obs_month:02d}",
        "max_data_age_days": 75,
        "max_data_age_measured_from": (
            "the end of observation_month. ERA5 monthly means publish about "
            "five weeks after a month closes, so a payload older than this "
            "means the monthly pull has stopped rather than that the world "
            "went quiet."),
        "series_declaration": {
            "means": "each region's series covers ITS OWN window months, not a "
                     "fixed calendar season, because the season that matters "
                     "differs by region. A cross-year window is labelled by the "
                     "year it OPENS, so 2026-27 means Sep 2026 to Feb 2027.",
            "percentile_basis": "leave-one-out: each season is ranked against "
                                "every OTHER season in the series, so a season "
                                "never inflates its own rank.",
            "incomplete_seasons": "a season missing any of its months is "
                                  "omitted entirely rather than part-counted. "
                                  "The current season appears only once every "
                                  "one of its months has been observed.",
            "s_amazon_note": "s_amazon has no window in this period, so its "
                             "series uses Jul-Oct, its actual fire season.",
        },
        "baseline": {
            "basis": f"{BASE_FIRST}-{BASE_LAST}, same calendar month of each year",
            "first": BASE_FIRST,
            "last": BASE_LAST,
            "n": BASE_LAST - BASE_FIRST + 1,
            "current_year_in_baseline": False,
            "means": (
                "every percentile in this file is computed against 35 PRIOR "
                "observations of the same calendar month, never including the "
                "year being reported. Matches the crops channel so a "
                "percentile means the same thing across the site. LOW is dry."),
        },
        "instrument_legend": {
            "soil_pctl": {
                "name": "Soil moisture, 28-100 cm",
                "unit": "percentile", "worse_is": "low",
                "window": "observation_month ONLY, ranked against the same "
                          "calendar month of 1991-2025",
                "not_to_be_confused_with": "series[].soil_pctl, which covers "
                          "the region's whole window season. Heat read the two "
                          "as comparable for the same season and they are not: "
                          "one is a month, one is a six-month season, and they "
                          "can disagree without either being wrong.",
                "summarises": "the water actually in the ground for the "
                              "observation month, which carries seasonal "
                              "memory rather than that month's weather"},
            "rain_pctl": {
                "name": "Rainfall", "unit": "percentile", "worse_is": "low",
                "window": "observation_month ONLY, ranked against the same "
                          "calendar month of 1991-2025",
                "not_to_be_confused_with": "series[].rain_pctl, which totals "
                          "the region's whole window season",
                "summarises": "the observation month alone"},
            "temp_anomaly_c": {
                "name": "Temperature anomaly", "unit": "degrees C",
                "worse_is": "high", "summarises": "against the 1991-2020 mean "
                                                  "for the same month"},
            "signal_months": {
                "name": "Driver active", "unit": "months",
                "worse_is": "n/a",
                "summarises": "when the teleconnection is forcing this region, "
                              "which precedes the observable window"},
            "render": {
                "name": "Show on the page", "unit": "boolean",
                "worse_is": "n/a",
                "summarises": "false means measured and deliberately withheld "
                              "from the reader surface. See the region's hazard "
                              "field for why."},
            "soil_pctl_trail": {
                "name": "Soil moisture, last three months",
                "unit": "percentile, oldest first", "worse_is": "falling",
                "summarises": "direction of travel. A region can sit mid-range "
                              "and be collapsing: Roraima ran 69, 36, 6."},
        },
        "windows": {
            "means": "window_months is when the consequence can be OBSERVED. "
                     "signal_months is when the DRIVER is active, which starts "
                     "earlier. Both are seasonality, not a forecast of magnitude.",
            "why_two": "Aftereffects' distinction and it prevents a real "
                       "misreading. Nordeste's drying signal runs from "
                       "September, but a failed rainy season cannot be "
                       "observed until March, and a reader shown only "
                       "'Mar-May' will assume nothing is happening there "
                       "until March. Its rainfall is already at the 6th "
                       "percentile of 35 prior Julys.",
            "source": "Cai et al. 2020, Nature Reviews Earth and Environment, "
                      "for the precipitation dipole and its seasonality; Chen "
                      "et al. 2017, Nature Climate Change, for the fire lag.",
            "peak_months_provenance": "peaks follow the cited seasonality only. "
                      "coastal_pe briefly carried a Jan-Mar peak taken from a "
                      "damage-ledger assertion that January was the costliest "
                      "month; aftereffects withdrew it on finding their cost "
                      "data is event-level with no monthly breakdown, so the "
                      "peak reverted to Cai's FMA. January stays in the WINDOW "
                      "as a shoulder month, which nothing contradicts.",
            "note": "s_amazon carries an empty window on purpose. Its response "
                    "arrives about 15 months after onset, so its principal "
                    "window is Jul-Oct 2027 and falls outside this period. "
                    "That absence is a finding, not missing data.",
        },
        "skill_caveat": {
            "headline": "This is not a fire forecast and must not be rendered as one.",
            "detail": "Measured against 27 years of INPE Amazon fire counts, "
                      "the best available predictor (NDJ ONI) explains 18% of "
                      "the variance in dry-season fire. The other 82% is "
                      "ignition, which is human: 2025 paired the third-driest "
                      "wet-season recharge on record with the lowest fire year "
                      "on record.",
            "render_required": True,
        },
        "absence_reasons": {
            "window_not_in_period": "the region's exposure window falls outside "
                                    "the nine months this payload covers. Its "
                                    "conditions are still measured and shown.",
            "box_outside_domain": "the region sits outside the ERA5 box this "
                                  "payload requests and carries no values.",
            "render_false": "the region is measured but withheld from the "
                            "reader surface, because no impact precedent "
                            "exists behind it. A row we could not defend if "
                            "asked is worse than a row we do not show.",
        },
        "limits": [
            "Every value is a box average. It cannot see a state, a catchment "
            "or a city, and a regional mean can sit at the 50th percentile "
            "with half of it in drought.",
            "The SESA wet signal was cancelled outright by a strong positive "
            "Southern Annular Mode in 2015-16.",
            "Central Chile's teleconnection has measurably decayed since 2000 "
            "and is excluded from this payload for that reason.",
            "SESA is deliberately split into Rio Grande do Sul and the "
            "Argentine Pampas because the same wet signal is a catastrophe in "
            "one and an upside in the other. Rendering SESA as a single "
            "coloured region is wrong whichever colour it picks.",
        ],
        "regions": regions,
    }

    n_checked = validate(payload)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}  ({len(regions)} regions, "
          f"observation month {payload['observation_month']})")
    print(f"  provenance check passed: {n_checked} numeric fields, all declared")
    for r in regions:
        w = "-" if not r["window_in_period"] else \
            f"{len(r['window_months'])}mo"
        print(f"  {r['name']:26} soil {r['soil_pctl']:>3}  rain {r['rain_pctl']:>3}"
              f"  {r['temp_anomaly_c']:+5.2f}C  trail {r['soil_pctl_trail']}  window {w}")


if __name__ == "__main__":
    main()
