"""
Generate the weekly brief markdown from sources.py + probs.py.

This is the entry point. Run from the repo root:
    python run_brief.py
Output goes to ./briefs/YYYY-MM-DD/brief.md alongside analog.png.

The runner:
  1. Renders the analog chart (idempotent).
  2. Computes headline buckets from CPC.
  3. Captures a JSON snapshot of all inputs to ./snapshots/YYYY-MM-DD.json.
  4. Loads the most recent prior snapshot and computes a diff.
  5. Embeds the auto-diff into the editorial layer.

After running, hand-edit briefs/YYYY-MM-DD/brief.md to add analyst
commentary on top of the auto-diff. The auto-diff is the floor; your
prose is the ceiling.
"""

from __future__ import annotations

from datetime import date
import json
import shutil
from pathlib import Path

import markdown as md_lib

import sources as S
import probs
import analog
import snapshot


PUBLIC_SOURCE_NAMES = {
    "cpc_strength": "NOAA CPC strength table",
    "oisst_weekly": "NOAA OISST weekly Niño 3.4",
    "heat_content": "CPC 0-300m heat content",
    "iri": "IRI plume",
    "bom": "BoM ENSO Outlook",
    "ecmwf_seas5": "ECMWF SEAS5",
    "era5_wwe": "ERA5 cumulative westerly wind anomaly (CWWA)",
}


def public_preamble(methodology_href: str) -> str:
    return (
        "Weekly probability tracker for the developing 2026-27 El Niño event, "
        "built from the official ENSO outlooks (NOAA CPC, IRI, BoM, ECMWF SEAS5) "
        "plus weekly Niño 3.4 observations. Numbers are reproduced from public "
        f"sources and recombined into a single set of peak-strength buckets; the "
        f"[methodology page]({methodology_href}) documents every step. Forecast "
        "disagreements are surfaced rather than averaged."
    )


HTML_CSS = """
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
         Arial, sans-serif; max-width: 820px; margin: 2em auto; padding: 0 1em;
         color: #222; line-height: 1.5; }
  h1 { border-bottom: 2px solid #888; padding-bottom: 0.2em; }
  h2 { border-bottom: 1px solid #ccc; padding-bottom: 0.1em; margin-top: 2em; }
  h3 { margin-top: 1.5em; }
  table { border-collapse: collapse; margin: 1em 0; }
  th, td { border: 1px solid #ccc; padding: 0.4em 0.7em; text-align: left; }
  th { background: #f4f4f4; }
  tr:nth-child(even) td { background: #fafafa; }
  blockquote { border-left: 4px solid #888; margin: 1em 0; padding: 0.2em 1em;
               color: #555; background: #f7f7f7; }
  code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px;
         font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
  img { max-width: 100%; height: auto; }
  hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
""".strip()


def render_html(markdown_text: str, title: str = None) -> str:
    body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
    page_title = title or f"El Nino brief, {S.BRIEF_DATE.isoformat()}"
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        f"<title>{page_title}</title>\n"
        f"<style>{HTML_CSS}</style>\n"
        "</head><body>\n"
        f"{body}\n"
        "</body></html>\n"
    )


BRIEF_DIR = Path(__file__).parent / "briefs" / S.BRIEF_DATE.isoformat()
DOCS_DIR = Path(__file__).parent / "docs"
DOCS_BRIEF_DIR = DOCS_DIR / "briefs" / S.BRIEF_DATE.isoformat()


def _cwwa_ranking(current_value: float, analogs: dict, target_iso: str | None) -> str:
    """Describe where the current CWWA falls among the analog years at the same calendar date."""
    if not target_iso or not analogs:
        return ""
    target_md = target_iso[5:]
    refs = []
    for yr_key, ser in analogs.items():
        if not ser:
            continue
        try:
            yr = int(yr_key)
        except (TypeError, ValueError):
            continue
        match = None
        for d_iso, v in ser:
            if d_iso[5:] == target_md:
                match = float(v)
                break
        if match is None:
            match = float(ser[-1][1])
        refs.append((yr, match))
    if not refs:
        return ""
    refs.sort(key=lambda x: abs(x[1] - current_value))
    closest_yr, closest_val = refs[0]
    return (f"At the same calendar date, 2026 CWWA ({current_value:.0f}) tracks "
            f"closest to {closest_yr} ({closest_val:.0f}); other reference years: "
            + ", ".join(f"{y} ({v:.0f})" for y, v in sorted(refs) if y != closest_yr) + ".")


def fmt_bucket(name: str, vals: dict) -> str:
    if "lo" in vals:
        return f"**{name}**: {vals['mid']}% (range {vals['lo']}-{vals['hi']}%, see caveat)"
    return f"**{name}**: {vals['mid']}%"


def build_markdown(fetched: dict, diff_md: str, freshness: dict,
                   analyst_read_md: str, diff_obj: dict = None,
                   audience: str = "internal",
                   methodology_href: str = "methodology.html") -> str:
    is_public = (audience == "public")
    offset_block = fetched.get("roni_to_oni_offset", {})
    offset = offset_block.get("value", S.RONI_TO_ONI_OFFSET)
    offset_live = (not offset_block.get("used_fallback", True)) and offset_block.get("issued")
    headline = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27", offset=offset)
    iri_djf = fetched["iri"]["three_cat"]["DJF 2026-27"]
    phys = fetched["physical_state"]
    bom = fetched["bom"]
    ecmwf = fetched["ecmwf_seas5"]
    cpc_ndj = fetched["cpc_strength"]["table"]["NDJ 2026-27"]
    cpc_issued = fetched["cpc_strength"]["issued"]
    analog_same = S.ANALOG_SAME_WEEK

    md = []
    md.append(f"# El Niño Probability Tracker, week of {S.BRIEF_DATE.isoformat()}")
    md.append("")
    md.append(public_preamble(methodology_href) if is_public else "Internal use.")
    md.append("")
    md.append("Target peak season: **DJF 2026-27**. CPC's longest-lead "
              "strength bin is NDJ 2026-27, used as the proxy for the DJF peak.")
    md.append("")

    # --------- Section 1: Headline probabilities ---------
    md.append("## 1. Headline probabilities")
    md.append("")
    md.append("Peak Niño 3.4 (traditional ONI), DJF 2026-27 / NDJ 2026-27.")
    if offset_live:
        offset_note = (f"RONI-to-traditional-ONI offset is {offset:+.2f}°C, "
                       f"the live tropical-mean SST anomaly observed for the "
                       f"week of {offset_block['issued']} (CPC).")
    else:
        offset_note = (f"RONI-to-traditional-ONI offset assumed flat at "
                       f"{offset:+.2f}°C (seed value).")
    md.append(f"Headline numbers below are CPC-derived after translating from "
              f"RONI bins to traditional ONI thresholds, then fitting a "
              f"skew-normal distribution to the nine bin probabilities and "
              f"evaluating its survival function at each threshold. {offset_note} "
              f"ECMWF SEAS5 member counts in caveat 2 are a second quantitative "
              f"cross-check.")
    md.append("")
    for label, key in [
        ("At least moderate (>+1.0°C peak)", "moderate_>1.0"),
        ("Strong (>+1.5°C peak)",            "strong_>1.5"),
        ("Very strong / super (>+2.0°C peak)", "super_>2.0"),
        ("1997/2015 magnitude (>+2.5°C peak)", "9715_>2.5"),
    ]:
        md.append(f"- {fmt_bucket(label, headline[key])}")
    md.append("")
    md.append("**Source-by-source check (qualitative where strength bins "
              "aren't broken out):**")
    md.append("")
    cpc_super = cpc_ndj.get(">=2.0", 0)
    cpc_strong = cpc_ndj.get("1.5to2.0", 0)
    cpc_moderate = cpc_ndj.get("1.0to1.5", 0)
    cpc_weak = cpc_ndj.get("0.5to1.0", 0)
    cpc_neutral = cpc_ndj.get("neutral", 0)
    cpc_la_nina = sum(cpc_ndj.get(k, 0) for k in
                      ["<=-2.0", "-2.0to-1.5", "-1.5to-1.0", "-1.0to-0.5"])
    md.append(f"- NOAA CPC strength table, NDJ 2026-27 (RONI): super "
              f"{cpc_super}%, strong {cpc_strong}%, moderate {cpc_moderate}%, "
              f"weak El Niño {cpc_weak}%, neutral {cpc_neutral}%, La Niña "
              f"{cpc_la_nina}%. Issued {cpc_issued}.")
    md.append(f"- IRI plume, DJF 2026-27: El Niño {iri_djf[2]}%, "
              f"neutral {iri_djf[1]}%, La Niña {iri_djf[0]}%. Issued "
              f"{fetched['iri']['issued']}. Strength not broken out in the "
              f"public Quick Look.")
    md.append(f"- BoM ENSO Outlook, issued {bom['issued']}: "
              f"{bom['alert_status']}. Categorical only.")
    md.append(f"- ECMWF SEAS5, run {ecmwf['issued']}: "
              f"{ecmwf['summary']}")
    md.append("")
    md.append("**Caveats this issue:**")
    md.append("")
    cpc_25_lo = headline["9715_>2.5"]["lo"]
    cpc_25_hi = headline["9715_>2.5"]["hi"]
    md.append(f"1. The +2.5°C bucket carries a {cpc_25_lo}-{cpc_25_hi}% range. "
              f"It comes from a bootstrap that perturbs CPC's published bin "
              f"probabilities by Gaussian noise (sigma 1 percentage point, "
              f"matching CPC's whole-percent reporting precision) and refits "
              f"the skew-normal each time. The range therefore reflects "
              f"reporting-quantization uncertainty in CPC's table, not "
              f"underlying forecast uncertainty.")
    if ecmwf.get("members_above") and ecmwf.get("member_count"):
        n_above = ecmwf["members_above"].get("2.5", 0)
        n_total = ecmwf["member_count"]
        pct = round(100 * n_above / n_total) if n_total else 0
        cal = ecmwf.get("max_lead_calendar", "max lead")
        cpc_lo = headline["9715_>2.5"]["lo"]
        cpc_hi = headline["9715_>2.5"]["hi"]
        md.append(f"2. ECMWF SEAS5 vs CPC, upper tail above +2.5°C trad ONI: "
                  f"SEAS5 has {n_above}/{n_total} members ({pct}%) at "
                  f"{cal} (max available lead). CPC's NDJ 2026-27 bucket lands at "
                  f"{cpc_lo}-{cpc_hi}%. We subtract SEAS5's own model climatology, "
                  f"which removes its known ENSO warm bias; an observational-"
                  f"climatology subtraction would put SEAS5 higher still. Real "
                  f"disagreement to surface, not a number to average.")
    else:
        md.append("2. ECMWF SEAS5 vs CPC, upper tail: SEAS5 not member-counted "
                  "this run; using qualitative read from sources.py.")
    md.append("3. Spring predictability barrier: April-May forecasts at any "
              "of these centers carry materially wider error bars than what "
              "we'll see in July-August. Treat all numbers as preliminary.")
    md.append("")

    # --------- Section 2: Physical state panel ---------
    md.append("## 2. Physical state panel")
    md.append("")
    md.append("| Indicator | Current (week of ~22 Apr 2026) | 1997 same week | "
              "2015 same week |")
    md.append("|---|---|---|---|")
    md.append(f"| Niño 3.4 weekly (traditional) | "
              f"{phys['nino34_weekly_traditional']:+.1f}°C | "
              f"{analog_same['1997_apr22_nino34_weekly']:+.1f}°C | "
              f"{analog_same['2015_apr22_nino34_weekly']:+.1f}°C |")
    md.append(f"| Niño 3.4 weekly (RONI) | "
              f"{phys['nino34_weekly_roni']:+.1f}°C | n/a (pre-RONI) | "
              f"n/a (pre-RONI) |")
    hc_fresh = freshness.get("heat_content", {})
    hc_live = hc_fresh.get("ok") and not hc_fresh.get("used_fallback")
    hc_label = (f"{phys['heat_content_0_300m_estimate']:+.2f}°C (CPC monthly, "
                f"180W-100W, vs 1981-2010 climo)" if hc_live
                else f"~{phys['heat_content_0_300m_estimate']:+.1f}°C "
                     f"(qualitative; placeholder)")
    md.append(f"| 0-300m heat content anomaly | {hc_label} | "
              f"{analog_same['1997_apr_heat_content']:+.1f}°C | "
              f"{analog_same['2015_apr_heat_content']:+.1f}°C |")
    wwe_fresh = freshness.get("era5_wwe", {})
    wwe_live = wwe_fresh.get("ok") and not wwe_fresh.get("used_fallback")
    cwwa_value = phys.get("cwwa_ms_days") if wwe_live else None
    cwwa_analogs = phys.get("cwwa_analogs", {}) if wwe_live else {}

    def _analog_value_at(year_int_or_str: int | str, target_iso: str) -> float | None:
        ser = cwwa_analogs.get(year_int_or_str) or cwwa_analogs.get(str(year_int_or_str))
        if not ser:
            return None
        target_md = target_iso[5:]
        for d_iso, v in ser:
            if d_iso[5:] == target_md:
                return float(v)
        return float(ser[-1][1])

    if wwe_live and cwwa_value is not None:
        target_iso = wwe_fresh.get("issued") or ""
        a97 = _analog_value_at(1997, target_iso)
        a15 = _analog_value_at(2015, target_iso)
        cell_curr = f"{cwwa_value:.0f} m/s·days (CWWA, ERA5 130E-150W, vs 1991-2020 climo)"
        cell_97 = f"{a97:.0f}" if a97 is not None else "n/a"
        cell_15 = f"{a15:.0f}" if a15 is not None else "n/a"
    else:
        cell_curr = "(CWWA fetch failed; not computed this run)"
        cell_97 = "n/a"
        cell_15 = "n/a"
    md.append(f"| Cumulative westerly wind anomaly since Mar 1 | "
              f"{cell_curr} | {cell_97} | {cell_15} |")
    md.append("")
    md.append(f"**Heat content note:** {phys['heat_content_qualitative']}")
    md.append("")
    if wwe_live and cwwa_value is not None:
        ranking = _cwwa_ranking(cwwa_value, cwwa_analogs, wwe_fresh.get("issued"))
        md.append(f"**CWWA note:** Live ERA5 daily 850 hPa zonal wind through "
                  f"{wwe_fresh.get('issued')}, area-meaned over 5N-5S, 130E-150W "
                  f"and integrated for positive (westerly) anomalies vs the "
                  f"1991-2020 same-calendar-day climatology. Higher = more "
                  f"cumulative westerly forcing on the equatorial Pacific, the "
                  f"mechanism that excites downwelling Kelvin waves and drives "
                  f"moderate-to-super event escalation. {ranking}")
    else:
        md.append(f"**CWWA note:** {phys.get('wwe_qualitative', '')}")
    md.append("")

    # --------- Section 3: Analog tracker ---------
    md.append("## 3. Analog tracker")
    md.append("")
    md.append("![Analog tracker](analog.png)")
    md.append("")
    md.append("Three reference El Niño events (1997-98, 2015-16, 2023-24) "
              "vs current 2026-27 trajectory in 3-month-running-mean ONI. "
              "Common reference is March 1 of develop year.")
    md.append("")
    md.append("**Read this week:** at the JFM tick (month -1 since Mar 1), "
              "2026 sits at -0.4°C, very close to where 1997 was (-0.4°C) "
              "and 2023 was (-0.3°C) at the same calendar point. Both went "
              "on to become super events. 2015 was already running ahead at "
              "+0.6°C in JFM. The takeaway is that JFM position is a weak "
              "discriminator; the ramp speed through MAM-AMJ is what matters, "
              "and we won't see that until the next 1-2 ONI updates.")
    md.append("")
    md.append("Caveat: the analog plot uses 3-month running mean ONI. The "
              "current weekly Niño 3.4 (+0.5°C trad, week of Apr 15) is not "
              "directly plotted because it's not a 3-month mean. Adding a "
              "weekly trajectory to this chart is on the V1.5 list.")
    md.append("")

    # --------- Section 4: Editorial layer ---------
    if is_public:
        md.append("## 4. Sources and freshness")
    else:
        md.append("## 4. Editorial layer")
    md.append("")

    suppress_diff = is_public and diff_obj is not None and diff_obj.get("is_first_issue")
    if not suppress_diff:
        md.append("### What changed week-over-week")
        md.append("")
        md.append(diff_md)
        md.append("")

    if not is_public:
        md.append("### Analyst read")
        md.append("")
        md.append(analyst_read_md)
        md.append("")

    md.append("### Source freshness this issue")
    md.append("")
    for src, info in freshness.items():
        display = PUBLIC_SOURCE_NAMES.get(src, src) if is_public else src
        if info.get("ok") and not info.get("used_fallback"):
            md.append(f"- **{display}**: fetched live, issued {info.get('issued')}.")
        elif info.get("used_fallback"):
            if is_public:
                md.append(f"- **{display}**: cached (issued {info.get('issued')}).")
            else:
                md.append(f"- **{display}**: live fetch failed; using last-good cache "
                          f"(issued {info.get('issued')}). Error: {info.get('error')}.")
        else:
            if is_public:
                md.append(f"- **{display}**: placeholder.")
            else:
                md.append(f"- **{display}**: not implemented or cache empty; using "
                          f"seed values from sources.py.")
    md.append("")
    md.append("---")
    md.append("")
    if offset_live:
        offset_footer = f"RONI offset {offset:+.2f}°C (live, week of {offset_block['issued']})"
    else:
        offset_footer = f"RONI offset {offset:+.2f}°C (seed)"
    if is_public:
        md.append(f"*Methodology version {S.METHODOLOGY_VERSION}. "
                  f"{offset_footer}. See [methodology]({methodology_href}).*")
    else:
        md.append(f"*Generated by run_brief.py from sources.py + probs.py + "
                  f"analog.py. Methodology version {S.METHODOLOGY_VERSION}. "
                  f"{offset_footer}. Next issue: Mon 4 May 2026 (per Monday "
                  f"cadence; first batch run is off-schedule).*")
    md.append("")
    return "\n".join(md)


def build_archive_index() -> str:
    """Render docs/briefs/index.html as markdown table from each meta.json."""
    rows = []
    briefs_root = DOCS_DIR / "briefs"
    if briefs_root.exists():
        for meta_path in sorted(briefs_root.glob("*/meta.json"), reverse=True):
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, ValueError):
                continue
            d = meta.get("date", meta_path.parent.name)
            h = meta.get("headline_buckets", {})
            mod = h.get("moderate_>1.0", {}).get("mid", "")
            strong = h.get("strong_>1.5", {}).get("mid", "")
            sup = h.get("super_>2.0", {}).get("mid", "")
            magn = h.get("9715_>2.5", {}).get("mid", "")
            rows.append(
                f"| [{d}]({d}/brief.html) | {mod}% | {strong}% | {sup}% | {magn}% |"
            )

    md = [
        "# Past briefs",
        "",
        "Weekly El Niño probability tracker, archive of past issues. "
        "Latest brief is on the [front page](../index.html); methodology "
        "overview is [here](../methodology.html).",
        "",
        "| Date | At least moderate (>+1.0°C) | Strong (>+1.5°C) | "
        "Super (>+2.0°C) | 1997/2015 magnitude (>+2.5°C) |",
        "|---|---|---|---|---|",
    ]
    md.extend(rows)
    md.append("")
    return "\n".join(md)


def main():
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_BRIEF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Run all fetchers (with fallback to cache / sources.py seeds)
    import fetch_all as F
    fetched = F.fetch_all()
    freshness = fetched.pop("_freshness", {})

    # 2. Chart (uses static analog CSV plus the live CWWA series and analogs)
    cwwa_data = None
    phys_for_chart = fetched.get("physical_state", {})
    if phys_for_chart.get("cwwa_series"):
        cwwa_data = {
            "cwwa_series": phys_for_chart["cwwa_series"],
            "cwwa_analogs": phys_for_chart.get("cwwa_analogs", {}),
        }
    today_offset = (S.BRIEF_DATE.toordinal() - date(S.BRIEF_DATE.year, 3, 1).toordinal()) / 30.44
    analog.plot(str(BRIEF_DIR / "analog.png"),
                cwwa_data=cwwa_data,
                current_develop_year=S.BRIEF_DATE.year,
                today_offset=today_offset)

    # 3. Snapshot current inputs and diff against last issue
    snap = snapshot.current_snapshot(fetched)
    prev = snapshot.load_prior_snapshot(before=S.BRIEF_DATE)
    d = snapshot.diff(prev, snap)
    diff_md = snapshot.render_diff_markdown(d)
    snap_path = snapshot.save_snapshot(snap)
    print(f"snapshot: {snap_path}")

    # 4. Auto-generate the Analyst Read prose (internal only)
    import editorial
    offset = fetched.get("roni_to_oni_offset", {}).get("value", S.RONI_TO_ONI_OFFSET)
    headline = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27", offset=offset)
    analyst_read_md = editorial.generate(
        headline=headline,
        diff=d,
        physical_state=fetched["physical_state"],
        freshness=freshness,
        brief_date=S.BRIEF_DATE.isoformat(),
    )

    # 5. Internal brief: markdown and HTML (unchanged outputs in briefs/)
    md_text = build_markdown(fetched, diff_md, freshness, analyst_read_md,
                             diff_obj=d, audience="internal")
    out_md = BRIEF_DIR / "brief.md"
    out_md.write_text(md_text)
    print(f"wrote: {out_md}")
    out_html = BRIEF_DIR / "brief.html"
    out_html.write_text(render_html(md_text))
    print(f"wrote: {out_html}")
    print(f"wrote: {BRIEF_DIR / 'analog.png'}")

    # 6. Public brief: render twice (latest at docs/index.html and archive
    #    at docs/briefs/YYYY-MM-DD/brief.html) with different methodology
    #    hrefs so the relative link resolves from each location.
    public_md_index = build_markdown(
        fetched, diff_md, freshness, analyst_read_md="",
        diff_obj=d, audience="public",
        methodology_href="methodology.html",
    )
    public_md_archive = build_markdown(
        fetched, diff_md, freshness, analyst_read_md="",
        diff_obj=d, audience="public",
        methodology_href="../../methodology.html",
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()
    (DOCS_DIR / "index.html").write_text(render_html(public_md_index))
    print(f"wrote: {DOCS_DIR / 'index.html'}")
    (DOCS_BRIEF_DIR / "brief.html").write_text(render_html(public_md_archive))
    print(f"wrote: {DOCS_BRIEF_DIR / 'brief.html'}")
    shutil.copyfile(BRIEF_DIR / "analog.png", DOCS_DIR / "analog.png")
    shutil.copyfile(BRIEF_DIR / "analog.png", DOCS_BRIEF_DIR / "analog.png")
    (DOCS_BRIEF_DIR / "meta.json").write_text(json.dumps({
        "date": S.BRIEF_DATE.isoformat(),
        "headline_buckets": headline,
    }, indent=2))
    print(f"wrote: {DOCS_BRIEF_DIR / 'meta.json'}")

    # 7. Archive index (regenerated each run from meta.json files)
    archive_md = build_archive_index()
    (DOCS_DIR / "briefs" / "index.html").write_text(
        render_html(archive_md, title="El Nino tracker, past briefs")
    )
    print(f"wrote: {DOCS_DIR / 'briefs' / 'index.html'}")

    # 8. Methodology overview HTML, regenerated from methodology.md if present
    meth_md = Path(__file__).parent / "methodology.md"
    if meth_md.exists():
        meth_html = DOCS_DIR / "methodology.html"
        meth_html.write_text(render_html(meth_md.read_text(),
                                         title="El Nino tracker, methodology"))
        print(f"wrote: {meth_html}")


if __name__ == "__main__":
    main()
