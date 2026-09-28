"""Does SEAS5 run hot on Nino 3.4 amplitude from a September start?

Asked by the aftereffects desk on 2026-09-28: CFSv2's 2015 hindcast had been
tested (+0.07 against observed), SEAS5 never had, and SEAS5 feeds the ladder.

The test uses the lead we actually read. Every September run SEAS5 has made
is pulled: the 1993-2016 hindcasts (25 members) and the 2023-2025 real-time
forecasts (51 members; system 51 has no real-time run before November 2022). Each member is turned into Nino 3.4 anomalies against
SEAS5's own 1993-2016 September-start climatology, the same subtraction the
fetcher makes, and then into the ladder's basis: 3-month running means, the
peak over the seasons centred November to February that a September run
reaches (OND, NDJ, DJF). Observed values are CPC's ERSSTv5 monthly Nino 3.4
totals, as anomalies against their own 1993-2016 monthly means, on the same
basis. Same years, same windows, same base period on both sides.

Two readings, because they answer different questions:
  - NDJ, signed, all years: the regression slope of observed on forecast
    median is the amplitude ratio. Below 1 means SEAS5 overstates the swing.
  - Peak basis, El Nino years: forecast median minus observed, event by
    event, with the strong events (1997, 2015, 2023) named.

Small n, and read as a sanity check on one input, not a calibration: nothing
here is fed back into the ladder. Writes data/seas5_amplitude_check.json.
"""
import json, os, sys, tempfile
from pathlib import Path
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fetchers import ecmwf_seas5 as E
from fetchers._common import http_get

START = 9
HINDCAST = [str(y) for y in range(1993, 2017)]
# System 51 (SEAS5.1) forecasts start November 2022; earlier Septembers ran
# under system 5, with its own climatology, and are not mixed in here.
REALTIME = [str(y) for y in range(2023, 2026)]
SEASONS = {"OND": (10, 11, 12), "NDJ": (11, 12, 13), "DJF": (12, 13, 14)}  # months from Jan of start year
STRONG = {1997, 2015, 2023}


def model_anomalies(years):
    """{year: array (member, lead 1..6)} of SEAS5 Nino 3.4 anomalies."""
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    try:
        E._retrieve_seas5(years, f"{START:02d}", E.LEADS, tmp)
        ds = xr.open_dataset(tmp)
        box = E._area_mean(ds["sst"])                      # (number, fcrt, forecastMonth)
        clim = E._build_or_load_climatology(START)         # (forecastMonth,)
        anom = box - clim
        out = {}
        for i, t in enumerate(anom["forecast_reference_time"].values):
            y = int(str(t)[:4])
            a = anom.isel(forecast_reference_time=i).transpose("number", "forecastMonth").values
            a = a[~np.isnan(a).all(axis=1)]                # hindcasts carry 25 of 51 member slots
            out[y] = a
        return out
    finally:
        try: os.remove(tmp)
        except OSError: pass


def observed():
    """{(year, month): anomaly} from CPC ERSSTv5 Nino 3.4 totals, 1993-2016 base."""
    txt = http_get("https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii",
                   timeout=60).text
    tot = {}
    for line in txt.splitlines()[1:]:
        p = line.split()
        tot[(int(p[0]), int(p[1]))] = float(p[8])
    base = {m: np.mean([tot[(y, m)] for y in range(1993, 2017)]) for m in range(1, 13)}
    return {k: v - base[k[1]] for k, v in tot.items()}


def season_means(monthly_by_offset, season):
    """Mean over a season; monthly_by_offset maps months-from-Jan-of-start-year (9..14) to values."""
    return sum(monthly_by_offset[m] for m in SEASONS[season]) / 3.0


def main():
    obs = observed()
    fc = {**model_anomalies(HINDCAST), **model_anomalies(REALTIME)}
    rows = []
    for y in sorted(fc):
        a = fc[y]                                          # (member, 6): Sep..Feb
        months = {9 + j: a[:, j] for j in range(a.shape[1])}
        m_ndj = season_means(months, "NDJ")
        m_peak = np.max([season_means(months, s) for s in SEASONS], axis=0)
        def o(m):
            yy, mm = (y, m) if m <= 12 else (y + 1, m - 12)
            return obs.get((yy, mm))
        omon = {m: o(m) for m in range(10, 15)}
        if any(v is None for v in omon.values()):
            continue                                        # season not yet observed
        o_ndj = season_means(omon, "NDJ")
        o_peak = max(season_means(omon, s) for s in SEASONS)
        rows.append({
            "year": y, "members": int(a.shape[0]),
            "source": "hindcast" if y <= 2016 else "real-time forecast",
            "fc_ndj_median": round(float(np.median(m_ndj)), 2),
            "obs_ndj": round(o_ndj, 2),
            "fc_peak_median": round(float(np.median(m_peak)), 2),
            "fc_peak_p10": round(float(np.percentile(m_peak, 10)), 2),
            "fc_peak_p90": round(float(np.percentile(m_peak, 90)), 2),
            "obs_peak": round(o_peak, 2),
            "peak_error": round(float(np.median(m_peak)) - o_peak, 2),
            "pct_members_above_obs_peak": round(100.0 * float(np.mean(m_peak > o_peak)), 0),
        })

    x = np.array([r["fc_ndj_median"] for r in rows]); yv = np.array([r["obs_ndj"] for r in rows])
    slope, intercept = np.polyfit(x, yv, 1)
    ninos = [r for r in rows if r["obs_peak"] >= 0.5]
    strong = [r for r in rows if r["year"] in STRONG]
    summary = {
        "n_years": len(rows),
        "ndj_amplitude_ratio_obs_on_fc": round(float(slope), 3),
        "ndj_intercept": round(float(intercept), 3),
        "ndj_correlation": round(float(np.corrcoef(x, yv)[0, 1]), 3),
        "ndj_mean_error_all_years": round(float(np.mean(x - yv)), 3),
        "el_nino_years": [r["year"] for r in ninos],
        "peak_mean_error_el_nino_years": round(float(np.mean([r["peak_error"] for r in ninos])), 3),
        "peak_error_strong_events": {r["year"]: r["peak_error"] for r in strong},
    }
    out = {"method": __doc__.strip().split("\n\n")[1], "start_month": START,
           "summary": summary, "years": rows}
    (ROOT / "data" / "seas5_amplitude_check.json").write_text(json.dumps(out, indent=1))

    print(f"{'year':<6}{'src':<5}{'fc NDJ':>8}{'obs NDJ':>9}{'fc peak':>9}{'obs peak':>9}{'error':>7}{'% above':>9}")
    for r in rows:
        tag = " *" if r["year"] in STRONG else ""
        print(f"{r['year']:<6}{'hc' if r['source']=='hindcast' else 'rt':<5}{r['fc_ndj_median']:>8.2f}{r['obs_ndj']:>9.2f}"
              f"{r['fc_peak_median']:>9.2f}{r['obs_peak']:>9.2f}{r['peak_error']:>+7.2f}{r['pct_members_above_obs_peak']:>8.0f}%{tag}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
