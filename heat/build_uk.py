"""Assemble the UK cities from MIDAS Open plus the Met Office's 2026 file.

GENERALISED FROM build_london.py, which handled one station and is now the
special case rather than the pattern. Every UK city has the same shape:

    history        MIDAS Open, annual files, Open Government Licence
    current year   Met Office National Meteorological Library and Archive,
                   supplied on request, Crown Copyright, re-use with
                   acknowledgement

MIDAS publishes in arrears, so no UK city can get its current season from the
archive. London proved the pattern and Rebecca at the NMLA now serves the
other three from one request.

STATION IDENTITY WAS VERIFIED BEFORE ANY OF THIS WAS BUILT, and that order
matters. Each SYNOP station was matched to its MIDAS record by coordinate and
then validated day by day against summer 2025:

    Nottingham Watnall  53.006,-1.251   Tmin 09Z 100% within 0.5 C
    Belfast Aldergrove  54.664,-6.225   Tmax 21Z 100% within 0.5 C
    Aberdeen Dyce       57.205,-2.205   Tmin 09Z 100% within 0.5 C

The Met Office workbook then states its own coordinates, which match all
three to four decimals. So three independent sources agree on which
thermometer each city is, which is what "verified" has to mean here after
Murcia and after Tallinn.

THE HOURS DIFFER PER STATION AND THAT IS THE POINT. Belfast reports its
maximum at 21Z where Nottingham and Aberdeen report at 18Z. Assuming a single
UK convention would have put Belfast quietly out. This file does not depend on
the hours because it reads daily extremes directly, but the check that found
it is why the identities are trustworthy.
"""
from __future__ import annotations

import concurrent.futures
import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from safe_write import write_series

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "heat" / ".cache" / "src"
OFFICIAL = ROOT / "heat" / "data" / "official"
CEDA = ("https://dap.ceda.ac.uk/badc/ukmo-midas-open/data/"
        "uk-daily-temperature-obs/dataset-version-202607")
TOKEN = Path.home() / ".ceda_token"

# WMO blocks for the bulletin extension. NOT TRUSTED ON THE STRENGTH OF THE
# NUMBER: each is validated against the Met Office workbook where the two
# overlap, and the extension is dropped if they disagree. That is what proves
# the block is this station rather than another with a similar name, which is
# the check that would have caught Murcia.
WMO = {"Nottingham": "03354", "Belfast": "03917", "Aberdeen": "03091"}
OGIMET = "https://www.ogimet.com/cgi-bin/getsynop"

# county path, MIDAS dir, workbook sheet, out file
STATIONS = {
    "Nottingham": ("nottinghamshire", "00556_nottingham-watnall",
                   "NOTTINGHAM_WATNALL_DAILY", "nottingham.json"),
    "Belfast":    ("antrim", "01450_aldergrove",
                   "ALDERGROVE_DAILY", "belfast.json"),
    "Aberdeen":   ("aberdeenshire", "00161_dyce",
                   "DYCE_DAILY", "aberdeen.json"),
}
WORKBOOK = OFFICIAL / "Aldergrove_Dyce_Nottingham_Jan_2026-Pres.xlsx"


def _token():
    if not TOKEN.exists():
        raise SystemExit(
            "no CEDA token at ~/.ceda_token. MIDAS needs one and it expires, "
            "so this fails loudly rather than building a city on a short "
            "history it silently could not download.")
    return TOKEN.read_text().strip()


def _unauthenticated(body):
    """Is this body an auth failure wearing a content type?

    THE STATUS CODE IS A PROPERTY OF YOUR CURL FLAGS, NOT OF THE SERVER, and
    that is the part that took two chats to see. Fetching an expired-token
    CEDA .csv gives:

        without -L    HTTP 302, 15 bytes, "Unauthenticated"
        with    -L    HTTP 200, 8015 bytes, <title>Login

    Same request, same server, same expired token. Floods measured the second
    and I had documented the first, and each of us had a rule the other's
    measurement broke: "look for a 302" and "look for a short body" both pass
    a full-sized login page returned as 200.

    So neither status nor size can answer this. Only content can. Floods also
    found the trap underneath it: diffing an authenticated fetch against an
    unauthenticated one showed a difference, which reads as proof the token
    works. Both were login pages differing at a CSRF nonce. A diff between two
    failures looks exactly like a difference between success and failure.
    """
    head = body[:4000].lower()
    return ("unauthenticated" in head
            or "<title>login" in head
            or "<html" in head)


def _get(url, tok):
    body = subprocess.run(
        ["curl", "-sS", "--max-time", "90", "-H", f"Authorization: Bearer {tok}",
         url], capture_output=True).stdout.decode("latin-1", "replace")
    if _unauthenticated(body):
        raise SystemExit(
            f"  CEDA returned an auth failure, not data, for {url}. The token "
            f"at ~/.ceda_token is expired or wrong. Nothing fetched and "
            f"nothing written; renew it and re-run.")
    return body


FROZEN_HISTORY = ROOT / "heat" / "data" / "histories"


def _frozen(city):
    """The station's MIDAS history, committed rather than refetched.

    MIDAS Open ends in 2025 and will not change; the 2026 season comes from
    the Met Office workbook. So the only reason these cities refetched ~300
    annual files every week is that the only copy lived in a gitignored
    cache, and that cost two chats a day in five: the CEDA token lives 72
    hours and expired twice, and each time these three could not rebuild.

    Four committed files at 620 KB remove the credential from the weekly
    path. CEDA is now needed to ADD a city or repair a history, which is
    genuinely episodic, and these cities become buildable on a machine that
    is not this laptop for the first time.
    """
    import gzip
    f = FROZEN_HISTORY / f"{city.lower()}_midas.json.gz"
    if not f.exists():
        return None
    with gzip.open(f, "rt") as fh:
        return {d: (mn, mx) for d, mn, mx in json.load(fh)}


def midas_years(county, sdir, tok):
    """Every annual file for one station, fetched in parallel.

    Reads the directory listing rather than constructing filenames: the
    naming carries the dataset version and the county, and guessing it is
    how a silent empty download happens.
    """
    listing = _get(f"{CEDA}/{county}/{sdir}/qc-version-1/", tok)
    import re
    files = re.findall(r'href="([^"]*_qcv-1_\d{4}\.csv)"', listing)
    if not files:
        raise SystemExit(f"{sdir}: no annual files listed. Token expired?")

    def one(f):
        return _get(f"{CEDA}/{county}/{sdir}/qc-version-1/{f}", tok)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        texts = list(ex.map(one, files))

    out = {}
    for txt in texts:
        if "\ndata\n" not in txt:
            continue
        for r in csv.DictReader(io.StringIO(txt.split("\ndata\n", 1)[1])):
            t = (r.get("ob_end_time") or "").strip()
            if len(t) < 13 or (r.get("ob_hour_count") or "").strip() != "12":
                continue
            d, hh = t[:10], t[11:13]

            def f(k):
                v = (r.get(k) or "").strip()
                try:
                    return float(v)
                except ValueError:
                    return None
            mn, mx = out.get(d, (None, None))
            if hh == "09" and f("min_air_temp") is not None:
                mn = f("min_air_temp")
            if hh == "21" and f("max_air_temp") is not None:
                mx = f("max_air_temp")
            out[d] = (mn, mx)
    return out, len(files)


def official(sheet):
    """The Met Office's own daily extremes for 2026, from Rebecca's workbook."""
    if not WORKBOOK.exists():
        return {}
    import datetime as _dt
    import openpyxl
    ws = openpyxl.load_workbook(WORKBOOK, data_only=True)[sheet]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and r[0] == "Date and time")
    out = {}
    for r in rows[hdr + 1:]:
        if not r or r[0] in (None, ""):
            continue
        d = r[0]
        if isinstance(d, _dt.datetime):
            key = d.strftime("%Y-%m-%d")
        else:
            s = str(d).strip().split()[-1]
            try:
                dd, mm, yy = s.split("/")
            except ValueError:
                continue
            key = f"{yy}-{mm}-{dd}"
        try:
            out[key] = (float(r[2]), float(r[1]))
        except (TypeError, ValueError):
            continue
    return out


def synop_raw(block, begin, end):
    raw = subprocess.run(
        ["curl", "-sS", "--max-time", "200",
         f"{OGIMET}?block={block}&begin={begin}&end={end}"],
        capture_output=True).stdout.decode("utf-8", "replace")
    return raw


def series_at(raw, hn, hx):
    sys.path.insert(0, str(ROOT / "heat"))
    import synop
    out = {}
    for d, h, tx, tn in synop.parse_ogimet(raw):
        mn, mx = out.get(d, (None, None))
        if h == hn and tn is not None:
            mn = tn
        if h == hx and tx is not None:
            mx = tx
        out[d] = (mn, mx)
    return {d: v for d, v in out.items()
            if v[0] is not None and v[1] is not None}


def fit_hours(raw, official):
    """FIT the reporting hours against the official series, do not guess them.

    UK stations bulletin extremes at 06, 09, 18 AND 21, four windows over the
    same day, so no property of the bulletins alone says which pair
    reproduces the Met Office's climatological day. Detecting by frequency
    picks the chattiest hour; detecting by value picks the widest window.
    Both are guesses, and they gave three different answers for four stations
    that share a convention: 09/18, 09/18, 09/21, 06/18.

    But we HOLD the answer. The workbook overlaps these bulletins by about a
    hundred days, so the right pair is simply the one that reproduces it.
    This tries every pair and returns the best with its error, and the caller
    still refuses anything outside tolerance. Fitting against ground truth
    beats inferring from the data's shape whenever the ground truth exists.
    """
    hours = ("06", "09", "12", "18", "21")
    best = None
    for hn in hours:
        for hx in hours:
            cand = series_at(raw, hn, hx)
            common = [k for k in cand if k in official]
            if len(common) < 20:
                continue
            dx = sorted(abs(cand[k][1] - official[k][1]) for k in common)
            dn = sorted(abs(cand[k][0] - official[k][0]) for k in common)
            # THE 90TH PERCENTILE, NOT THE WORST DAY. A single bad bulletin
            # was rejecting stations that otherwise reproduce the official
            # series exactly: Nottingham and Belfast both sit at median 0.0
            # and p90 0.0, which is the same thermometer, and were failing on
            # one 3 C outlier in a hundred days. A worst-day test cannot tell
            # "a different station" from "one garbled report".
            err = max(dx[int(.9 * (len(dx) - 1))], dn[int(.9 * (len(dn) - 1))])
            if best is None or err < best[0]:
                best = (err, hn, hx, len(common))
    return best


def extend(city, official):
    """Carry the season past the workbook's last day, if the two agree.

    THE WORKBOOK IS SENT BY HAND. It reached 10 August while these stations
    kept reporting, so three pages sat four days short during the days people
    were looking, and the only remedy on offer was to ask for a new file.
    London solved this on the 17th; this is the same mechanism for the other
    three.

    LEGAL ONLY BECAUSE THE TWO AGREE, re-tested on every build rather than
    remembered. If the bulletins ever diverge from the official series the
    extension is dropped and the page stops at the workbook, because a
    disagreement means one of them is wrong and we would not know which.
    """
    if not official or city not in WMO:
        return {}, {"agree": None, "synop_days": [],
                    "note": "no workbook or no WMO block for this station"}
    last = max(official)
    y = int(last[:4])
    raw = synop_raw(WMO[city], f"{y}05010000", f"{y}12312359")
    fit = fit_hours(raw, official)
    if fit is None:
        return {}, {"agree": False, "synop_days": [],
                    "note": "no hour pair overlapped the workbook enough to fit"}
    err, hn, hx, n = fit
    tail = series_at(raw, hn, hx)
    # p90 within 0.5 C on BOTH extremes. Nottingham and Belfast pass at 0.0
    # and 0.1; Aberdeen fails at 0.9, agreeing on only 81% of days against
    # their 95%, so it keeps the workbook and stays four days short. That is
    # the right way round: these counts feed thresholds, and a 0.9 C error
    # moves days across one.
    agree = err <= 0.5
    added = sorted(k for k in tail if k > last) if agree else []
    prov = {
        "official_to": last,
        "synop_days": added,
        "overlap_days": n,
        "overlap_worst_c": round(err, 1),
        "hours": {"min": hn, "max": hx},
        "hours_note": ("Fitted against the Met Office series over the "
                       "overlap, not inferred from the bulletins. UK stations "
                       "report at four hours and only one pair reproduces the "
                       "climatological day."),
        "agree": agree,
        "wmo_block": WMO[city],
        "note": ("Days after the workbook come from the station's own WMO "
                 "bulletins, checked against the official series where they "
                 "overlap. Not applied when they disagree."),
    }
    return ({k: tail[k] for k in added}, prov)


def main() -> int:
    # The token is only needed for a city with no committed history, so it is
    # fetched lazily rather than demanded up front. Three cities that all
    # have one must not be blocked by a credential none of them will use.
    tok = None
    if any(_frozen(c) is None for c in STATIONS):
        tok = _token()
    prov = {}
    for city, (county, sdir, sheet, fname) in STATIONS.items():
        hist = _frozen(city)
        if hist is not None:
            nfiles = "committed"
            print(f"  {city}: {len(hist)} days from the committed history, "
                  f"no CEDA call")
        else:
            hist, nfiles = midas_years(county, sdir, tok)
        cur = official(sheet)
        tail, season_prov = extend(city, cur)
        cur = {**cur, **tail}
        print(f"  {city}: official to {season_prov.get('official_to')}, "
              f"overlap {season_prov.get('overlap_days')} days worst "
              f"{season_prov.get('overlap_worst_c')} C at hours "
              f"{season_prov.get('hours')}, agree "
              f"{season_prov.get('agree')}, extended by {len(tail)}")
        # REFUSE TO WRITE A TRUNCATED FILE. On 2026-08-13 this wrote before it
        # checked, MIDAS returned nothing for Nottingham, and the city's file
        # went from 69 years to 222 rows of 2026 alone. The crash came one
        # line later, at min() on an empty year set, so the traceback looked
        # like a reporting bug while the damage was already on disk.
        #
        # These files are in a gitignored cache, so there is no revert. An
        # empty history is always a fetch failure and never a fact about the
        # station, and the safe response to a failed fetch is to keep what we
        # have. Raising here loses the run; writing here loses the record.
        if not hist:
            raise SystemExit(
                f"  {city}: MIDAS returned no history ({nfiles} files seen). "
                f"Refusing to overwrite {fname}, which still holds the good "
                f"record. Nothing written; re-run when CEDA answers.")
        merged = dict(hist)
        merged.update({d: v for d, v in cur.items() if d.startswith("2026")})
        rows = [[d, mn, mx] for d, (mn, mx) in sorted(merged.items())]
        write_series(SRC / fname, rows, label=city)
        d26 = [d for d, mn, mx in rows
               if d.startswith("2026") and mn is not None and mx is not None]
        hy = sorted({int(d[:4]) for d in hist})
        base = [y for y in hy if 1971 <= y <= 2000]
        prov[city] = {
            "station": sdir, "midas_files": nfiles,
            "history": f"{min(hy)}-{max(hy)}",
            "baseline_years_1971_2000": len(base),
            "season_2026_days": len(d26),
            "season_source": ("Met Office NMLA, Crown Copyright, re-use with "
                              "acknowledgement" if cur else "MISSING"),
            "season_provenance": season_prov,
        }
        print(f"  {city:11s} {min(hy)}-{max(hy)}  {len(base)}/30 baseline  "
              f"2026: {len(d26)} days  ({nfiles} MIDAS files)")
    (ROOT / "heat" / "data" / "uk_provenance.json").write_text(
        json.dumps(prov, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
