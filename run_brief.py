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

import argparse
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
AUTHOR_CONTACT_URL = "https://www.linkedin.com/in/kristjanlepik/"
LICENSE_NAME = "CC BY-NC 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"


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

  /* Editor's note: a quote-style block that signals "this is the author's voice"
     rather than auto-generated prose. Sits in the same slot as the bottom-line. */
  .editor-note {
    margin: 0 0 32px;
    padding: 16px 20px 14px;
    background: #fbf5e6;
    border-left: 3px solid var(--accent);
    border-radius: 0 6px 6px 0;
    max-width: 720px;
  }
  .editor-note .editor-note-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 6px;
  }
  .editor-note p {
    margin: 0;
    font-size: 15.5px;
    line-height: 1.55;
    color: var(--text);
    font-style: italic;
  }
  .editor-note p + p { margin-top: 10px; }
  .editor-note strong { font-style: normal; }

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
  .rung .pct .wow-delta {
    display: block;
    margin-top: 4px;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Helvetica, Arial, sans-serif;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.01em;
    color: var(--text-faint);
    text-align: right;
  }
  .rung .pct .wow-delta.wow-up   { color: var(--super); }
  .rung .pct .wow-delta.wow-down { color: var(--accent); }
  .rung .label { font-size: 13px; color: var(--text-soft); }
  .rung .label .sep { color: var(--text-faint); margin: 0 6px; }
  .rung .label .range { color: var(--text-faint); }
  .rung.magn     { border-left-color: var(--magn); }
  .rung.super    { border-left-color: var(--super); }
  .rung.strong   { border-left-color: var(--strong); }
  .rung.moderate { border-left-color: var(--moderate); }
  .buckets-note { font-size: 13px; color: var(--text-faint); margin: 0 0 32px; }

  /* Analyst section: tinted block directly under the ladder, only renders
     when at least one observer fires. Reader gets "what changed / what does
     it mean" before scrolling to the chart. */
  section.analyst-read {
    background: #fbf9f0;
    border-left: 4px solid var(--accent);
    border-radius: 6px;
    padding: 22px 26px 16px;
    margin: 32px 0;
  }
  section.analyst-read h2 {
    margin: 0 0 4px;
    color: var(--text);
  }
  section.analyst-read .section-sub {
    margin: 0 0 14px;
    color: var(--text-soft);
  }
  section.analyst-read ul {
    list-style: none;
    padding-left: 0;
    margin: 0;
  }
  section.analyst-read li {
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14.5px;
    line-height: 1.55;
    color: var(--text);
  }
  section.analyst-read li:last-child { border-bottom: none; }
  section.analyst-read li strong {
    color: var(--text);
    font-weight: 700;
  }

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
  section.impacts > p:first-of-type {
    color: var(--text-faint); font-size: 13px;
    margin: 0 0 16px;
  }

  /* World map: real Natural Earth-derived SVG referenced as <img>, with
     hotspot markers absolutely positioned over it as <button> elements. */
  .impacts-map {
    position: relative;
    margin: 16px 0 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    background: #f5f4ee;
  }
  .impacts-map .world-map-bg {
    display: block; width: 100%; height: auto;
  }
  .impacts-map .map-hotspot {
    position: absolute; transform: translate(-50%, -50%);
    width: 22px; height: 22px;
    background: transparent; border: 0; padding: 0;
    cursor: pointer; outline: none;
  }
  .impacts-map .map-hotspot-ring {
    position: absolute; inset: 0;
    border-radius: 50%;
    background: rgba(217, 67, 39, 0.15);
    border: 1.5px solid var(--super);
    transition: all 0.18s ease;
  }
  .impacts-map .map-hotspot-dot {
    position: absolute; inset: 7px;
    border-radius: 50%;
    background: var(--super);
    transition: all 0.18s ease;
  }
  .impacts-map .map-hotspot:hover .map-hotspot-ring {
    background: rgba(217, 67, 39, 0.25);
  }
  .impacts-map .map-hotspot.active .map-hotspot-ring {
    background: rgba(217, 67, 39, 0.32);
    border-width: 2.5px;
    inset: -3px;
  }
  .impacts-map .map-hotspot.active .map-hotspot-dot {
    inset: 5px;
  }
  .impacts-map .map-hotspot:focus-visible .map-hotspot-ring {
    border-color: var(--accent);
    border-width: 2.5px;
  }

  /* Region tabs strip */
  .region-tabs {
    display: flex; flex-wrap: wrap; gap: 6px;
    margin: 14px 0 16px;
  }
  .region-tab {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 999px; padding: 6px 14px;
    font-size: 13px; color: var(--text-soft);
    cursor: pointer; font-family: inherit;
    transition: all 0.15s ease;
  }
  .region-tab:hover { border-color: var(--border-strong); color: var(--text); }
  .region-tab[aria-selected="true"] {
    background: var(--super); border-color: var(--super);
    color: #fff; font-weight: 600;
  }

  /* Region content panels: only the active one shows */
  .region-panel { display: none; }
  .region-panel.active { display: block; }
  .region-panel h3 {
    font-family: "Charter", "Iowan Old Style", "Georgia", serif;
    font-size: 22px; font-weight: 600;
    margin: 0 0 10px; letter-spacing: -0.01em;
  }
  .region-panel p {
    font-size: 14.5px; line-height: 1.6; color: var(--text); margin: 0 0 12px;
  }

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


def _render_rung(css_class: str, threshold: str, pct_dict: dict, label_main: str,
                 prev_mid: int | None = None) -> str:
    """One probability-ladder row.

    Smoothed headline value (`mid`) is the prominent number. A small WoW
    delta sits below it when last week's snapshot is available and the
    change is non-zero; an arrow indicates direction. The methodology
    breakdown (CPC anchor + SEAS5 deflection) is documented on the
    methodology page rather than crammed into the rung label.
    """
    delta_html = ""
    if prev_mid is not None:
        try:
            delta = int(round(pct_dict["mid"] - prev_mid))
        except (TypeError, ValueError):
            delta = 0
        if delta != 0:
            if delta > 0:
                cls, arrow, sign = "wow-up", "▲", "+"
            else:
                cls, arrow, sign = "wow-down", "▼", "−"
            delta_html = (
                f'<span class="wow-delta {cls}">{arrow} {sign}{abs(delta)} pp vs last month</span>'
            )
    return (
        f'<div class="rung {css_class}">'
        f'<div class="threshold"><span class="gt">&gt;</span>{h(threshold)}</div>'
        f'<div class="pct">{pct_dict["mid"]}<span class="pct-sym">%</span>'
        f'<span class="word">probability</span>{delta_html}</div>'
        f'<div class="label">{h(label_main)}</div>'
        f'</div>'
    )


def _signed_temp(value: float, decimals: int = 1) -> str:
    """Format a temperature with explicit sign and Unicode minus where negative."""
    formatted = f"{value:+.{decimals}f}"
    return formatted.replace("-", "−")  # U+2212 minus sign


def _heat_content_compare(val: float, hc97: float, hc15: float) -> str:
    """One-sentence quantitative comparison of current heat content vs the
    1997 and 2015 super-event same-week analogs. Auto-banded above-both /
    between / below-both. Empty string if any input is missing.
    """
    if val is None or hc97 is None or hc15 is None:
        return ""
    if val > max(hc97, hc15):
        return (f" At {val:+.2f}°C, 2026 already exceeds both 1997 "
                f"({hc97:+.1f}°C) and 2015 ({hc15:+.1f}°C) at this calendar "
                f"week, running ahead of either super-event analog at this "
                f"stage of development.")
    if val > min(hc97, hc15):
        return (f" At {val:+.2f}°C, 2026 sits between 1997 ({hc97:+.1f}°C) "
                f"and 2015 ({hc15:+.1f}°C) at this calendar week.")
    return (f" At {val:+.2f}°C, 2026 is below both 1997 ({hc97:+.1f}°C) and "
            f"2015 ({hc15:+.1f}°C) at this calendar week.")


def _wwb_peak_finding(phys: dict) -> str:
    """One sentence on the strongest current-year westerly wind burst vs the
    full-season peak bursts of the super-event analogs.

    CWWA (the cumulative scalar) and peak burst amplitude can tell different
    stories: the cumulative energy can lag while individual burst strength
    is already in super-event territory. v1.7 of the methodology added a
    peak-detection WWB diagnostic complementing CWWA; the public brief
    surfaces only the peak-amplitude finding (which is robust across
    algorithm versions per the methodology page) and skips raw event counts
    (which are less stable). Returns empty string when WWB data is missing
    or the current year has no events yet.
    """
    events = phys.get("wwb_events_detail") or []
    analogs = phys.get("wwb_analogs") or {}
    if not events:
        return ""
    top = max(events, key=lambda e: e.get("peak_ms") or 0)
    current_peak = top.get("peak_ms")
    if not current_peak:
        return ""
    peak_date = top.get("peak_date") or ""

    def _season_peak(year):
        seasons = analogs.get(year) or analogs.get(str(year)) or []
        peaks = [(e.get("peak_ms") or 0) for e in seasons]
        return max(peaks) if peaks else None

    p97 = _season_peak(1997)
    p15 = _season_peak(2015)
    p23 = _season_peak(2023)
    if p97 is None or p15 is None:
        return ""

    date_clause = f" on {peak_date}" if peak_date else ""
    sentence = (f" Peak burst amplitude tells a different story: 2026's strongest "
                f"burst to date peaks at {current_peak:.1f} m/s{date_clause}, "
                f"in super-event territory (1997 full-season peak: {p97:.1f}, "
                f"2015: {p15:.1f})")
    if p23 is not None and current_peak > p23:
        sentence += f" and already exceeding 2023's full-season peak ({p23:.1f})"
    sentence += ". Cumulative wind energy is lagging; individual burst strength is not."
    return sentence


def _cwwa_divergence(cwwa, cwwa97, cwwa15, sst, hc) -> str:
    """When the current CWWA is conspicuously below super-event analogs while
    surface SST and subsurface heat content are both running hot, append a
    sentence flagging the divergence. The thresholds (0.6 * min analog;
    SST >= +0.5; HC >= +1.0) are heuristic flags for "this is interesting to
    mention", not a methodology calibration. Returns empty string when the
    pattern doesn't fit.
    """
    if any(x is None for x in (cwwa, cwwa97, cwwa15, sst, hc)):
        return ""
    weak_wind = cwwa < min(cwwa97, cwwa15) * 0.6
    hot_ocean = sst >= 0.5 and hc >= 1.0
    if weak_wind and hot_ocean:
        return (f" Wind forcing has not kept pace with the SST and heat-content "
                f"rise: 2026 CWWA at this week ({cwwa:.0f}) is well below both "
                f"super-event analogs (1997: {cwwa97:.0f}, 2015: {cwwa15:.0f}), "
                f"suggesting recent warming is being driven more by accumulated "
                f"subsurface heat (residual Kelvin-wave propagation) than by "
                f"ongoing wind events.")
    return ""


IMPACTS_FILE = Path(__file__).parent / "impacts.md"
IMPACTS_SYNTHESIS_DIVIDER = "<!-- SYNTHESIS -->"


# Region marker positions as (left%, top%) over the docs/world-map.svg
# (equirectangular projection, viewBox 800x400). Slugs match _slugify() of
# the impacts.md h3 headings.
REGION_MAP_COORDS = {
    "mediterranean":                         (52.7, 26.7),  # ~ Italy / Iberia
    "amazon-basin":                          (33.4, 52.7),  # ~ Brazil
    "australia-and-the-great-barrier-reef":  (90.5, 62.2),  # ~ NE Australia
    "southern-africa":                       (57.0, 64.0),  # ~ Botswana / Zimbabwe
    "india-and-south-asia":                  (71.6, 37.7),  # ~ central India
    "united-states":                         (22.2, 27.7),  # ~ continental US
    "southeast-asia":                        (82.0, 51.7),  # ~ Indonesia
    "global-coral":                          (8.4,  50.0),  # ~ central Pacific
}


def _slugify(text: str) -> str:
    """region-name → URL-safe slug. Match REGION_MAP_COORDS keys."""
    import re
    s = re.sub(r'[^\w\s-]', '', text.lower()).strip()
    return re.sub(r'[\s_]+', '-', s)


DOCS_BRIEFS_ROOT = Path(__file__).parent / "docs" / "briefs"


def _load_prev_headline_smoothed(current_brief_date: date) -> dict | None:
    """Find the most recent docs/briefs/YYYY-MM-DD/meta.json strictly before
    `current_brief_date` and return its `headline_buckets` dict (which has
    the smoothed structure: mid + anchor + seas5 + deflection per bucket
    since v1.5). Returns None if no prior archive is found or meta.json
    doesn't have the expected fields.

    Used by build_public_html to fire the Analyst-section observers that
    compare this week to last (CPC re-issue delta, convergence).
    """
    if not DOCS_BRIEFS_ROOT.exists():
        return None
    candidates = []
    for d in DOCS_BRIEFS_ROOT.iterdir():
        if not d.is_dir():
            continue
        try:
            d_date = date.fromisoformat(d.name)
        except ValueError:
            continue
        if d_date < current_brief_date:
            candidates.append((d_date, d))
    if not candidates:
        return None
    candidates.sort()
    latest_dir = candidates[-1][1]
    meta_path = latest_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("headline_buckets")


def _load_month_prior_headline_smoothed(current_brief_date: date) -> dict | None:
    """Find the most recent archive whose date is at least ~28 days before
    `current_brief_date`, and return its `headline_buckets` ONLY IF its
    methodology_version matches the current S.METHODOLOGY_VERSION.

    This drives the public ladder's MoM delta. The 28-day window aligns with
    CPC's monthly issuance cadence: when a delta shows on the ladder, the
    reader can trust that the move reflects an actual agency re-issue rather
    than mechanical drift in the RONI offset or bounded SEAS5 deflection
    between CPC issuances.

    Returns None when:
      - No archive exists at least 28 days before `current_brief_date`
      - The prior meta.json doesn't carry methodology_version (pre-v1.5
        archives written before the field was added)
      - The prior methodology_version differs from current (cross-version
        comparison would mislead; the methodology-version-bump banner
        already discloses non-comparability at the headline level)
    """
    if not DOCS_BRIEFS_ROOT.exists():
        return None
    from datetime import timedelta
    cutoff = current_brief_date - timedelta(days=28)
    candidates = []
    for d in DOCS_BRIEFS_ROOT.iterdir():
        if not d.is_dir():
            continue
        try:
            d_date = date.fromisoformat(d.name)
        except ValueError:
            continue
        if d_date <= cutoff:
            candidates.append((d_date, d))
    if not candidates:
        return None
    candidates.sort()
    latest_dir = candidates[-1][1]
    meta_path = latest_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    prev_version = data.get("methodology_version")
    if prev_version is None or str(prev_version) != str(S.METHODOLOGY_VERSION):
        return None
    return data.get("headline_buckets")


EDITORIAL_NOTE_FILE = Path(__file__).parent / "editorial_note.md"


def load_editorial_note() -> str:
    """Load the optional editorial_note.md at project root.

    If present and non-empty, returns the raw markdown — caller renders it
    to HTML and uses it in place of the auto-populated bottom-line copy.
    If absent or empty, returns "" and the bottom line falls back to the
    default "X% chance of at least a moderate El Niño this winter, Y%
    chance of a 1997 / 2015-magnitude event."

    The note is per-issue editorial copy: a short narrative paragraph
    (1-3 sentences typically) used on weeks where a numeric bottom line
    doesn't carry the story. Operator deletes the file or empties it
    when the standard bottom line is right again.
    """
    if not EDITORIAL_NOTE_FILE.exists():
        return ""
    return EDITORIAL_NOTE_FILE.read_text().strip()


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


def _split_aggregation_into_regions(agg_html: str):
    """Parse the rendered aggregation HTML into a lede + per-region list.

    Returns (lede_html, [(name, slug, content_html), ...]).
    """
    import re
    parts = re.split(r'(<h3>.*?</h3>)', agg_html, flags=re.DOTALL)
    lede_html = parts[0].strip() if parts else ""
    regions = []
    for i in range(1, len(parts) - 1, 2):
        h3_tag = parts[i]
        content = parts[i + 1].strip()
        name = re.sub(r'<[^>]+>', '', h3_tag).strip()
        regions.append((name, _slugify(name), content))
    return lede_html, regions


def _render_world_map_block(regions, active_slug: str, world_map_href: str) -> str:
    """Real world map (Natural Earth-derived SVG) referenced as an <img>, with
    region hotspots layered over it as absolute-positioned <button> elements.
    The map asset lives at docs/world-map.svg and is shared across the public
    index and the archive briefs (the href differs by depth)."""
    parts = ['<div class="impacts-map">']
    parts.append(
        f'<img class="world-map-bg" src="{h(world_map_href)}" '
        f'alt="World map of regional impact zones" loading="lazy"/>'
    )
    for name, slug, _ in regions:
        left, top = REGION_MAP_COORDS.get(slug, (50.0, 50.0))
        active = " active" if slug == active_slug else ""
        parts.append(
            f'<button type="button" class="map-hotspot{active}" '
            f'data-region="{slug}" '
            f'style="left: {left}%; top: {top}%;" '
            f'aria-label="{h(name)}">'
            f'<span class="map-hotspot-ring"></span>'
            f'<span class="map-hotspot-dot"></span>'
            f'</button>'
        )
    parts.append('</div>')
    return ''.join(parts)


# Vanilla JS for tab + map-hotspot switching. No framework. Reads URL hash on load.
IMPACTS_TAB_SCRIPT = """<script>
(function () {
  var section = document.querySelector('.impacts');
  if (!section) return;
  var tabs = section.querySelectorAll('.region-tab');
  var panels = section.querySelectorAll('.region-panel');
  var hotspots = section.querySelectorAll('.impacts-map .map-hotspot');
  function activate(slug) {
    if (!slug) return;
    var ok = false;
    panels.forEach(function (p) {
      var match = p.getAttribute('data-region') === slug;
      p.classList.toggle('active', match);
      if (match) ok = true;
    });
    if (!ok) return;
    tabs.forEach(function (t) {
      t.setAttribute('aria-selected',
        t.getAttribute('data-region') === slug ? 'true' : 'false');
    });
    hotspots.forEach(function (h) {
      h.classList.toggle('active', h.getAttribute('data-region') === slug);
    });
    if (history.replaceState) {
      history.replaceState(null, '', '#region=' + slug);
    }
  }
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      activate(t.getAttribute('data-region'));
    });
  });
  hotspots.forEach(function (h) {
    h.addEventListener('click', function () {
      activate(h.getAttribute('data-region'));
    });
  });
  var m = (location.hash || '').match(/region=([\\w-]+)/);
  if (m) activate(m[1]);
})();
</script>"""


def build_impacts_html_block(impacts: dict, world_map_href: str = "world-map.svg") -> str:
    """Render the impacts section as a self-contained <section> for the public
    brief. Lede paragraph at top; regional content compressed into a real
    world map + tab strip + one-region-at-a-time panels.
    """
    if not impacts:
        return ""
    parts = ['<section class="impacts"><h2>Impact outlook</h2>']
    agg = impacts.get("aggregation", "").strip()
    if not agg:
        parts.append('</section>')
        return ''.join(parts)

    agg_html = md_lib.markdown(agg, extensions=["tables", "fenced_code"])
    lede_html, regions = _split_aggregation_into_regions(agg_html)
    if lede_html:
        parts.append(lede_html)
    if regions:
        default_slug = regions[0][1]
        parts.append(_render_world_map_block(regions, default_slug, world_map_href))

        parts.append('<div class="region-tabs" role="tablist" '
                     'aria-label="Regional impacts">')
        for name, slug, _ in regions:
            selected = "true" if slug == default_slug else "false"
            parts.append(
                f'<button type="button" class="region-tab" '
                f'data-region="{slug}" role="tab" '
                f'aria-selected="{selected}">{h(name)}</button>'
            )
        parts.append('</div>')

        parts.append('<div class="region-content">')
        for name, slug, content_html in regions:
            cls = "region-panel active" if slug == default_slug else "region-panel"
            parts.append(
                f'<div class="{cls}" data-region="{slug}" role="tabpanel" '
                f'aria-label="{h(name)}">'
            )
            parts.append(f'<h3>{h(name)}</h3>')
            parts.append(content_html)
            parts.append('</div>')
        parts.append('</div>')

    parts.append(IMPACTS_TAB_SCRIPT)
    parts.append('</section>')
    return ''.join(parts)


def build_public_html(fetched: dict, freshness: dict, headline: dict,
                      methodology_href: str, brief_date_iso: str,
                      canonical_url: str, og_image_url: str,
                      world_map_href: str = "world-map.svg",
                      prev_headline: dict | None = None,
                      prev_snapshot: dict | None = None,
                      prev_headline_month: dict | None = None) -> str:
    """Render the public brief as structured HTML (bypasses markdown).

    methodology_href and world_map_href are both relative paths whose depth
    differs between the index ("methodology.html", "world-map.svg") and the
    archive briefs ("../../methodology.html", "../../world-map.svg").
    canonical_url and og_image_url are absolute Pages URLs for the
    OG/Twitter card metadata.

    prev_headline (WoW): smoothed buckets from last week's archive. Used by
    Analyst-section observers ("CPC re-issued, super +12pp from last week").

    prev_headline_month (MoM, version-aware): smoothed buckets from ~28 days
    prior, ONLY if same methodology version as current. Drives the ladder
    delta indicator. None means no delta is shown on the rungs (first runs,
    methodology-version mismatches, or no archive in the 4-week window).
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

    # Bottom-line slot: per-issue editorial note replaces the default copy
    # when editorial_note.md exists and is non-empty. Otherwise fall back
    # to the data-driven default ("X% chance of ... Y% chance of ...").
    editorial_note = load_editorial_note()
    if editorial_note:
        bottom_line_html = (
            '<aside class="editor-note">'
            '<div class="editor-note-label">Editor\'s note</div>'
            + md_lib.markdown(editorial_note,
                              extensions=["tables", "fenced_code"])
            + '</aside>'
        )
    else:
        bottom_line_html = (
            f'<p class="lede bottom-line"><strong>Bottom line:</strong> '
            f'{moderate_pct}% chance of at least a moderate El Niño this winter, '
            f'{magn_pct}% chance of a 1997 / 2015-magnitude event.</p>'
        )

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

    # Caveat numbers. v1.5: `headline` is the smoothed estimator output and
    # no longer carries lo/hi; fetch the CPC anchor's bootstrap range
    # separately for the +2.5 caveats. Smoothed mid + deflection come from
    # the headline dict.
    anchor_with_range = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27", offset=offset)
    cpc_25_lo = anchor_with_range["9715_>2.5"]["lo"]
    cpc_25_hi = anchor_with_range["9715_>2.5"]["hi"]
    smoothed_25_mid = headline["9715_>2.5"]["mid"]
    smoothed_25_def = headline["9715_>2.5"].get("deflection", 0)
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
  {bottom_line_html}
'''

    def _prev_mid(key: str):
        # Ladder delta uses the MoM headline (28+ days back, same methodology
        # version). prev_headline (WoW) is reserved for Analyst observers.
        if not prev_headline_month:
            return None
        return (prev_headline_month.get(key) or {}).get("mid")

    ladder_html = (
        '<section><div class="ladder">'
        + _render_rung("magn",     "+2.5°C peak", headline["9715_>2.5"],
                       "1997 / 2015 magnitude", _prev_mid("9715_>2.5"))
        + _render_rung("super",    "+2.0°C peak", headline["super_>2.0"],
                       "Very strong / super",   _prev_mid("super_>2.0"))
        + _render_rung("strong",   "+1.5°C peak", headline["strong_>1.5"],
                       "Strong",                _prev_mid("strong_>1.5"))
        + _render_rung("moderate", "+1.0°C peak", headline["moderate_>1.0"],
                       "At least moderate",     _prev_mid("moderate_>1.0"))
        + '</div>'
        + f'<p class="buckets-note">Probabilities use the v1.5 smoothed estimator: a CPC-derived '
          f'anchor ({offset_phrase}, skew-normal fit on the nine-bin strength table) plus a '
          f'bounded SEAS5 deflection (W = 0.2, capped at ±10 pp per bucket per week). Deltas next '
          f'to each percentage compare to the issue four weeks prior, aligned with CPC\'s monthly '
          f'issuance cadence; weeks where no comparable prior exists (early issues, methodology '
          f'version changes) show no delta. Full estimator math on the '
          f'<a href="{h(methodology_href)}">methodology page</a>.</p>'
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
        f'<li>The CPC anchor for the +2.5°C bucket carries a {cpc_25_lo}–{cpc_25_hi}% range. It '
        f'comes from a bootstrap that perturbs CPC\'s published bin probabilities by Gaussian '
        f'noise (sigma 1 percentage point, matching CPC\'s whole-percent reporting precision) and '
        f'refits the skew-normal each time. The range reflects reporting-quantization uncertainty '
        f'in CPC\'s table, not underlying forecast uncertainty. The smoothed headline '
        f'({smoothed_25_mid}%) sits above this anchor range because the bounded SEAS5 deflection '
        f'(+{smoothed_25_def}pp this issue) lifts it.</li>'
        f'<li>ECMWF SEAS5 vs CPC anchor on the upper tail above +2.5°C trad ONI: SEAS5 has '
        f'{seas5_25_n}/{seas5_n} members ({seas5_25_pct}%) at {h(seas5_calendar)} (max available '
        f'lead); the CPC anchor lands at {cpc_25_lo}–{cpc_25_hi}%. The v1.5 smoothing absorbs 20% '
        f'of this gap (capped at ±10pp/week), moving the smoothed headline to {smoothed_25_mid}%. '
        f'We subtract SEAS5\'s own model climatology, which removes its known ENSO warm bias; an '
        f'observational-climatology subtraction would put SEAS5 higher still. For broader context, '
        f'multi-model pools (e.g., the <a href="https://dashboard.theclimatebrink.com/#enso">'
        f'Climate Brink dashboard</a>\'s 13-model 637-member view) currently report a meaningfully '
        f'higher probability for the same threshold; the gap reflects CPC\'s analyst-correction vs '
        f'raw multi-model breadth, documented as methodology limitation #7.</li>'
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
        f'<p class="footer-meta" style="margin-top:18px;">By '
        f'<a href="{h(AUTHOR_CONTACT_URL)}"><strong style="color:var(--text)">{h(AUTHOR_NAME)}</strong></a>. '
        f'Source on <a href="{h(GITHUB_REPO_URL)}">GitHub</a>.</p>'
        f'<p class="footer-meta" style="margin-top:6px;">'
        f'Licensed <a href="{h(LICENSE_URL)}">{h(LICENSE_NAME)}</a>. '
        f'Cite as: Lepik, K. (2026). El Niño Tracker. '
        f'<a href="{h(PAGES_BASE_URL)}/">kristjanlepik-commits.github.io/el-nino-tracker</a>. '
        f'Free to share and quote with attribution; commercial reuse requires permission.'
        f'</p>'
        '</footer>'
    )

    impacts_html = build_impacts_html_block(load_impacts(), world_map_href=world_map_href)

    # ----------- Analyst section -----------
    # "What's interesting this week" — six observers, each fires only when
    # its condition is met. Section is omitted entirely on quiet weeks.
    # Lives directly under the ladder so a reader who sees the headline
    # numbers gets "what changed / what does it mean" before scrolling.
    analyst_obs: list[str] = []
    prev_cpc_issued = (prev_snapshot or {}).get("cpc_strength", {}).get("issued")
    prev_cpc_table = (prev_snapshot or {}).get("cpc_strength", {}).get("table", {})
    cpc_table_full = fetched.get("cpc_strength", {}).get("table", {})
    super_cur = headline.get("super_>2.0", {})
    super_prev = (prev_headline or {}).get("super_>2.0", {})

    # 1. CPC re-issued the strength table this week
    if (prev_cpc_issued and cpc_issued
            and str(cpc_issued) != str(prev_cpc_issued)):
        cur_anchor = super_cur.get("anchor")
        prev_anchor = super_prev.get("anchor")
        if cur_anchor is not None and prev_anchor is not None:
            delta = cur_anchor - prev_anchor
            sign = "+" if delta >= 0 else "−"
            analyst_obs.append(
                f"<strong>CPC re-issued the strength table.</strong> "
                f"The super (>+2.0°C) anchor moved from {prev_anchor}% to "
                f"{cur_anchor}% ({sign}{abs(delta)}pp). First CPC issuance "
                f"since the previous brief; the smoothed headline updates "
                f"accordingly."
            )

    # 2. CPC ↔ SEAS5 convergence (deflection was near cap, now shrank)
    cur_defl = super_cur.get("deflection")
    prev_defl = super_prev.get("deflection")
    if (cur_defl is not None and prev_defl is not None
            and prev_defl >= 8 and cur_defl < prev_defl - 2):
        cur_anchor = super_cur.get("anchor")
        prev_anchor = super_prev.get("anchor")
        analyst_obs.append(
            f"<strong>CPC and SEAS5 converged.</strong> "
            f"Last week the smoothed super bucket was being pulled up by a "
            f"SEAS5 deflection of +{prev_defl:.1f}pp (near the +10pp weekly "
            f"cap). This week the deflection is +{cur_defl:.1f}pp — CPC's "
            f"anchor moved up from {prev_anchor}% to {cur_anchor}%, closing "
            f"most of the gap with what SEAS5 had been pointing at."
        )

    # 3. DJF 2026-27 in CPC's table for the first time
    if ("DJF 2026-27" in cpc_table_full
            and "DJF 2026-27" not in prev_cpc_table):
        djf_super = cpc_table_full.get("DJF 2026-27", {}).get(">=2.0")
        if djf_super is not None:
            analyst_obs.append(
                f"<strong>First direct DJF 2026-27 read from CPC.</strong> "
                f"CPC's strength table now includes the peak season directly. "
                f"Super (≥+2.0 RONI) on the direct DJF read: {djf_super}%. "
                f"Brief still anchors on NDJ for continuity; switching to DJF "
                f"is queued as a separate methodology decision."
            )

    # 4. Heat content above both Godzilla analogs at this calendar week
    hc_val = phys.get("heat_content_0_300m_estimate")
    hc97 = analog_same.get("1997_apr_heat_content")
    hc15 = analog_same.get("2015_apr_heat_content")
    if (hc_val is not None and hc97 is not None and hc15 is not None
            and hc_val > max(hc97, hc15)):
        analyst_obs.append(
            f"<strong>Subsurface heat ahead of both Godzilla analogs.</strong> "
            f"0–300 m heat content anomaly is now {hc_val:+.2f}°C, vs "
            f"{hc97:+.1f}°C in 1997 and {hc15:+.1f}°C in 2015 at the same "
            f"calendar week — running ahead of either super-event analog at "
            f"this stage of development."
        )

    # 5. CWWA divergence (wind forcing lagging while ocean runs hot)
    sst_cur = phys.get("nino34_weekly_traditional")
    if (cwwa_value is not None and cwwa_97 is not None and cwwa_15 is not None
            and cwwa_value < min(cwwa_97, cwwa_15) * 0.6
            and sst_cur is not None and sst_cur >= 0.5
            and hc_val is not None and hc_val >= 1.0):
        analyst_obs.append(
            f"<strong>Wind forcing has not kept pace.</strong> "
            f"CWWA this week ({cwwa_value:.0f}) is well below both super-event "
            f"analogs (1997: {cwwa_97:.0f}, 2015: {cwwa_15:.0f}), even as SST "
            f"and subsurface heat run hot. Recent warming is being driven more "
            f"by accumulated subsurface heat (residual Kelvin-wave propagation) "
            f"than by ongoing wind events."
        )

    # 6. Strongest WWB peak in super-event territory
    wwb_events = phys.get("wwb_events_detail") or []
    wwb_analogs = phys.get("wwb_analogs") or {}
    if wwb_events and wwb_analogs:
        top_event = max(wwb_events, key=lambda e: e.get("peak_ms") or 0)
        current_peak = top_event.get("peak_ms") or 0
        if current_peak > 0:
            def _season_peak(year):
                seasons = wwb_analogs.get(year) or wwb_analogs.get(str(year)) or []
                peaks = [(e.get("peak_ms") or 0) for e in seasons]
                return max(peaks) if peaks else None
            p97 = _season_peak(1997)
            p15 = _season_peak(2015)
            if p97 is not None and p15 is not None:
                pd = top_event.get("peak_date", "")
                date_clause = f" on {pd}" if pd else ""
                analyst_obs.append(
                    f"<strong>Strongest WWB already in super-event territory.</strong> "
                    f"2026's strongest westerly wind burst peaks at "
                    f"{current_peak:.1f} m/s{date_clause} — vs full-season peaks "
                    f"of {p97:.1f} (1997) and {p15:.1f} (2015). Peak amplitude "
                    f"is super-event-aligned even though cumulative wind energy "
                    f"is lagging."
                )

    if analyst_obs:
        items_html = "".join(f"<li>{obs}</li>" for obs in analyst_obs)
        analyst_html = (
            '<section class="analyst-read">'
            '<h2>What\'s interesting this week</h2>'
            '<p class="section-sub">Observations from this week\'s data, '
            'beyond what the headline numbers say.</p>'
            f'<ul>{items_html}</ul>'
            '</section>'
        )
    else:
        analyst_html = ''

    return (head + ladder_html + analyst_html + chart_html + physical_html
            + impacts_html + sources_html + caveats_html + footer_html
            + '\n</main>\n</body>\n</html>\n')


DOCS_DIR = Path(__file__).parent / "docs"
# brief_dir and docs_brief_dir are computed inside main() so they can be
# overridden by --date and --preview CLI args.


def _wwb_analyst_read(current_events: list[dict], analogs: dict,
                      analog_counts_to_date: dict[int, int]) -> str:
    """Build a data-driven analyst summary of the WWB diagnostic row.

    The framing: peak amplitude carries the operational signal, not raw
    event count. After the v1.7 peak-detection algorithm the count metric
    is more comparable across years than v1.6, but peak amplitude remains
    the cleanest single number.

    Returns a multi-paragraph markdown block; empty string if there is not
    enough data to anchor a read.
    """
    if not current_events or not analogs:
        return ""

    # Strongest peak in current year to date, and date of that peak
    curr_peak = max(float(e.get("peak_ms", 0.0)) for e in current_events)
    curr_peak_date = next(
        (e.get("peak_date") or e.get("start", "") for e in current_events
         if float(e.get("peak_ms", 0.0)) == curr_peak), ""
    )

    # Full-season peak amplitude for each analog year
    analog_peaks: dict[int, float] = {}
    for yr_key, evs in (analogs or {}).items():
        try:
            yr = int(yr_key)
        except (TypeError, ValueError):
            continue
        if not evs:
            analog_peaks[yr] = 0.0
            continue
        analog_peaks[yr] = max(float(e.get("peak_ms", 0.0)) for e in evs)
    if not analog_peaks:
        return ""

    super_peers = {y: p for y, p in analog_peaks.items() if y in (1997, 2015)}
    weaker_peers = {y: p for y, p in analog_peaks.items() if y in (2023, 2025)}
    super_min = min(super_peers.values()) if super_peers else None
    weaker_max = max(weaker_peers.values()) if weaker_peers else None

    lines = []
    lines.append("**Analyst read on WWB row (v1.7).**")

    # Peak-amplitude framing
    peer_str = ", ".join(
        f"{y}: {analog_peaks[y]:.1f} m/s"
        for y in sorted(analog_peaks.keys())
    )
    lines.append(f"Peak amplitude is the primary signal in this row, not the "
                 f"count. 2026's strongest burst to date peaks at "
                 f"{curr_peak:.1f} m/s (peak day {curr_peak_date}). "
                 f"Full-season peaks for the analog years: {peer_str}.")

    # Interpretive paragraph based on where curr_peak lands
    if super_min is not None and weaker_max is not None:
        if curr_peak >= super_min * 0.7:
            lines.append(f"This lands in super-event territory: 2026's first "
                         f"burst is comparable in magnitude to 1997 and 2015 "
                         f"first bursts, well above what 2023 (sub-event El "
                         f"Niño) and 2025 (neutral / La Niña) produced. "
                         f"Peak amplitude is the strongest quantitative "
                         f"evidence to date that 2026's forcing is "
                         f"structurally aligned with the super-event analogs "
                         f"rather than the weaker recent analogs.")
        elif curr_peak >= weaker_max:
            lines.append(f"This sits between the super-event peers and the "
                         f"weaker analogs. Forcing is materially stronger than "
                         f"2023 or 2025 but has not yet produced a single "
                         f"burst of 1997 or 2015 magnitude. Watch the next "
                         f"4-8 weeks for whether a follow-up burst extends "
                         f"the peak.")
        else:
            lines.append(f"This is weaker than both super-event analogs and "
                         f"within the range of the weaker analog years. "
                         f"Peak-amplitude evidence is not currently supporting "
                         f"the super-event trajectory; the structural-similarity "
                         f"case rests on heat content and Kelvin-wave evidence.")

    # Count framing with v1.7 caveat
    counts_str = ", ".join(
        f"{y} ({analog_counts_to_date[y]})"
        for y in sorted(analog_counts_to_date.keys())
    )
    lines.append(f"On count: 2026 has {len(current_events)} event"
                 f"{'s' if len(current_events) != 1 else ''} so far; analogs at "
                 f"the same calendar date: {counts_str}. v1.7's peak-detection "
                 f"algorithm with a 10-day recovery interval splits sustained "
                 f"westerly periods into distinct bursts where v1.6 collapsed "
                 f"them. The count is now reasonably comparable across years, "
                 f"but peak amplitude remains the cleaner single number.")
    return "\n\n".join(lines)


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

    # v1.5: smoothed headline (CPC anchor + bounded SEAS5 deflection).
    # Internal brief reports both anchor and smoothed; public template
    # decides on its own how to display these.
    seas5_per_lead = fetched.get("ecmwf_seas5", {}).get("per_lead", []) or []
    smoothed = probs.smoothed_headline_buckets(
        fetched["cpc_strength"]["table"], seas5_per_lead,
        "NDJ 2026-27", offset=offset)

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
        s = smoothed.get(key, {})
        smoothed_pct = s.get("mid")
        anchor_pct = s.get("anchor")
        deflection = s.get("deflection")
        if smoothed_pct is not None and anchor_pct is not None:
            if abs(deflection or 0) >= 0.5:
                md.append(f"- **{label}**: {smoothed_pct}% "
                          f"(CPC anchor {anchor_pct}%, SEAS5 deflection "
                          f"{deflection:+.1f} ppt)")
            else:
                md.append(f"- **{label}**: {smoothed_pct}%")
        else:
            md.append(f"- {fmt_bucket(label, headline[key])}")
    md.append("")
    md.append("Headline values use the v1.5 smoothed estimator: CPC anchor "
              "(monthly cadence) plus a bounded weekly deflection from the "
              "SEAS5 ensemble (weight 0.2, capped at ±10 ppt per bucket per "
              "week). The anchor and deflection are shown alongside the "
              "smoothed value where they differ. See methodology.html for "
              "the full rule.")
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
                  f"1991-2020 same-calendar-day climatology. {ranking} "
                  f"Caveat: CWWA is a cumulative-area-mean metric and "
                  f"systematically understates transient localized westerly "
                  f"wind bursts, including those occurring just outside the "
                  f"5N-5S band. A short intense burst can generate a "
                  f"downwelling Kelvin wave that does substantial physical "
                  f"work even when it barely moves the cumulative integral. "
                  f"For the operational read on whether ENSO development is "
                  f"on track, the surfacing-Kelvin-wave evidence in heat "
                  f"content (above) is at least as informative as this "
                  f"metric. See the WWB row below for the spatial-peak "
                  f"event count and analyst read (v1.7, complementary "
                  f"to CWWA).")
    else:
        md.append(f"**CWWA note:** {phys.get('wwe_qualitative', '')}")
    md.append("")

    # Spatial-peak WWB row (methodology v1.7, complement to CWWA)
    wwb_count = phys.get("wwb_events_since_mar1")
    wwb_analogs_raw = phys.get("wwb_analogs", {})
    wwb_events_detail = phys.get("wwb_events_detail", []) or []
    if wwb_count is not None:
        # Filter analog events to those that started on or before today's
        # calendar date in each respective year (so 1997 events Mar 1 to
        # May 11 in this run, etc.)
        target_md = (wwe_fresh.get("issued") or "")[5:]
        analog_counts: dict[int, int] = {}
        for yr_key, events in (wwb_analogs_raw or {}).items():
            try:
                yr = int(yr_key)
            except (TypeError, ValueError):
                continue
            if not target_md:
                analog_counts[yr] = len(events)
            else:
                analog_counts[yr] = sum(
                    1 for e in events if e.get("start", "")[5:] <= target_md
                )
        analog_str = ", ".join(
            f"{y} ({analog_counts[y]})" for y in sorted(analog_counts)
        )
        md.append(f"**WWB events (spatial-peak detection, v1.7):** "
                  f"{wwb_count} westerly wind burst event"
                  f"{'s' if wwb_count != 1 else ''} detected since Mar 1, "
                  f"2026. Detection: sliding 5x10 deg sub-region area-mean "
                  f"anomaly over 10N-10S, 130E-150W; dual threshold (5 m/s "
                  f"sustained for at least 5 days, peak day above 7 m/s) "
                  f"with peak-detection plus a 10-day recovery interval "
                  f"between events. Analogs (events to same calendar date): "
                  f"{analog_str}.")
        for e in wwb_events_detail:
            peak_date = e.get("peak_date")
            peak_str = f", peak day {peak_date}" if peak_date else ""
            md.append(f"  - {e.get('start')} to {e.get('end')}, "
                      f"{e.get('duration_days')} days, peak "
                      f"{e.get('peak_ms')} m/s{peak_str}")
        md.append("")
        # Analyst Read block for the WWB row
        wwb_read = _wwb_analyst_read(wwb_events_detail,
                                     wwb_analogs_raw, analog_counts)
        if wwb_read:
            md.append(wwb_read)
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
                f"| [{d}]({d}/) | {mod}% | {strong}% | {sup}% | {magn}% |"
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
    parser = argparse.ArgumentParser(
        description="Generate the weekly El Niño brief.")
    parser.add_argument(
        "--force", action="store_true",
        help=("Overwrite this week's archive even if it already exists. "
              "Default behavior preserves any existing briefs/YYYY-MM-DD/ "
              "and docs/briefs/YYYY-MM-DD/ as published; methodology or "
              "prose changes only land in subsequent issues."),
    )
    parser.add_argument(
        "--date",
        help=("Target brief date in YYYY-MM-DD form. Defaults to today's "
              "most-recent Monday (the production cron behavior). Useful "
              "with --preview to render a future Monday's brief from "
              "current live data."),
    )
    parser.add_argument(
        "--preview", action="store_true",
        help=("Preview mode. Writes to briefs/<date>-preview/ instead of "
              "briefs/<date>/, skips docs/ regeneration, skips snapshot "
              "save, and bypasses the archive-immutability check. Use to "
              "see how a future Monday's brief would look from current "
              "live data without disturbing the production archive or "
              "the diffing snapshot history."),
    )
    args = parser.parse_args()

    # Resolve target brief date. Monkey-patch sources.BRIEF_DATE so that
    # downstream functions reading S.BRIEF_DATE (snapshot.current_snapshot,
    # build_markdown header, render_html title, build_public_html, etc.)
    # see the override without needing function-signature changes.
    if args.date:
        S.BRIEF_DATE = date.fromisoformat(args.date)
    date_iso = S.BRIEF_DATE.isoformat()

    # Output directories. Preview mode lands at briefs/<date>-preview/ so
    # it cannot collide with the production briefs/<date>/ artifact.
    brief_dir = Path(__file__).parent / "briefs" / (
        f"{date_iso}-preview" if args.preview else date_iso
    )
    docs_brief_dir = DOCS_DIR / "briefs" / date_iso

    # Archive immutability: once a Monday's brief is written, it stays
    # that Monday's brief. Methodology improvements, prose tweaks, or
    # any other changes apply only to subsequent issues. The first run
    # for a given Monday (typically the cron at 13:00 UTC) wins; later
    # within-week regenerations are a no-op unless --force is passed.
    # Preview mode bypasses this check (preview output is always
    # regenerated and never overwrites the production archive).
    if not args.preview:
        archive_marker = docs_brief_dir / "index.html"
        if archive_marker.exists() and not args.force:
            print(f"Archive {docs_brief_dir.relative_to(Path(__file__).parent)} "
                  f"exists and is preserved as published.")
            print(f"Methodology / prose changes apply to subsequent issues. "
                  f"Pass --force only when explicitly fixing a published archive.")
            return

    brief_dir.mkdir(parents=True, exist_ok=True)
    if not args.preview:
        docs_brief_dir.mkdir(parents=True, exist_ok=True)

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
    analog.plot(str(brief_dir / "analog.png"),
                cwwa_data=cwwa_data,
                seas5_per_lead=fetched.get("ecmwf_seas5", {}).get("per_lead"),
                current_develop_year=S.BRIEF_DATE.year,
                today_offset=today_offset,
                live_oni_by_year=live_oni_by_year)

    # 3. Snapshot current inputs and diff against last issue. The
    # snapshot file is the source of truth for next week's diff, so we
    # do NOT write it in preview mode (a preview run otherwise
    # corrupts the production diff history).
    snap = snapshot.current_snapshot(fetched)
    prev = snapshot.load_prior_snapshot(before=S.BRIEF_DATE)
    d = snapshot.diff(prev, snap)
    diff_md = snapshot.render_diff_markdown(d)
    if not args.preview:
        snap_path = snapshot.save_snapshot(snap)
        print(f"snapshot: {snap_path}")
    else:
        print("(preview) snapshot not saved")

    # 4. Auto-generate the Analyst Read prose (internal only)
    import editorial
    offset = fetched.get("roni_to_oni_offset", {}).get("value", S.RONI_TO_ONI_OFFSET)
    headline = probs.cpc_headline_with_uncertainty(
        fetched["cpc_strength"]["table"], "NDJ 2026-27", offset=offset)
    # v1.5: smoothed headline (CPC anchor + bounded SEAS5 deflection) for
    # the public ladder and the archive meta.json. Internal build_markdown
    # computes its own smoothed locally; we keep the legacy `headline`
    # variable above so editorial.generate keeps its current input shape.
    seas5_per_lead = fetched.get("ecmwf_seas5", {}).get("per_lead", []) or []
    headline_smoothed = probs.smoothed_headline_buckets(
        fetched["cpc_strength"]["table"], seas5_per_lead,
        "NDJ 2026-27", offset=offset)
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
    out_md = brief_dir / "brief.md"
    out_md.write_text(md_text)
    print(f"wrote: {out_md}")
    out_html = brief_dir / "brief.html"
    out_html.write_text(render_html(md_text))
    print(f"wrote: {out_html}")
    print(f"wrote: {brief_dir / 'analog.png'}")

    # In preview mode we stop here: docs/ regeneration and archive
    # index are production-side concerns we don't want to disturb.
    if args.preview:
        print(f"(preview) docs/ regeneration skipped; "
              f"preview output at briefs/{brief_dir.name}/")
        return

    # 6. Public brief: structured-HTML render (bypasses markdown for the public
    #    path). Different methodology_href and og_image_url for index vs archive
    #    so links/social cards resolve correctly from each location.
    # Load the previous week's headline_smoothed structure from the most
    # recent prior archive meta.json. Enables the Analyst section observers
    # that compare this week to last (CPC reissue delta, convergence).
    prev_headline_smoothed = _load_prev_headline_smoothed(S.BRIEF_DATE)
    # MoM (version-aware) drives the ladder delta. None when the 4-week
    # comparison would cross a methodology-version bump or no archive exists.
    prev_headline_smoothed_month = _load_month_prior_headline_smoothed(S.BRIEF_DATE)

    archive_rel = f"briefs/{S.BRIEF_DATE.isoformat()}/"
    public_html_index = build_public_html(
        fetched, freshness, headline_smoothed,
        methodology_href="methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/",
        og_image_url=f"{PAGES_BASE_URL}/analog.png",
        world_map_href="world-map.svg",
        prev_headline=prev_headline_smoothed,
        prev_snapshot=prev,
        prev_headline_month=prev_headline_smoothed_month,
    )
    public_html_archive = build_public_html(
        fetched, freshness, headline_smoothed,
        methodology_href="../../methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/{archive_rel}",
        og_image_url=f"{PAGES_BASE_URL}/{archive_rel}analog.png",
        world_map_href="../../world-map.svg",
        prev_headline=prev_headline_smoothed,
        prev_snapshot=prev,
        prev_headline_month=prev_headline_smoothed_month,
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").touch()
    (DOCS_DIR / "index.html").write_text(public_html_index)
    print(f"wrote: {DOCS_DIR / 'index.html'}")
    # Write as index.html so GitHub Pages serves the brief on the bare
    # directory URL (briefs/YYYY-MM-DD/) without a 404.
    (docs_brief_dir / "index.html").write_text(public_html_archive)
    print(f"wrote: {docs_brief_dir / 'index.html'}")
    shutil.copyfile(brief_dir / "analog.png", DOCS_DIR / "analog.png")
    shutil.copyfile(brief_dir / "analog.png", docs_brief_dir / "analog.png")
    (docs_brief_dir / "meta.json").write_text(json.dumps({
        "date": S.BRIEF_DATE.isoformat(),
        # methodology_version pinned per-issue so the MoM delta loader can
        # detect version mismatches across the 4-week comparison window
        # and hide the delta when headlines are not strictly comparable.
        "methodology_version": str(S.METHODOLOGY_VERSION),
        # v1.5: full smoothed structure (mid + anchor + seas5 + deflection
        # per bucket) so the archive index AND any future audit can
        # reconstruct the headline math from this single artifact.
        "headline_buckets": headline_smoothed,
    }, indent=2))
    print(f"wrote: {docs_brief_dir / 'meta.json'}")

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
