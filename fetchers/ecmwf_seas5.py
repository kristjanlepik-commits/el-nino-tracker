"""
Fetch ECMWF SEAS5 ensemble Niño 3.4 forecasts via Copernicus CDS.

Dataset: seasonal-monthly-single-levels
Variable: sea_surface_temperature (K)
Region:   5N-5S, 170W-120W (= 190E-240E in 0-360 convention)
Cadence:  monthly, around the 5th.

Auth:     CDS API key in ~/.cdsapirc.

The fetcher pulls the latest SEAS5 monthly forecast (51 members, leads 1-6,
which is the standard SEAS5 product window), then computes member-level
anomalies against the SEAS5 model climatology. The climatology is the mean
across the 1993-2016 hindcasts (25 members, same start month, same leads)
and is cached on disk because it changes essentially never; only the
forecast pull runs on each weekly invocation.

We report on every lead month available, but the headline metric is the
LONGEST-lead month available (forecastMonth=6), which from an April run
is October. DJF target months are typically not reachable until a June or
later run; when they are, the same code path picks them up automatically.

Expected payload:
  issued: ISO date (first day of the SEAS5 run month)
  system: int (51)
  run_year, run_month: ints
  member_count: int (51 for current SEAS5)
  max_lead_month: int (typically 6)
  max_lead_calendar: str ("YYYY-MM")
  median_anomaly: float (median Niño 3.4 anomaly across members at max lead, deg C)
  members_above: dict[str, int] for thresholds {"1.0", "1.5", "2.0", "2.5"} at max lead
  per_lead: list of dicts (one per lead) with the same shape, for the brief
  summary: short auto-generated text describing the headline result
"""

from __future__ import annotations

import os
import tempfile
from datetime import date

import xarray as xr

from pathlib import Path

from ._common import (CACHE_DIR, FetchResult, now_iso, committed_result,
                      write_committed, _force_live)

# A published SEAS5 run never changes, so a committed copy of the newest run
# is as good as a live pull of it, and needs no CDS. Same pattern as ERA5
# (D-300), for a different reason: on 2026-10-04 CDS's seasonal queue stalled
# for over 40 minutes (ERA5 requests the same morning ran in a minute), and
# the GitHub runner has no cache, so a stall on a Monday would drop SEAS5 to
# seeds after the 40-minute alarm. TLS_ERA5_FORCE_LIVE=1 forces a live pull.
SEAS5_COMMITTED_DIR = Path(__file__).resolve().parent.parent / "data" / "seas5"

DATASET = "seasonal-monthly-single-levels"
SYSTEM = "51"
ORIGIN = "ecmwf"
NINO34_AREA = [5, 190, -5, 240]   # N, W, S, E in 0-360 longitude
HINDCAST_YEARS = [str(y) for y in range(1993, 2017)]  # 1993-2016, 24 years
LEADS = ["1", "2", "3", "4", "5", "6", "7"]
# +3.0 added in v1.8, +3.5 added 2026-07-06: each time the headline gained
# a higher "unprecedented" bucket, SEAS5 must report its member fraction at
# that threshold to keep the multi-model consensus complete (the NMME suite
# reports the same set).
# 4.0 and 4.5 added 2026-09-10. The list stopped at 3.5, so
# _seas5_p_above returned None for the 4.0 bucket and the consensus fell
# through to NMME alone, while every other bucket pooled both models. The
# published record_>4.0 figure was therefore one model wearing a
# consensus label, and 4.0 is now the live question: the September run's
# median peaks at +4.11.
THRESHOLDS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5)


def _cds_client():
    import cdsapi
    return cdsapi.Client(quiet=True, progress=False)


def _retrieve_seas5(years: list[str], month: str, leads: list[str], path: str) -> None:
    _cds_client().retrieve(
        DATASET,
        {
            # data_format, not format. CDS deprecated the latter and now
            # warns that it "is no longer part of the system testing,
            # therefore it is not guaranteed to work". Both ERA5 fetchers
            # were migrated; this one was missed. Verified 2026-09-06 by
            # retrieving the August run with the new key: 51 members, 6
            # lead months, identical shape.
            "data_format": "netcdf",
            "originating_centre": ORIGIN,
            "system": SYSTEM,
            "variable": "sea_surface_temperature",
            "product_type": "monthly_mean",
            "year": years,
            "month": month,
            "leadtime_month": leads,
            "area": NINO34_AREA,
        },
        path,
    )


def _area_mean(da: xr.DataArray) -> xr.DataArray:
    return da.mean(dim=["latitude", "longitude"])


def _climatology_path(start_month: int) -> str:
    return str(CACHE_DIR / f"seas5_clim_M{start_month:02d}_S{SYSTEM}.nc")


def _build_or_load_climatology(start_month: int) -> xr.DataArray:
    """Return (forecastMonth,) area-mean climatological SST in K."""
    path = _climatology_path(start_month)
    if os.path.exists(path):
        return xr.open_dataarray(path)
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    _retrieve_seas5(HINDCAST_YEARS, f"{start_month:02d}", LEADS, tmp)
    ds = xr.open_dataset(tmp)
    # area-mean per (year, member, lead), then mean over years and members
    sst_box_mean = _area_mean(ds["sst"])
    clim = sst_box_mean.mean(dim=["forecast_reference_time", "number"])
    clim = clim.rename("sst_clim")
    clim.to_netcdf(path)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return xr.open_dataarray(path)


def _summarize_lead(per_lead: list[dict]) -> str:
    # The PEAK month leads, not the last one. This summary used to open on
    # the longest lead, and by September that is the declining tail: the
    # 09-01 run's "+3.71" was February, while its December median was
    # +4.11. The last-lead figure was being quoted as SEAS5's forecast for
    # the event, 0.4 C under the model's own peak.
    peak = max(per_lead, key=lambda r: r["median"])
    last = per_lead[-1]
    pct_above_2 = round(100 * peak["members_above"]["2.0"] / peak["member_count"])
    pct_above_25 = round(100 * peak["members_above"]["2.5"] / peak["member_count"])
    tail = ("" if last is peak else
            f" Last lead {last['calendar']}: median {last['median']:+.2f} deg C.")
    return (
        f"{peak['member_count']}-member SEAS5 ensemble, peak month "
        f"{peak['calendar']}: median Niño 3.4 anomaly "
        f"{peak['median']:+.2f} deg C (single month); "
        f"{peak['members_above']['1.5']}/{peak['member_count']} members above "
        f"+1.5 (~{pct_above_2}% above +2.0, ~{pct_above_25}% above +2.5).{tail}"
    )


def _calendar_for_lead(run_year: int, run_month: int, lead: int) -> str:
    """The calendar month a CDS leadtime_month refers to.

    leadtime_month 1 IS THE START MONTH: the 1 September run's lead 1 is
    September, lead 6 February. This added `lead` rather than `lead - 1`
    from April to 2026-09-28, so every SEAS5 month we printed or matched
    was one month late. The anomalies were right throughout, because the
    forecast and its hindcast climatology are indexed by the same lead;
    only the labels were wrong. It mattered once probs.py began picking
    the lead by its label (2026-09-10): the NDJ read, meant to be
    December, took November, and 09-28's >+4.0 rung published 37% where
    December gives 41%.

    Checked against the data rather than the documentation: SEAS5's own
    hindcast climatology for each start month (April to September) was
    correlated with CPC's observed Nino 3.4 seasonal cycle for the same
    years, 1993-2016, under both readings. Lead 1 = start month fits for
    every start month (September run: r = 0.88, against 0.02 shifted).
    """
    abs_month = run_year * 12 + (run_month - 1) + (lead - 1)
    y = abs_month // 12
    m = (abs_month % 12) + 1
    return f"{y}-{m:02d}"


# ECMWF's run reaches CDS around the 5th: in every issue this year the
# current month's run was there from the 6th (07-06, 09-07) and absent before
# it (06-01, 08-03). Before that day the request is not refused, it QUEUES:
# on 2026-10-04 two requests for the unpublished October run sat "accepted"
# at CDS for 25 minutes without starting. The fetch has a 40-minute alarm
# covering both attempts, and the runner has no cache, so on a Monday early
# in the month the September fallback would never get its turn and SEAS5
# would drop to seeds. So before this day, do not ask for a run that cannot
# exist yet.
FIRST_DAY_CURRENT_RUN = 6


def _latest_run(now_year: int, now_month: int,
                now_day: int = 31) -> tuple[int, int, str]:
    """The newest SEAS5 run CDS can serve: this month's from the 6th, last
    month's before it, falling back one month on failure either way."""
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False).name
    reasons = []
    offsets = (0, -1) if now_day >= FIRST_DAY_CURRENT_RUN else (-1, -2)
    if now_day < FIRST_DAY_CURRENT_RUN:
        print(f"  [seas5] day {now_day} < {FIRST_DAY_CURRENT_RUN}: this month's "
              f"run is not on CDS yet; asking for last month's directly.")
    for offset in offsets:
        abs_m = now_year * 12 + (now_month - 1) + offset
        y, m = abs_m // 12, (abs_m % 12) + 1
        try:
            _retrieve_seas5([str(y)], f"{m:02d}", LEADS, tmp)
            if reasons:
                # Falling back a month is normal early in the month, before
                # ECMWF's run reaches CDS. It is NOT normal in the second
                # half. Say so where a reader of the logs can see it: the
                # bare `continue` this replaces meant a brief could carry a
                # month-old forecast with nothing recording that it had,
                # or why. A CDS auth failure and an unpublished run looked
                # identical from the outside.
                print(f"  [seas5] {now_year}-{now_month:02d} run unavailable, "
                      f"using {y}-{m:02d}. Reason: {reasons[-1][:200]}")
            return y, m, tmp
        except Exception as exc:
            reasons.append(f"{type(exc).__name__}: {exc}")
            continue
    raise RuntimeError(
        "could not retrieve SEAS5 forecast for current or previous month; "
        + " | ".join(reasons))


def _newest_servable_run(today: date) -> tuple[int, int]:
    """The run CDS can serve today under the FIRST_DAY_CURRENT_RUN rule."""
    off = 0 if today.day >= FIRST_DAY_CURRENT_RUN else -1
    abs_m = today.year * 12 + (today.month - 1) + off
    return abs_m // 12, abs_m % 12 + 1


def fetch() -> FetchResult:
    today = date.today()
    if not _force_live():
        y, m = _newest_servable_run(today)
        c = committed_result("ecmwf_seas5", max_age_days=70, today=today,
                             directory=SEAS5_COMMITTED_DIR)
        # Only when the committed run IS the newest one CDS could give us.
        # From the 6th the committed copy is last month's and this falls
        # through to a live pull, exactly as before.
        if c is not None and c.issued == date(y, m, 1).isoformat():
            return c
    try:
        run_year, run_month, fc_path = _latest_run(today.year, today.month, today.day)

        ds = xr.open_dataset(fc_path)
        fc_box = _area_mean(ds["sst"])  # (number, fcrt, forecastMonth)

        clim = _build_or_load_climatology(run_month)  # (forecastMonth,)

        anom = (fc_box - clim).squeeze("forecast_reference_time", drop=True)
        # anom dims: (number, forecastMonth)

        per_lead = []
        for fm in anom.coords["forecastMonth"].values.tolist():
            arr = anom.sel(forecastMonth=fm).values  # (member,)
            members_above = {f"{t:.1f}": int((arr > t).sum()) for t in THRESHOLDS}
            per_lead.append({
                "lead": int(fm),
                "calendar": _calendar_for_lead(run_year, run_month, int(fm)),
                "member_count": int(arr.size),
                "median": float(_safe_median(arr)),
                "p5": float(_pctl(arr, 5)),
                "p25": float(_pctl(arr, 25)),
                "p75": float(_pctl(arr, 75)),
                "p95": float(_pctl(arr, 95)),
                "members_above": members_above,
                # Per-member values, so probs.py can put SEAS5 on the same
                # ONI basis as NMME (3-month mean, peak over the window)
                # instead of one month. 1.11 named this as the correction
                # still owed; it needed exactly these. 51 x 6 floats.
                "members": [round(float(x), 3) for x in arr.tolist()],
            })

        try:
            os.remove(fc_path)
        except OSError:
            pass

        headline = per_lead[-1]
        payload = {
            "system": int(SYSTEM),
            "run_year": run_year,
            "run_month": run_month,
            "member_count": headline["member_count"],
            "max_lead_month": headline["lead"],
            "max_lead_calendar": headline["calendar"],
            "median_anomaly": headline["median"],
            "members_above": headline["members_above"],
            "per_lead": per_lead,
            "summary": _summarize_lead(per_lead),
        }
        issued = date(run_year, run_month, 1).isoformat()
        result = FetchResult(
            source="ecmwf_seas5",
            ok=True,
            issued=issued,
            fetched_at=now_iso(),
            payload=payload,
        )
        try:
            # Written wherever this runs; persists only where someone
            # commits it (locally). On the runner it is discarded.
            write_committed("ecmwf_seas5", result, directory=SEAS5_COMMITTED_DIR)
        except Exception:
            pass
        return result
    except Exception as e:
        return FetchResult(source="ecmwf_seas5", ok=False, fetched_at=now_iso(),
                           error=f"{type(e).__name__}: {e}")


def _safe_median(arr) -> float:
    import numpy as np
    return float(np.median(arr))


def _pctl(arr, q: float) -> float:
    import numpy as np
    return float(np.percentile(arr, q))
