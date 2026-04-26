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

from datetime import date
from pathlib import Path
import sources as S
import probs
import analog
import snapshot


BRIEF_DIR = Path(__file__).parent / "briefs" / S.BRIEF_DATE.isoformat()


def fmt_bucket(name: str, vals: dict) -> str:
    if "lo" in vals:
        return f"**{name}**: {vals['mid']}% (range {vals['lo']}-{vals['hi']}%, see caveat)"
    return f"**{name}**: {vals['mid']}%"


def build_markdown(fetched: dict, diff_md: str, freshness: dict,
                   analyst_read_md: str) -> str:
    headline = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27")
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
    md.append("Internal use. V1 first batch run.")
    md.append("")
    md.append("Target peak season: **DJF 2026-27**. CPC's longest-lead "
              "strength bin is NDJ 2026-27, used as the proxy for the DJF peak.")
    md.append("")

    # --------- Section 1: Headline probabilities ---------
    md.append("## 1. Headline probabilities")
    md.append("")
    md.append("Peak Niño 3.4 (traditional ONI), DJF 2026-27 / NDJ 2026-27.")
    md.append("V1 first batch has one quantitative source for strength "
              "bins (NOAA CPC). Numbers below are CPC-derived after "
              f"translating from RONI to traditional ONI using a flat "
              f"+{S.RONI_TO_ONI_OFFSET}°C offset (revisit each issue).")
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
    md.append("1. The +2.5°C bucket range is wider than the others because "
              "CPC's table doesn't separate >+2.5 from >+2.0 RONI; the "
              "12-21% reflects how much of the open `>=+2.0` RONI bin sits "
              "above +2.5°C trad ONI under different mass-distribution "
              "assumptions. Honest answer: we don't know precisely without "
              "the underlying ensemble.")
    md.append("2. ECMWF SEAS5 implies a much warmer upper tail than CPC: "
              "roughly half the ensemble exceeds +2.5°C traditional Niño "
              "3.4 for October. If that's representative of DJF, the +2.5°C "
              "bucket would be near 50%, not 12-21%. Treat as a real "
              "disagreement to surface, not a number to average. ECMWF has "
              "a known warm bias for ENSO; CPC may be slow to adjust to "
              "rising subsurface heat. We resolve once we wire up direct "
              "CDS member-counted pulls in V1.5.")
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
    md.append(f"| 0-300m heat content anomaly | "
              f"~{phys['heat_content_0_300m_estimate']:+.1f}°C "
              f"(qualitative; placeholder) | "
              f"{analog_same['1997_apr_heat_content']:+.1f}°C | "
              f"{analog_same['2015_apr_heat_content']:+.1f}°C |")
    md.append(f"| WWE count since Mar 1 | "
              f"~{phys['wwe_count_since_mar1_estimate']} (estimated; not "
              f"McPhaden-defined this run) | "
              f"{analog_same['1997_wwe_to_apr22']} | "
              f"{analog_same['2015_wwe_to_apr22']} |")
    md.append("")
    md.append(f"**Heat content note:** {phys['heat_content_qualitative']}")
    md.append("")
    md.append(f"**WWE note:** {phys['wwe_qualitative']}")
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
    md.append("## 4. Editorial layer")
    md.append("")
    md.append("### What changed week-over-week")
    md.append("")
    md.append(diff_md)
    md.append("")
    md.append("### Analyst read")
    md.append("")
    md.append(analyst_read_md)
    md.append("")
    md.append("### Source freshness this issue")
    md.append("")
    for src, info in freshness.items():
        if info.get("ok") and not info.get("used_fallback"):
            md.append(f"- **{src}**: fetched live, issued {info.get('issued')}.")
        elif info.get("used_fallback"):
            md.append(f"- **{src}**: live fetch failed; using last-good cache "
                      f"(issued {info.get('issued')}). Error: {info.get('error')}.")
        else:
            md.append(f"- **{src}**: not implemented or cache empty; using "
                      f"seed values from sources.py.")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"*Generated by run_brief.py from sources.py + probs.py + "
              f"analog.py. Methodology version {S.METHODOLOGY_VERSION}. "
              f"RONI offset assumed flat at +{S.RONI_TO_ONI_OFFSET}°C. "
              f"Next issue: Mon 4 May 2026 (per Monday cadence; first "
              f"batch run is off-schedule).*")
    md.append("")
    return "\n".join(md)


def main():
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Run all fetchers (with fallback to cache / sources.py seeds)
    import fetch_all as F
    fetched = F.fetch_all()
    freshness = fetched.pop("_freshness", {})

    # 2. Chart (idempotent; uses static analog CSV, doesn't depend on fetch)
    analog.plot(str(BRIEF_DIR / "analog.png"))

    # 3. Snapshot current inputs and diff against last issue
    snap = snapshot.current_snapshot(fetched)
    prev = snapshot.load_prior_snapshot(before=S.BRIEF_DATE)
    d = snapshot.diff(prev, snap)
    diff_md = snapshot.render_diff_markdown(d)
    snap_path = snapshot.save_snapshot(snap)
    print(f"snapshot: {snap_path}")

    # 4. Auto-generate the Analyst Read prose
    import editorial
    headline = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27")
    analyst_read_md = editorial.generate(
        headline=headline,
        diff=d,
        physical_state=fetched["physical_state"],
        freshness=freshness,
        brief_date=S.BRIEF_DATE.isoformat(),
    )

    # 5. Brief
    out = BRIEF_DIR / "brief.md"
    out.write_text(build_markdown(fetched, diff_md, freshness, analyst_read_md))
    print(f"wrote: {out}")
    print(f"wrote: {BRIEF_DIR / 'analog.png'}")


if __name__ == "__main__":
    main()
