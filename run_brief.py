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
from html import escape as h
import json
import shutil
from pathlib import Path

import markdown as md_lib

import sources as S
import probs
import analog
import snapshot


PAGES_BASE_URL = "https://kristjanlepik-commits.github.io/el-nino-tracker"
GITHUB_REPO_URL = "https://github.com/kristjanlepik-commits/el-nino-tracker"
AUTHOR_NAME = "Kristjan Lepik"


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


# Full editorial-style stylesheet for the public brief. Curly braces are
# CSS-literal; this is a plain string, not an f-string.
PUBLIC_CSS = """
  :root {
    --bg: #ffffff;
    --bg-soft: #fafafa;
    --bg-card: #fbfbf9;
    --border: #e5e5e0;
    --border-strong: #cccac2;
    --text: #1a1a1a;
    --text-soft: #555;
    --text-faint: #888;
    --accent: #1f4068;
    --neutral: #9ca3af;
    --moderate: #f7c948;
    --strong: #ef8b3a;
    --super: #d94327;
    --magn: #8b1a1a;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
    font-size: 16px;
  }
  nav.top {
    border-bottom: 1px solid var(--border);
    padding: 14px 28px;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    background: var(--bg);
    position: sticky;
    top: 0;
    z-index: 10;
  }
  nav.top .brand { font-weight: 600; font-size: 15px; letter-spacing: -0.01em; }
  nav.top .brand .dot { color: var(--super); }
  nav.top ul { list-style: none; margin: 0; padding: 0; display: flex; gap: 24px; }
  nav.top a { color: var(--text-soft); text-decoration: none; font-size: 14px; }
  nav.top a.active {
    color: var(--text); font-weight: 600;
    border-bottom: 2px solid var(--accent); padding-bottom: 4px;
  }
  main { max-width: 880px; margin: 0 auto; padding: 36px 28px 80px; }
  .issue-stamp {
    color: var(--text-faint); font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;
  }
  h1 {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 36px; font-weight: 600; letter-spacing: -0.015em;
    margin: 0 0 8px; line-height: 1.15;
  }
  .lede { color: var(--text-soft); font-size: 16px; margin: 0 0 18px; max-width: 640px; }
  .lede.bottom-line { font-weight: 500; color: var(--text); margin-bottom: 32px; }

  .ladder { display: flex; flex-direction: column; gap: 8px; margin: 28px 0 16px; }
  .rung {
    background: var(--bg-card); border: 1px solid var(--border);
    border-left: 4px solid var(--border-strong);
    border-radius: 6px; padding: 18px 24px 16px;
    display: grid; grid-template-columns: 1fr auto;
    column-gap: 24px; row-gap: 4px; align-items: baseline;
  }
  .rung .threshold {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 30px; font-weight: 600; letter-spacing: -0.015em;
    color: var(--text); line-height: 1.1;
  }
  .rung .threshold .gt { color: var(--text-faint); margin-right: 2px; font-weight: 400; }
  .rung .pct {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 22px; font-weight: 600; color: var(--text-soft);
    font-feature-settings: "tnum"; white-space: nowrap;
  }
  .rung .pct .pct-sym { font-size: 14px; color: var(--text-faint); margin-left: 1px; }
  .rung .pct .word { color: var(--text-faint); font-weight: 400; font-size: 13px; margin-left: 6px; }
  .rung .label { font-size: 13px; color: var(--text-soft); }
  .rung .label .sep { color: var(--text-faint); margin: 0 6px; }
  .rung .label .range { color: var(--text-faint); }
  .rung.magn     { border-left-color: var(--magn); }
  .rung.super    { border-left-color: var(--super); }
  .rung.strong   { border-left-color: var(--strong); }
  .rung.moderate { border-left-color: var(--moderate); }
  .buckets-note { font-size: 13px; color: var(--text-faint); margin: 0 0 32px; }

  section { margin: 48px 0; }
  h2 {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 22px; font-weight: 600; margin: 0 0 4px; letter-spacing: -0.01em;
  }
  .section-sub { color: var(--text-faint); font-size: 13px; margin: 0 0 20px; }

  .chart-card {
    background: var(--bg-soft); border: 1px solid var(--border);
    border-radius: 6px; padding: 20px;
  }
  .chart-card img { width: 100%; height: auto; display: block; }
  .chart-caption { font-size: 13px; color: var(--text-soft); margin-top: 14px; line-height: 1.5; }
  .chart-caption strong { color: var(--text); }

  table.phys { width: 100%; border-collapse: collapse; font-size: 14px; }
  table.phys th, table.phys td {
    padding: 10px 12px; text-align: left;
    border-bottom: 1px solid var(--border); vertical-align: top;
  }
  table.phys th {
    background: var(--bg-soft); font-weight: 500; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-soft);
  }
  table.phys td.num { font-feature-settings: "tnum"; white-space: nowrap; }
  .note {
    font-size: 14px; color: var(--text-soft);
    background: var(--bg-soft); border-left: 3px solid var(--border-strong);
    padding: 12px 16px; margin: 14px 0 0;
  }
  .note strong { color: var(--text); }

  .src-list { padding-left: 0; list-style: none; margin: 0; }
  .src-list li {
    padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px;
  }
  .src-list li:last-child { border-bottom: none; }
  .src-list .src-name { font-weight: 600; color: var(--text); }
  .src-list .src-issued { color: var(--text-faint); font-size: 12px; margin-left: 8px; }
  .src-list .src-detail { color: var(--text-soft); margin-top: 4px; }

  ol.caveats { padding-left: 22px; margin: 0; }
  ol.caveats li { margin-bottom: 14px; font-size: 14px; color: var(--text); line-height: 1.55; }

  footer {
    margin-top: 64px; padding-top: 24px;
    border-top: 1px solid var(--border);
    font-size: 13px; color: var(--text-soft);
  }
  .freshness-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 6px 24px; margin: 12px 0 18px;
  }
  .freshness-grid .src { color: var(--text); font-weight: 500; }
  .freshness-grid .meta { color: var(--text-faint); font-size: 12px; }
  .footer-meta { color: var(--text-faint); font-size: 12px; line-height: 1.6; }
  .footer-meta a { color: var(--accent); }

  /* ---------- Impact outlook section ---------- */
  section.impacts h3 {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 18px; font-weight: 600;
    margin: 28px 0 8px; letter-spacing: -0.005em;
  }
  section.impacts > p:first-of-type {
    color: var(--text-faint); font-size: 13px;
    margin: 0 0 8px;
  }
  section.impacts ul {
    list-style: none; padding-left: 0; margin: 8px 0 0;
  }
  section.impacts ul li {
    padding: 14px 0; border-bottom: 1px solid var(--border);
    font-size: 14px; line-height: 1.55; color: var(--text);
  }
  section.impacts ul li:last-child { border-bottom: none; }
  section.impacts ul li strong { color: var(--text); }
  section.impacts > p:not(:first-of-type) {
    font-size: 14px; line-height: 1.55; color: var(--text); margin: 12px 0;
  }

  /* ---------- Editorial synthesis (labeled, visually distinct) ---------- */
  .editorial-synthesis {
    margin-top: 36px;
    background: #fdf7e3;
    border-left: 4px solid #b58900;
    border-radius: 6px;
    padding: 18px 24px 8px;
  }
  .editorial-synthesis h3 {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 18px; font-weight: 600;
    margin: 0 0 12px; color: #5b4d12;
  }
  .editorial-synthesis blockquote {
    margin: 0 0 16px; padding: 10px 16px;
    background: rgba(255, 255, 255, 0.55);
    border-left: 3px solid #b58900;
    font-size: 13px; color: #5b4d12;
  }
  .editorial-synthesis blockquote p { margin: 0; }
  .editorial-synthesis blockquote strong { color: #4a3f10; }
  .editorial-synthesis p {
    margin: 12px 0; font-size: 14px; line-height: 1.6; color: var(--text);
  }
  .editorial-synthesis p strong { color: var(--text); font-weight: 700; }

  @media (max-width: 720px) {
    main { padding: 24px 16px 60px; }
    h1 { font-size: 28px; }
    .freshness-grid { grid-template-columns: 1fr; }
    nav.top { padding: 12px 16px; }
    nav.top ul { gap: 14px; }
    .rung { grid-template-columns: 1fr; }
    .rung .pct { margin-top: 4px; }
  }
""".strip()


def _render_rung(css_class: str, threshold: str, pct_dict: dict, label_main: str) -> str:
    """One probability-ladder row."""
    extras = ""
    if "lo" in pct_dict and "hi" in pct_dict:
        extras = (f'<span class="sep">·</span>'
                  f'<span class="range">range {pct_dict["lo"]}–{pct_dict["hi"]}%</span>')
    return (
        f'<div class="rung {css_class}">'
        f'<div class="threshold"><span class="gt">&gt;</span>{h(threshold)}</div>'
        f'<div class="pct">{pct_dict["mid"]}<span class="pct-sym">%</span>'
        f'<span class="word">probability</span></div>'
        f'<div class="label">{h(label_main)}{extras}</div>'
        f'</div>'
    )


def _signed_temp(value: float, decimals: int = 1) -> str:
    """Format a temperature with explicit sign and Unicode minus where negative."""
    formatted = f"{value:+.{decimals}f}"
    return formatted.replace("-", "−")  # U+2212 minus sign


IMPACTS_FILE = Path(__file__).parent / "impacts.md"
IMPACTS_SYNTHESIS_DIVIDER = "<!-- SYNTHESIS -->"


def load_impacts() -> dict:
    """Load impacts.md from project root, split on the synthesis divider.

    Returns {"aggregation": str, "synthesis": str} when both halves present,
    {"aggregation": str} when no divider, or {} when the file is missing
    or empty. The brief omits the impacts section if the result is empty.
    """
    if not IMPACTS_FILE.exists():
        return {}
    raw = IMPACTS_FILE.read_text().strip()
    if not raw:
        return {}
    if IMPACTS_SYNTHESIS_DIVIDER in raw:
        agg, syn = raw.split(IMPACTS_SYNTHESIS_DIVIDER, 1)
        return {"aggregation": agg.strip(), "synthesis": syn.strip()}
    return {"aggregation": raw}


def build_impacts_html_block(impacts: dict) -> str:
    """Render the impacts section as a self-contained <section> for the public brief.

    Aggregation content goes inline; synthesis is wrapped in
    <div class="editorial-synthesis"> so a cold reader can see at a glance
    where aggregation ends and the labeled editorial layer begins.
    """
    if not impacts:
        return ""
    parts = ['<section class="impacts"><h2>Impact outlook</h2>']
    agg = impacts.get("aggregation", "").strip()
    if agg:
        parts.append(md_lib.markdown(agg, extensions=["tables", "fenced_code"]))
    syn = impacts.get("synthesis", "").strip()
    if syn:
        parts.append('<div class="editorial-synthesis">')
        parts.append(md_lib.markdown(syn, extensions=["tables", "fenced_code"]))
        parts.append('</div>')
    parts.append('</section>')
    return ''.join(parts)


def build_public_html(fetched: dict, freshness: dict, headline: dict,
                      methodology_href: str, brief_date_iso: str,
                      canonical_url: str, og_image_url: str) -> str:
    """Render the public brief as structured HTML (bypasses markdown).

    methodology_href is relative ("methodology.html" for index, "../../methodology.html"
    for archive). canonical_url and og_image_url are absolute Pages URLs for the
    OG/Twitter card metadata.
    """
    iri_djf = fetched["iri"]["three_cat"]["DJF 2026-27"]
    phys = fetched["physical_state"]
    bom = fetched["bom"]
    ecmwf = fetched["ecmwf_seas5"]
    cpc_ndj = fetched["cpc_strength"]["table"]["NDJ 2026-27"]
    cpc_issued = fetched["cpc_strength"]["issued"]
    analog_same = S.ANALOG_SAME_WEEK

    offset_block = fetched.get("roni_to_oni_offset", {})
    offset = offset_block.get("value", S.RONI_TO_ONI_OFFSET)
    offset_live = (not offset_block.get("used_fallback", True)) and offset_block.get("issued")
    if offset_live:
        offset_phrase = (f"live offset {offset:+.2f}°C, week of "
                         f"{offset_block['issued']}")
    else:
        offset_phrase = f"flat seed offset {offset:+.2f}°C"

    # Bottom-line numbers from the headline
    moderate_pct = headline["moderate_>1.0"]["mid"]
    magn_pct = headline["9715_>2.5"]["mid"]
    description = (f"Weekly probability tracker for the developing 2026-27 El Niño "
                   f"event. {magn_pct}% chance of a 1997/2015-magnitude winter peak.")
    title = f"El Niño Tracker, week of {brief_date_iso}"

    # CWWA from physical-state fetch
    wwe_fresh = freshness.get("era5_wwe", {})
    wwe_live = wwe_fresh.get("ok") and not wwe_fresh.get("used_fallback")
    cwwa_value = phys.get("cwwa_ms_days") if wwe_live else None
    cwwa_analogs = phys.get("cwwa_analogs", {}) if wwe_live else {}

    def _cwwa_at(year, target_iso):
        ser = cwwa_analogs.get(year) or cwwa_analogs.get(str(year))
        if not ser or not target_iso:
            return None
        target_md = target_iso[5:]
        for d_iso, v in ser:
            if d_iso[5:] == target_md:
                return float(v)
        return float(ser[-1][1])

    target_iso = wwe_fresh.get("issued") or ""
    cwwa_97 = _cwwa_at(1997, target_iso)
    cwwa_15 = _cwwa_at(2015, target_iso)
    cwwa_23 = _cwwa_at(2023, target_iso)
    cwwa_25 = _cwwa_at(2025, target_iso)
    cwwa_curr_str = f"{cwwa_value:.0f}" if cwwa_value is not None else "n/a"
    cwwa_97_str = f"{cwwa_15:.0f}" if False else (f"{cwwa_97:.0f}" if cwwa_97 is not None else "n/a")
    cwwa_15_str = f"{cwwa_15:.0f}" if cwwa_15 is not None else "n/a"

    # Ranking sentence for the CWWA note
    cwwa_ranking = ""
    if cwwa_value is not None:
        refs = []
        for yr, val in [(1997, cwwa_97), (2015, cwwa_15), (2023, cwwa_23), (2025, cwwa_25)]:
            if val is not None:
                refs.append((yr, val))
        if refs:
            refs_sorted = sorted(refs, key=lambda x: abs(x[1] - cwwa_value))
            closest_yr, closest_val = refs_sorted[0]
            other_str = ", ".join(
                f"{y} ({v:.0f})" for y, v in sorted(refs) if y != closest_yr)
            cwwa_ranking = (f" At the same calendar date, 2026 CWWA "
                            f"({cwwa_value:.0f}) tracks closest to {closest_yr} "
                            f"({closest_val:.0f}); other reference years: "
                            f"{other_str}.")

    # Live JFM 2026 ONI value for the chart caption, with fallback
    jfm_2026 = None
    oni_history = fetched.get("oni_history", {})
    by_year = oni_history.get("by_year") if isinstance(oni_history, dict) else None
    if by_year:
        season_map = by_year.get(2026) or by_year.get("2026")
        if isinstance(season_map, dict):
            try:
                jfm_2026 = float(season_map.get("JFM"))
            except (TypeError, ValueError):
                jfm_2026 = None
    jfm_2026_str = (_signed_temp(jfm_2026, 2) if jfm_2026 is not None else "−0.16")

    # Heat content cell for physical state table
    hc_fresh = freshness.get("heat_content", {})
    hc_live = hc_fresh.get("ok") and not hc_fresh.get("used_fallback")
    hc_str = (f"{phys['heat_content_0_300m_estimate']:+.2f}°C" if hc_live
              else f"~{phys['heat_content_0_300m_estimate']:+.1f}°C (placeholder)")

    # Caveat numbers
    cpc_25_lo = headline["9715_>2.5"]["lo"]
    cpc_25_hi = headline["9715_>2.5"]["hi"]
    seas5_25_n = ecmwf.get("members_above", {}).get("2.5", 0)
    seas5_n = ecmwf.get("member_count", 0) or 0
    seas5_25_pct = round(100 * seas5_25_n / seas5_n) if seas5_n else 0
    seas5_calendar = ecmwf.get("max_lead_calendar", "max lead")

    # Source-by-source check (same content as internal, minor styling)
    cpc_super = cpc_ndj.get(">=2.0", 0)
    cpc_strong = cpc_ndj.get("1.5to2.0", 0)
    cpc_moderate = cpc_ndj.get("1.0to1.5", 0)
    cpc_weak = cpc_ndj.get("0.5to1.0", 0)
    cpc_neutral = cpc_ndj.get("neutral", 0)
    cpc_la_nina = sum(cpc_ndj.get(k, 0) for k in
                      ["<=-2.0", "-2.0to-1.5", "-1.5to-1.0", "-1.0to-0.5"])

    # ---- Assemble HTML ----
    head = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(description)}">
<meta property="og:image" content="{h(og_image_url)}">
<meta property="og:url" content="{h(canonical_url)}">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{h(title)}">
<meta name="twitter:description" content="{h(description)}">
<meta name="twitter:image" content="{h(og_image_url)}">
<style>{PUBLIC_CSS}</style>
</head>
<body>
<nav class="top">
  <span class="brand">El Niño Tracker<span class="dot">.</span></span>
  <ul>
    <li><a href="./" class="active">Brief</a></li>
    <li><a href="briefs/">Past briefs</a></li>
    <li><a href="{h(methodology_href)}">Methodology</a></li>
  </ul>
</nav>
<main>
  <div class="issue-stamp">Week of {h(brief_date_iso)} · Methodology v{h(str(S.METHODOLOGY_VERSION))}</div>
  <h1>How likely is a super<br>El Niño this winter?</h1>
  <p class="lede">Updated each Monday from the four major ENSO outlooks (NOAA CPC, IRI, BoM, ECMWF SEAS5) and weekly Niño 3.4 observations. Peak season target: <strong>DJF 2026-27</strong>. Forecast disagreements are surfaced rather than averaged.</p>
  <p class="lede bottom-line"><strong>Bottom line:</strong> {moderate_pct}% chance of at least a moderate El Niño this winter, {magn_pct}% chance of a 1997 / 2015-magnitude event.</p>
'''

    ladder_html = (
        '<section><div class="ladder">'
        + _render_rung("magn",     "+2.5°C peak", headline["9715_>2.5"], "1997 / 2015 magnitude")
        + _render_rung("super",    "+2.0°C peak", headline["super_>2.0"], "Very strong / super")
        + _render_rung("strong",   "+1.5°C peak", headline["strong_>1.5"], "Strong")
        + _render_rung("moderate", "+1.0°C peak", headline["moderate_>1.0"], "At least moderate")
        + '</div>'
        + f'<p class="buckets-note">Probabilities are CPC-derived after RONI→trad-ONI translation '
          f'({offset_phrase}) and a skew-normal fit on CPC\'s nine-bin strength table. '
          f'ECMWF SEAS5 ensemble counts are a second cross-check.</p>'
        + '</section>'
    )

    chart_html = (
        '<section>'
        '<h2>Analog tracker</h2>'
        '<p class="section-sub">2026-27 trajectory vs reference El Niño events, plus the SEAS5 ensemble forecast (median + uncertainty bands) forward.</p>'
        '<div class="chart-card">'
        '<img src="analog.png" alt="Analog tracker chart">'
        '<div class="chart-caption">'
        f'<strong>Read this week:</strong> at the JFM tick (month -1 since Mar 1), '
        f'2026 sits at {jfm_2026_str}°C. Both 1997 (−0.4°C) and 2023 (−0.3°C) were '
        f'similarly cool at the same calendar point and went on to become super events; '
        f'2015 was already running ahead at +0.6°C in JFM. The takeaway: JFM position '
        f'is a weak discriminator, ramp speed through MAM–AMJ matters more, and we '
        f'won\'t see that until the next 1–2 ONI updates. The dashed line marks the '
        f'ECMWF SEAS5 ensemble median forward to {h(ecmwf.get("max_lead_calendar", "Oct 2026"))} '
        f'(peak +{ecmwf.get("median_anomaly", 0):.1f}°C); the shaded bands show the '
        f'25–75 and 5–95 percentile spreads across the 51-member ensemble.'
        '</div></div></section>'
    )

    physical_html = (
        '<section>'
        '<h2>Physical state</h2>'
        '<p class="section-sub">Current observations vs the same calendar week in past super-event develop years.</p>'
        '<table class="phys">'
        '<thead><tr>'
        '<th>Indicator</th>'
        f'<th>Current<br><span style="font-weight:400">week of {h(brief_date_iso)}</span></th>'
        '<th>1997 same week</th>'
        '<th>2015 same week</th>'
        '</tr></thead><tbody>'
        '<tr>'
        '<td>Niño 3.4 weekly (traditional)</td>'
        f'<td class="num">{_signed_temp(phys["nino34_weekly_traditional"])}°C</td>'
        f'<td class="num">{_signed_temp(analog_same["1997_apr22_nino34_weekly"])}°C</td>'
        f'<td class="num">{_signed_temp(analog_same["2015_apr22_nino34_weekly"])}°C</td>'
        '</tr>'
        '<tr>'
        '<td>Niño 3.4 weekly (RONI)</td>'
        f'<td class="num">{_signed_temp(phys["nino34_weekly_roni"])}°C</td>'
        '<td class="num">n/a (pre-RONI)</td>'
        '<td class="num">n/a (pre-RONI)</td>'
        '</tr>'
        '<tr>'
        '<td>0–300 m heat content anomaly</td>'
        f'<td class="num">{h(hc_str)}</td>'
        f'<td class="num">{_signed_temp(analog_same["1997_apr_heat_content"])}°C</td>'
        f'<td class="num">{_signed_temp(analog_same["2015_apr_heat_content"])}°C</td>'
        '</tr>'
        '<tr>'
        '<td>Cumulative westerly wind anomaly since Mar 1<br>'
        '<span style="color:var(--text-faint); font-size:12px">CWWA, ERA5 5°N–5°S, 130°E–150°W, m/s·days</span></td>'
        f'<td class="num">{h(cwwa_curr_str)}</td>'
        f'<td class="num">{h(cwwa_97_str)}</td>'
        f'<td class="num">{h(cwwa_15_str)}</td>'
        '</tr>'
        '</tbody></table>'
        f'<div class="note"><strong>Heat content:</strong> {h(phys.get("heat_content_qualitative", ""))}</div>'
    )

    if wwe_live and cwwa_value is not None:
        physical_html += (
            f'<div class="note"><strong>CWWA:</strong> Live ERA5 daily 850 hPa zonal wind through '
            f'{h(wwe_fresh.get("issued", ""))}, area-meaned over 5°N–5°S, 130°E–150°W and integrated '
            f'for positive (westerly) anomalies vs the 1991-2020 same-calendar-day climatology. '
            f'Higher = more cumulative westerly forcing on the equatorial Pacific, the mechanism '
            f'that excites downwelling Kelvin waves and drives moderate-to-super event '
            f'escalation.{h(cwwa_ranking)}</div>'
        )
    physical_html += '</section>'

    sources_html = (
        '<section>'
        '<h2>Source-by-source check</h2>'
        '<p class="section-sub">What each agency said this week, verbatim where useful.</p>'
        '<ul class="src-list">'
        '<li>'
        '<span class="src-name">NOAA CPC strength table, NDJ 2026-27 (RONI)</span>'
        f'<span class="src-issued">issued {h(str(cpc_issued))}</span>'
        f'<div class="src-detail">super {cpc_super}%, strong {cpc_strong}%, moderate {cpc_moderate}%, '
        f'weak El Niño {cpc_weak}%, neutral {cpc_neutral}%, La Niña {cpc_la_nina}%.</div>'
        '</li>'
        '<li>'
        '<span class="src-name">IRI plume, DJF 2026-27</span>'
        f'<span class="src-issued">issued {h(str(fetched["iri"]["issued"]))}</span>'
        f'<div class="src-detail">El Niño {iri_djf[2]}%, neutral {iri_djf[1]}%, '
        f'La Niña {iri_djf[0]}%. Strength not broken out in the public Quick Look.</div>'
        '</li>'
        '<li>'
        '<span class="src-name">BoM ENSO Outlook</span>'
        f'<span class="src-issued">issued {h(str(bom["issued"]))}</span>'
        f'<div class="src-detail">{h(bom["alert_status"])}. Categorical only.</div>'
        '</li>'
        '<li>'
        '<span class="src-name">ECMWF SEAS5</span>'
        f'<span class="src-issued">run {h(str(ecmwf["issued"]))}</span>'
        f'<div class="src-detail">{h(ecmwf.get("summary", ""))}</div>'
        '</li>'
        '</ul>'
        '</section>'
    )

    caveats_html = (
        '<section>'
        '<h2>Caveats this issue</h2>'
        '<ol class="caveats">'
        f'<li>The +2.5°C bucket carries a {cpc_25_lo}–{cpc_25_hi}% range. It comes from a bootstrap '
        f'that perturbs CPC\'s published bin probabilities by Gaussian noise (sigma 1 percentage point, '
        f'matching CPC\'s whole-percent reporting precision) and refits the skew-normal each time. '
        f'The range therefore reflects reporting-quantization uncertainty in CPC\'s table, not '
        f'underlying forecast uncertainty.</li>'
        f'<li>ECMWF SEAS5 vs CPC, upper tail above +2.5°C trad ONI: SEAS5 has {seas5_25_n}/{seas5_n} '
        f'members ({seas5_25_pct}%) at {h(seas5_calendar)} (max available lead). CPC\'s NDJ 2026-27 '
        f'bucket lands at {cpc_25_lo}–{cpc_25_hi}%. We subtract SEAS5\'s own model climatology, which '
        f'removes its known ENSO warm bias; an observational-climatology subtraction would put '
        f'SEAS5 higher still. Real disagreement to surface, not a number to average.</li>'
        '<li>Spring predictability barrier: April–May forecasts at any of these centers carry materially '
        'wider error bars than what we\'ll see in July–August. Treat all numbers as preliminary.</li>'
        '</ol>'
        '</section>'
    )

    # Footer freshness grid
    fresh_rows = []
    for src, info in freshness.items():
        display = PUBLIC_SOURCE_NAMES.get(src, src)
        if info.get("ok") and not info.get("used_fallback"):
            meta = f'live, issued {info.get("issued")}'
        elif info.get("used_fallback"):
            meta = f'cached (issued {info.get("issued")})'
        else:
            meta = "placeholder"
        fresh_rows.append(
            f'<div><span class="src">{h(display)}</span>'
            f'<span class="meta"> · {h(meta)}</span></div>'
        )

    footer_html = (
        '<footer>'
        '<strong style="color:var(--text); font-weight:600">Source freshness this issue</strong>'
        f'<div class="freshness-grid">{"".join(fresh_rows)}</div>'
        f'<p class="footer-meta">Methodology version {h(str(S.METHODOLOGY_VERSION))}. '
        f'RONI to traditional ONI offset {offset:+.2f}°C ({"live, week of " + offset_block["issued"] if offset_live else "seed"}). '
        f'See <a href="{h(methodology_href)}">methodology</a> for the full audit trail.</p>'
        f'<p class="footer-meta" style="margin-top:18px;">By <strong style="color:var(--text)">{h(AUTHOR_NAME)}</strong>. '
        f'Source on <a href="{h(GITHUB_REPO_URL)}">GitHub</a>.</p>'
        '</footer>'
    )

    impacts_html = build_impacts_html_block(load_impacts())

    return (head + ladder_html + chart_html + physical_html
            + impacts_html + sources_html + caveats_html + footer_html
            + '\n</main>\n</body>\n</html>\n')


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

    # --------- Section 4: Impact outlook (if curated for this issue) -------
    impacts_for_md = load_impacts()
    next_section_num = 4
    if impacts_for_md:
        md.append("## 4. Impact outlook")
        md.append("")
        agg = impacts_for_md.get("aggregation", "").strip()
        if agg:
            md.append(agg)
            md.append("")
        syn = impacts_for_md.get("synthesis", "").strip()
        if syn:
            md.append(syn)
            md.append("")
        next_section_num = 5

    # --------- Editorial layer (number depends on whether impacts present) ---
    if is_public:
        md.append(f"## {next_section_num}. Sources and freshness")
    else:
        md.append(f"## {next_section_num}. Editorial layer")
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
    live_oni_by_year = fetched.get("oni_history", {}).get("by_year") or None
    analog.plot(str(BRIEF_DIR / "analog.png"),
                cwwa_data=cwwa_data,
                seas5_per_lead=fetched.get("ecmwf_seas5", {}).get("per_lead"),
                current_develop_year=S.BRIEF_DATE.year,
                today_offset=today_offset,
                live_oni_by_year=live_oni_by_year)

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

    # 6. Public brief: structured-HTML render (bypasses markdown for the public
    #    path). Different methodology_href and og_image_url for index vs archive
    #    so links/social cards resolve correctly from each location.
    archive_rel = f"briefs/{S.BRIEF_DATE.isoformat()}/"
    public_html_index = build_public_html(
        fetched, freshness, headline,
        methodology_href="methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/",
        og_image_url=f"{PAGES_BASE_URL}/analog.png",
    )
    public_html_archive = build_public_html(
        fetched, freshness, headline,
        methodology_href="../../methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/{archive_rel}",
        og_image_url=f"{PAGES_BASE_URL}/{archive_rel}analog.png",
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()
    (DOCS_DIR / "index.html").write_text(public_html_index)
    print(f"wrote: {DOCS_DIR / 'index.html'}")
    (DOCS_BRIEF_DIR / "brief.html").write_text(public_html_archive)
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
