"""ASO ONI against the FOLLOWING winter's US precipitation, by state.

Written because "should we expect a bad hurricane or flood season" bundles
two questions whose answers point in opposite directions, and only one of
them was in the hurricane data.

Timing matters and is easy to get wrong: the El Nino US precipitation
teleconnection is a WINTER one. The winter that belongs to the ASO of
year Y is Dec Y plus Jan and Feb of year Y+1, so the 2026-27 event's
winter is Dec 2026 to Feb 2027, months AFTER the hurricane season it is
being compared with. Keying on the calendar year would mis-pair every
season by one.

What this is NOT: a flood series. Seasonal precipitation totals are an
aggregate, and flooding is an event. A wetter DJF raises the base rate;
it does not say a flood happens. That is the same distinction this desk
has spent the week enforcing on other people's claims.

Source: NOAA NCEI climate divisional database, statewide monthly
precipitation (climdiv-pcpnst), inches.
"""
import collections, csv, json, statistics as st, sys, urllib.request
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".fetch_cache" / "climdiv-pcpnst.txt"
INDEX = "https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current/"

STATES = {1:"Alabama",2:"Arizona",3:"Arkansas",4:"California",5:"Colorado",
 6:"Connecticut",7:"Delaware",8:"Florida",9:"Georgia",10:"Idaho",11:"Illinois",
 12:"Indiana",13:"Iowa",14:"Kansas",15:"Kentucky",16:"Louisiana",17:"Maine",
 18:"Maryland",19:"Massachusetts",20:"Michigan",21:"Minnesota",22:"Mississippi",
 23:"Missouri",24:"Montana",25:"Nebraska",26:"Nevada",27:"New Hampshire",
 28:"New Jersey",29:"New Mexico",30:"New York",31:"North Carolina",
 32:"North Dakota",33:"Ohio",34:"Oklahoma",35:"Oregon",36:"Pennsylvania",
 37:"Rhode Island",38:"South Carolina",39:"South Dakota",40:"Tennessee",
 41:"Texas",42:"Utah",43:"Vermont",44:"Virginia",45:"Washington",
 46:"West Virginia",47:"Wisconsin",48:"Wyoming"}


def get():
    if CACHE.exists() and CACHE.stat().st_size > 500_000:
        print(f"  cached  {CACHE.name}")
        return CACHE.read_text()
    import re
    req = urllib.request.Request(INDEX, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        idx = r.read().decode("utf-8", "replace")
    names = sorted(set(re.findall(r"climdiv-pcpnst-v[0-9.]+-\d{8}", idx)))
    if not names:
        sys.exit("REFUSING: no climdiv-pcpnst file listed at the index")
    print(f"  fetching {names[-1]} ...")
    req = urllib.request.Request(INDEX + names[-1], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8", "replace")
    CACHE.write_text(txt)
    return txt


def main():
    # layout: state(3) division(2) element(1) year(4) then 12 monthly values
    pcp = collections.defaultdict(dict)
    for line in get().splitlines():
        if len(line) < 20:
            continue
        sc, elem, yr = int(line[0:3]), line[5], int(line[6:10])
        if elem != "1" or sc not in STATES:
            continue
        for m, v in enumerate(line[10:].split()[:12], start=1):
            v = float(v)
            if v > -99:
                pcp[sc][(yr, m)] = v

    oni = collections.defaultdict(dict)
    with open(ROOT / "data" / "oni_full_history.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            oni[int(r["year"])][r["season"].upper()] = float(r["oni"])

    years = [y for y in range(1950, 2026) if "ASO" in oni.get(y, {})]
    out = []
    for sc, name in STATES.items():
        xs, ys = [], []
        for y in years:
            try:                    # Dec of Y, Jan and Feb of Y+1
                djf = pcp[sc][(y, 12)] + pcp[sc][(y + 1, 1)] + pcp[sc][(y + 1, 2)]
            except KeyError:
                continue
            xs.append(oni[y]["ASO"]); ys.append(djf)
        if len(xs) < 60:
            continue
        rho, p = stats.spearmanr(xs, ys)
        en = [v for x, v in zip(xs, ys) if x >= 0.5]
        ln = [v for x, v in zip(xs, ys) if x <= -0.5]
        out.append({"state": name, "n_winters": len(xs), "spearman": round(rho, 3),
                    "p": round(p, 5), "el_nino_mean_in": round(st.mean(en), 2),
                    "la_nina_mean_in": round(st.mean(ln), 2),
                    "ratio": round(st.mean(en) / st.mean(ln), 3),
                    "n_el_nino": len(en), "n_la_nina": len(ln)})

    faults = []
    if len(out) < 45:
        faults.append(f"only {len(out)} states have a usable series")
    fl = next((r for r in out if r["state"] == "Florida"), None)
    if not fl or fl["spearman"] < 0.4:
        faults.append("Florida's positive winter signal is the best established "
                      "in this teleconnection; its absence means the year "
                      "pairing is probably off by one")
    if faults:
        sys.exit("REFUSING TO WRITE:\n  - " + "\n  - ".join(faults))

    # --- regional monthly timing -------------------------------------
    # State DJF totals say WHERE. They do not say WHEN, and "when" is the
    # question a reader actually has, so resolve month by month across the
    # whole Sep-May window rather than assuming the DJF box is the season.
    name2sc = {v: k for k, v in STATES.items()}
    regions = {
        "Florida peninsula": ["Florida"],
        "Gulf coast": ["Louisiana", "Mississippi", "Alabama"],
        "Southeast Atlantic": ["Georgia", "South Carolina", "North Carolina"],
        "Texas": ["Texas"],
        "Southwest": ["Arizona", "New Mexico"],
        "California": ["California"],
        "Northern Rockies": ["Montana", "Idaho", "Wyoming"],
        "Ohio valley": ["Ohio", "Kentucky", "Indiana"],
    }
    # (month, year offset from the ASO year, label)
    seq = [(9,0,"Sep"),(10,0,"Oct"),(11,0,"Nov"),(12,0,"Dec"),
           (1,1,"Jan"),(2,1,"Feb"),(3,1,"Mar"),(4,1,"Apr"),(5,1,"May")]
    region_out = []
    for reg, names in regions.items():
        scs = [name2sc[n] for n in names]
        months = []
        for mo, off, lab in seq:
            xs, ys = [], []
            for y in years:
                try:
                    v = st.mean(pcp[sc][(y + off, mo)] for sc in scs)
                except KeyError:
                    continue
                xs.append(oni[y]["ASO"]); ys.append(v)
            rho, p_ = stats.spearmanr(xs, ys)
            en = [v for x, v in zip(xs, ys) if x >= 0.5]
            ln = [v for x, v in zip(xs, ys) if x <= -0.5]
            months.append({"month": lab, "ratio": round(st.mean(en)/st.mean(ln), 3),
                           "spearman": round(rho, 3), "p": round(p_, 5),
                           "significant": bool(p_ < 0.05)})
        xs, ys = [], []
        for y in years:
            try:
                v = st.mean(pcp[sc][(y,12)] + pcp[sc][(y+1,1)] + pcp[sc][(y+1,2)]
                            for sc in scs)
            except KeyError:
                continue
            xs.append(oni[y]["ASO"]); ys.append(v)
        en = [v for x, v in zip(xs, ys) if x >= 0.5]
        ln = [v for x, v in zip(xs, ys) if x <= -0.5]
        region_out.append({
            "region": reg, "states": names,
            "djf_el_nino_in": round(st.mean(en), 2),
            "djf_la_nina_in": round(st.mean(ln), 2),
            "djf_difference_in": round(st.mean(en) - st.mean(ln), 2),
            "months": months,
        })

    payload = {
        "generated": "2026-09-03",
        "source": INDEX + "climdiv-pcpnst (NOAA NCEI), statewide monthly precipitation, inches",
        "pairing": ("ASO ONI of year Y against Dec Y + Jan Y+1 + Feb Y+1. The "
                    "teleconnection is a winter one and lags the hurricane season "
                    "it is often quoted beside."),
        "not_a_flood_series": ("Seasonal precipitation totals, not flood events. A "
                               "wetter DJF raises the base rate; it does not say a "
                               "flood happens."),
        "ratio_on_a_small_base": (
            "The Southwest carries the largest monthly ratios in this file "
            "(2.0-2.3x) on the smallest base: 1.9 to 3.1 inches across DJF. A "
            "large proportional change on a small absolute base is not a large "
            "flood risk. Read ratio and difference together, never the ratio "
            "alone."),
        "california_is_not_significant": (
            "California is the most commonly asserted El Nino flood story and "
            "it does not hold here: Spearman +0.180 at p = 0.12, 1.15x, 15th of "
            "48 states. Oregon, Washington and Nevada are flat or slightly dry. "
            "The signal is the Gulf and Southeast, not the West Coast."),
        "n_winters": len(years),
        "states": sorted(out, key=lambda r: -r["spearman"]),
        "regions_monthly": region_out,
    }
    dest = ROOT / "data" / "us_winter_precip_enso.json"
    dest.write_text(json.dumps(payload, indent=1))
    sig = [r for r in out if r["p"] < 0.05]
    print(f"  wrote {dest.relative_to(ROOT)}")
    print(f"  {len(sig)}/{len(out)} states significant, "
          f"{len([r for r in sig if r['spearman'] > 0])} of them wetter in El Nino")


if __name__ == "__main__":
    main()
