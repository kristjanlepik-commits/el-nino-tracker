"""
Weekly situation card: a one-page PNG summary of the current issue,
composed entirely from already-published artifacts (docs/briefs/*/
meta.json, snapshots/*.json, the issue's analog.png) so it can be
regenerated deterministically for any archived Monday without a fetch.

Public-side module (design, composition, prose). Called by run_brief.py
after the issue's docs and snapshot are written; also runnable
standalone:  .venv/bin/python card.py 2026-07-13 out.png

Design: visual language v1.0 "Bulletin" (D-016; see tokens.py). Bone
ground, hairline print rules, the El Nino channel hue for structure,
and the diverging anomaly scale for physical magnitude. Spectral sets
the house wordmark and all prose; IBM Plex Mono sets every figure,
label and stamp. Confidence is rendered on the odds rungs rather than
stated.

Font note: Spectral and IBM Plex Mono are vendored as static TTFs
under assets/fonts/ (both SIL OFL) so the GitHub Actions cron renders
the same design as local runs.
"""

from __future__ import annotations

import glob
import json
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Arc, Rectangle

import tokens as T

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
BRIEFS = DOCS / "briefs"
SNAPS = ROOT / "snapshots"

# Register the vendored brand faces so CI (Ubuntu) matches local output.
for _pat in ("spectral/*.ttf", "ibm-plex-mono/*.ttf"):
    for _f in glob.glob(str(ROOT / "assets" / "fonts" / _pat)):
        try:
            font_manager.fontManager.addfont(_f)
        except Exception:
            pass
_available = {f.name for f in font_manager.fontManager.ttflist}
SERIF = T.FONT_PROSE if T.FONT_PROSE in _available else "DejaVu Serif"
MONO = T.FONT_DATA if T.FONT_DATA in _available else "DejaVu Sans Mono"

PAPER = T.PAPER; INK = T.INK; GREY = T.INK_SOFT; HAIR = T.RULE
# NAVY is the structural/label color, now the El Nino channel hue since
# this card is the El Nino product. RED marks warm anomaly and comes
# from the diverging scale, never from the Fire channel (D-016 #4).
NAVY = T.NINO; RED = T.ANOMALY[7]; SLATE = T.INK_FAINT; AMBER = T.ANOMALY[6]
# Ladder bars: confidence is rendered. Solid for the calibrated rungs,
# fading for the two beyond the instrumental record.
RAMP = {k: v["bar"] for k, v in T.LADDER.items()}
RAMP_TEXT = {k: v["text"] for k, v in T.LADDER.items()}
RUNG_ORDER = ["record_>3.5", "record_>3.0", "9715_>2.5", "super_>2.0"]
RUNG_LABEL = {"record_>3.5": ("+3.5°", "far beyond the record ²"),
              "record_>3.0": ("+3.0°", "beyond the record ¹"),
              "9715_>2.5":   ("+2.5°", "1997 / 2015 class"),
              "super_>2.0":  ("+2.0°", "very strong, super")}
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

RECORD_PEAK = 2.8   # 2015-16, strongest observed (house convention)


def _fmt_day(d: date) -> str:
    return f"{MONTHS[d.month][:3]} {d.day}"


def _signed(v, dec=1) -> str:
    return f"{v:+.{dec}f}°".replace("-", "−")


def _status_word(sst: float) -> str:
    if sst >= 2.0:
        return "El Niño, very strong"
    if sst >= 1.5:
        return "El Niño, strong"
    if sst >= 1.0:
        return "El Niño, moderate"
    if sst >= 0.5:
        return "El Niño, weak"
    return "Neutral conditions"


def _next_monthly(after: date, day: int) -> date:
    d = date(after.year, after.month, day)
    if d <= after:
        y, m = (after.year + 1, 1) if after.month == 12 else (after.year, after.month + 1)
        d = date(y, m, day)
    return d


def _next_second_thursday(after: date) -> date:
    def second_thu(y, m):
        first = date(y, m, 1)
        off = (3 - first.weekday()) % 7   # Thursday = 3
        return first + timedelta(days=off + 7)
    d = second_thu(after.year, after.month)
    if d <= after:
        y, m = (after.year + 1, 1) if after.month == 12 else (after.year, after.month + 1)
        d = second_thu(y, m)
    return d


def _cwwa_same_date(analog_series, brief_d: date):
    """Value of an analog-year CWWA series at the same month-day."""
    best = None
    for iso, val in analog_series or []:
        try:
            d = date.fromisoformat(iso)
        except ValueError:
            continue
        if (d.month, d.day) <= (brief_d.month, brief_d.day):
            best = val
    return best


def collect(date_iso: str) -> dict:
    """Assemble everything the card needs from published artifacts."""
    brief_d = date.fromisoformat(date_iso)
    meta = json.loads((BRIEFS / date_iso / "meta.json").read_text())
    hb = meta["headline_buckets"]
    snap = json.loads((SNAPS / f"{date_iso}.json").read_text())
    ps = snap["physical_state"]

    # Archive series (only issues at or before this one)
    dirs = sorted(d for d in glob.glob(str(BRIEFS / "*/meta.json"))
                  if Path(d).parent.name <= date_iso)
    series = {k: [] for k in RUNG_ORDER}
    for p in dirs:
        b = json.loads(open(p).read()).get("headline_buckets", {})
        for k in series:
            v = b.get(k, {}).get("mid")
            if v is not None:
                series[k].append(v)
    issue_no = len(dirs)

    prev_iso = Path(dirs[-2]).parent.name if len(dirs) >= 2 else None
    prev_meta = (json.loads((BRIEFS / prev_iso / "meta.json").read_text())
                 if prev_iso else None)
    prev_snap_p = SNAPS / f"{prev_iso}.json" if prev_iso else None
    prev_snap = (json.loads(prev_snap_p.read_text())
                 if prev_snap_p and prev_snap_p.exists() else None)

    first_files = sorted(glob.glob(str(SNAPS / "2026-*.json")))
    first_snap = json.loads(open(first_files[0]).read()) if first_files else None

    sst = ps.get("nino34_weekly_traditional")
    ec = snap.get("ecmwf") or {}
    pl = ec.get("per_lead") or []
    peak_med, peak_cal = None, None
    for e in pl:
        m = e.get("median")
        if m is not None and (peak_med is None or m > peak_med):
            peak_med, peak_cal = m, e.get("calendar")

    # --- "this week" chips (up to 3, most newsworthy first) ---
    chips = []
    cur_cpc = (snap.get("cpc_strength") or {}).get("issued")
    prev_cpc = ((prev_snap or {}).get("cpc_strength") or {}).get("issued")
    if prev_meta and cur_cpc and prev_cpc and cur_cpc != prev_cpc:
        da = (hb.get("super_>2.0", {}).get("anchor") or 0) - \
             (prev_meta["headline_buckets"].get("super_>2.0", {}).get("anchor") or 0)
        chips.append((f"CPC re-issue: super anchor {da:+.0f}pp", "up" if da >= 0 else "down"))
    elif prev_meta:
        deltas = [(abs((hb.get(k, {}).get("mid") or 0) -
                       (prev_meta["headline_buckets"].get(k, {}).get("mid") or 0)),
                   (hb.get(k, {}).get("mid") or 0) -
                   (prev_meta["headline_buckets"].get(k, {}).get("mid") or 0), k)
                  for k in RUNG_ORDER if k in hb and k in prev_meta["headline_buckets"]]
        deltas.sort(reverse=True)
        if deltas and deltas[0][0] > 0:
            _, d, k = deltas[0]
            chips.append((f"Odds {RUNG_LABEL[k][0]} moved {d:+.0f}pp on the week", "up" if d > 0 else "down"))
        else:
            chips.append(("Headline steady on the week", "flat"))
    if prev_snap and sst is not None:
        psst = (prev_snap.get("physical_state") or {}).get("nino34_weekly_traditional")
        if psst is not None:
            d = sst - psst
            if abs(d) < 0.05:
                chips.append(("Niño 3.4 flat on the week", "flat"))
            else:
                word = "up" if d > 0 else "down"
                chips.append((f"Niño 3.4 {word} {_signed(abs(d))} on the week", "up" if d > 0 else "down"))
    if peak_med is not None and peak_cal:
        y, m = (int(x) for x in peak_cal.split("-"))
        chips.append((f"Forecast peak near {_signed(peak_med)} in {MONTHS[m]}", "up"))
    chips = chips[:3]

    # --- momentum vs first issue ---
    momentum = None
    if first_snap:
        f = (first_snap.get("physical_state") or {}).get("nino34_weekly_traditional")
        if f is not None and sst is not None:
            momentum = sst - f

    # --- race vs analogs ---
    import sources as S
    a = S.ANALOG_SAME_WEEK
    cwwa = ps.get("cwwa_ms_days")
    # Compare analog CWWA at the ERA5 series' own end date (not the brief
    # date): matches how the published brief computes "same calendar date".
    cwwa_ref = brief_d
    cser = ps.get("cwwa_series") or []
    if cser:
        try:
            cwwa_ref = date.fromisoformat(cser[-1][0])
        except (ValueError, TypeError, IndexError):
            pass
    cw97 = _cwwa_same_date((ps.get("cwwa_analogs") or {}).get("1997"), cwwa_ref)
    cw15 = _cwwa_same_date((ps.get("cwwa_analogs") or {}).get("2015"), cwwa_ref)

    def verdict(cur, v97, v15):
        if cur is None or v97 is None or v15 is None:
            return None
        ahead97, ahead15 = cur > v97, cur > v15
        if ahead97 and ahead15:
            return ("Ahead of both", RED)
        if not ahead97 and not ahead15:
            return ("Behind both", SLATE)
        return (f"Ahead of {'1997' if ahead97 else '2015'} only", AMBER)

    hc = ps.get("heat_content_0_300m_estimate")
    race = []
    if sst is not None:
        race.append(("Sea surface (Niño 3.4)", _signed(sst),
                     _signed(a["1997_apr22_nino34_weekly"]),
                     _signed(a["2015_apr22_nino34_weekly"]),
                     *verdict(sst, a["1997_apr22_nino34_weekly"],
                              a["2015_apr22_nino34_weekly"])))
    if hc is not None:
        race.append(("Subsurface heat (0-300 m)", _signed(hc, 2),
                     _signed(a["1997_apr_heat_content"]),
                     _signed(a["2015_apr_heat_content"]),
                     *verdict(hc, a["1997_apr_heat_content"],
                              a["2015_apr_heat_content"])))
    if cwwa is not None and cw97 is not None and cw15 is not None:
        race.append(("Cumulative wind (CWWA)", f"{cwwa:.0f}", f"{cw97:.0f}",
                     f"{cw15:.0f}", *verdict(cwwa, cw97, cw15)))

    wwb = ps.get("wwb_events_detail") or []
    strongest = max((e.get("peak_ms") or 0) for e in wwb) if wwb else None

    # --- sources line from snapshot issued dates ---
    src_bits = []
    if cur_cpc:
        src_bits.append(f"CPC strength table ({_fmt_day(date.fromisoformat(cur_cpc))})")
    if ec.get("issued"):
        src_bits.append(f"ECMWF SEAS5 ({_fmt_day(date.fromisoformat(ec['issued']))})")
    ob = snap.get("roni_to_oni_offset_block") or {}
    if ob.get("issued"):
        src_bits.append(f"NOAA OISST ({_fmt_day(date.fromisoformat(ob['issued']))})")
    if ps.get("issued"):
        try:
            src_bits.append(f"ERA5 winds ({_fmt_day(date.fromisoformat(ps['issued']))})")
        except ValueError:
            src_bits.append("ERA5 winds")

    return {
        "date": brief_d, "issue_no": issue_no,
        "version": meta.get("methodology_version", ""),
        "hb": hb, "series": series, "chips": chips,
        "sst": sst, "roni": ps.get("nino34_weekly_roni"),
        "status": _status_word(sst) if sst is not None else "",
        "momentum": momentum, "wwb_count": len(wwb), "strongest": strongest,
        "hc": hc, "race": race,
        "peak_med": peak_med,
        "analog_png": BRIEFS / date_iso / "analog.png",
        "sources": src_bits,
    }


def render(date_iso: str, out_path) -> Path:
    d = collect(date_iso)
    bd = d["date"]

    W, H = 16, 20
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(PAPER)
    # Two voices: serif (F) for prose, mono (M) for numbers, labels,
    # stamps, and the house wordmark. The split is the brand.
    F = SERIF
    M = MONO
    ML, MR = 0.08, 0.92

    def label(x, y, text, **kw):
        """Section label: mono, uppercase, tracked-out feel at small size."""
        kw.setdefault("color", NAVY)
        kw.setdefault("va", "top")
        fig.text(x, y, text.upper(), fontsize=9.5, family=M,
                 fontweight="medium", **kw)

    def mark(x, y, s):
        """The propagation mark (on-paper colorway), lower-left anchored
        at figure coords (x, y); s is the mark height as a figure-height
        fraction. Geometry matches assets/brand/mark-on-light.svg: each
        arc is a chord at chord_x spanning 13 +/- half, radius r."""
        import math
        ax = fig.add_axes([x, y, s * (H / W), s])
        ax.set_xlim(0, 26)
        ax.set_ylim(26, 0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(Rectangle((1, 10), 6, 6, facecolor=T.WARM,
                               edgecolor="none"))
        for chord_x, half, r, col in [(10, 9.8, 13.5, INK),
                                      (15, 7.4, 10.0, GREY),
                                      (20, 4.9, 6.4, SLATE)]:
            cx = chord_x - math.sqrt(r * r - half * half)
            ang = math.degrees(math.asin(half / r))
            ax.add_patch(Arc((cx, 13), 2 * r, 2 * r, angle=0,
                             theta1=-ang, theta2=ang,
                             edgecolor=col, lw=1.6))

    def hline(y, x0=ML, x1=MR, lw=0.8, color=HAIR):
        fig.add_artist(plt.Line2D([x0, x1], [y, y], color=color, lw=lw))

    def vline(x, y0, y1, lw=0.8, color=HAIR):
        fig.add_artist(plt.Line2D([x, x], [y0, y1], color=color, lw=lw))

    def sq(x, y, size, color, alpha=1.0):
        fig.add_artist(Rectangle((x, y), size, size * (W / H), facecolor=color,
                                 edgecolor="none", alpha=alpha,
                                 transform=fig.transFigure))

    # Masthead rule. The heaviest of the three permitted weights, in
    # INK, sitting above the wordmark. The old colored band and its
    # four-step ramp strip are gone: the language allows three rule
    # weights and one filled surface, and this is neither.
    fig.add_artist(Rectangle((0, 0.9905), 1.0, 0.0035, facecolor=INK,
                             edgecolor="none", transform=fig.transFigure))

    # header: house in mono, product in serif (the split is the brand)
    mark(ML - 0.006, 0.9555, 0.017)
    fig.text(ML + 0.026, 0.9665, "The Long Swell", fontsize=17, color=INK,
             family=F, fontweight="medium", va="top")
    fig.text(ML, 0.9445, "EL NIÑO 2026-27", fontsize=11, color=NAVY,
             family=M, fontweight="medium", va="top")
    fig.text(MR, 0.9655, f"NO {d['issue_no']}", fontsize=13, color=NAVY,
             family=M, fontweight="semibold", ha="right", va="top")
    fig.text(MR, 0.9465,
             f"{bd.isoformat()} · methodology v{d['version']}",
             fontsize=11.5, color=GREY, family=M, ha="right", va="top")
    hline(0.928, lw=T.RULE_MASTHEAD * 0.6, color=T.INK)

    # this week
    cy = 0.9115
    label(ML, cy, "This week")
    xs = [0.185, 0.44, 0.675][:len(d["chips"])]
    for x, (t, kind) in zip(xs, d["chips"]):
        marker, mcol = {"up": ("^", RED), "down": ("v", T.COLD),
                        "flat": ("o", SLATE)}[kind]
        fig.add_artist(plt.Line2D([x + 0.004], [cy - 0.0055],
                                  transform=fig.transFigure, color=mcol,
                                  marker=marker,
                                  markersize=7 if kind != "flat" else 5,
                                  linestyle="none"))
        fig.text(x + 0.017, cy, t, fontsize=11, color=INK, family=M, va="top")
    hline(0.8935)

    # hero left
    label(ML, 0.875, "Observed now")
    fig.text(ML - 0.005, 0.864, _signed(d["sst"]) if d["sst"] is not None else "n/a",
             fontsize=92, color=INK, family=M, fontweight="regular", va="top")
    sq(ML, 0.7565, 0.011, RED)
    fig.text(ML + 0.020, 0.7655, d["status"], fontsize=17.5, color=INK,
             family=F, fontweight="medium", va="top")
    sub = [f"Weekly Niño 3.4, traditional · RONI {_signed(d['roni'])}"
           if d["roni"] is not None else "Weekly Niño 3.4, traditional"]
    if d["momentum"] is not None:
        sub.append(f"Up {_signed(d['momentum'])} since the tracker began in April.")
    if d["wwb_count"]:
        sub.append(f"{d['wwb_count']} westerly wind bursts since 1 March.")
    fig.text(ML, 0.7395, "\n".join(sub), fontsize=12, color=GREY, family=F,
             va="top", linespacing=1.65)

    vline(0.475, 0.708, 0.882)

    # hero right: odds
    label(0.52, 0.875, "Odds the winter peak exceeds")
    label(MR, 0.875, "arc since April", color=SLATE, ha="right")
    rows = [k for k in RUNG_ORDER if k in d["hb"]]
    y = 0.8455
    any_footnote = False
    for key in rows:
        mid = d["hb"][key]["mid"]
        thr, lbl = RUNG_LABEL[key]
        if "¹" in lbl or "²" in lbl:
            any_footnote = True
        # Confidence is rendered, not stated: the marker loses substance
        # and the supporting text steps down the ink ramp as certainty
        # falls. The two rungs above +2.5 are beyond the instrumental
        # record and must never look as solid as the two below.
        spec = T.LADDER[key]
        c = spec["bar"]
        marker_alpha = {None: 1.0, (4, 4): 0.55, (2, 6): 0.30}.get(
            spec["dash"], 1.0)
        sq(0.52, y - 0.0065, 0.009, c, alpha=marker_alpha)
        fig.text(0.538, y, thr, fontsize=14, color=spec["text"], family=M,
                 fontweight="medium", va="center")
        fig.text(0.655, y, f"{mid}%", fontsize=26, color=c, family=M,
                 fontweight="regular", ha="right", va="center",
                 alpha=marker_alpha if marker_alpha > 0.5 else 0.62)
        fig.text(0.672, y - 0.0015, lbl, fontsize=11, color=spec["text"],
                 family=F, va="center")
        s = d["series"][key]
        if len(s) >= 2:
            sx0, sw, sy0, sh = 0.847, 0.073, y - 0.0115, 0.024
            n = len(s) - 1
            lx = [sx0 + (i / n) * sw for i in range(len(s))]
            ly = [sy0 + (v / 105.0) * sh for v in s]
            dash = spec["dash"]
            fig.add_artist(plt.Line2D(
                lx, ly, transform=fig.transFigure, color=c, lw=1.5,
                alpha=0.65 * marker_alpha + 0.2,
                linestyle="solid" if dash is None else (0, dash)))
            fig.add_artist(plt.Line2D([lx[-1]], [ly[-1]],
                                      transform=fig.transFigure, color=c,
                                      marker="o", markersize=4.4,
                                      alpha=marker_alpha,
                                      linestyle="none"))
        y -= 0.0405
        if key != rows[-1]:
            hline(y + 0.0205, x0=0.52, x1=MR, lw=0.6)

    # chart
    hline(0.7025)
    if d["analog_png"].exists():
        img = plt.imread(str(d["analog_png"]))
        Himg = img.shape[0]
        crop = img[int(0.078 * Himg):int(0.615 * Himg), :, :]
        ax = fig.add_axes([0.075, 0.430, 0.85, 0.255])
        ax.imshow(crop)
        ax.axis("off")
    fig.text(ML, 0.424, "2026 in red against the three strongest events on record. Combined SEAS5 and NMME forecast through the winter peak; dotted segments are the softer, longer-horizon parts.",
             fontsize=11, color=GREY, family=F, va="top")
    hline(0.402)

    # bottom left: race table
    top = 0.385
    label(ML, top, "The race")
    fig.text(ML + 0.062, top, "vs 1997 and 2015, same calendar week",
             fontsize=11, color=GREY, family=F, va="top")
    tx_name, tx_26, tx_97, tx_15, tx_ver = ML, 0.288, 0.352, 0.416, 0.545
    th_y = 0.362
    fig.add_artist(Rectangle((ML - 0.006, th_y - 0.0245), tx_ver - ML + 0.018,
                             0.030, facecolor=T.PAPER_SUNK, edgecolor="none",
                             transform=fig.transFigure))
    for x, htxt, ha in [(tx_name, "INDICATOR", "left"), (tx_26, "2026", "right"),
                        (tx_97, "1997", "right"), (tx_15, "2015", "right"),
                        (tx_ver, "VERDICT", "right")]:
        fig.text(x, th_y - 0.0035, htxt, fontsize=9.5, color=NAVY, family=M,
                 fontweight="medium", ha=ha, va="top")
    y = th_y - 0.040
    for name, v26, v97, v15, verdict, vc in d["race"]:
        fig.text(tx_name, y, name, fontsize=12.5, color=INK, family=F, va="top")
        fig.text(tx_26, y, v26, fontsize=11.5, color=INK, family=M,
                 fontweight="medium", ha="right", va="top")
        fig.text(tx_97, y, v97, fontsize=11.5, color=GREY, family=M,
                 ha="right", va="top")
        fig.text(tx_15, y, v15, fontsize=11.5, color=GREY, family=M,
                 ha="right", va="top")
        fig.text(tx_ver, y, verdict, fontsize=12.5, color=vc, family=F,
                 fontweight="medium", ha="right", va="top")
        y -= 0.0345
        hline(y + 0.0245, x0=ML, x1=0.555, lw=0.6)
    if d["strongest"]:
        fig.text(ML, y + 0.012,
                 f"Wind lags, but the strongest single burst ({d['strongest']:.1f} m/s) is already super-class.",
                 fontsize=11, color=GREY, family=F, va="top")

    vline(0.60, 0.225, 0.385)

    # bottom right: watch next + if verifies
    label(0.635, top, "Watch next")
    watch = [(_fmt_day(_next_monthly(bd, 5)), "ECMWF SEAS5 run"),
             (_fmt_day(_next_monthly(bd, 8)), "NMME initialisation"),
             (_fmt_day(_next_second_thursday(bd)), "CPC strength table"),
             ("Nov to Jan", "peak window")]
    y = 0.360
    for dt, ev in watch:
        fig.text(0.635, y, dt, fontsize=11.5, color=NAVY, family=M,
                 fontweight="semibold", va="top")
        fig.text(0.715, y, ev, fontsize=12.5, color=INK, family=F, va="top")
        y -= 0.0265
    label(0.635, 0.248, "If the forecast verifies")
    if d["peak_med"] is not None and d["peak_med"] > RECORD_PEAK:
        vtext = (f"The strongest El Niño in the instrumental\nrecord, roughly "
                 f"{d['peak_med'] - RECORD_PEAK:.1f}° above 2015-16, and beyond\n"
                 f"every model's verified experience.")
    else:
        vtext = "A peak near the top of the historical range."
    fig.text(0.635, 0.2315, vtext, fontsize=12, color=INK, family=F,
             va="top", linespacing=1.5)

    if any_footnote:
        fig.text(ML, 0.196, "¹ Little agency anchor; driven by model member counts.    "
                            "² No agency forecasts this threshold; where the hottest runs cluster, not a calibrated probability.",
                 fontsize=10, color=GREY, family=F, va="top")

    # footer
    hline(0.172, lw=T.RULE_SECTION * 0.7, color=T.INK)
    if d["sources"]:
        fig.text(ML, 0.159, "Sources this issue: " + " · ".join(d["sources"]),
                 fontsize=10, color=GREY, family=M, va="top")
    fig.text(ML, 0.143, "Odds are a CPC anchor deflected toward a six-model consensus, weight 0.85. Disagreements are surfaced, not averaged. Every issue archived, immutable.",
             fontsize=10.5, color=GREY, family=F, va="top")
    # House sign-off. Host string comes from tokens.SITE_HOST_DISPLAY,
    # the single copy shared with the citable chart.
    mark(ML - 0.006, 0.1065, 0.0145)
    fig.text(ML + 0.022, 0.1205, "The Long Swell",
             fontsize=13, color=INK, family=F, fontweight="medium",
             va="top")
    fig.text(ML + 0.022, 0.1055, T.SITE_HOST_DISPLAY,
             fontsize=11.5, color=GREY, family=M, va="top")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=100, facecolor=PAPER)
    plt.close(fig)
    print(f"card: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    iso = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else str(DOCS / "card.png")
    if iso is None:
        dirs = sorted(glob.glob(str(BRIEFS / "*/meta.json")))
        iso = Path(dirs[-1]).parent.name
    render(iso, out)
