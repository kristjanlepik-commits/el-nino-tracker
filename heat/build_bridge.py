"""Bridge a thin archive with the station's own bulletins, and COUNT the result.

WHY. Four cities have a long GHCN history that stops or thins out before the
present, and a WMO station that has been transmitting throughout. Larnaca's
GHCN ends in 2016; Algiers has one usable recent year in fifteen. In both
cases the station is not the problem, the archive is.

WHAT MAKES THIS LEGAL. One station, two transports, validated where they
overlap. Larnaca's bulletins reproduce GHCN exactly on summer 2016, the last
year both hold: 100.0% of days exact, worst 0.0 C, at 06Z and 18Z. That is
the same test that made London publishable and the same one that would have
caught Murcia.

WHY THIS COUNTS RATHER THAN SAMPLES. A bridge is not a current season. The
bridge years enter the RANKED series, so each one has to carry enough days to
be ranked, and a July that returns bytes is not a year that passes the bar. I
made exactly that mistake earlier today: I called three North African cities
viable on record SPAN and current-season presence, then found their maxima
were missing from most recent years. **Span is not coverage**, and this
script exists to print coverage rather than assert it.

FAILS BY REPORTING, NOT BY GUESSING. Every year is printed with its day
count. A year below the bar is shown, not silently dropped, so the decision
to include a city is made against the table rather than against a summary.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "heat"))

import synop  # noqa: E402
from safe_write import RefusedWrite, write_series
import builder_status as ST  # noqa: E402
# WRITES TO heat/data/sources/, NOT the cache. See source_file() in
# build_city_series: this file is expensive to regenerate and is tracked.
import build_city_series as _B  # noqa: E402


SRC = ROOT / "heat" / ".cache" / "src"
OGIMET = "https://www.ogimet.com/cgi-bin/getsynop"

# city: (WMO block, GHCN id, first bridge year, hours for min/max)
CITIES = {
    # BRIDGE FROM 2014, not 2017. The first run started where GHCN stopped
    # and left 1991-2020 at 27/30, short on exactly 2014, 2015 and 2016:
    # years GHCN holds PARTIALLY, at 61, 72 and 63 days. A gap does not
    # begin where an archive ends; it begins where the archive thins.
    "Larnaca":    ("17609", "CY000176090", 2014, "06", "18"),
    # BRIDGE FROM 1999. Algiers is short on exactly two years of 1971-2000,
    # 1999 at 60 days and 2000 at 92, so closing those two makes the
    # PREFERRED baseline complete and no exception is needed. OGIMET has
    # 2000 and nothing at 1995, so the archive begins in between; 1999 is
    # the year this turns on.
    "Algiers":    ("60390", "AG000060390", 1999, "06", "18"),
    "Tunis":      ("60715", "TSM00060715", 2010, "06", "18"),
    "Casablanca": ("60155", "MOM00060155", 2010, "06", "18"),
    # EASTERN EUROPE, added 2026-08-13 on Kristjan's instruction, because the
    # forecast moves the heat east after mid-August and we hold three cities
    # east of Vienna out of forty-two.
    #
    # Each starts where its archive THINS rather than where it ends, which is
    # the Larnaca lesson: bridging from the last year present left 1991-2020 at
    # 27/30 because GHCN held 2014-2016 partially.
    #
    # BUDAPEST CAN NEVER HAVE 1971-2000. GHCN begins in 1973 and OGIMET does
    # not reach the 1970s, so 1971 and 1972 are zero and unclosable. Its only
    # possible baseline is 1991-2020, where thirteen years sit just under the
    # bar at 91 to 99 days. Those are days missing, not years missing.
    "Budapest":   ("12843", "HUM00012843", 1998, "06", "18"),
    # Vilnius already has a COMPLETE 1971-2000. Everything from 2010 runs 20 to
    # 53 days, so the bridge is for the ranked series rather than the baseline.
    "Vilnius":    ("26730", "LH000026730", 2009, "06", "18"),
    # Zagreb is the cleanest of the three: 123 days a year almost throughout,
    # one short year at 2020, and the archive simply stops after 2023.
    "Zagreb":     ("14240", "HR000142360", 2020, "06", "18"),
    # ROME, shipped 2026-08-13 BECAUSE it is unremarkable rather than despite
    # it. Rome sits at +5.9 against Paris at +13.6 and is not in the August
    # event, which socials offered as a reason to drop it. It is the reason to
    # ship it: adding a city because it is hot is the selection effect D-141
    # killed this morning, and the option to add Italy uncontaminated expires
    # the moment the forecast verifies. A quiet city beside a loud one is what
    # makes the loud one credible.
    # Ciampino is an AIRPORT and one station in Rome is not Italy solved;
    # both ride in the station class and record_scope rather than in prose.
    # BRIDGE FROM 1999, not 2024. The first run started where the archive
    # STOPS and left 1971-2000 at 28/30 and 1991-2020 at 13/30, because
    # GHCN holds every year from 1999 PARTIALLY: 62 to 95 days, never zero,
    # so nothing looked absent. Same trap as Larnaca, and this is the third
    # time: a gap begins where an archive THINS, not where it ends, and a
    # partial year is invisible to any check that asks whether a year exists.
    "Rome":       ("16239", "IT000016239", 1999, "06", "18"),
}
MIN_DAYS = 100          # May-Aug days with both extremes for a usable year


def ghcn(gid):
    """Whole-record daily extremes, quality-flagged values excluded."""
    path = SRC / f"ghcn_{gid}.dly"
    # THE SAME BUG AS THE BULLETIN CACHE, IN THE SAME FILE, and I fixed that
    # one first and left this one. `if not path.exists()` meant the archive
    # was downloaded once and never again: every .dly here was fetched on 12
    # or 14 August 2026 and still served in September. Budapest's season
    # "stopped on 10 August" because our copy of NOAA's file did, and I had
    # already reported that to two chats as a property of the archive.
    #
    # GHCN-Daily appends. So refetch, and keep the old file unless the new one
    # is at least as long, which is the same rule safe_write applies to the
    # series and the same reason: a truncated or empty response is
    # indistinguishable from a real answer until you compare.
    #
    # ONE DAY, platform's bound and their reasoning: GHCN-Daily appends on a
    # lag of days and this job is weekly, so a one-day floor makes the
    # scheduled run pay the download once and every rerun pay nothing, and it
    # cannot skip an append that has actually landed.
    #
    # AND IT SAVES CI NOTHING, which is the honest way to book it. No .dly is
    # tracked, so a fresh checkout has none of these eleven archives and
    # downloads all 11 MB whatever this condition says. It helps this laptop
    # and any warm rerun. That is the second optimisation today conditioned on
    # state a cold runner does not have, after the sleep skip in build(), and
    # platform's tell for the class is worth keeping: the improvement is real
    # for the environment we develop in and absent from the one that publishes.
    fresh_enough = (path.exists()
                    and time.time() - path.stat().st_mtime < 86400)
    if fresh_enough:
        return _read_ghcn(path)
    blob = subprocess.run(
        ["curl", "-sS", "--max-time", "120",
         f"https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{gid}.dly"],
        capture_output=True).stdout
    if len(blob) >= (path.stat().st_size if path.exists() else 0) and blob:
        path.write_bytes(blob)
    elif path.exists():
        print(f"    {gid}: refetch returned {len(blob)} bytes against "
              f"{path.stat().st_size} cached; keeping the cached archive",
              file=sys.stderr)
    else:
        raise RuntimeError(f"{gid}: no cached archive and the fetch returned "
                           f"{len(blob)} bytes")
    return _read_ghcn(path)


def _read_ghcn(path):
    """Parse a .dly. Split out so the cached and refetched paths share it
    rather than diverging, which is how the two would eventually disagree."""
    out = {}
    for L in path.read_text(errors="replace").splitlines():
        el = L[17:21]
        if el not in ("TMAX", "TMIN"):
            continue
        y, m = int(L[11:15]), int(L[15:17])
        for d in range(31):
            o = 21 + d * 8
            v, q = L[o:o + 5].strip(), L[o + 6:o + 7]
            if v in ("-9999", "") or q.strip():
                continue
            key = f"{y}-{m:02d}-{d + 1:02d}"
            mn, mx = out.get(key, (None, None))
            if el == "TMIN":
                mn = int(v) / 10.0
            else:
                mx = int(v) / 10.0
            out[key] = (mn, mx)
    return out


def detect_hours(raw, fallback=("06", "18")):
    """Which hours does THIS station bulletin its extremes at? Measured.

    FIFTH TIME, and this one I caused while fixing the fourth. Rome bulletins
    at 17Z/05Z and the configured 06Z/18Z returned nine stray maxima, so I
    made the hours measured. Counting reports per hour then broke Larnaca,
    which bulletins BOTH extremes at BOTH 06Z and 18Z: the counter picked 06Z
    for the maximum as well, the 06Z maximum is the overnight one, and
    Larnaca's rank fell from 10th to 51st on night-time maxima. The refresh
    gate caught it, which is the only reason it is not live.

    SO COUNTING REPORTS IS THE WRONG TEST. Frequency says which hour talks
    most, not which hour carries the day's peak. The physical question is
    which hour reports the HIGHEST maxima and which the LOWEST minima, and
    that is answerable from the values themselves:

        maximum hour   the one whose mean reported maximum is greatest
        minimum hour   the one whose mean reported minimum is lowest

    Rome resolves to 17Z/05Z, Larnaca back to 18Z/06Z, and neither needs a
    rule about what synoptic hours mean. Hours carrying under a third of the
    best hour's reports are ignored, so a handful of stray bulletins at an
    odd hour cannot win on one unusual day.
    """
    import collections as _c
    hx, hn = _c.defaultdict(list), _c.defaultdict(list)
    for _d, h, tx, tn in synop.parse_ogimet(raw):
        if tx is not None:
            hx[h].append(tx)
        if tn is not None:
            hn[h].append(tn)
    if not hx or not hn:
        return fallback
    xbar = max(len(v) for v in hx.values())
    nbar = max(len(v) for v in hn.values())
    hxs = {h: v for h, v in hx.items() if len(v) >= xbar / 3}
    hns = {h: v for h, v in hn.items() if len(v) >= nbar / 3}
    best_x = max(hxs, key=lambda h: sum(hxs[h]) / len(hxs[h]))
    best_n = min(hns, key=lambda h: sum(hns[h]) / len(hns[h]))
    return best_n, best_x


def _is_synop(raw, block):
    """Is this actually bulletins for THIS block, or something else that is
    merely large?

    SIZE IS NOT SHAPE, and this file used `> 1000 bytes` as its test, so any
    error page or login page above a kilobyte would have passed AND BEEN
    CACHED as though it were data, freezing the failure permanently.

    Product's refinement of the content rule, which is sharper than the rule:
    content-checking only helps if you check THE OBJECT YOU NEED. They
    content-checked a CEDA directory listing, confirmed it was a genuine
    listing, and concluded the data behind it was readable. It was not. A
    listing is not a file, and a large body is not a bulletin.

    The object needed here is OGIMET's CSV of SYNOP reports for one block, so
    that is what is checked: lines beginning with this block number, carrying
    an AAXX group. Nothing else can satisfy it by being big.
    """
    if not raw or len(raw) < 200:
        return False
    hits = 0
    for line in raw.splitlines():
        if line.startswith(f"{block},") and "AAXX" in line:
            hits += 1
            if hits >= 20:
                return True
    return False


CURRENT_YEAR = dt.date.today().year


def _days(raw):
    """How many distinct dates a raw OGIMET body carries.

    Compared rather than byte length: the body includes headers and variable
    whitespace, so a shorter file is not reliably fewer observations.
    """
    return len({d for d, _h, _tx, _tn in synop.parse_ogimet(raw)})


def synop_year(block, year, hmin, hmax):
    """One May-to-August pull, CACHED TO DISK.

    OGIMET returns an empty body intermittently and it is indistinguishable
    from a station having no data. That cost two false negatives earlier
    today, and then cost two YEARS: a rerun rebuilt from the archive, hit the
    transient on 2018 and 2022, and dropped both from a file that had them.

    So the raw pull is the artifact and it is kept. A rerun reuses what was
    fetched successfully and only retries what is missing, which makes the
    build idempotent against a flaky upstream instead of destructive.
    """
    cache = SRC / "synop_cache"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{block}_{year}.txt"
    cached = (f.read_text(errors="replace")
              if f.exists() and _is_synop(f.read_text(errors="replace"), block)
              else None)

    # A FINISHED YEAR NEVER CHANGES. THE CURRENT ONE CHANGES EVERY DAY, and
    # reusing its cache is why six cities froze. Measured 2026-09-07: the
    # 2026 files for all six blocks were fetched on 12 and 14 August and never
    # again, and the payload's cut dates match those fetch dates exactly.
    # Rome sat at 2026-08-14 for three and a half weeks while OGIMET had more,
    # and every run "succeeded". That is an absence produced by our own
    # pipeline, reported as a property of the source, which is the failure
    # refresh_sources.py was written for.
    #
    # THE ANTI-FLAKE PROTECTION IS KEPT, because it was expensive to learn:
    # OGIMET returns an empty body intermittently and that once destroyed two
    # whole years on a rerun. So the current year REFETCHES, and the result
    # replaces the cache ONLY IF it parses AND carries at least as many days.
    # A transient short response leaves the good file untouched.
    if cached is not None and year != CURRENT_YEAR:
        return _parse(cached, hmin, hmax), False
    else:
        raw = ""
        for _attempt in (1, 2, 3):
            fresh = subprocess.run(
                ["curl", "-sS", "--max-time", "200",
                 f"{OGIMET}?block={block}&begin={year}05010000&end={year}08312359"],
                capture_output=True).stdout.decode("utf-8", "replace")
            if _is_synop(fresh, block):
                if cached is not None and _days(fresh) < _days(cached):
                    print(f"    {block} {year}: refetch returned "
                          f"{_days(fresh)} days against {_days(cached)} "
                          f"cached; keeping the cached pull",
                          file=sys.stderr)
                    raw = cached
                else:
                    f.write_text(fresh)
                    raw = fresh
                break
            time.sleep(8)
        if not _is_synop(raw, block) and cached is not None:
            print(f"    {block} {year}: refetch failed, using the cached pull",
                  file=sys.stderr)
            raw = cached
    return _parse(raw, hmin, hmax), True


def _parse(raw, hmin, hmax):
    # DETECT THE CONVENTION FOR THIS YEAR, not for this station. Rome
    # bulletins at 05Z/17Z in 2001 and at 06Z/18Z now, so a station-level
    # probe read 2001, applied it to every year, and wiped out the recent
    # coverage it had just been fixed to recover. A reporting convention is a
    # property of a station AND a period, and only the data knows which.
    hn, hx = detect_hours(raw, (hmin, hmax))
    out = {}
    for d, h, tx, tn in synop.parse_ogimet(raw):
        mn, mx = out.get(d, (None, None))
        if h == hn and tn is not None:
            mn = tn
        if h == hx and tx is not None:
            mx = tx
        out[d] = (mn, mx)
    return out


def usable(rows, lo, hi):
    per = {}
    for d, (mn, mx) in rows.items():
        if mn is not None and mx is not None and d[5:7] in ("05", "06", "07", "08"):
            per[int(d[:4])] = per.get(int(d[:4]), 0) + 1
    return per, sum(1 for y in range(lo, hi + 1) if per.get(y, 0) >= MIN_DAYS)


def build(city, full=False):
    """Bridge this city's archive with its own bulletins.

    THE FINISHED YEARS ARE ALREADY IN THE REPO AND WE WERE RE-DERIVING THEM.
    Every run walked every year from `first` to now, re-fetching bulletins to
    fill gaps the archive leaves. But the bridged result is committed in
    heat/data/sources/<city>.json, so a cold runner already holds those rows.
    Measured on Larnaca: 8 days in 2018, 12 in 2021 and 23 in 2024 exist ONLY
    from bulletins, and they are in the tracked file.

    THE COST OF NOT NOTICING was the whole weekly job. On 2026-09-07 the
    builder step took 83 minutes on a cold runner and was cancelled by a 90
    minute ceiling, most of it this loop: about 129 finished-year pulls across
    the bridge cities, each behind a 3 second politeness sleep, all of them
    reconstructing rows a fresh checkout had on disk. Platform declined to
    raise the timeout a third time and was right to: three raises would each
    have been defensible and collectively an admission that nobody looked at
    the work.

    So the tracked series seeds the PAST and only the current year is fetched.
    That is roughly 136 requests down to 6.

    WHAT SEEDS WHAT, because the order is the correctness:

        the fresh archive wins everywhere it has a value
        the tracked series fills gaps in PAST years only, standing in for
            the bulletin pulls that produced it
        fresh bulletins fill what is left, current year only

    The current year is deliberately NOT seeded from the tracked copy: that
    copy is last run's bulletins, and letting it fill a gap first would freeze
    a value the fresh pull would have corrected. This is the same defect as
    the cache that froze Rome, and seeding it here would reintroduce it.

    WHAT THIS GIVES UP, stated because it is not free. A past year whose gap
    OGIMET backfills, or a fix to our own parsing, no longer reaches history
    without a full walk. `--full` does that walk and is what platform's
    scheduled audit runs; it is also what a new city gets automatically,
    since it has no tracked series to seed from.
    """
    block, gid, first, hmin, hmax = CITIES[city]
    rows = ghcn(gid)
    ghcn_years = sorted({int(d[:4]) for d in rows})

    tracked = {}
    if not full:
        p = _B.source_file(f"{city.lower()}.json")
        if p.exists():
            tracked = {d: (mn, mx) for d, mn, mx in json.loads(p.read_text())}
    for d, (mn, mx) in tracked.items():
        # DO NOT DELETE THIS SKIP. It looks like an oversight in a loop whose
        # job is filling gaps, and removing it reintroduces the bug this whole
        # change exists to avoid. The tracked series holds LAST RUN'S bulletins
        # for the current year. Let them fill a current-year gap here and they
        # win over the fresh pull that follows, so a value freezes at whatever
        # was first fetched and every later run confirms it. That is exactly
        # how Rome sat at 2026-08-14 for three and a half weeks while every
        # build reported success, and it would be that bug reintroduced
        # through the fix for it.
        #
        # Past years are safe to seed precisely because they are finished:
        # their bulletins cannot change, which is the property the whole
        # reduction rests on.
        if int(d[:4]) == CURRENT_YEAR:
            continue
        omn, omx = rows.get(d, (None, None))
        rows[d] = (omn if omn is not None else mn,
                   omx if omx is not None else mx)

    years = (range(first, CURRENT_YEAR + 1) if full or not tracked
             else [CURRENT_YEAR])
    fetched_current = False
    for y in years:
        got, fetched = synop_year(block, y, hmin, hmax)
        if y == CURRENT_YEAR and fetched:
            fetched_current = True
        # Bulletins fill gaps and never overwrite an archived value: the
        # archive is the better record where it exists.
        for d, (mn, mx) in got.items():
            omn, omx = rows.get(d, (None, None))
            rows[d] = (omn if omn is not None else mn,
                       omx if omx is not None else mx)
        # SLEEP ONLY IF WE ACTUALLY ASKED. The pause is politeness to OGIMET
        # between requests, and a year served from the on-disk cache makes no
        # request. Algiers walks from 1999, so it was spending 84 seconds
        # sleeping between reads of local files. Across the six bridge cities
        # that is minutes per run, and it is pure waste rather than caution.
        if fetched:
            time.sleep(3)
    per, _ = usable(rows, min(ghcn_years), 2026)
    return rows, per, fetched_current


def main() -> int:
    # ONE CITY'S FAILURE MUST NOT COST THE OTHERS. Run weekly in CI as of
    # platform's d0475cbc, so an exception here would skip every city after it
    # while the payload still built from their stale tracked files: a silent
    # partial refresh, which is the failure the isolated fetch loop one level
    # up exists to prevent. Named loudly, counted, and a non-zero exit so the
    # step reports it rather than passing.
    # PUBLISHED CITIES BY DEFAULT, CANDIDATES ON DEMAND. Casablanca and Tunis
    # are in CITIES as bridge candidates and appear on no page: they are not
    # in build_city_series.CITIES. Since platform's d0475cbc this loop runs
    # weekly in CI, where every year of every city is a live fetch with a
    # 3-second pause, so two unpublished cities were about a quarter of a step
    # that is currently taking 43 minutes against a 90 minute budget.
    #
    # NAMED, NOT SILENTLY DROPPED. Skipping them without saying so is the
    # failure this channel spent 2026-09-07 fixing in three other places, and
    # a candidate that quietly stops being fetched is a candidate nobody
    # revisits. Pass them by name to run them.
    argv = [a for a in sys.argv[1:] if a != "--full"]
    full = "--full" in sys.argv[1:]
    if full:
        print("  --full: walking every year and refetching finished ones. "
              "This is the audit path, not the weekly one.")
    named = argv
    skipped = [] if named else [c for c in CITIES if c not in _B.CITIES]
    if skipped:
        print(f"  candidates not published, skipped: {', '.join(skipped)}. "
              f"Pass by name to include.")
    failed = []
    held = []
    todo = named or [c for c in CITIES if c in _B.CITIES]
    ST.open_status("build_bridge", todo)
    for city in todo:
        try:
            _p = _B.source_file(f"{city.lower()}.json")
            _was_last = ""
            if _p.exists():
                _prev_rows = json.loads(_p.read_text())
                _was_last = _prev_rows[-1][0] if _prev_rows else ""
            rows, per, fetched_current = build(city, full=full)
            yrs = sorted(per)
            ok = [y for y in yrs if per[y] >= MIN_DAYS]
            b71 = sum(1 for y in range(1971, 2001)
                      if per.get(y, 0) >= MIN_DAYS)
            b91 = sum(1 for y in range(1991, 2021)
                      if per.get(y, 0) >= MIN_DAYS)
            recent = [y for y in range(2017, 2027)
                      if per.get(y, 0) >= MIN_DAYS]
            write_series(_B.source_file(f"{city.lower()}.json"),
                         [[d, mn, mx] for d, (mn, mx) in sorted(rows.items())],
                         label=city)
        except RefusedWrite as exc:
            # A REFUSED WRITE IS THE GUARD WORKING, NOT THE BUILDER FAILING,
            # and conflating them cost a whole step on 2026-09-07. Budapest
            # refused to shrink by ONE row in 18380, safe_write kept the good
            # file exactly as designed, and my exit code reported the builder
            # as failed. Platform's step then counted it among "4 of 4
            # builders failed" and errored the job, on a run where five of six
            # bridge cities had refreshed correctly.
            #
            # This is platform's own rule about the refresh gate, one level
            # down: a hold is the guard working, and turning it red trains
            # everyone to ignore red. Held cities keep their previous series
            # and are named; only an unexpected exception is a failure.
            held.append(city)
            ST.set_status("build_bridge", city, "held", str(exc)[:200])
            print(f"  {city}: HELD by the write guard, previous series kept. "
                  f"{exc}", file=sys.stderr)
            continue
        except Exception as exc:
            failed.append(city)
            ST.set_status("build_bridge", city, "failed",
                          f"{type(exc).__name__}: {exc}"[:200])
            print(f"  {city}: FAILED {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        # ADVANCED MEANS THE DATA MOVED, not that the code ran. Compared
        # against the last date this city held before the build, because
        # "it ran fine" is precisely what Rome reported while frozen.
        _new_last = max(rows) if rows else None
        # ADVANCED, CHECKED OR UNCHANGED. Advanced means the data moved.
        # Checked means we asked the source about the current year and it had
        # nothing new, which accounts for a short city. Unchanged means we
        # completed without asking, which is what Rome did for three and a
        # half weeks and must never read as an explanation.
        if _new_last and _new_last > _was_last:
            _st, _why = "advanced", f"last {_new_last}, was {_was_last}"
        elif fetched_current:
            _st, _why = "checked", (f"fetched {CURRENT_YEAR}, nothing new "
                                    f"upstream; still at {_new_last}")
        else:
            _st, _why = "unchanged", (f"did NOT fetch {CURRENT_YEAR}; "
                                      f"still at {_new_last}")
        ST.set_status("build_bridge", city, _st, _why)
        print(f"  {city}: usable {len(ok)} years, {ok[0] if ok else '-'}"
              f" to {ok[-1] if ok else '-'}")
        print(f"    1971-2000 {b71}/30   1991-2020 {b91}/30   "
              f"2017-2026 {len(recent)}/10  {recent}")
        print(f"    2026 days: {per.get(2026, 0)}")
    if held:
        print(f"\n  {len(held)} city/cities HELD by the write guard and kept "
              f"their previous series: {', '.join(held)}. Not a failure.",
              file=sys.stderr)
    if failed:
        print(f"\n  {len(failed)} city/cities FAILED and kept their previous "
              f"series: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
