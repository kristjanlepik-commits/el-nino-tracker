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
from datetime import date, timedelta
from html import escape as h
import json
import re
import shutil
from pathlib import Path

import markdown as md_lib

import sources as S
import tokens as T
T_LADDER = T.LADDER
import probs
import analog
import snapshot


PAGES_BASE_URL = "https://thelongswell.com"
# Analytics (platform-owned seam; D-020). Plausible is cookieless and
# stores no personal data, so no consent banner is required and the
# page stays clean. Public pages only: never the internal brief, which
# is emailed. Set ANALYTICS_SNIPPET = "" to disable site-wide.
#
# This is Plausible's current site-specific form, copied from the
# install screen for thelongswell.com. The id in the filename is a
# public site identifier, not a secret; it is visible in page source
# by design. Outbound links, file downloads and form submissions are
# enabled in the account, and that config ships inside the served
# script rather than as attributes here.
#
# The inline block is REQUIRED, not decoration: the served script ends
# with `plausible.o && S(plausible.o)`, so it initializes only if the
# options object was set first, and it drains a `plausible.q` queue for
# calls made before the async file lands. Deleting it silently records
# nothing. Plain string, not an f-string, because the JS is full of
# braces.
ANALYTICS_SITE_ID = "pa-UzORTw8rlmViOEWGoqLYK"
ANALYTICS_SNIPPET = (
    "<!-- Privacy-friendly analytics by Plausible -->\n"
    f'<script async src="https://plausible.io/js/{ANALYTICS_SITE_ID}.js">'
    "</script>\n"
    "<script>\n"
    "window.plausible=window.plausible||function()"
    "{(plausible.q=plausible.q||[]).push(arguments)},"
    "plausible.init=plausible.init||function(i){plausible.o=i||{}};\n"
    "plausible.init()\n"
    "</script>"
)

# EMAIL CAPTURE (D-088). Passed to templates/subscribe.py's
# `render_subscribe(form_embed=...)`, whose docstring already names this
# as platform's to supply and renders an explanatory slot when it is
# empty. Design defined that interface; this fills it.
#
# TWO PLACEMENTS ONLY, form on the front page and /subscribe, with a
# LINK everywhere else. That is not a design preference, it is the whole
# reason this is one constant rather than four: the surfaces that
# multiply are the channel indexes, one brief a week forever and roughly
# ninety-six Notes a year, and a third-party script on all of those runs
# for every visitor. A link costs nothing and a reader at the bottom of a
# brief has already selected themselves.
#
# There is no plain HTML form alternative. Product checked the Beehiiv
# dashboard: the subscribe-form product emits only this loader plus
# attribution tracking, and the v2 API needs a Bearer key that cannot go
# in client-side HTML. So placement is the only lever available.
#
# Invisible to the analytics guard, which counts the literal string
# "plausible.io/js" and expects exactly one (scripts/publish_all.py).
# Checked rather than assumed.
EMAIL_CAPTURE_FORM_ID = "9782858"
EMAIL_CAPTURE_ACTION = (
    f"https://app.kit.com/forms/{EMAIL_CAPTURE_FORM_ID}/subscriptions")


# The subscribe page has its own stylesheet, so this lives in one
# constant read by both rather than being pasted twice. Two copies of
# a form style is how the front page and /subscribe drifted apart the
# first time, when only one of them had a width rule.
EMAIL_FORM_CSS = """  /* The form is ours now, so the note above is history: there is no
     iframe and no fixed button width, and the input can be told to give
     up its space last rather than first. The failure it describes is
     structurally unavailable here. */
  .ec-form { display: flex; gap: 8px; flex-wrap: wrap; }
  .ec-lab {
    position: absolute; width: 1px; height: 1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap;
  }
  .ec-in {
    flex: 1 1 200px; min-width: 0;
    font-family: var(--sans); font-size: 16px;   /* 16px: iOS zooms below it */
    color: var(--ink); background: var(--paper);
    border: 1.4px solid var(--ink); border-radius: 0;
    padding: 11px 12px; -webkit-appearance: none;
  }
  .ec-in::placeholder { color: var(--ink-faint); }
  .ec-in:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  .ec-sub {
    flex: 0 0 auto;
    font-family: var(--mono); font-size: 10.5px;
    letter-spacing: .18em; text-transform: uppercase;
    color: var(--paper); background: var(--ink);
    border: 1.4px solid var(--ink); border-radius: 0;
    padding: 12px 20px; cursor: pointer;
  }
  .ec-sub:hover { background: var(--ink-soft); border-color: var(--ink-soft); }
  .ec-sub:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  @media (max-width: 420px) {
    /* Full width both, rather than a button squeezing the field. The
       field is the control that has to be legible while typing. */
    .ec-in, .ec-sub { flex: 1 1 100%; }
  }
"""


def email_capture_form(label="Subscribe", cls="ec-form"):
    """A real form. No iframe, no third-party script, our own markup.

    EVERY CONSTRAINT ABOVE CAME FROM THE IFRAME, so read the note above as
    history rather than as rules. Beehiiv had no plain-HTML form, which is
    why placement was the only lever and why the front page ended up with a
    link: the embed measured absent on three of four cold loads, and when
    it did arrive it was a white panel on bone paper with our wordmark
    repeated inside it in a different serif and an input clipped to one
    character at 300px, none of it reachable from our CSS.

    Kit posts natively to the action below. Their own embed puts a
    ck.5.js above it; product confirmed it is optional enhancement, so it
    is dropped and the page carries ZERO third-party assets, which is
    better than the two-placement compromise was ever going to be.

    So the compromise is reversed rather than relaxed: the form goes
    everywhere the link went, because the cost it was protecting against
    was a script running on every surface that multiplies, and there is
    no script.

    STILL PROHIBITED, and not by the provider: no modal, no exit-intent,
    no sticky bar, no slide-in. Product chose Kit's inline format so those
    are not available to reach for later.

    Double opt-in is on and auto-confirm off, so editor's "Confirmation
    email required" stays true. On submit Kit shows its own confirmation
    line; after the reader confirms, Kit redirects to /subscribed/.
    """
    return (
        '<!-- Email capture by Kit. Double opt-in; posts natively, no '
        'third-party script. -->\n'
        f'<form class="{cls}" action="{EMAIL_CAPTURE_ACTION}" method="post">'
        '<label class="ec-lab" for="ec-email">Email address</label>'
        '<input id="ec-email" class="ec-in" type="email" name="email_address" '
        'required autocomplete="email" placeholder="you@example.com">'
        f'<button class="ec-sub" type="submit">{label}</button>'
        '</form>'
    )


# Kept so the old constant name fails loudly rather than rendering nothing
# if anything still imports it.
EMAIL_CAPTURE_SNIPPET = email_capture_form()
# Editor's approved promise, accepted 2026-08-06 (D-091). Defined here
# rather than in templates/subscribe.py because the front page needs it
# too and subscribe.py already imports from this module, so this is the
# one direction that does not create a cycle. One string, two surfaces,
# no drift.
EMAIL_CAPTURE_PROMISE = (
    "We find climate signals in the data, and send you the ones that matter.")
GITHUB_REPO_URL = "https://github.com/kristjanlepik-commits/el-nino-tracker"
AUTHOR_NAME = "Kristjan Lepik"
AUTHOR_CONTACT_URL = "https://www.linkedin.com/in/kristjanlepik/"
LICENSE_NAME = "CC BY-NC 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"

# Brand (The Long Swell rebrand, 2026-07-26). The house sets in mono,
# products in serif; see tokens.py and research/handover_design.md.
# Channels, in display order. The masthead nav and the footer links both
# generate from this, so adding Floods is one edit rather than two.
# Unbuilt channels stay out entirely (D-ratified: hidden until they have
# something to show), which is why Floods and Damages are absent.
ELNINO_HREF = "elnino/"

def lead_sentence(ev) -> str:
    """Editor's approved lead, shared by the front page and the fires index.

    "For this week of the year, Greece burned at four and a half times
    its own record."

    Two things editor settled that the previous wording got wrong.

    THE BASIS IS STATED. "4.5x its previous record week" is ambiguous
    between a country's worst week ever and its worst EQUIVALENT week.
    It is the equivalent week: `prev_best` in fires/build_events.py is
    keyed by year over the same calendar week. The old sentence left a
    reader to carry the basis over from a preceding clause, which is the
    inference we stopped relying on this morning.

    IT LEADS WITH THE RECORD, NOT THE AVERAGE. Beating a record is a
    stronger kind of claim than exceeding an average, and the average
    multiple is closer in shape to the count we just removed from both
    surfaces. Editor's argument, and it is the better one.

    The record multiple is NOT emitted as a number; it exists only
    inside the `title` prose. Parsing prose to build a headline is the
    antipattern removed from the ECON ledger this morning, so this
    extracts defensively and returns "" rather than guessing when the
    shape changes. Fire has been asked for a numeric field.
    """
    import re as _re
    region = (ev or {}).get("region", "")
    m = _re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)x\b",
                  str((ev or {}).get("title", "")))
    if not (region and m):
        return ""
    return (f"For this week of the year, {region} burned at "
            f"{_spell_multiple(float(m.group(1)))} times its own record.")


def _spell_multiple(x: float) -> str:
    """Spell whole numbers and halves; fall back to the numeral.

    Editor wrote "four and a half". That is only generatable for values
    landing on .0 or .5, and a week at 4.3 has no comfortable spelling,
    so the numeral is the fallback rather than a forced word. Flagged to
    editor: this means the register varies week to week.
    """
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen", "twenty"]
    whole, frac = int(x), round(x - int(x), 2)
    if whole > 20 or frac not in (0.0, 0.5):
        return f"{x:g}"
    if frac == 0.0:
        return ones[whole]
    return f"{ones[whole]} and a half"


CHANNELS = [
    ("elnino", "El Ni\u00f1o", None),   # None: resolved to the channel home
    ("fire", "Fires", "fires/"),
    ("crop", "Crops", "crops/"),
    ("heat", "Heat", "heat/"),
    # NOTES IS NOT A CHANNEL and sits at the end of the run, next to About,
    # because it is the human-voice surface rather than an instrument.
    # Kristjan put it in the main nav on 2026-08-09, which reversed
    # product's scoping of the index: a nav item needs a destination, and
    # pointing it at a single Note breaks silently the moment there is a
    # second one, with the nav still resolving to the first piece forever.
    # So it points at /notes/, an index, even while that index has one row.
    ("notes", "Notes", "notes/"),
]

SITE_NAME = "The Long Swell"
# The product is event-scoped by D-001 and keeps its full name on its own
# masthead, in page titles and in the citation line. The nav carries a
# short label instead, for legibility. Do not collapse these into one
# constant: renaming the product is a brand decision, shortening a menu
# item is not.
PRODUCT_NAME = "El Niño 2026-27"
PRODUCT_NAV_LABEL = "El Niño"
# Display form of the site URL for citation lines. Derived so the
# platform chat's domain migration is a one-constant change.
DISPLAY_HOST = PAGES_BASE_URL.split("//", 1)[-1]
# Email capture (T10 retention layer). Empty string disables the block;
# the platform chat wires the real signup URL here.
EMAIL_SIGNUP_URL = ""

# The About page's independence and corrections copy was gated here
# pending ratification. Both are now resolved and the wording is inline
# in build_about_html, so the gates are gone.
#
# Worth keeping the reasoning: the first draft claimed "no funder, no
# advertising, no sponsored channel". Advertising is genuinely ruled out,
# but an anchor sponsor is priority 1 commercially at T8 and the working
# product framing is "Presented by [X]", so "no funder" would have been
# false the week a sponsor signed. The ratified copy claims independence
# as a firewall (independent publication, named editor, methodology
# reviewed externally) rather than as an absence of money, which is both
# true and durable. The corrections copy went the same way: "nothing is
# edited in place" was falsifiable from this repo's own history, and the
# ratified version promises less and survives an audit.


PUBLIC_SOURCE_NAMES = {
    "cpc_strength": "NOAA CPC strength table",
    "oisst_weekly": "NOAA OISST weekly Niño 3.4",
    "heat_content": "CPC 0-300m heat content",
    "iri": "IRI plume",
    "bom": "BoM ENSO Outlook",
    "ecmwf_seas5": "ECMWF SEAS5",
    "nmme": "NMME multi-model suite (incl. CFSv2)",
    "era5_wwe": "ERA5 cumulative westerly wind anomaly (CWWA)",
    # Added 2026-07-27. Both fetchers have been feeding published copy
    # while missing from this map, so the freshness grid printed their
    # raw variable names, "era5_burst" and "oni_history", among properly
    # named agencies. Wording is editor's to ratify; the entries stay
    # either way, because both drive published numbers and a provenance
    # block that omits an input is worse than one that names it plainly.
    "era5_burst": "ERA5 westerly wind burst events",
    "oni_history": "NOAA ONI historical record",
}


# The order the four published buckets appear in, most extreme first,
# defined once. The probability ladder and the archive trend used to
# hardcode this separately and had drifted into opposite directions:
# the ladder ran +3.5 down to +2.0, the archive ran +2.0 up to +3.5, so
# the same four numbers reversed as a reader moved between two pages.
#
# Open question, not mine to settle: whether most-extreme-first is the
# right lead. Reading order is a form of prominence, and the system
# rule is that prominence descends with claim strength, which is why
# the ladder's own rungs lose substance downward. Leading with +3.5
# means the first figure a reader meets is the least anchored one on
# the site, and the visual weight then increases as they read down,
# against the gradient. Flipping it is a one-line change here now.
BUCKET_ORDER = ["record_>3.5", "record_>3.0", "9715_>2.5", "super_>2.0"]
BUCKET_LABEL = {
    "record_>3.5": "> +3.5 °C",
    "record_>3.0": "> +3.0 °C",
    "9715_>2.5": "> +2.5 °C",
    "super_>2.0": "> +2.0 °C",
}


def public_preamble(methodology_href: str) -> str:
    return (
        "Weekly probability tracker for the developing 2026-27 El Niño event, "
        "built from the official ENSO outlooks (NOAA CPC, IRI, BoM) and a "
        "multi-model forecast consensus (ECMWF SEAS5 with the NMME suite) "
        "plus weekly Niño 3.4 observations. Numbers are reproduced from public "
        f"sources and recombined into a single set of peak-strength buckets; the "
        f"[methodology page]({methodology_href}) documents every step. Forecast "
        "disagreements are surfaced rather than averaged."
    )


# Reading-page stylesheet for markdown-rendered pages (methodology,
# archive index, internal brief). Same visual language as PUBLIC_CSS,
# reduced to prose needs. External reviewers read methodology.html, so
# it gets the same furniture as everything else.
_HTML_CSS_TEMPLATE = """
  :root {
/*VARS_LIGHT*/
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
/*VARS_DARK*/
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--paper); color: var(--ink);
    font-family: var(--serif); font-size: 17.5px; line-height: 1.62;
    -webkit-font-smoothing: antialiased;
  }
  /* The masthead here is the shared one, styled by SITE_MASTHEAD_CSS,
     which render_html adds alongside this block. Nothing masthead
     related belongs below, except lining its shell up with the reading
     column, which is narrower here than on the tracker pages. */
  :root { --shell-max: 820px; --shell-pad: 40px; }
  main { max-width: 820px; margin: 0 auto; padding: 40px 40px 80px; }
  h1 { font-size: clamp(32px, 4vw, 44px); font-weight: 500;
       letter-spacing: -0.018em; line-height: 1.10; margin: 0 0 20px; }
  h2 { font-size: 20px; font-weight: 500; line-height: 1.30;
       margin: 2.2em 0 10px; padding-bottom: 10px;
       border-bottom: 2px solid var(--ink); }
  h3 { font-size: 17.5px; font-weight: 500; margin: 1.8em 0 6px; }
  p, li { max-width: 62ch; }
  a { color: inherit; border-bottom: 1px solid var(--rule); text-decoration: none; }
  a:hover { color: var(--fire); border-bottom-color: var(--fire); }
  table { border-collapse: collapse; margin: 1.4em 0; width: 100%; font-size: 14px; }
  th, td { padding: 12px 12px 12px 0; text-align: left;
           border-bottom: 1px solid var(--rule); vertical-align: top; }
  thead th { font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.22em;
       text-transform: uppercase; color: var(--ink-faint); font-weight: 400;
       border-bottom: 2px solid var(--ink); }
  tbody tr:last-child td { border-bottom: 2px solid var(--ink); }
  blockquote { border-left: 3px solid var(--nino); margin: 1.2em 0;
               padding: 2px 0 2px 20px; color: var(--ink-soft); }
  code { font-family: var(--mono); font-size: 0.85em;
         background: var(--paper-sunk); padding: 2px 5px; }
  pre { background: var(--paper-sunk); padding: 14px 16px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  img { max-width: 100%; height: auto; display: block; }
  hr { border: none; border-top: 2px solid var(--ink); margin: 2.4em 0; }
  @media (max-width: 760px) {
    :root { --shell-pad: 20px; }
    main { padding-left: 20px; padding-right: 20px; }
    body { font-size: 17px; }
  }
""".strip()


def _week_mark_opacities(events: list[dict]) -> tuple:
    """Arc opacities for this week's mark, from the largest published
    multiple among event-channel items.

    The mark reports the week: how far the signal reaches is set by the
    biggest thing on the site. Stroke widths never move, only opacity,
    and the mark stays ink at every band (D-017). Event `stat` values
    look like "8.1x"; anything unparseable is ignored rather than
    guessed at.
    """
    best = 0.0
    for e in events or []:
        raw = str(e.get("stat", "")).strip().lower().rstrip("x")
        try:
            best = max(best, float(raw))
        except ValueError:
            continue
    opacities, _color = T.mark_band(best)
    return opacities


def _mark_svg(size: int = 26, opacities: tuple | None = None) -> str:
    """The propagation mark: a filled square (the source) and three arcs
    attenuating outward (the signal weakening as it travels).

    It inks in currentColor so it takes INK or PAPER from context, never
    a channel hue: the mark belongs to the house, not to a variable.
    `opacities` sets the three arcs from inner to outer, so the mark can
    report the week (see _week_mark_opacities); the default is the
    canonical resting ratio used on pages that do not know the week.
    Geometry per the visual language, viewBox 0 0 42 40.
    """
    o1, o2, o3 = opacities or (1.0, 0.45, 0.2)
    h_px = size
    w_px = round(size * 42 / 40)
    return (
        f'<svg width="{w_px}" height="{h_px}" viewBox="0 0 42 40" '
        f'fill="none" aria-hidden="true">'
        f'<rect x="4" y="14" width="12" height="12" fill="currentColor" '
        f'opacity="{o1:g}"/>'
        f'<path d="M19,8 A15,15 0 0 1 19,32" stroke="currentColor" '
        f'stroke-width="3" opacity="{o1:g}"/>'
        f'<path d="M28.4,8 A22,22 0 0 1 28.4,32" stroke="currentColor" '
        f'stroke-width="2.4" opacity="{o2:g}"/>'
        f'<path d="M36.4,8 A29,29 0 0 1 36.4,32" stroke="currentColor" '
        f'stroke-width="1.8" opacity="{o3:g}"/>'
        f'</svg>'
    )


def _favicon_links(root_prefix: str) -> str:
    return (
        f'<link rel="icon" href="{h(root_prefix)}favicon.svg" type="image/svg+xml">\n'
        f'<link rel="icon" href="{h(root_prefix)}favicon.ico" sizes="48x48">\n'
        f'<link rel="apple-touch-icon" href="{h(root_prefix)}apple-touch-icon.png">\n'
    )


def render_html(markdown_text: str, title: str = None,
                root_prefix: str = None,
                analytics: bool = False, nav_active: str = "elnino") -> str:
    """Markdown page in the house reading style.

    analytics defaults to False because this same helper renders the
    internal brief that gets emailed; a tracker belongs only on pages
    served from docs/, so public callers opt in. Platform owns that
    contract (D-020) and it is kept explicit rather than inferred from
    root_prefix.

    root_prefix is the relative path back to the docs root ("" for
    docs/methodology.html, "../" for docs/briefs/index.html); it wires
    the self-hosted fonts and favicon. None means a standalone render
    (internal briefs/ pages, emailed HTML) with no docs/ asset links;
    those fall back to the system font stacks.

    Public pages get the shared house masthead, not a reduced one. This
    page previously carried a "masthead-lite" with a brand and a link
    home and nothing else, which left methodology.html with no nav and
    no About: the same dead end the fire channel had, on the page a
    journalist is most likely to arrive at cold from a citation. Chrome
    is shared or it drifts, so there is one masthead and every public
    page carries it. nav_active defaults to the El Nino channel because
    methodology.md is that channel's document; a future markdown page
    on another channel passes its own key.
    """
    body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
    page_title = title or f"El Nino brief, {S.BRIEF_DATE.isoformat()}"
    head_assets = ""
    masthead = ""
    if root_prefix is not None:
        head_assets = (
            f"<style>{T.font_faces_css(root_prefix + 'fonts/')}</style>\n"
            + _favicon_links(root_prefix)
            + (f"{ANALYTICS_SNIPPET}\n" if analytics else "")
        )
        masthead = site_masthead(root_prefix, active=nav_active)
        head_assets += f"<style>{SITE_MASTHEAD_CSS}</style>\n"
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{page_title}</title>\n"
        f"{head_assets}"
        f"<style>{HTML_CSS}</style>\n"
        "</head><body>\n"
        f"{masthead}"
        "<main>\n"
        f"{body}\n"
        "</main>\n</body></html>\n"
    )


# Visual language v1.0 "Bulletin" (D-016). Token values come from
# tokens.py; the template below carries structure only. Curly braces
# are CSS-literal, so this is a plain string and not an f-string.
#
# The rules that outrank convenience: radius is 0, there are no shadows
# and no gradients, nothing is enclosed on four sides, and the only
# filled surface is PAPER_SUNK behind the tracker strip.
#
# Three rule weights, carrying the mark's own attenuation ratio so the
# site is recognizable from a cropped screenshot with no logo in frame:
#   3px   at full ink, opens a section or a list
#   2.4px at 45% ink,  divides items within a list
#   1px   at 20% ink,  divides rows within a table
# No other weights exist. The ratio is furniture only: it never appears
# on a mark that carries data, because concentric rings on a map marker
# would read as an epicenter, which is a causal claim.

# The house masthead, markup and the CSS it needs, as a pair. Any page
# on the site can carry it, not only the ones run_brief builds: the fire
# channel had to invent its own, which left it with no link home, no
# nav and no About, a dead end for anyone who landed there first.
SITE_MASTHEAD_CSS = """
  /* ---------- masthead ---------- */
  /* Self-contained: a page that does not include PUBLIC_CSS has no link
     reset, so the wordmark and nav arrived underlined on the fire page. */
  header.field a, header.field a:hover { text-decoration: none; }
  /* Nor does it carry the shell, which left the live fire masthead
     running edge to edge with no padding while its content sat centred
     at 760px. The defaults below are PUBLIC_CSS's own values, so on
     pages that include both this rule is a no-op whichever order they
     land in; a standalone page sets the two variables to match its own
     content column instead. */
  .field-shell {
    max-width: var(--shell-max, 1180px);
    margin: 0 auto;
    padding: 0 var(--shell-pad, 40px);
  }
  header.field { background: var(--paper); border-bottom: 3px solid var(--ink); }
  header.field::after { display: none; }
  .masthead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px 28px;
    flex-wrap: wrap;
    padding: 18px 0 16px;
  }
  /* Wordmark: the house sets in the prose face at natural fit, product
     names in tracked mono, so house and channels differ in kind. */
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand svg { display: block; flex: none; color: var(--ink); }
  .brand-name {
    font-family: var(--serif);
    font-size: 21px;
    font-weight: 500;
    letter-spacing: 0;
    color: var(--ink);
    white-space: nowrap;
  }
  .prodnav {
    display: flex;
    align-items: baseline;
    gap: 8px 22px;
    flex-wrap: wrap;
  }
  .prodnav a {
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--nino);
    transition: color .12s;
  }
  .prodnav a.ch-fire { color: var(--fire); }
  .prodnav a.ch-crop { color: var(--crop); }
  /* Heat gets NO hue. Section 7 retired channel colour and heat never had
     one, so its identity is type: the tracked mono against the Spectral
     wordmark. Without this rule it inherits the .prodnav default, which is
     var(--nino), and the heat channel renders in El Nino's blue. */
  .prodnav a.ch-heat { color: var(--ink); }
  .prodnav a.util { color: var(--ink-faint); letter-spacing: 0.16em; }
  .prodnav a:hover { color: var(--ink); }
""".strip()

_PUBLIC_CSS_TEMPLATE = """
  :root {
/*VARS_LIGHT*/
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
/*VARS_DARK*/
    }
  }
  :root[data-theme="dark"] {
/*VARS_DARK*/
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--paper);
    color: var(--ink);
    font-family: var(--serif);
    font-size: 17.5px;
    line-height: 1.62;
    -webkit-font-smoothing: antialiased;
  }
  a { color: inherit; text-decoration: none; }
  main a:not(.attr):not(.card-link),
  .foot-cite a, .src-list a, .buckets-note a, .section-sub a {
    border-bottom: 1px solid var(--rule);
    transition: color .12s, border-color .12s;
  }
  main a:hover, .foot-cite a:hover, .src-list a:hover,
  .buckets-note a:hover, .section-sub a:hover {
    color: var(--fire);
    border-bottom-color: var(--fire);
  }
  a:focus-visible, button:focus-visible {
    outline: 2px solid var(--nino);
    outline-offset: 3px;
  }
  p, li, td, th { text-wrap: pretty; }
  h1, h2, h3 { text-wrap: balance; margin: 0; font-weight: 500; }
  img { max-width: 100%; height: auto; display: block; }

  /* ---------- the six type steps, no more ---------- */
  .eyebrow, .issue-stamp, .rail-block .eyebrow, .foot-fresh-label,
  .break-head .eyebrow, .chan .meta, .ws-label {
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 400;
    line-height: 2.0;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  .num, td.num, .rung .pct, .ev-stat, .ws-num, .wow-delta,
  .src-list .src-issued, .footer-meta, .rail-block .val {
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
  }

  /* ---------- shell ---------- */
  .field-shell, .shell {
    max-width: 1180px;
    margin: 0 auto;
    padding: 0 40px;
  }
  .shell { padding-bottom: 8px; }

/*MASTHEAD_CSS*/
  /* ---------- lead block ---------- */
  .field, .wave-strip { background: var(--paper); color: var(--ink); }
  .field::after { display: none; }
  .hero, .issue-head { padding: 40px 0 0; }
  .hero-stamp, .issue-stamp {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    margin-bottom: 20px;
    color: var(--ink-faint);
  }
  .hero-stamp span:not(:last-child)::after,
  .issue-stamp span:not(:last-child)::after {
    content: " ·";
    color: var(--rule);
  }
  .issue-stamp a, .hero-stamp a { color: var(--ink-soft); }
  .hero h1, .issue-head h1 {
    font-size: clamp(34px, 4.2vw, 50px);
    line-height: 1.10;
    letter-spacing: -0.018em;
    margin: 0 0 18px;
    max-width: 24ch;
  }
  .hero .lede, .issue-head .lede {
    color: var(--ink-soft);
    font-size: 17.5px;
    line-height: 1.62;
    max-width: 48ch;
    margin: 0 0 28px;
  }
  .lede.bottom-line { color: var(--ink); margin-bottom: 36px; max-width: 56ch; }

  /* Readout: the figure is the subject of the block. Physical anomaly
     magnitude reads from the diverging scale, never a channel hue. */
  .readout {
    display: flex;
    align-items: flex-start;
    gap: 40px;
    flex-wrap: wrap;
    padding: 22px 0 0;
    border-top: 1px solid var(--rule);
  }
  .readout-main .v, .readout-side div .v {
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    line-height: 1.0;
    letter-spacing: -0.02em;
  }
  .readout-main .v { font-size: 40px; color: var(--nino); }
  .readout-main .v small { font-size: 20px; }
  .readout-side div .v { font-size: 24px; color: var(--ink); }
  .readout-side div .v small { font-size: 13px; }
  .readout-main .k, .readout-side div .k {
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.6;
    color: var(--ink-faint);
    margin-top: 8px;
    max-width: 28ch;
  }
  .readout-side { display: flex; gap: 32px; }

  /* ---------- the break: event list ---------- */
  .break-head { padding: 34px 0 0; display: flex; align-items: baseline; gap: 14px; }
  .break-lede {
    color: var(--ink-soft);
    font-size: 17.5px;
    max-width: 56ch;
    margin: 8px 0 4px;
  }
  .events { display: flex; flex-direction: column; padding: 20px 0 46px; }
  /* The fixed magnitude column is the point: a reader scanning it sees
     only sizes, which answers the house question before any prose. */
  .event {
    display: grid;
    grid-template-columns: 118px minmax(0, 1fr) auto;
    gap: 6px 24px;
    align-items: baseline;
    padding: 18px 0;
    border-bottom: 2.4px solid var(--rule-45);
  }
  .event:first-child { border-top: 3px solid var(--ink); }
  .event:last-child { border-bottom: 3px solid var(--ink); }
  .event .ev-stat {
    font-size: 40px;
    font-weight: 500;
    line-height: 1.0;
    letter-spacing: -0.02em;
    color: var(--fire);
    grid-column: 1;
    grid-row: 1;
  }
  .event .ev-body { grid-column: 2; grid-row: 1; }
  .event h3 { font-size: 20px; font-weight: 500; line-height: 1.30; }
  .event h3 .ev-region { font-weight: 500; }
  .event h3 .ev-claim { color: var(--ink-soft); font-weight: 400; }
  .event .ev-src {
    display: block;
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.75;
    color: var(--ink-faint);
    margin-top: 4px;
  }
  .event .attr { grid-column: 3; grid-row: 1; justify-self: end; }

  /* Vocabulary defined once, above the list it governs. Without it the
     page shows three bare chips in expert language to a reader who has
     never met the term "ENSO-loaded window". */
  .attr-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 26px;
    padding: 14px 0 16px;
    border-top: 1px solid var(--rule);
  }
  .attr-lead {
    flex: 1 1 100%;
    font-family: var(--serif);
    font-size: 15px;
    color: var(--ink);
  }
  .attr-key { display: inline-flex; align-items: baseline; gap: 9px; }
  .attr-gloss {
    font-family: var(--serif);
    font-size: 14px;
    color: var(--ink-soft);
    text-transform: none;
    letter-spacing: 0;
  }

  /* ---------- attribution tags ---------- */
  /* Three states, worded verbatim, never removed or softened.
     Prominence descends with claim strength. */
  .attr {
    display: inline-block;
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 500;
    line-height: 1.6;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 5px 8px;
    white-space: nowrap;
  }
  .attr.attr-enso    { background: var(--tag-loaded-bg);  color: var(--tag-loaded-fg); }
  .attr.attr-none    { background: var(--tag-notlink-bg); color: var(--tag-notlink-fg); }
  .attr.attr-pending { background: var(--tag-pending-bg); color: var(--tag-pending-fg); }

  /* ---------- tracker strip: the credential, visible and secondary ---------- */
  .wave-strip { padding: 0 0 46px; }
  .wave-strip .field-shell {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: baseline;
    gap: 10px 22px;
    background: var(--paper-sunk);
    border-left: 3px solid var(--nino);
    padding: 18px 22px;
    max-width: 1100px;
  }
  .wave-strip .ws-label { color: var(--nino); }
  .wave-strip .ws-read { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
  .wave-strip .ws-num { font-size: 24px; font-weight: 500; color: var(--nino); }
  .wave-strip .ws-num small { font-size: 13px; }
  .wave-strip .ws-desc { font-size: 17px; color: var(--ink); }
  .wave-strip a.ws-go {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-faint);
    white-space: nowrap;
  }
  .wave-strip a.ws-go:hover { color: var(--ink); }

  /* ---------- rail + body ---------- */
  .shell { display: block; }
  .rail { grid-column: 2; padding-top: 44px; order: 2; }
  .rail-inner {
    position: sticky;
    top: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    border-left: 1px solid var(--rule);
    padding-left: 22px;
  }
  .rail-block { display: flex; flex-direction: column; gap: 3px; }
  .rail-block .eyebrow { color: var(--ink-faint); }
  .rail-block .val { font-size: 13px; line-height: 1.75; color: var(--ink-soft); }
  .rail-block .val b { font-weight: 500; color: var(--ink); }
  .body { padding: 0 0 8px; min-width: 0; }

  main.body section { margin: 0; padding-bottom: 48px; }
  .sec-head {
    display: flex;
    align-items: baseline;
    gap: 14px;
    padding-bottom: 10px;
    margin-bottom: 20px;
    border-bottom: 3px solid var(--ink);
  }
  .sec-head .eyebrow { color: var(--ink-faint); flex: none; }
  .sec-head h2 { font-size: 20px; font-weight: 500; line-height: 1.30; }
  .section-sub {
    color: var(--ink-soft);
    font-size: 17.5px;
    margin: -8px 0 22px;
    max-width: 62ch;
  }

  /* ---------- editor's note ---------- */
  .editor-note {
    margin: 0 0 36px;
    padding: 0 0 0 22px;
    border-left: 3px solid var(--nino);
    max-width: 62ch;
  }
  .editor-note .editor-note-label {
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--nino);
    margin-bottom: 8px;
  }
  .editor-note p { margin: 0; font-size: 17.5px; font-style: italic; }
  .editor-note p + p { margin-top: 12px; }
  .editor-note strong { font-style: normal; font-weight: 500; }

  /* ---------- probability ladder ---------- */
  /* Confidence is rendered, not stated: the bar loses substance as
     certainty falls and the text steps down the ink ramp with it. */
  .ladder { display: flex; flex-direction: column; margin: 0 0 18px; }
  .rung {
    display: grid;
    grid-template-columns: 130px 92px minmax(0, 1fr) 300px;
    align-items: center;
    gap: 6px 20px;
    padding: 16px 0;
    border-bottom: 2.4px solid var(--rule-45);
  }
  .rung:first-child { border-top: 3px solid var(--ink); }
  .rung:last-child { border-bottom: 3px solid var(--ink); }
  .rung .threshold {
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
    font-size: 13px;
    font-weight: 500;
    color: var(--ink);
    grid-column: 1;
  }
  .rung .threshold .gt { color: var(--ink-faint); font-weight: 400; }
  .rung .pct {
    position: relative;   /* containing block for the sr-only .word */
    font-size: 24px;
    font-weight: 500;
    color: var(--ink);
    grid-column: 2;
    text-align: right;
    white-space: nowrap;
  }
  .rung .pct .pct-sym { font-size: 13px; color: var(--ink-faint); }
  /* Visually hidden, not removed. display:none took this out of the
     accessibility tree as well, so a screen reader heard "98" with no
     unit. The word is redundant beside the printed bar for a sighted
     reader and load-bearing for everyone else. */
  .rung .pct .word {
    position: absolute;
    width: 1px; height: 1px;
    margin: -1px; padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
  .rung .label {
    grid-column: 4;
    font-size: 15px;
    color: var(--ink-soft);
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;
  }
  /* The bar: solid for the calibrated rungs, losing substance above. */
  .rung.record .pct, .rung.record .label { color: var(--ink-soft); }
  .rung.far .pct, .rung.far .label { color: var(--ink-faint); }
  .rung.record .threshold { color: var(--ink-soft); }
  .rung.far .threshold { color: var(--ink-faint); }
  .rung .label .tag {
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-faint);
    padding: 4px 7px;
    background: var(--paper-sunk);
  }
  .rung .pct .wow-delta {
    display: block;
    font-size: 10.5px;
    font-weight: 400;
    color: var(--ink-faint);
    margin-top: 5px;
  }
  .rung .pct .wow-delta.wow-up { color: var(--fire); }
  .rung .pct .wow-delta.wow-down { color: var(--flood); }
  .rung .label .sep, .rung .label .range { color: var(--ink-faint); }
  .buckets-note {
    font-size: 13px;
    font-family: var(--mono);
    line-height: 1.75;
    color: var(--ink-faint);
    margin: 0;
    max-width: 78ch;
  }

  /* ---------- analyst read ---------- */
  section.analyst-read {
    padding: 0 0 48px 22px;
    border-left: 3px solid var(--nino);
    margin-bottom: 0;
  }
  section.analyst-read h2 { font-size: 20px; margin: 0 0 4px; }
  section.analyst-read .section-sub { margin: 0 0 12px; }
  section.analyst-read ul { list-style: none; padding: 0; margin: 0; }
  section.analyst-read li {
    padding: 14px 0;
    border-bottom: 1px solid var(--rule);
    font-size: 17.5px;
  }
  section.analyst-read li:last-child { border-bottom: none; padding-bottom: 0; }
  section.analyst-read li strong { font-weight: 500; }

  /* ---------- chart ---------- */
  .chart-card { border-top: 3px solid var(--ink); border-bottom: 1px solid var(--rule); padding: 18px 0; }
  .chart-caption {
    font-size: 15px;
    color: var(--ink-soft);
    margin-top: 16px;
    line-height: 1.62;
    max-width: 68ch;
  }
  .chart-caption strong { color: var(--ink); font-weight: 500; }

  /* ---------- tables ---------- */
  table.phys { width: 100%; border-collapse: collapse; font-size: 15px; }
  table.phys th, table.phys td {
    padding: 14px 12px 14px 0;
    text-align: left;
    border-bottom: 1px solid var(--rule);
    vertical-align: top;
  }
  table.phys thead th {
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
    font-weight: 400;
    border-bottom: 3px solid var(--ink);
    vertical-align: bottom;
  }
  table.phys td.num { white-space: nowrap; font-size: 14px; }
  table.phys tbody tr:last-child td { border-bottom: 3px solid var(--ink); }
  .note {
    font-size: 15px;
    color: var(--ink-soft);
    border-left: 1px solid var(--rule);
    padding: 4px 0 4px 18px;
    margin: 18px 0 0;
    max-width: 68ch;
  }
  .note strong { color: var(--ink); font-weight: 500; }

  /* ---------- sources ---------- */
  .src-list { padding: 0; list-style: none; margin: 0; }
  .src-list li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 20px;
    align-items: baseline;
    padding: 13px 0;
    border-bottom: 1px solid var(--rule);
    font-size: 15px;
  }
  .src-list li:first-child { border-top: 3px solid var(--ink); }
  .src-list li:last-child { border-bottom: 3px solid var(--ink); }
  .src-list .src-name { font-weight: 500; }
  .src-list .src-issued {
    font-size: 12.5px;
    color: var(--ink-faint);
    white-space: nowrap;
    text-align: right;
  }
  .src-list .src-detail {
    grid-column: 1 / -1;
    color: var(--ink-soft);
    font-size: 14px;
    margin-top: 2px;
  }

  ol.caveats { padding-left: 20px; margin: 0; }
  ol.caveats li { margin-bottom: 16px; font-size: 15px; line-height: 1.62; }
  ol.caveats li::marker { font-family: var(--mono); font-size: 12px; color: var(--ink-faint); }

  /* ---------- channels ---------- */
  .chans {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
    gap: 0;
    border-top: 3px solid var(--ink);
    padding-top: 22px;
  }
  .chan {
    padding: 0 22px 0 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-left: 1px solid var(--rule);
    padding-left: 20px;
  }
  .chan:first-child { border-left: none; padding-left: 0; }
  .chan-top { display: flex; align-items: center; gap: 9px; }
  .dot { width: 8px; height: 8px; flex: none; }
  .chan h3 { font-size: 20px; font-weight: 500; }
  .chan p { margin: 0; font-size: 15px; color: var(--ink-soft); line-height: 1.55; }
  .chan.next h3, .chan.next p { color: var(--ink-faint); }

  /* ---------- email capture ---------- */
  .email-cap {
    border-top: 3px solid var(--ink);
    border-bottom: 2.4px solid var(--rule-45);
    padding: 26px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px 40px;
    flex-wrap: wrap;
  }
  .email-cap .ec-pitch { max-width: 46ch; }
  /* The form gets its own rule rather than whatever the flex row has
     left over. QA measured the consequence of not having one: the
     iframe rendered at 300px on a 375px front page against 327px on
     /subscribe/, so the HIGHER-TRAFFIC placement was the more
     constrained of the two, which is backwards.

     Beehiiv lays the field and the button side by side at a fixed
     button width, so every pixel lost falls on the input. At 300px the
     placeholder rendered as "E". The real fix is theirs, since the form
     is cross-origin and our CSS cannot reach inside it. The container
     is ours, and it should never be the reason the field is narrow. */
  .email-cap .ec-form { flex: 1 1 340px; min-width: 0; }
  /*EMAIL_FORM_CSS*/
  @media (max-width: 700px) {
    /* Stack rather than share the row, and drop the 40px column gap,
       which is pure loss once the children are full width. */
    .email-cap { gap: 16px 0; }
    .email-cap .ec-pitch,
    .email-cap .ec-form { flex: 1 1 100%; max-width: 100%; }
  }
  .email-cap .ec-pitch .eyebrow { display: block; color: var(--ink-faint); margin-bottom: 6px; }
  .email-cap .ec-pitch p { margin: 0; font-size: 17.5px; }
  .email-cap a.ec-btn {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--paper);
    background: var(--ink);
    padding: 14px 24px;
    white-space: nowrap;
  }
  .email-cap a.ec-btn:hover { background: var(--nino); }

  /* ---------- footer ---------- */
  footer.field { border-top: 3px solid var(--ink); margin-top: 8px; }
  .foot { padding: 32px 0 44px; display: flex; flex-direction: column; gap: 26px; }
  .foot-top {
    display: flex;
    justify-content: space-between;
    gap: 24px 40px;
    flex-wrap: wrap;
    align-items: flex-start;
  }
  .foot-links { display: flex; gap: 22px; flex-wrap: wrap; }
  .foot-links a {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  .foot-links a:hover { color: var(--ink); }
  .foot-cite {
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.85;
    color: var(--ink-faint);
    max-width: 68ch;
    margin: 0;
  }
  .foot-cite b { color: var(--ink-soft); font-weight: 500; }
  .foot-fresh-label { display: block; color: var(--ink-faint); margin-bottom: 10px; }
  .freshness-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px 32px;
    margin: 0;
  }
  .freshness-grid .src { color: var(--ink-soft); font-size: 13px; }
  .freshness-grid .meta { font-family: var(--mono); font-size: 11px; color: var(--ink-faint); }
  .footer-meta { font-size: 12px; line-height: 1.85; color: var(--ink-faint); margin: 0; max-width: 78ch; }
  .footer-meta strong { color: var(--ink-soft); font-weight: 500; }

  /* ---------- impact outlook ---------- */
  section.impacts > p:first-of-type { color: var(--ink-soft); font-size: 17.5px; margin: -8px 0 18px; }
  .impacts-map {
    position: relative;
    margin: 18px 0 14px;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
  }
  .impacts-map .world-map-bg { width: 100%; }
  .impacts-map .map-hotspot {
    position: absolute; transform: translate(-50%, -50%);
    /* 32px target with a 10px dot inside it. 22px was under the WCAG 2.2
       AA minimum of 24px (SC 2.5.8). 44px is the AAA figure (2.5.5) and
       is too big here: measured at a 350px-wide map the closest two
       regions sit 35px apart, so 44px targets would steal each other's
       taps, which is worse than a small one. 32px clears AA with margin
       and fits the spacing. The region tab strip is the redundant
       control for anyone who finds the discs fiddly. */
    width: 32px; height: 32px;
    background: transparent; border: 0; padding: 0; cursor: pointer;
  }
  /* A plain disc. This was a ring around a dot, with the active state
     expanding the ring outward, which is the epicenter figure: radiating
     causation, on the one map that is specifically about El Nino's
     regional impacts, where the text refuses to make that claim. D-017
     forbids the attenuation ratio on any mark that carries data, and the
     same objection applies to any concentric figure. Selection is carried
     by opacity and a hairline, not by radiating rings. */
  .impacts-map .map-hotspot-dot {
    position: absolute; inset: 11px;
    border-radius: 50%;
    background: var(--fire);
    opacity: 0.75;
    transition: opacity .15s ease;
  }
  .impacts-map .map-hotspot:hover .map-hotspot-dot { opacity: 1; }
  /* Selection rings use outline with outline-offset. SHADOW is None in
     the token file, deliberately, so a contributor has to delete a line
     rather than add one; a spread-only shadow used as a ring renders
     fine but leaves a hit for anyone auditing that rule. */
  .impacts-map .map-hotspot.active .map-hotspot-dot {
    opacity: 1;
    outline: 1.5px solid var(--ink);
    outline-offset: 1px;
  }
  .impacts-map .map-hotspot:focus-visible .map-hotspot-dot {
    outline: 2px solid var(--nino);
    outline-offset: 2px;
  }
  .region-tabs { display: flex; flex-wrap: wrap; gap: 0; margin: 16px 0 18px; border-bottom: 1px solid var(--rule); }
  .region-tab {
    background: none;
    border: 0;
    border-bottom: 2.4px solid transparent;
    padding: 13px 14px 13px 0;
    margin-right: 18px;
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-faint);
    cursor: pointer;
  }
  .region-tab:hover { color: var(--ink); }
  .region-tab[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--ink); }
  .region-panel { display: none; }
  .region-panel.active { display: block; }
  .region-panel h3 { font-size: 20px; font-weight: 500; margin: 0 0 10px; }
  .region-panel p { font-size: 17.5px; line-height: 1.62; margin: 0 0 12px; max-width: 62ch; }

  /* ---------- issue page: answer left, ocean heat right ---------- */
  /* Secondary column is COLUMN_SECOND (300px), not a number picked to
     suit this page. An earlier 380px panel forced these grids to stack
     at 1000px, which let one layout choice rewrite a system rule; the
     visual-language chat called it correctly as drift. On the token the
     single 760 breakpoint holds: at 761px the prose column still gets
     325px and it only widens from there. */
  .top {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 300px;
    gap: 56px;
    padding: 40px 0 0;
    align-items: start;
  }
  .heat { border-left: 1px solid var(--rule); padding-left: 24px; }
  .heat .cap { color: var(--ink-faint); margin-bottom: 14px; display: block; }
  .hrow {
    display: grid;
    grid-template-columns: 52px minmax(0, 1fr) 62px;
    gap: 10px;
    align-items: center;
    padding: 7px 0;
  }
  .hrow .yr { font-family: var(--mono); font-size: 11.5px; color: var(--ink-soft); }
  .htrack { display: block; position: relative; height: 14px; }
  .hzero {
    position: absolute; top: -2px; bottom: -2px; width: 1px;
    background: var(--ink-faint);
  }
  .hbar { position: absolute; top: 0; height: 14px; }
  .hrow .val {
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    font-size: 13px; text-align: right;
  }
  .hrow.now .yr, .hrow.now .val { color: var(--ink); font-weight: 500; }
  .hnote {
    font-family: var(--mono); font-size: 10.5px; line-height: 1.7;
    color: var(--ink-faint); margin: 12px 0 0;
    border-top: 1px solid var(--rule); padding-top: 10px;
  }

  /* ladder bar: length is probability, substance is confidence */
  .rung .track { display: block; height: 9px; background: var(--paper-sunk); }
  .rung .fill { display: block; height: 9px; background: var(--nino); }
  .rung.record .fill {
    background: repeating-linear-gradient(90deg,
      var(--nino) 0 4px, transparent 4px 8px);
  }
  .rung.far .fill {
    background: repeating-linear-gradient(90deg,
      #7B88AF 0 2px, transparent 2px 8px);
  }

  /* chart left, reading note right */
  .two {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 300px;
    gap: 56px;
    align-items: start;
  }
  .two .note-side { border-left: 3px solid var(--nino); padding-left: 20px; }
  .two .note-side h3 { font-size: 15px; margin-bottom: 8px; }
  .two .note-side p { font-size: 15px; color: var(--ink-soft); margin: 0; }
  .two .note-side p + p { margin-top: 12px; }

  /* issue metadata, which used to be the rail */
  .issue-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px 32px;
    border-top: 3px solid var(--ink);
    padding-top: 16px;
    margin-top: 8px;
  }
  .issue-meta .k {
    font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.22em;
    text-transform: uppercase; color: var(--ink-faint); display: block;
  }
  .issue-meta .v {
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    font-size: 13px; line-height: 1.75; color: var(--ink-soft);
  }
  .issue-meta .v b { color: var(--ink); font-weight: 500; }

  /* ---------- front page: lead, then the map ---------- */
  .lead-block { padding: 40px 0 30px; }
  .lead-block .eyebrow { color: var(--ink-faint); display: block; margin-bottom: 14px; }
  h1.lead-answer {
    font-size: clamp(34px, 4.2vw, 50px);
    line-height: 1.10;
    letter-spacing: -0.018em;
    max-width: 660px;
    margin: 0 0 18px;
  }
  .lead-stand { color: var(--ink-soft); max-width: 58ch; margin: 0; }

  .mapwrap {
    border-top: 3px solid var(--ink);
    border-bottom: 2.4px solid var(--rule-45);
    padding: 14px 0 12px;
    margin-bottom: 4px;
  }
  .mapcap {
    display: flex; justify-content: space-between;
    gap: 14px; flex-wrap: wrap; margin-bottom: 8px;
  }
  .mapcap .eyebrow { color: var(--ink-faint); }
  svg.map { display: block; width: 100%; height: auto; }
  /* The coastline rule was already wired to LAND_LINE but at 0.4 in
     viewBox units, which on an 800-unit map rendered 1440px wide is
     0.72px: present in the markup and invisible on screen. So the map
     had two kinds of edge that looked identical, the coast being
     geography and the field's top and bottom being a crop, and the
     honest edge inherited the clipped-image feeling from the arbitrary
     ones. non-scaling-stroke because the rule weights are defined in px
     and must not scale with the viewport. It also separates the Chile
     coastline from the field's southern crop boundary, which had merged
     into one ambiguous line. */
  svg.map .land {
    fill: var(--land); stroke: var(--land-line);
    stroke-width: 1.8; vector-effect: non-scaling-stroke;
  }
  .mk { cursor: pointer; }
  .mk .mk-hit { fill: transparent; }
  /* No stroke. A 1px stroke on a radius that encodes magnitude added
     36% apparent area at r=3 against 11% at r=9, so small multiples read
     systematically larger than they are; hover at 2.5px doubled the
     smallest. Opacity carries the state instead, because it does not
     touch the geometry that carries the number. */
  /* A paper ring OUTSIDE the disc, never a stroke on it. FIRE #B32E10
     against the field's hot end #8E240A measures 1.377:1, so a marker
     landing on the eastern Pacific, or where the tongue meets the
     Ecuador coast, would be indistinguishable from the ocean under it.
     No marker sits there this week, which is why this was latent rather
     than visible. A stroke would have eaten into the radius, and radius
     is the number here, so the separation goes outside it. Same device
     as D-023, applied to a mark instead of a label. */
  .mk-ring { fill: none; stroke: var(--paper); stroke-width: 2.4; }
  /* Context, not an event: an open ring of the same radius, so the
     size still carries the number and the fill no longer claims
     something the data denies. */
  .mk.ctx .mk-dot { fill: none; stroke: var(--fire);
    stroke-width: 1.6; fill-opacity: 1; }
  .mk.ctx:hover .mk-dot, .mk.ctx:focus .mk-dot { fill: var(--fire);
    fill-opacity: 0.18; }
  .mk .mk-dot {
    fill: var(--fire); fill-opacity: 0.78;
    stroke: none;
    transition: fill-opacity .12s;
  }
  .mk:hover .mk-dot, .mk:focus .mk-dot { fill-opacity: 1; }
  /* A dedicated focus ring, because opacity 0.78 to 1 is not a visible
     indicator, and the global a:focus-visible outline is unreliable on
     SVG <a>. It sits outside the disc so the geometry that carries the
     number is untouched. */
  .mk .mk-focus {
    fill: none; stroke: var(--nino); stroke-width: 2;
    opacity: 0; transition: opacity .1s;
  }
  .mk:focus-visible .mk-focus, .mk:focus .mk-focus { opacity: 1; }
  .nino-g, .sst-g { cursor: pointer; }
  /* An SVG anchor gets no pointer cursor and no focus ring for free, and
     the field is a large silent target, so both are stated. The focus
     outline sits on the group rather than on the image so it traces the
     clickable area a keyboard user has actually reached. */
  .sst-g:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  /* Over the SST field these sat dark on dark and the box outline
     disappeared entirely: the anomaly scale reaches near-black at its
     ends, so ink furniture on top of it is unreadable exactly where the
     event is strongest. Everything here carries a paper-coloured stroke
     behind its fill, so the contrast is against paper rather than
     against whatever the field happens to be doing underneath. This is
     the same collision D-016 amendment 4 names, met on the label
     instead of on a mark: the hue still says which channel this is, the
     halo is what keeps it legible. */
  /* Two rects, because one stroke cannot be legible against both a
     near-paper ocean and a near-black anomaly. The paper one widens the
     ink one just enough to separate it from whatever is underneath. */
  .nino-halo { fill: none; stroke: var(--paper); stroke-width: 2.8; }
  .nino-brk-halo { fill: none; stroke: var(--paper); stroke-width: 3.2; }
  .nino-brk { fill: none; stroke: var(--ink); stroke-width: 1; }
  .nino-box {
    stroke: var(--ink); stroke-width: 0.9; fill-opacity: 1;
  }
  .nino-g:hover .nino-box, .nino-g:focus .nino-box {
    stroke: var(--ink); stroke-width: 1.2;
  }
  .nino-lb, .nino-v {
    paint-order: stroke; stroke: var(--paper); stroke-linejoin: round;
  }
  .nino-lb {
    font-family: var(--mono); font-size: 7px;
    letter-spacing: 0.16em; fill: var(--ink-soft); stroke-width: 2.6;
  }
  /* INK, not the channel hue. This was set in NINO blue, and on this
     palette blue is the whole cold half of the anomaly ramp, visible in
     the same frame as the cold tongue's western end. So the page's
     headline ocean value was printed in the colour that means the
     opposite of what the number says, and it spent a channel hue on a
     figure whose own scale already carries the encoding. The field is
     what says the value is remarkable. */
  .nino-v {
    font-family: var(--mono); font-size: 13px;
    font-weight: 500; fill: var(--ink); stroke-width: 3.4;
  }
  .legends { display: flex; justify-content: space-between; gap: 24px; flex-wrap: wrap; }
  .lg-dot { fill: var(--fire); fill-opacity: 0.8; }
  .lg-tx { font-family: var(--mono); font-size: 9px; fill: var(--ink-faint); }
  .lg-tick { fill: var(--ink); }
  .lg-cap { fill: var(--ink-faint); }
  .lg-now {
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    font-size: 9.5px; font-weight: 500; fill: var(--ink);
  }
  .mapnote {
    font-family: var(--mono); font-size: 10.5px; line-height: 1.7;
    color: var(--ink-faint); margin: 8px 0 0;
  }
  .break-more { margin: 18px 0 0; }
  .break-more a {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--ink-soft);
  }

  /* ---------- about: numbered section grid ---------- */
  /* Label column floors at 0, deliberately. Per the Grid spec a minmax()
     whose min exceeds its max resolves to the min, so an intrinsic floor
     on a column carrying 20px headings ignores the 220px cap entirely:
     "Where the numbers come from" measures 277px unwrapped and stole
     57px from the prose. An intrinsic floor suits short tracked-mono
     labels and not headings, which can wrap. The prose track keeps
     minmax(0, 1fr) so it is the one that gives. */
  .about-sec {
    display: grid;
    grid-template-columns: minmax(0, 220px) minmax(0, 1fr);
    gap: 10px 56px;
    padding: 26px 0 34px;
    border-top: 2.4px solid var(--rule-45);
  }
  /* Explicit classes, not :first-of-type. That pseudo matches the first
     element of its TYPE among siblings, so one <section> added above the
     nine would leave every .about-sec without an opening rule and the
     page would quietly open at 2.4px. :first-child does not work either,
     since .issue-head precedes them. The builder marks the ends. */
  .about-sec.about-open { border-top: 3px solid var(--ink); }
  .about-sec.about-close { border-bottom: 3px solid var(--ink); }
  .about-num {
    font-family: var(--mono); font-size: 9.5px; line-height: 2;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--ink-faint);
  }
  .about-sec h2 { font-size: 20px; font-weight: 500; margin-bottom: 10px; }
  .about-body p { margin: 0; max-width: 62ch; }
  .about-body p + p { margin-top: 14px; }
  /* No bullet lists anywhere in this system. ol.caveats styles its own
     markers and every other list is rule-separated rows, so discs would
     be the one exception. The refusals in particular carry more weight as
     rows than as a bulleted aside. */
  .refusals {
    margin: 0;
    /* Opens and closes at 3px like .src-list, .event, .rung and
       .swell-row. This is the block the page's credibility argument
       leans on, so it reads as a closed list rather than trailing off.
       Interior dividers stay at the 1px hairline. */
    border-top: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
  }
  .refusal {
    display: grid;
    grid-template-columns: minmax(0, 200px) minmax(0, 1fr);
    gap: 4px 24px;
    padding: 13px 0;
    border-top: 1px solid var(--rule);
  }
  .refusal:first-child { border-top: 0; }
  .refusal dt { font-weight: 500; }
  .refusal dd { margin: 0; color: var(--ink-soft); }
  .about-aside {
    font-family: var(--mono); font-size: 12.5px; line-height: 1.75;
    color: var(--ink-soft); margin-top: 14px;
    border-left: 1px solid var(--rule); padding-left: 16px;
  }

  /* The three-row hierarchy: the only place the ratio's 1.8px width is
     used as a rule, because here the hierarchy is the content. The
     default top rule is the hairline step, so a fourth row added later
     degrades to 1.8px rather than to no rule at all. */
  .swell-rows { margin: 0; }
  .swell-row {
    border-top: 1.8px solid var(--rule-20);
    display: grid;
    grid-template-columns: minmax(0, 118px) minmax(0, 1fr);
    gap: 6px 22px;
    padding: 14px 0;
  }
  .swell-row:nth-child(1) { border-top: 3px solid var(--ink); }
  .swell-row:nth-child(2) { border-top: 2.4px solid var(--rule-45); }
  .swell-row:nth-child(3) {
    border-top: 1.8px solid var(--rule-20);
    border-bottom: 3px solid var(--ink);
  }
  .swell-row dt {
    font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--ink);
  }
  .swell-row dd { margin: 0; color: var(--ink-soft); max-width: 56ch; }

  /* ---------- archive ---------- */
  .ar-chart { display: block; width: 100%; height: auto; margin: 4px 0 10px; }
  .ar-grid { stroke: var(--rule); stroke-width: 1; }
  .ar-ax {
    font-family: var(--mono); font-size: 9.5px; fill: var(--ink-faint);
  }
  .ar-line { fill: none; stroke-width: 2; stroke-linejoin: round; }
  /* A version bump is a caveat, not decoration: deltas either side of
     one are not comparable, so it gets a rule and a label. */
  .ar-bump { stroke: var(--ink-faint); stroke-width: 1; stroke-dasharray: 2 3; }
  .ar-bump-lb {
    font-family: var(--mono); font-size: 9px; fill: var(--ink-faint);
  }
  .ar-legend {
    display: flex; flex-wrap: wrap; gap: 8px 22px;
    padding: 10px 0 4px; border-top: 1px solid var(--rule);
  }
  .ar-key {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--mono); font-size: 10.5px; color: var(--ink-soft);
  }
  .ar-swatch { width: 16px; height: 3px; flex: none; }

  .ar-head, .ar-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 320px) 62px;
    gap: 6px 20px;
    align-items: baseline;
  }
  .ar-head {
    padding-bottom: 8px;
    border-bottom: 3px solid var(--ink);
    font-family: var(--mono); font-size: 9.5px; line-height: 2;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--ink-faint);
  }
  .ar-vals { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .ar-head .ar-vals > span { text-align: right; }
  .ar-row {
    padding: 13px 0;
    border-bottom: 1px solid var(--rule);
    color: inherit;
  }
  .ar-row:last-child { border-bottom: 3px solid var(--ink); }
  .ar-row:hover { background: var(--paper-sunk); }
  .ar-row:hover .ar-date { color: var(--fire); }
  .ar-date { font-size: 15px; font-weight: 500; }
  .ar-val { font-size: 14px; color: var(--ink-soft); text-align: right; }
  .ar-ver {
    font-family: var(--mono); font-size: 11px; color: var(--ink-faint);
    text-align: right;
  }
  /* The issue where the arithmetic changed is the one worth finding. */
  .ar-ver.bumped { color: var(--ink); font-weight: 500; }
  .ar-ver.bumped::before { content: "\2022 "; color: var(--nino); }

  /* ---------- one breakpoint ---------- */
  @media (max-width: 760px) {
    .field-shell, .shell { padding-left: 20px; padding-right: 20px; }
    .about-sec, .swell-row, .refusal {
      grid-template-columns: minmax(0, 1fr); gap: 8px;
    }
    .ar-head, .ar-row { grid-template-columns: minmax(0, 1fr) auto; }
    .ar-head > span:nth-child(2), .ar-vals { grid-column: 1 / -1; }
    .ar-vals { gap: 8px; padding-top: 4px; }
    .top, .two { grid-template-columns: minmax(0, 1fr); gap: 30px; }
    .heat, .two .note-side {
      border-left: 0; border-top: 1px solid var(--rule); padding: 20px 0 0;
    }
    .heat { max-width: 520px; }
    .rung { grid-template-columns: 130px 92px minmax(0, 1fr); gap: 6px 20px; }
    .rung .label { grid-column: 1 / -1; padding-top: 2px; }
    .shell { grid-template-columns: minmax(0, 1fr); gap: 0; }
    .rail { grid-column: 1; order: 2; padding-top: 8px; }
    .rail-inner {
      position: static;
      flex-direction: row;
      flex-wrap: wrap;
      gap: 18px 30px;
      border-left: 0;
      border-top: 1px solid var(--rule);
      padding: 22px 0 0;
    }
    .body { grid-column: 1; order: 1; padding-top: 32px; }
    body { font-size: 17px; }
    .hero h1, .issue-head h1 { font-size: 34px; }
    .event { grid-template-columns: minmax(0, 1fr) auto; }
    .event .ev-stat { grid-column: 1; grid-row: 1; font-size: 32px; }
    .event .ev-body { grid-column: 1 / -1; grid-row: 2; }
    .event .attr { grid-column: 2; grid-row: 1; align-self: center; }
    .wave-strip .field-shell { grid-template-columns: minmax(0, 1fr); }
    .freshness-grid { grid-template-columns: minmax(0, 1fr); }
    .readout { gap: 24px; }
  }
  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
  }
""".strip()

PUBLIC_CSS = (_PUBLIC_CSS_TEMPLATE
              .replace("/*MASTHEAD_CSS*/", SITE_MASTHEAD_CSS)
              .replace("/*VARS_LIGHT*/", T.css_vars_light())
              .replace("/*VARS_DARK*/", T.css_vars_dark())
              .replace("/*EMAIL_FORM_CSS*/", EMAIL_FORM_CSS))

HTML_CSS = (_HTML_CSS_TEMPLATE
            .replace("/*VARS_LIGHT*/", T.css_vars_light())
            .replace("/*VARS_DARK*/", T.css_vars_dark()))


def _render_rung(css_class: str, threshold: str, pct_dict: dict, label_main: str,
                 prev_mid: int | None = None,
                 delta_label: str = "vs last month",
                 tag: str | None = None) -> str:
    """One probability-ladder row.

    Smoothed headline value (`mid`) is the prominent number. A small
    delta sits below it when a comparable prior issue is available and
    the change is non-zero; an arrow indicates direction. `delta_label`
    sets the suffix copy ("vs last month" for the ≥28-day-back case,
    "since first issue" for the fallback used in the brief's first
    month). `tag` adds a small pill next to the label (used to flag the
    +3.0 bucket as "most uncertain", since it is the least-anchored
    figure on the ladder). The methodology breakdown is documented on
    the methodology page rather than crammed into the rung label.
    """
    tag_html = f'<span class="tag">{h(tag)}</span>' if tag else ""
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
                f'<span class="wow-delta {cls}">{arrow} {sign}{abs(delta)} pp {h(delta_label)}</span>'
            )
    # The bar carries two variables at once: length is the probability,
    # substance is the confidence. They vary independently, so a high
    # probability on a rung nobody can calibrate still looks uncertain.
    try:
        pct_width = max(0, min(100, float(pct_dict["mid"])))
    except (TypeError, ValueError):
        pct_width = 0
    return (
        f'<div class="rung {css_class}">'
        f'<div class="threshold"><span class="gt">&gt;</span>{h(threshold)}</div>'
        f'<div class="pct">{pct_dict["mid"]}<span class="pct-sym">%</span>'
        f'<span class="word">probability</span>{delta_html}</div>'
        f'<div class="track"><span class="fill" '
        f'style="width:{pct_width:g}%"></span></div>'
        f'<div class="label">{h(label_main)}{tag_html}</div>'
        f'</div>'
    )


def _signed_temp(value: float, decimals: int = 1) -> str:
    """Format a temperature with explicit sign and Unicode minus where negative."""
    formatted = f"{value:+.{decimals}f}"
    return formatted.replace("-", "−")  # U+2212 minus sign


# Minimum margin (deg C) before the brief claims one year is "ahead of"
# another on heat content. CPC reports to two decimals, but month-to-month
# sampling noise in the 0-300m index is far larger than a hundredth, so a
# +0.01 gap is not a real difference. Below this margin the brief says
# "essentially tied" instead of "ahead", which is what the 2026-vs-1997
# June comparison (+2.26 vs +2.25) actually warrants.
HC_MATERIAL_MARGIN_C = 0.10


def _hc_analogs(phys: dict, analog_same: dict):
    """Resolve (hc97, hc15, basis) for heat-content analog comparisons.

    Prefers the live same-calendar-month values fetched from the same CPC
    series as the current reading, so July compares to July. Falls back to
    the sources.py April seeds, and says so in `basis`, rather than
    silently presenting an April number as a same-stage comparison.
    """
    live = phys.get("heat_content_analogs_same_month") or {}
    if live.get("1997") is not None and live.get("2015") is not None:
        month = (phys.get("heat_content_data_month") or "")[-2:]
        month_name = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November",
            "12": "December",
        }.get(month, "the same month")
        return live["1997"], live["2015"], f"same calendar month ({month_name})"
    return (analog_same.get("1997_apr_heat_content"),
            analog_same.get("2015_apr_heat_content"),
            "April of each develop year")


def _heat_content_compare(val: float, hc97: float, hc15: float) -> str:
    """One-sentence quantitative comparison of current heat content vs the
    1997 and 2015 super-event same-week analogs. Auto-banded above-both /
    between / below-both. Empty string if any input is missing.
    """
    if val is None or hc97 is None or hc15 is None:
        return ""
    if val > max(hc97, hc15) + HC_MATERIAL_MARGIN_C:
        return (f" At {val:+.2f}°C, 2026 exceeds both 1997 "
                f"({hc97:+.2f}°C) and 2015 ({hc15:+.2f}°C) at the same "
                f"calendar month, running ahead of either super-event "
                f"analog at this stage of development.")
    if abs(val - max(hc97, hc15)) <= HC_MATERIAL_MARGIN_C:
        hotter = 1997 if hc97 >= hc15 else 2015
        return (f" At {val:+.2f}°C, 2026 is effectively level with "
                f"{hotter} (1997 {hc97:+.2f}°C, 2015 {hc15:+.2f}°C) at the "
                f"same calendar month; the gap is smaller than the "
                f"month-to-month noise in this index.")
    if val > min(hc97, hc15):
        return (f" At {val:+.2f}°C, 2026 sits between 1997 ({hc97:+.2f}°C) "
                f"and 2015 ({hc15:+.2f}°C) at the same calendar month.")
    return (f" At {val:+.2f}°C, 2026 is below both 1997 ({hc97:+.2f}°C) and "
            f"2015 ({hc15:+.2f}°C) at the same calendar month.")


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
    """Find a prior archive for the public ladder's delta indicator,
    methodology-version gated. Returns a dict with keys:
      - "buckets": headline_buckets from the chosen archive
      - "date":    that archive's date (date object)
      - "label":   human label for the delta suffix ("vs last month" when
                   the prior is ≥28 days back, "since first issue" when
                   we fell back to the oldest available archive)
    or None if no comparable prior is available.

    Selection rule:
      1. Prefer the most recent archive whose date is at least 28 days
         before `current_brief_date`. The 4-week window aligns with CPC's
         monthly issuance cadence and filters mechanical drift in RONI
         offset / SEAS5 deflection between CPC issuances.
      2. If no such archive exists yet (the brief launched <4 weeks ago),
         fall back to the OLDEST available archive (the "first issue").
         A visible delta still tracks the brief's lifetime drift, which
         is more honest than no signal at all; the label distinguishes
         the two cases so readers know what they're seeing.

    Either way the chosen archive's `methodology_version` must match
    current S.METHODOLOGY_VERSION. Cross-version comparison would
    mislead; the methodology-version-bump banner already discloses
    non-comparability at the headline level.
    """
    if not DOCS_BRIEFS_ROOT.exists():
        return None
    from datetime import timedelta
    cutoff = current_brief_date - timedelta(days=28)

    # Collect ALL prior archives whose meta.json carries a matching
    # methodology_version. We filter on version FIRST so that older
    # archives lacking the field (written before it was introduced)
    # don't shadow newer matching ones via the 28-day preference below.
    matching = []
    for d in DOCS_BRIEFS_ROOT.iterdir():
        if not d.is_dir():
            continue
        try:
            d_date = date.fromisoformat(d.name)
        except ValueError:
            continue
        if d_date >= current_brief_date:
            continue
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        prev_version = data.get("methodology_version")
        if prev_version is None or str(prev_version) != str(S.METHODOLOGY_VERSION):
            continue
        buckets = data.get("headline_buckets")
        if not buckets:
            continue
        matching.append((d_date, buckets))

    if not matching:
        return None
    matching.sort()  # ascending by date

    month_or_older = [m for m in matching if m[0] <= cutoff]
    if month_or_older:
        chosen_date, chosen_buckets = month_or_older[-1]
        label = "vs last month"
        return {"buckets": chosen_buckets, "date": chosen_date, "label": label}

    # Fallback: only when the oldest same-version archive genuinely IS the
    # site's first issue, so the "since first issue" copy stays true. After
    # a mid-life methodology bump the oldest same-version archive is just a
    # recent issue; comparing against it two weeks in produced a false
    # "since first issue" pill on 2026-07-27 (caught by Kristjan). In that
    # case show no delta; "vs last month" returns once a same-version
    # archive is 28+ days old.
    all_dirs = [d.name for d in DOCS_BRIEFS_ROOT.iterdir() if d.is_dir()
                and (d / "meta.json").exists()]
    first_issue_iso = min(all_dirs) if all_dirs else None
    chosen_date, chosen_buckets = matching[0]
    if first_issue_iso and chosen_date.isoformat() == first_issue_iso:
        return {"buckets": chosen_buckets, "date": chosen_date,
                "label": "since first issue"}
    return None


EDITORIAL_NOTE_FILE = Path(__file__).parent / "editorial_note.md"


def load_editorial_note() -> str:
    """Load the optional editorial_note.md at project root.

    If present and non-empty, returns the raw markdown; caller renders it
    to HTML and uses it in place of the auto-populated bottom-line copy.
    If absent or empty, returns "" and the bottom line falls back to the
    default "X% chance of at least a moderate El Niño this winter, Y%
    chance of a 1997 / 2015-magnitude event."

    The note is per-issue editorial copy. If the first line is an issue
    stamp of the form `<!-- issue: YYYY-MM-DD -->`, the note only renders
    when that date matches the brief being generated; otherwise it is
    treated as stale and skipped. This exists because an un-cleared note
    once leaked into two later cron issues (2026-06-22 and 06-29 carried
    the 06-15 note). Un-stamped notes render unconditionally, preserving
    the old behavior, but every new note should carry the stamp.
    """
    if not EDITORIAL_NOTE_FILE.exists():
        return ""
    raw = EDITORIAL_NOTE_FILE.read_text().strip()
    if not raw:
        return ""
    m = re.match(r"<!--\s*issue:\s*(\d{4}-\d{2}-\d{2})\s*-->\s*", raw)
    if m:
        if m.group(1) != S.BRIEF_DATE.isoformat():
            return ""   # stamped for a different issue: stale, skip
        raw = raw[m.end():].strip()
    return raw


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


# Attribution tags (T9, hard requirement): every event item carries a
# visible status. The three states are fixed vocabulary; subsection
# chats pick one per item in data/events.json, never invent new ones.
ATTR_LABELS = {
    "enso": "ENSO-loaded window",
    "non_enso": "Not ENSO-linked",
    "pending": "Attribution pending",
}
_ATTR_CLASSES = {"enso": "attr-enso", "non_enso": "attr-none",
                 "pending": "attr-pending"}


def _attr_tag(status: str) -> str:
    """The attribution tag component. Unknown statuses render as pending
    rather than crashing or silently vanishing; saying less than we know
    beats implying more."""
    key = status if status in ATTR_LABELS else "pending"
    return (f'<span class="attr {_ATTR_CLASSES[key]}">'
            f'{h(ATTR_LABELS[key])}</span>')


# Plain-language gloss for each tag. The three tag strings are fixed by
# T9 and are expert language: "ENSO-loaded window" means nothing to the
# non-expert this site is written for. The ratified rule is to define the
# vocabulary once above the first row of a list, and to gloss inline
# where a tag appears alone. Wording here is the design chat's first
# pass and is the editor's to ratify; the tag strings themselves are not
# negotiable.
ATTR_GLOSS = {
    "enso": "a season and place where El Ni\u00f1o shifts the odds",
    "non_enso": ("no established pathway ties this kind of event to El "
                 "Ni\u00f1o"),
    "pending": "the formal attribution work is not in yet",
}


def _attr_legend(events: list[dict]) -> str:
    """Define the tag vocabulary once, above the list it governs.

    Only the states actually present are defined, so the legend never
    explains a chip the reader cannot see.
    """
    present = []
    for key in ("enso", "non_enso", "pending"):
        if any((e.get("attribution") or "pending") == key for e in events):
            present.append(key)
    if not present:
        return ""
    items = "".join(
        f'<span class="attr-key">{_attr_tag(k)}'
        f'<span class="attr-gloss">{h(ATTR_GLOSS[k])}</span></span>'
        for k in present)
    # The lead-in is not decoration. It states the posture as a fact
    # before any term is defined, so a reader who skips the definitions
    # still learns the question is answered on every item. Without it the
    # legend is three definitions and no claim.
    return ('<div class="attr-legend">'
            '<span class="attr-lead">Every item says whether El '
            'Ni\u00f1o is involved.</span>'
            f'{items}</div>')


def _load_events() -> list[dict]:
    """Front-page event items from data/events.json (editor-curated).
    Defensive: a malformed file means no break section, never a crash."""
    path = Path(__file__).parent / "data" / "events.json"
    try:
        payload = json.loads(path.read_text())
        events = payload.get("events", [])
        return [e for e in events if isinstance(e, dict) and e.get("title")]
    except (OSError, ValueError):
        return []



# Front-page list length. The fire sweep now publishes every country
# that clears its gate, which was 14 in the first full week. A front
# page cannot carry 14 rows without becoming a table, so the list shows
# the largest few by multiple and links to the channel for the rest.
BREAK_LIST_MAX = 6



_WORLD_SVG_CACHE = None


def _world_map_inner() -> str:
    """Land paths from docs/world-map.svg, ready to drop inside our own
    <svg>. Inlined rather than referenced as an <img> so the land colour
    can follow the theme; an img would bake the light palette in.
    """
    global _WORLD_SVG_CACHE
    if _WORLD_SVG_CACHE is None:
        path = DOCS_DIR / "world-map.svg"
        try:
            raw = path.read_text()
            inner = raw[raw.index(">", raw.index("<svg")) + 1:raw.rindex("</svg>")]
            inner = re.sub(r'<rect width="800" height="400"[^>]*/>', "", inner)
            inner = re.sub(r'<g fill="#[0-9a-fA-F]+" stroke="#[0-9a-fA-F]+"'
                           r'\s+stroke-width="[\d.]+">', '<g class="land">', inner)
            _WORLD_SVG_CACHE = inner
        except (OSError, ValueError):
            _WORLD_SVG_CACHE = ""
    return _WORLD_SVG_CACHE


def _load_markers() -> dict:
    """Fire map markers from data/fire_markers.json (fire-chat generated)."""
    try:
        payload = json.loads((Path(__file__).parent / "data" /
                             "fire_markers.json").read_text())
        if isinstance(payload.get("markers"), list):
            return payload
    except (OSError, ValueError):
        pass
    return {"markers": [], "window": "", "complete": False}


def _pacific_sst() -> dict:
    """Metadata for the SST underlay, or {} when the asset is absent.

    Absent is a normal state, not an error: the field is a hand-refreshed
    asset, so the map has to render without it rather than crash a Monday
    (invariant 1). Extent comes from this file rather than from constants
    retyped into the template, because a field drawn half a basin off is
    worse than no field.
    """
    try:
        meta = json.loads((DOCS_DIR / "pacific-sst.json").read_text())
    except (OSError, ValueError):
        return {}
    if not (DOCS_DIR / "pacific-sst.png").exists():
        return {}
    need = ("lon_west", "lon_east", "lat_south", "lat_north",
            "observation_date")
    return meta if all(meta.get(k) is not None for k in need) else {}


def _issue_href(is_front: bool, root_prefix: str) -> str:
    """Where "this week's issue" points from a given page.

    An issue page is its own target, so it keeps the in-page anchor. The
    front page is not an issue page any more, and after that split three
    href="#issue" links were left on it pointing at an id that is no
    longer there, so they silently did nothing. qa_check follows real
    links but not fragments, which is why it stayed clean throughout.
    Resolved in one place so a fourth copy cannot drift.
    """
    return "#issue" if not is_front else root_prefix + _latest_issue_href()


def _map_html(markers_payload: dict, nino_value, root_prefix: str,
              brief_date_iso: str = "", issue_href: str = "#issue") -> str:
    """The global event map.

    Marker AREA is proportional to the multiple, so radius scales with
    its square root: doubling the area must not look like doubling the
    number. Markers are plain discs, never concentric rings, because
    rings read as an epicenter and that is a causal claim (D-017).

    The Pacific carries the measured SST field where one is available,
    as a PNG underlay beneath the land, with the Nino 3.4 box reduced to
    an outline and its label on top. Before the field existed the box
    was filled flat at the diverging-scale step for the week's index,
    which was the honest maximum when no fetcher returned a grid: the
    spatial structure could not be invented without presenting original
    modeling as observation. The field is observation, so it replaces the
    flat fill and the box goes back to being a locator.

    Eastern Pacific only, by design. The western half sits across the
    map's antimeridian seam and rendering it put a second disconnected
    copy of the same event against Australia. The crop runs off the left
    edge, so it reads as continuing rather than stopping, and it is an
    intrigue generator here rather than the full picture.

    The underlay is a committed asset refreshed by hand
    (design/make_pacific_sst.py), so it carries its own observation date
    from pacific-sst.json and the caption states it. A static picture of
    a moving field that does not say how old it is goes quietly wrong.
    """
    markers = markers_payload.get("markers") or []
    if not markers:
        return ""
    land = _world_map_inner()
    if not land:
        return ""
    peak = max((m.get("multiple") or 0) for m in markers) or 1.0

    def xy(lon, lat):
        return (float(lon) + 180) / 360 * 800, (90 - float(lat)) / 180 * 400

    def radius(mult):
        return max(3.0, 9.0 * ((float(mult) / peak) ** 0.5))

    pins = []
    for m in sorted(markers, key=lambda d: d.get("multiple") or 0):
        try:
            cx, cy = xy(m["lon"], m["lat"])
        except (KeyError, TypeError, ValueError):
            continue
        r = radius(m.get("multiple") or 0)
        href = h(f'{root_prefix}{m.get("href", "")}')
        # A filled disc asserts an event. Four of the fifteen countries
        # on this map are large and above normal but explicitly NOT
        # anomalous, and DR Congo is the clearest: 75,849 detections at
        # exactly 1.0x, the largest fire system on Earth behaving
        # completely normally. It belongs on a world fire map and it is
        # not news, and one symbol cannot say both. So an anomaly is a
        # filled disc and context is an open ring at the same radius:
        # present, sized honestly, and not claiming anything.
        #
        # TWO reasons a marker can be non-anomalous, and only one was
        # labelled. `volume_context` means large and shown for scale;
        # `pinned` means shown every week so the country can be checked.
        # Canada sat at 0.4x, the furthest BELOW normal on the page,
        # with no qualifier at all, while Angola at 0.9x carried "within
        # its historical range". QA read that as an unexplained
        # asymmetry and they were right that it needed an answer.
        #
        # Pinned countries do NOT get "within its historical range".
        # The gate tests for an unusually HIGH week, so failing it says
        # nothing about a country sitting at 40% of normal: that could
        # be ordinary or it could be unusual in the other direction, and
        # this instrument does not distinguish them. The honest label is
        # why it is on the map, which is also what the fires index says
        # in its own row qualifier.
        anom = m.get("anomalous")
        ctx = (m.get("volume_context") and not anom)
        pin = (m.get("pinned") and not anom and not ctx)
        base = (f'{m.get("region", "")}, {m.get("multiple")} times its '
                f'same-week average')
        if ctx:
            label = base + ", within its historical range"
        elif pin:
            label = base + ", shown every week so this country can be checked"
        else:
            label = base
        pins.append(
            # Open ring for ANY non-anomalous marker, not just the
            # volume-context ones. A filled disc asserts an event, and
            # Canada at 0.4x of its own normal was drawing one: the
            # furthest below normal on the map, rendered in the symbol
            # that means "this is the news". The ring is the whole
            # device for saying present-but-not-claiming, and it was
            # gated on the narrower flag by accident.
            f'<a class="mk{"" if anom else " ctx"}" href="{href}" '
            f'aria-label="{h(label)}">'
            f'<circle class="mk-hit" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{max(r + 7, 12):.1f}"/>'
            f'<circle class="mk-focus" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{r + 4:.2f}"/>'
            f'<circle class="mk-ring" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{r + 1.6:.2f}"/>'
            f'<circle class="mk-dot" cx="{cx:.1f}" cy="{cy:.1f}" '
            f'r="{r:.2f}"/></a>')

    # The field, under the land so coastlines cut it cleanly. Placed from
    # the asset's own recorded extent.
    sst = _pacific_sst()
    field = ""
    if sst:
        fx1, fy1 = xy(sst["lon_west"], sst["lat_north"])
        fx2, fy2 = xy(sst["lon_east"], sst["lat_south"])
        # The field is the largest and most legible thing on the map, so
        # it is also the obvious thing to click, and it was inert. It now
        # carries the same link as the Nino 3.4 mark, with an accessible
        # name on the anchor: the image itself stays aria-hidden, because
        # a decorative raster has nothing useful to announce and the
        # anchor is what a screen reader should reach.
        field = (
            f'<a class="sst-g" href="{h(issue_href)}" '
            f'aria-label="Pacific sea surface temperature anomaly this '
            f'week. Goes to the El Nino tracker.">'
            f'<image class="sstfield" href="{h(root_prefix)}pacific-sst.png" '
            f'x="{fx1:.2f}" y="{fy1:.2f}" width="{fx2 - fx1:.2f}" '
            f'height="{fy2 - fy1:.2f}" preserveAspectRatio="none" '
            f'aria-hidden="true"/></a>')

    nino = ""
    if nino_value is not None:
        # Nino 3.4 region: 170W to 120W, 5N to 5S. The FILL is the datum,
        # taken from the same scale the legend prints, so the box can be
        # decoded against it. It carries a hairline outline only: a heavy
        # stroke in the channel hue made this read as a UI selection box
        # rather than as a measured value, which is the opposite of the
        # intent. The region boundary is real geography, so it earns a
        # line, but a quiet one.
        x1, y1 = xy(-170, 5)
        x2, y2 = xy(-120, -5)
        # Extent bracket: a hairline just below 5S spanning 170W to 120W,
        # with short ticks turning up at each end. It states the same
        # region as the old box using one open line instead of four
        # closed sides.
        yb = y2 + 4.0
        bracket = (f'M{x1:.1f},{yb - 4.5:.1f} L{x1:.1f},{yb:.1f} '
                   f'L{x2:.1f},{yb:.1f} L{x2:.1f},{yb - 4.5:.1f}')
        nino = (
            f'<a class="nino-g" href="{h(issue_href)}" aria-label="Nino 3.4 region, '
            f'{nino_value:+.1f} degrees Celsius this week. Goes to the El '
            f'Nino issue.">'
            # Two treatments, because what the mark has to do changed when
            # the field arrived.
            #
            # With the field: an extent bracket under the region, not a
            # box around it. A closed rectangle over the strongest part of
            # the field was the loudest thing in the frame, brighter than
            # any data, and it enclosed on four sides, which the Bulletin
            # rules forbid. It also no longer had a job: the box was the
            # datum when a flat fill was all we had, and the field is the
            # datum now. The bracket still earns its place, because the
            # headline number is the average of this strip and the field
            # peaks at more than twice it, so a bare "+2.2 C" floating on
            # the Pacific would read as the whole ocean.
            #
            # Without the field: keep the filled box. It is then the only
            # measured thing on the map.
            + (f'<path class="nino-brk-halo" d="{bracket}"/>'
               f'<path class="nino-brk" d="{bracket}"/>'
               if field else
               f'<rect class="nino-halo" x="{x1:.1f}" y="{y1:.1f}" '
               f'width="{x2 - x1:.1f}" height="{y2 - y1:.1f}"/>'
               f'<rect class="nino-box" x="{x1:.1f}" y="{y1:.1f}" '
               f'width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" '
               f'fill="{T.anomaly_color(nino_value, T.OCEAN_SCALE)}"/>')
            # Label and value are one object and now read as one. The
            # label used to sit above the region's northern edge, which
            # was fine when a box enclosed the region and gave it
            # something to belong to. Against a bracket it floated over
            # pale water with nothing tying it to anything, while the
            # value below was correctly anchored. Both now stack at the
            # bracket's left tip, label first.
            + (f'<text class="nino-lb" x="{x1:.1f}" y="{yb + 13:.1f}">'
               f'NI\u00d1O 3.4</text>'
               f'<text class="nino-v" x="{x1:.1f}" y="{yb + 30:.1f}">'
               f'{nino_value:+.1f} \u00b0C</text>'
               if field else
               f'<text class="nino-lb" x="{x1:.1f}" y="{y1 - 7:.1f}">'
               f'NI\u00d1O 3.4</text>'
               f'<text class="nino-v" x="{x1:.1f}" y="{y2 + 17:.1f}">'
               f'{nino_value:+.1f} \u00b0C</text>')
            + '</a>')

    # Hard stops, not a gradient. The fills are nine discrete steps, so
    # an interpolating ramp would let a reader decode a colour off the
    # legend that never appears on the map.
    ramp = "".join(
        f'<stop offset="{i / 9:.4f}" stop-color="{c}"/>'
        f'<stop offset="{(i + 1) / 9:.4f}" stop-color="{c}"/>'
        for i, c in enumerate(T.ANOMALY))
    keys = "".join(
        f'<circle class="lg-dot" cx="{cx}" cy="26" r="{radius(v):.2f}"/>'
        f'<text class="lg-tx" x="{cx}" y="46" text-anchor="middle">{v:g}x</text>'
        for cx, v in [(16, 2), (52, 6), (96, peak)])
    # Caret marking where this week's index sits on the printed ramp.
    nino_tick = ""
    if nino_value is not None:
        tx = max(0.0, min(1.0, (float(nino_value) + T.OCEAN_SCALE)
                          / (2 * T.OCEAN_SCALE))) * 170
        nino_tick = (
            f'<path class="lg-tick" d="M{tx:.1f},18 l-4,-6 l8,0 z"/>'
            f'<text class="lg-now" x="{tx:.1f}" y="9" text-anchor="middle">'
            f'{float(nino_value):+.1f}</text>')

    window = markers_payload.get("window", "")
    return (
        '<div class="mapwrap">'
        '<div class="mapcap">'
        '<span class="eyebrow">Where, and how big</span>'
        '<span class="eyebrow">Marker area = multiple of that place\u2019s '
        'own baseline</span>'
        + (f'<span class="eyebrow">Issue {h(brief_date_iso)}</span>'
           if brief_date_iso else '')
        + (f'<span class="eyebrow">Observed 7 days to '
           f'{h(sst["observation_date"])}</span>' if sst else '')
        + '</div>'
        + '<svg class="map" viewBox="0 0 800 400" role="group" '
        'aria-label="World map of this week\u2019s events">'
        f'<defs><linearGradient id="anomramp" x1="0" y1="0" x2="1" y2="0">'
        f'{ramp}</linearGradient></defs>'
        f'{field}{land}{nino}{"".join(pins)}</svg>'
        '<div class="legends">'
        f'<svg width="160" height="52" aria-hidden="true">'
        f'<text class="lg-tx" x="0" y="10">MULTIPLE OF BASELINE</text>'
        f'{keys}</svg>'
        f'<svg width="230" height="56" aria-hidden="true">'
        f'<text class="lg-tx" x="0" y="10">SST ANOMALY</text>'
        f'<rect x="0" y="22" width="170" height="9" fill="url(#anomramp)"/>'
        f'{nino_tick}'
        f'<path class="lg-cap" d="M0,22 l-7,4.5 l7,4.5 z"/>'
        f'<path class="lg-cap" d="M170,22 l7,4.5 l-7,4.5 z"/>'
        f'<text class="lg-tx" x="-7" y="47">\u2264\u2212{T.OCEAN_SCALE:g}</text>'
        f'<text class="lg-tx" x="80" y="47">0</text>'
        f'<text class="lg-tx" x="140" y="47">\u2265+{T.OCEAN_SCALE:g} \u00b0C</text>'
        f'</svg>'
        '</div>'
        + (f'<p class="mapnote">Week {h(window)}, seven fully closed UTC '
           f'days. Every country that cleared its baseline gate is on the '
           f'map.</p>' if window else '')
        + (f'<p class="mapnote">Pacific SST anomaly against the 1991-2020 '
           f'climatology, nine steps to \u00b1{T.OCEAN_SCALE:g} \u00b0C. '
           f'The end steps are open: {sst["fraction_beyond_scale"] * 100:.1f}% '
           f'of cells lie beyond the scale and the week\u2019s highest is '
           f'{sst["anomaly_max"]:+.2f} \u00b0C. Near-zero water is not '
           f'shaded, so bare page inside the band means an unremarkable '
           f'anomaly, not missing data. The window is the Pacific alone, '
           f'{abs(sst["lat_south"]):.0f}\u00b0S to '
           f'{abs(sst["lat_north"]):.0f}\u00b0N and the dateline east to '
           f'{abs(sst["lon_east"]):.0f}\u00b0W, so its upper edge is a chosen '
           f'boundary and not the end of the anomaly.</p>'
           if sst else '')
        + '</div>'
    )


def _latest_issue_href() -> str:
    """Path to the El Nino channel home, relative to the docs root.

    This used to resolve to the newest dated archive, which made an
    immutable record the channel's front door. Two costs: the nav target
    changed URL every week, and the page a reader landed on could not be
    restyled or corrected without touching a frozen archive, which
    invariant 5 forbids. So the channel has a standing home at
    /elnino/ that renders the current issue live, and the dated pages go
    back to being purely the record.

    Constant, not probed. An earlier version returned elnino/ only if
    the file already existed, which made the nav depend on build order:
    that page is written last, so within a single publish the four
    pages built before it linked to the dated archive and the fire page
    built after it linked to the channel home. One run, two navs. The
    page is always in publish_all's TARGETS, and qa_check's dead-link
    pass is what catches its absence, rather than the nav quietly
    rerouting itself.
    """
    return ELNINO_HREF


def _masthead_html(root_prefix: str, methodology_href: str,
                   briefs_href: str, active: str = "elnino",
                   mark_opacities: tuple | None = None) -> str:
    home = root_prefix if root_prefix else "./"
    on = lambda key: ' class="on"' if key == active else ""
    return (
        '<header class="field"><div class="field-shell">'
        '<div class="masthead">'
        f'<a class="brand" href="{h(home)}" aria-label="{h(SITE_NAME)}, home">'
        f'{_mark_svg(26, mark_opacities)}<span class="brand-name">{h(SITE_NAME)}</span></a>'
        '<nav class="prodnav" aria-label="Sections">'
        + "".join(
            # One class attribute. Emitting the active flag and the
            # channel class separately produced <a class="on"
            # class="ch-elnino">, and a browser keeps the first and drops
            # the second, so the channel hue never applied to the active
            # item.
            '<a class="{cls}" href="{href}">{label}</a>'.format(
                cls=" ".join(x for x in (f"ch-{key}",
                                         "on" if key == active else "") if x),
                href=h(root_prefix + (href if href is not None
                                      else _latest_issue_href())),
                label=label)
            for key, label, href in CHANNELS)
        + f'<a class="util" href="{h(root_prefix)}about.html">About</a>'
        + '</nav></div></div></header>\n'
    )


def site_masthead(root_prefix: str = "", active: str = "",
                  methodology_href: str = "methodology.html",
                  briefs_href: str = "briefs/") -> str:
    """The house masthead, for generators outside run_brief.

    Pair it with SITE_MASTHEAD_CSS if the page does not already include
    PUBLIC_CSS. root_prefix is the path back to the docs root: "" from
    docs/, "../" from docs/fires/. active is a channel key from CHANNELS.
    """
    return _masthead_html(root_prefix, methodology_href, briefs_href,
                          active=active)


def _break_html(events: list[dict]) -> str:
    """The break (T10): current events lead the front page, each with its
    baseline number and attribution tag. Renders nothing when the events
    file is empty; no placeholder slots."""
    if not events:
        return ""
    shown = events[:BREAK_LIST_MAX]
    hidden = len(events) - len(shown)
    items = []
    for e in shown:
        href = e.get("href", "")
        region = h(e.get("region", ""))
        claim = h(e.get("title", ""))
        # Region carries the weight, the claim runs on the same line in
        # softer ink. Linked as one unit so the whole line is the target.
        head = (f'<span class="ev-region">{region}</span> '
                f'<span class="ev-claim">{claim}</span>')
        if href:
            head = f'<a href="{h(href)}">{head}</a>'
        stat = e.get("stat", "")
        stat_html = f'<div class="ev-stat num">{h(stat)}</div>' if stat else ""
        baseline = e.get("stat_label", "")
        src_bits = " · ".join(
            b for b in (e.get("source", ""), f"baseline: {baseline}" if baseline
                        else "") if b)
        items.append(
            '<article class="event">'
            f'{stat_html}'
            f'<div class="ev-body"><h3>{head}</h3>'
            f'<span class="ev-src">{h(src_bits)}</span></div>'
            f'{_attr_tag(e.get("attribution", "pending"))}'
            '</article>'
        )
    # A silent top-N would read as "this is everything". Say the count.
    more = ""
    if hidden > 0:
        more = (f'<p class="break-more"><a href="fires/">'
                f'{hidden} more countries cleared their baseline this week '
                f'&rarr;</a></p>')
    return (
        '<div class="field"><div class="field-shell">'
        '<div class="break-head">'
        '<div class="eyebrow">The break &middot; in the news now</div>'
        '</div>'
        '<p class="break-lede">Current events, each sized against its own '
        'historical baseline. The link to the El Ni&ntilde;o window is '
        'stated per item, never assumed.</p>'
        + _attr_legend(shown)
        + f'<div class="events">{"".join(items)}</div>'
        f'{more}'
        '</div></div>\n'
    )


def _wave_strip_html(magn_pct, brief_date_iso: str,
                     issue_href: str = "#issue") -> str:
    """The wave (T10): the tracker's headline stays persistent but
    secondary; the full issue is further down the same page."""
    return (
        '<div class="wave-strip"><div class="field-shell">'
        '<span class="ws-label eyebrow">The wave &middot; '
        f'{h(PRODUCT_NAME)}</span>'
        '<span class="ws-read">'
        f'<span class="ws-num num">{magn_pct}<small>%</small></span>'
        '<span class="ws-desc">chance of a 1997 / 2015-magnitude winter '
        f'peak &middot; issue of {h(brief_date_iso)}</span>'
        '</span>'
        f'<a class="ws-go" href="{h(issue_href)}">This week\'s issue '
        f'&rarr;</a>'
        '</div></div>\n'
    )



def _basis(label: str) -> str:
    """The comparison basis for one row of the physical-state table.

    Set small and faint under the indicator name, in the same slot the
    CWWA row already uses for its units. A table whose rows compare on
    different bases has to say so per row; the alternative is a column
    header that is true for some rows and false for others, which is
    what this table shipped with.
    """
    return ('<br><span style="color:var(--text-faint); font-size:12px">'
            f'vs {h(label)}</span>')


def _ocean_heat_html(phys: dict, analog_same: dict) -> str:
    """The hero's right column: subsurface heat now against the two
    super-event analogs, on whatever basis the analog constants are
    actually on.

    Bar colour comes from the diverging anomaly scale, never a channel
    hue (D-016 amendment 4): this is a physical magnitude, and a Fire
    red here would make an ENSO datum read as a Fire datum. Length and
    colour therefore encode the same quantity twice.

    The basis is read off the constants rather than asserted. This block
    shipped captioned "same calendar week" while reading
    1997_apr_heat_content and 2015_apr_heat_content, which are frozen
    late-April values: it compared July 2026 against April 1997 and
    April 2015 and told the reader the weeks matched. Three bars side by
    side claim like-for-like by construction, harder than a sentence
    does, so a wrong basis is worse here than in prose. ENSO tracker is
    fetching same-week analog values for 2026-08-03; until those exist
    the label names April, and it flips on its own when the keys land,
    so the caption cannot go stale independently of the data again.
    """
    now = phys.get("heat_content_0_300m_estimate")
    if now is None:
        return ""
    same_month = phys.get("heat_content_analogs_same_month") or {}
    month = phys.get("heat_content_data_month")
    if same_month.get("1997") is not None:
        basis = f"same month{f', {month}' if month else ''}"
        v97, v15 = same_month.get("1997"), same_month.get("2015")
    else:
        basis = "2026 this week, analogs at late April"
        v97 = analog_same.get("1997_apr_heat_content")
        v15 = analog_same.get("2015_apr_heat_content")
    same_basis = bool(same_month.get("1997") is not None)
    rows = [("2026", float(now), True), ("2015", v15, False),
            ("1997", v97, False)]
    rows = [(y, float(v), cur) for y, v, cur in rows if v is not None]

    # Bars diverge from zero and are normalised on the SAME absolute
    # scale as their colour, T.OCEAN_SCALE. An earlier version used
    # abs(value) over the span of the rows present, which meant two
    # things: -0.5 and +0.5 drew identical bars, and bar lengths
    # rescaled every week as the maximum moved, so two issues
    # screenshotted a month apart were not comparable. On a site whose
    # distribution channel is the screenshot that is a real cost. The
    # track is now the full ramp width, zero sits at its centre, and a
    # cold year runs left.
    scale = T.OCEAN_SCALE
    zero_pct = 50.0

    out = ['<div class="heat">',
           '<span class="cap eyebrow">Ocean heat, 0 to 300 m'
           f' &middot; {h(basis)}</span>']
    for year, val, is_now in rows:
        clamped = max(-scale, min(scale, val))
        left = (min(0.0, clamped) + scale) / (2 * scale) * 100.0
        width = max(1.0, abs(clamped) / (2 * scale) * 100.0)
        out.append(
            f'<div class="hrow{" now" if is_now else ""}">'
            f'<span class="yr">{h(year)}</span>'
            f'<span class="htrack">'
            f'<span class="hzero" style="left:{zero_pct:.2f}%"></span>'
            f'<span class="hbar" style="background:'
            f'{T.anomaly_color(val, T.OCEAN_SCALE)};'
            f'left:{left:.2f}%;width:{width:.2f}%"></span>'
            f'</span>'
            f'<span class="val">{val:+.2f}</span></div>')
    out.append(
        '<p class="hnote">Degrees Celsius anomaly, diverging from zero. '
        'Bar colour is the position on the anomaly scale, not a channel '
        'hue.'
        + ('' if same_basis else
           ' The two analog values are late-April readings set against a '
           'current value from this week, so the comparison is not '
           'like-for-like and the small gap shown should not be read as '
           'a lead.')
        + '</p></div>')
    return "".join(out)


def _issue_meta_html(brief_date_iso: str, offset_phrase: str,
                     freshness: dict, briefs_href: str = "briefs/",
                     as_published_href: str = "") -> str:
    """Issue metadata, as a strip above the footer.

    This was a sticky rail. The delivered spec has no rail on the issue
    page, and Kristjan moved Methodology and Archive off the site nav on
    the grounds that they are El Nino artifacts rather than house-level
    ones. So the furniture lands here and in the stamp instead, and the
    page keeps a single column.
    """
    live = sum(1 for i in freshness.values()
               if i.get("ok") and not i.get("used_fallback"))
    total = len(freshness) or 1
    try:
        next_iso = (date.fromisoformat(brief_date_iso)
                    + timedelta(days=7)).isoformat()
    except ValueError:
        next_iso = "next Monday"
    cells = [
        ("Issue", f"<b>{h(brief_date_iso)}</b>"),
        ("Methodology", f"<b>v{h(str(S.METHODOLOGY_VERSION))}</b>"),
        ("RONI offset", h(offset_phrase)),
        ("Sources", f"<b>{live}</b> of {total} live"),
        ("Next issue", h(next_iso)),
        ("Archive", f'<a href="{h(briefs_href)}">every issue, immutable</a>'),
    ]
    # On the channel home this page is a live rendering of the current
    # issue, so it points at the frozen copy that is the citable record.
    # Absent on the dated pages, which are that record.
    if as_published_href:
        cells.append(("As published",
                      f'<a href="{h(as_published_href)}">'
                      f'{h(brief_date_iso)}, frozen</a>'))
    return ('<div class="issue-meta">'
            + "".join(f'<div><span class="k">{h(k)}</span>'
                      f'<span class="v">{v}</span></div>' for k, v in cells)
            + '</div>')


def _channels_html(root_prefix: str, issue_href: str = "#issue") -> str:
    """Products grid (front page). Channels are siblings under the house
    question, per T9; the tracker is one of them, not the source signal."""
    return (
        '<section>'
        '<h2>Channels</h2>'
        '<p class="section-sub">Each channel reads one domain against its '
        'own baselines, as its own publication.</p>'
        '<div class="chans">'
        '<div class="chan">'
        f'<div class="chan-top"><span class="dot" style="background:{T.NINO}"></span>'
        '<span class="meta">Live &middot; weekly</span></div>'
        f'<h3><a href="{h(issue_href)}">{h(PRODUCT_NAME)}</a></h3>'
        '<p>Weekly probability tracker for the DJF winter peak, aggregated '
        'across seven agency and model sources. Every issue archived, '
        'immutable.</p></div>'
        '<div class="chan">'
        f'<div class="chan-top"><span class="dot" style="background:{T.FIRE}"></span>'
        '<span class="meta">First issue 2026-08-03</span></div>'
        f'<h3><a href="{h(root_prefix)}fires/">Fires</a></h3>'
        '<p>Hotspot activity against same-week satellite baselines across '
        'five regions, plus a vintage-tracked damage ledger.</p></div>'
        '<div class="chan next">'
        '<div class="chan-top"><span class="dot" '
        f'style="background:{T.RULE}"></span>'
        '<span class="meta">Not scheduled</span></div>'
        '<h3>Next channel</h3>'
        '<p>Candidates: floods and crops. Each needs its own baseline '
        'before it ships.</p></div>'
        '</div></section>'
    )


def _email_capture_html() -> str:
    """The front-page capture slot: the real form, not a link to one.

    Gated on EMAIL_SIGNUP_URL until now, which was empty, so this rendered
    nothing and the front page had no capture at all. The gate is gone
    because the form is no longer a link to somewhere else.

    Its old copy was also stale in two ways. It promised "the updated
    probabilities and what changed", which describes the El Nino tracker
    alone and not the four channels the site now runs. And it led on what
    a reader would NOT get ("No more than that"), which is the framing
    Kristjan rejected on the subscribe page for the same reason: it is a
    reason not to subscribe, stated as though it were a reason to.

    The promise sentence is EMAIL_CAPTURE_PROMISE, defined once and read
    by templates/subscribe.py too, so the two surfaces cannot drift. The
    words are editor's and are not to be edited here.

    A LINK, NOT AN EMBEDDED FORM, and that is deliberate.

    The Beehiiv embed was here and came out. QA measured it absent on
    three of four cold loads, with the one success following a
    /subscribe/ visit in the same session, so the script was warm. A
    reader reaching the bottom of the front page got the eyebrow, the
    promise, a rule, seventy pixels of nothing, then the footer.

    It also arrives wrong when it does arrive: a white panel on bone
    paper, our wordmark repeated inside it in a different serif, a black
    button with rounded corners against a system that is radius 0, and
    an input clipped to a single character at 300px because the iframe
    is a fixed width we cannot reach across the origin boundary.

    None of that is fixable in our CSS, so the front page stops
    depending on it. The link is ours: it always renders, it is in our
    type, and it cannot arrive 300px wide. The inline form stays on
    /subscribe/, where a reader has already chosen to be and will
    tolerate a seam that a passer-by would just read as broken.

    Reinstate the embed only when the provider renders reliably and in
    something close to this system, which may mean a different provider.
    """
    return (
        '<section><div class="email-cap">'
        '<div class="ec-pitch">'
        '<span class="eyebrow">One email a week</span>'
        f'<p>{h(EMAIL_CAPTURE_PROMISE)}</p></div>'
        f'{email_capture_form()}'
        '</div></section>'
    )


def _number_sections(html_text: str) -> str:
    """Give plain and impacts sections the numbered sec-head treatment.
    Callout sections (analyst-read) keep their unnumbered headings."""
    counter = {"n": 0}

    def repl(m):
        counter["n"] += 1
        return (f'<section{m.group(1)}><div class="sec-head">'
                f'<div class="eyebrow">{counter["n"]:02d}</div>'
                f'<h2>{m.group(2)}</h2></div>')

    return re.sub(r'<section((?: class="impacts")?)><h2>(.*?)</h2>',
                  repl, html_text)


def build_public_html(fetched: dict, freshness: dict, headline: dict,
                      methodology_href: str, brief_date_iso: str,
                      canonical_url: str, og_image_url: str,
                      world_map_href: str = "world-map.svg",
                      prev_headline: dict | None = None,
                      prev_snapshot: dict | None = None,
                      prev_headline_month: dict | None = None,
                      briefs_href: str = "briefs/",
                      root_prefix: str = "",
                      is_front: bool = False,
                      as_published_href: str = "",
                      asset_prefix: str = "") -> str:
    """Render the public brief as structured HTML (bypasses markdown).

    methodology_href and world_map_href are both relative paths whose depth
    differs between the index ("methodology.html", "world-map.svg") and the
    archive briefs ("../../methodology.html", "../../world-map.svg").
    canonical_url and og_image_url are absolute Pages URLs for the
    OG/Twitter card metadata.

    prev_headline (WoW): smoothed buckets from last week's archive. Used by
    Analyst-section observers ("CPC re-issued, super +12pp from last week").

    prev_headline_month (version-aware ladder-delta info): an info dict
    {"buckets": ..., "date": ..., "label": ...} from a prior archive
    with matching methodology_version. Prefers ≥28 days back ("vs last
    month"); falls back to the oldest available archive in the brief's
    first month ("since first issue"). None means no delta is shown on
    the rungs (methodology-version mismatch, or no prior archive at all).
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

    # Bottom-line numbers from the headline. The default copy quotes the
    # super and magnitude buckets; the +1.0/+1.5 buckets were retired from
    # the public surface 2026-07-13 after pinning at 100% (data still
    # computed and archived).
    super_pct = headline["super_>2.0"]["mid"]
    magn_pct = headline["9715_>2.5"]["mid"]
    far_pct = headline.get("record_>3.5", {}).get("mid")
    description = (f"Weekly probability tracker for the developing 2026-27 El Niño "
                   f"event. {magn_pct}% chance of a 1997/2015-magnitude winter peak.")
    if is_front:
        title = f"{SITE_NAME} · how big is this, actually?"
    else:
        title = f"{PRODUCT_NAME}, week of {brief_date_iso} · {SITE_NAME}"

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
            f'{super_pct}% chance of a very strong / super El Niño this winter, '
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
<style>{T.font_faces_css(root_prefix + "fonts/")}</style>
{_favicon_links(root_prefix)}<style>{PUBLIC_CSS}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
'''
    week_events = _load_events()
    mark_ops = _week_mark_opacities(week_events)
    head += _masthead_html(root_prefix, methodology_href, briefs_href,
                           mark_opacities=mark_ops)

    # Shared stamp line for the issue. The card link resolves in both
    # the docs root and the archive dir (card.png sits alongside each).
    stamp_html = (
        '<div class="issue-stamp">'
        f'<span>Week of {h(brief_date_iso)}</span>'
        f'<span><a href="{h(methodology_href)}">methodology '
        f'v{h(str(S.METHODOLOGY_VERSION))}</a></span>'
        '<span>immutable</span>'
        f'<span><a class="card-link" href="{h(asset_prefix)}card.png">one-page card &darr;</a></span>'
        '</div>'
    )
    lede_text = (
        'Updated each Monday from the major ENSO outlooks (NOAA CPC, IRI, '
        'BoM) and a multi-model forecast consensus (ECMWF SEAS5 with the '
        'NMME suite), plus weekly Niño 3.4 observations. Peak season '
        'target: <strong>DJF 2026-27</strong>. Forecast disagreements are '
        'surfaced rather than averaged.'
    )

    if is_front:
        # T10 hybrid front page: the break leads, the wave strip carries
        # the tracker headline, and the full issue follows on paper.
        # The lead is the largest published event, in the words the
        # channel that measured it chose. The design chat does not author
        # event claims; `title` comes straight from the fire pipeline.
        lead = week_events[0] if week_events else None
        if lead:
            # NO COUNT IN THE LEDE. Product's call under D-077 and it
            # supersedes the corrected figure I had put here.
            #
            # The sentence read "14 other countries also cleared their
            # own baseline" while five of them had not, Canada at 0.4x
            # being the furthest BELOW normal on the page. Counting the
            # `anomalous` flag instead gives a true nine.
            #
            # But nine is true and meaningless. Fire ran our own gate
            # against every historical year of this window, leave one
            # out: an ordinary week yields a mean of 7.6 qualifiers,
            # median 8, range 3 to 10, and this week's ten TIES the
            # maximum rather than exceeding it. The rank==1 clause is
            # satisfied by each country exactly once across the record
            # by construction, manufacturing roughly seven qualifiers a
            # year regardless of the weather. Replacing a false number
            # with a meaningless one is not a fix.
            #
            # Third channel to reach this today, after CRO found it
            # three times in crops: aggregate counts of
            # threshold-crossings sit near chance in this data, and the
            # individual extremes are the finding. So the lede leads
            # with Greece and stops.
            head += (
                '<div class="field"><div class="field-shell">'
                '<div class="lead-block">'
                f'<div class="eyebrow">Week of {h(brief_date_iso)}</div>'
                f'<h1 class="lead-answer">'
                f'{h(lead_sentence(lead) or (lead.get("region", "") + " ran " + lead.get("stat", "") + " its average for this week of the year."))}'
                f'</h1>'
                + f'<p class="lead-stand">Each item below says whether it '
                  f'is linked to El Ni&ntilde;o, and most are not.</p>'
                + '</div></div></div>\n')
        head += _map_html(_load_markers(),
                          (fetched.get("physical_state") or {})
                          .get("nino34_weekly_traditional"),
                          root_prefix, brief_date_iso,
                          _issue_href(is_front, root_prefix))
        head += _break_html(week_events)
        head += _wave_strip_html(magn_pct, brief_date_iso,
                                 _issue_href(is_front, root_prefix))
        issue_open = '<div class="shell"><main class="body">'
    else:
        # Archive issue page, built to the delivered spec: the answer on
        # the left, the ocean heat comparison on the right. The hero no
        # longer restates the probability ladder that follows it.
        issue_open = (
            '<div class="shell"><main class="body" id="issue">'
            '<div class="top"><div>'
            + stamp_html
            + '<h1>How likely is a super El Niño this winter?</h1>'
            + f'<p class="lede">{lede_text}</p>'
            + '</div>'
            + _ocean_heat_html(phys, analog_same)
            + '</div>'
            + bottom_line_html
        )
    head += issue_open

    # Unpack the version-aware ladder-delta info dict. prev_buckets is the
    # smoothed headline buckets we compare against; delta_label is the
    # human suffix ("vs last month" when the prior is ≥28 days back,
    # "since first issue" for the fallback that runs while the brief is
    # still in its first month).
    prev_buckets = prev_headline_month["buckets"] if prev_headline_month else None
    delta_label = prev_headline_month["label"] if prev_headline_month else "vs last month"

    def _prev_mid(key: str):
        # Ladder delta uses the version-aware prior headline. prev_headline
        # (WoW) is reserved for Analyst observers and stays separate.
        if not prev_buckets:
            return None
        return (prev_buckets.get(key) or {}).get("mid")

    # The two beyond-record rungs sit above the calibrated rungs and are
    # rendered progressively muted: +3.0 ("beyond instrumental record",
    # v1.8) dashed and tagged "highly uncertain"; +3.5 ("far beyond
    # record", added 2026-07-06 when the July SEAS5 run saturated +3.0)
    # dotted, faintest, tagged "most uncertain". +3.5 has effectively no
    # agency anchor and is the least-anchored figure on the ladder. Both
    # guarded so the brief still renders if a headline dict lacks them.
    far_rung = ""
    if "record_>3.5" in headline:
        far_rung = _render_rung(
            "far", "+3.5°C peak", headline["record_>3.5"],
            "Far beyond the record", _prev_mid("record_>3.5"),
            delta_label, tag="most uncertain")
    record_rung = ""
    if "record_>3.0" in headline:
        record_rung = _render_rung(
            "record", "+3.0°C peak", headline["record_>3.0"],
            "Beyond the instrumental record", _prev_mid("record_>3.0"),
            delta_label, tag="highly uncertain")

    # Retired rungs (2026-07-13, Kristjan's call): +1.0 "at least moderate"
    # and +1.5 "strong" had been pinned at 100% since mid-June and carried
    # no information, so they are dropped from the PUBLIC render only. The
    # headline computation, the internal brief, and meta.json keep all six
    # buckets, so the archive time series and month-over-month deltas stay
    # unbroken. The buckets-note carries a one-line retirement footnote for
    # continuity; the event outgrowing the bottom of the scale is itself
    # part of the story.
    # Rung order is BUCKET_ORDER; the archive trend derives its column
    # order from the same constant. Reorder there, not here.
    ladder_html = (
        '<section><h2>Probability ladder</h2>'
        '<p class="section-sub">Peak three-month ONI, DJF 2026-27. Each rung '
        'is computed independently; adding one does not recalculate the '
        'others.</p>'
        '<div class="ladder">'
        + far_rung
        + record_rung
        + _render_rung("magn",     "+2.5°C peak", headline["9715_>2.5"],
                       "1997 / 2015 magnitude", _prev_mid("9715_>2.5"), delta_label)
        + _render_rung("super",    "+2.0°C peak", headline["super_>2.0"],
                       "Very strong / super",   _prev_mid("super_>2.0"), delta_label)
        + '</div>'
        + f'<p class="buckets-note">The "at least moderate" (+1.0°C) and "strong" (+1.5°C) '
          f'thresholds reached 100% in June and have been retired from the ladder; the event has '
          f'outgrown the bottom of the scale. Their full history stays in the '
          f'<a href="{h(briefs_href)}">archive</a>. Probabilities use the consensus estimator: a CPC-derived '
          f'anchor ({offset_phrase}, skew-normal fit on the strength table) deflected toward an '
          f'equal-weight multi-model consensus (ECMWF SEAS5 plus the NMME suite), consensus-led at '
          f'weight 0.85. The rungs above +2.5°C are different in kind: no event in the '
          f'instrumental record has reached them, so they carry little to no agency anchor and are '
          f'driven mostly by direct model member counts. The +3.5°C rung is the furthest out: no '
          f'official agency forecasts a threshold that extreme, so read it as where the hottest '
          f'dynamical runs are clustering, not a calibrated probability. Adding a rung does not '
          f'recalculate the others, so their week-over-week deltas stay comparable. Deltas compare '
          f'to the issue four weeks prior, aligned with CPC\'s monthly cadence; in the brief\'s '
          f'first month the comparison falls back to the launch issue, and weeks crossing a '
          f'methodology-version change show no delta. Full estimator math on the '
          f'<a href="{h(methodology_href)}">methodology page</a>.</p>'
        + '</section>'
    )

    # Chart caption dynamic values for the merged multi-model fan. Computed
    # defensively with fallbacks so the caption never crashes the brief.
    _MONTHS = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

    def _fmt_cal(s, fallback):
        try:
            yy, mm = str(s).split("-")
            return f"{_MONTHS[int(mm)]} {yy}"
        except (ValueError, IndexError):
            return str(s) if s else fallback

    _SEASON_ORDER = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS",
                     "ASO", "SON", "OND", "NDJ"]
    obs_season, obs_val = "latest", None
    _sm_2026 = (by_year.get(2026) or by_year.get("2026")) if by_year else None
    if isinstance(_sm_2026, dict):
        for _s in reversed(_SEASON_ORDER):
            try:
                obs_val = float(_sm_2026[_s])
                obs_season = _s
                break
            except (KeyError, TypeError, ValueError):
                continue
    obs_str = _signed_temp(obs_val, 1) if obs_val is not None else "near 0"
    seas5_end = _fmt_cal(ecmwf.get("max_lead_calendar"), "this autumn")
    # Extension end date: prefer the v1.9 pooled NMME trajectory, fall back
    # to the older CFSv2-only key so pre-v1.9 data still captions cleanly.
    _ext_traj = ((fetched.get("nmme") or {}).get("pooled_trajectory")
                 or (fetched.get("nmme") or {}).get("cfsv2_trajectory") or [])
    ext_end = _fmt_cal(_ext_traj[-1].get("calendar") if _ext_traj else None,
                       "early 2027")

    chart_html = (
        '<section>'
        '<h2>Analog tracker</h2>'
        '<p class="section-sub">2026-27 trajectory vs reference El Niño events, plus a combined SEAS5 and NMME multi-model forecast carried through the winter peak.</p>'
        '<div class="two"><div class="chart-card">'
        f'<img src="{h(asset_prefix)}analog.png" alt="Analog tracker chart">'
        '</div>'
        '<div class="note-side">'
        '<h3>Reading this</h3>'
        '<p>Only the current year carries colour. The reference years '
        'separate by line weight and dash instead, so the chart holds '
        'when it is screenshotted, reposted, or printed in grey.</p>'
        '<p>2025 is in deliberately as a non-event, a La Ni\u00f1a year, '
        'to show what the absence of a signal looks like on the same '
        'axes.</p>'
        '</div></div>'
        '<div class="chart-caption">'
        f'<strong>Read this week:</strong> the shaded red field marks El Niño territory, '
        f'deepening through moderate, strong and super up to the +2.5°C line that 1997 and '
        f'2015 peaked near. 2026\'s observed ONI (the solid red line) runs to the {h(obs_season)} '
        f'season at {obs_str}°C; 1997 and 2023 were similarly cool this early and still became '
        f'super events, so position this far out is a weak discriminator. Forward, the forecast '
        f'is one combined ensemble: the dashed line and grey bands are ECMWF SEAS5 (median with '
        f'25-75 and 5-95 percentile spreads) to its {h(seas5_end)} horizon, and the dotted line '
        f'carries the NMME multi-model pool from there through the DJF peak to {h(ext_end)}, '
        f'above the 1997/2015 record. The dotted stretches are the softer parts: a short bridge '
        f'over the gap to the first forecast month, then the pooled extension, its member band '
        f'widening with lead. Read the dotted tail as direction, not precision.'
        '</div></section>'
    )

    # Comparison basis, per row, read off the data rather than asserted.
    # This table headed both analog columns "same week" while the Nino
    # 3.4 cells read *_apr22_* constants and the heat-content cells read
    # *_apr_* ones, so a July current column was set against April
    # analogs under a header saying the weeks matched. ENSO tracker has
    # moved heat content to same-calendar-month (f1a7477); Nino 3.4 is
    # still April and is theirs to fix. Until every row is on one basis
    # the column header cannot name one, so it names the year and each
    # row carries its own.
    same_month = phys.get("heat_content_analogs_same_month") or {}
    hc_month = phys.get("heat_content_data_month")
    if same_month.get("1997") is not None:
        hc_97, hc_15 = same_month.get("1997"), same_month.get("2015")
        hc_basis = f"same month{f', {hc_month}' if hc_month else ''}"
    else:
        hc_97 = analog_same.get("1997_apr_heat_content")
        hc_15 = analog_same.get("2015_apr_heat_content")
        hc_basis = "late April"
    if "1997_same_week_nino34_weekly" in analog_same:
        n34_97, n34_15 = ("1997_same_week_nino34_weekly",
                          "2015_same_week_nino34_weekly")
        n34_basis = "same week"
    else:
        n34_97, n34_15 = ("1997_apr22_nino34_weekly",
                          "2015_apr22_nino34_weekly")
        n34_basis = "week of Apr 22"

    physical_html = (
        '<section>'
        '<h2>Physical state</h2>'
        '<p class="section-sub">Current observations against the same '
        'super-event develop years. The rows do not all compare on the '
        'same basis, so each one states its own.</p>'
        '<table class="phys">'
        '<thead><tr>'
        '<th>Indicator</th>'
        f'<th>Current<br><span style="font-weight:400">week of {h(brief_date_iso)}</span></th>'
        '<th>1997</th>'
        '<th>2015</th>'
        '</tr></thead><tbody>'
        '<tr>'
        f'<td>Niño 3.4 weekly (traditional){_basis(n34_basis)}</td>'
        f'<td class="num">{_signed_temp(phys["nino34_weekly_traditional"])}°C</td>'
        f'<td class="num">{_signed_temp(analog_same[n34_97])}°C</td>'
        f'<td class="num">{_signed_temp(analog_same[n34_15])}°C</td>'
        '</tr>'
        '<tr>'
        '<td>Niño 3.4 weekly (RONI)</td>'
        f'<td class="num">{_signed_temp(phys["nino34_weekly_roni"])}°C</td>'
        '<td class="num">n/a (pre-RONI)</td>'
        '<td class="num">n/a (pre-RONI)</td>'
        '</tr>'
        '<tr>'
        f'<td>0–300 m heat content anomaly{_basis(hc_basis)}</td>'
        f'<td class="num">{h(hc_str)}</td>'
        f'<td class="num">{_signed_temp(hc_97)}°C</td>'
        f'<td class="num">{_signed_temp(hc_15)}°C</td>'
        '</tr>'
        '<tr>'
        '<td>Cumulative westerly wind anomaly since Mar 1<br>'
        '<span style="color:var(--text-faint); font-size:12px">CWWA, ERA5 5°N–5°S, 130°E–150°W, m/s·days</span></td>'
        f'<td class="num">{h(cwwa_curr_str)}</td>'
        f'<td class="num">{h(cwwa_97_str)}</td>'
        f'<td class="num">{h(cwwa_15_str)}</td>'
        '</tr>'
        '</tbody></table>'
        # The heat_content_qualitative note is gone. It was a static seed
        # that had not moved since April while the computed sentence
        # tracked the data, so the page contradicted itself; ENSO tracker
        # removed the seed in f1a7477 and this rendered an empty note div
        # after that. The computed comparison already carries it.
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
        '<li>Forecast skill note: mid-year forecasts for the DJF peak are past the boreal-spring '
        'predictability barrier and carry materially narrower error bars than the April&ndash;May '
        'issuances did. The remaining uncertainty is concentrated in peak magnitude at the top of '
        'the distribution (the +3.0 and +3.5 rungs), not in whether a strong-to-super event '
        'occurs.</li>'
        '</ol>'
        '</section>'
    )

    # Footer freshness grid
    fresh_rows = []
    for src, info in freshness.items():
        # Never fall back to the raw key on a public page. A missing
        # name is a build-time omission to fix, not something to print
        # at a reader on the one block whose whole job is provenance.
        # Warn loudly and keep building: invariant 1 says Monday still
        # ships.
        if src not in PUBLIC_SOURCE_NAMES:
            print(f"  WARNING: source {src!r} has no PUBLIC_SOURCE_NAMES "
                  f"entry; omitted from the public freshness grid")
            continue
        display = PUBLIC_SOURCE_NAMES[src]
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

    home = root_prefix if root_prefix else "./"
    footer_html = (
        ("" if is_front else
         _issue_meta_html(brief_date_iso, offset_phrase, freshness,
                          briefs_href=briefs_href,
                          as_published_href=as_published_href))
        + '</main></div>\n'
        '<footer class="field"><div class="field-shell"><div class="foot">'
        '<div class="foot-top">'
        f'<a class="brand" href="{h(home)}" aria-label="{h(SITE_NAME)}, home">'
        f'{_mark_svg(26, mark_ops)}<span class="brand-name">{h(SITE_NAME)}</span></a>'
        '<div class="foot-links">'
        f'<a href="{h(_issue_href(is_front, root_prefix))}">{h(PRODUCT_NAME)}</a>'
        f'<a href="{h(root_prefix)}fires/">Fires</a>'
        f'<a href="{h(methodology_href)}">Methodology</a>'
        f'<a href="{h(briefs_href)}">Archive</a>'
        f'<a href="{h(GITHUB_REPO_URL)}">GitHub</a>'
        '</div></div>'
        + ("" if is_front else
           '<div>'
           '<span class="foot-fresh-label">Source freshness this issue</span>'
           f'<div class="freshness-grid">{"".join(fresh_rows)}</div>'
           '</div>')
        + ("" if is_front else
           f'<p class="footer-meta">Methodology version '
           f'{h(str(S.METHODOLOGY_VERSION))}. RONI to traditional ONI offset '
           f'{offset:+.2f}°C '
           f'({"live, week of " + offset_block["issued"] if offset_live else "seed"}). '
           f'See <a href="{h(methodology_href)}">methodology</a> for the full '
           f'audit trail.</p>')
        + '<p class="foot-cite">'
        f'<b>By <a href="{h(AUTHOR_CONTACT_URL)}">{h(AUTHOR_NAME)}</a>.</b> '
        f'Licensed <a href="{h(LICENSE_URL)}">{h(LICENSE_NAME)}</a>.<br>'
        f'Cite as: Lepik, K. (2026). <b>{h(SITE_NAME)}: {h(PRODUCT_NAME)}.</b> '
        f'<a href="{h(PAGES_BASE_URL)}/">{h(DISPLAY_HOST)}</a>.<br>'
        'Free to share and quote with attribution; commercial reuse requires '
        'permission. Every issue archived, immutable. Disagreements are '
        'surfaced, not averaged.'
        '</p>'
        '</div></div></footer>'
    )

    impacts_html = build_impacts_html_block(load_impacts(), world_map_href=world_map_href)

    # ----------- Analyst section -----------
    # "What's interesting this week": six observers, each fires only when
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
            f"cap). This week the deflection is +{cur_defl:.1f}pp; CPC's "
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

    # 4. Heat content vs the Godzilla analogs at the same stage. Values are
    # same-calendar-month from the same CPC series (see _hc_analogs); the
    # claim is gated on a material margin so a noise-level gap does not get
    # reported as "ahead".
    hc_val = phys.get("heat_content_0_300m_estimate")
    hc97, hc15, hc_basis = _hc_analogs(phys, analog_same)
    if (hc_val is not None and hc97 is not None and hc15 is not None
            and hc_val > max(hc97, hc15) + HC_MATERIAL_MARGIN_C):
        analyst_obs.append(
            f"<strong>Subsurface heat ahead of both Godzilla analogs.</strong> "
            f"0–300 m heat content anomaly is now {hc_val:+.2f}°C, vs "
            f"{hc97:+.2f}°C in 1997 and {hc15:+.2f}°C in 2015 at the "
            f"{hc_basis}, running ahead of either super-event analog at "
            f"this stage of development."
        )
    elif (hc_val is not None and hc97 is not None and hc15 is not None
          and abs(hc_val - hc97) <= HC_MATERIAL_MARGIN_C
          and hc_val > hc15 + HC_MATERIAL_MARGIN_C):
        # Matching 1997, the strongest analog, is itself the story; without
        # this branch the observation would silently disappear the moment
        # the gap narrowed below the material margin.
        analyst_obs.append(
            f"<strong>Subsurface heat matching 1997.</strong> "
            f"0–300 m heat content anomaly is {hc_val:+.2f}°C, effectively "
            f"level with 1997 ({hc97:+.2f}°C) and well above 2015 "
            f"({hc15:+.2f}°C) at the {hc_basis}. 1997 is the strongest "
            f"subsurface analog on record, so tracking it rather than "
            f"exceeding it is the accurate read."
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
                    f"{current_peak:.1f} m/s{date_clause}, vs full-season peaks "
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

    if is_front:
        # Channels and the signup, and nothing from the report.
        body_sections = (_channels_html(root_prefix,
                                        _issue_href(is_front, root_prefix))
                         + _email_capture_html())
    else:
        body_sections = (ladder_html + analyst_html + chart_html
                         + physical_html + impacts_html + sources_html
                         + caveats_html)
    body_sections = _number_sections(body_sections)
    return (head + body_sections + footer_html
            + '\n</body>\n</html>\n')


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


# Friendly model display names for the NMME consensus panel.
_NMME_MODEL_LABELS = {
    "CFSv2": "NCEP CFSv2",
    "CanESM5": "CanESM5",
    "GEM5.2_NEMO": "GEM5.2-NEMO",
    "NCAR_CCSM4": "NCAR CCSM4",
    "NCAR_CESM1": "NCAR CESM1",
}


def build_nmme_panel_markdown(nmme: dict) -> list[str]:
    """Render the NMME multi-model consensus panel as markdown lines.

    Informational panel: shows per-model peak Nino 3.4 forecast and the
    fraction of each model's members above a set of traditional-ONI
    thresholds, plus an equal-model-weighted consensus row. Does NOT feed
    the headline math (that is a separate methodology change, queued for
    v1.8). Returns [] if NMME is unavailable this issue.
    """
    if not nmme or not nmme.get("ok") or not nmme.get("models"):
        return []
    models = nmme["models"]
    ok_models = {k: v for k, v in models.items() if "error" not in v}
    if not ok_models:
        return []

    # Threshold columns. Pull from the payload so a future threshold add
    # flows through automatically; fall back to the canonical set.
    thresholds = nmme.get("thresholds_degC") or [1.0, 1.5, 2.0, 2.5, 3.0]
    thr_keys = [f"{t:.1f}" for t in thresholds]

    md = []
    md.append("## 2b. Multi-model consensus (NMME)")
    md.append("")
    md.append(f"North American Multi-Model Ensemble, init {nmme.get('init', 'n/a')} "
              f"(issued {nmme.get('issued', 'n/a')}). Peak Nino 3.4 over "
              f"{nmme.get('peak_window', 'NDJ-DJF')}, region "
              f"{nmme.get('nino34_region', '5N-5S, 170W-120W')}. Each cell is "
              f"the percent of that model's ensemble members whose peak "
              f"exceeds the threshold. Anomalies are vs each model's own "
              f"hindcast climatology (same convention as SEAS5).")
    md.append("")

    # Header row
    header = "| Model | Members | Peak (mean) | " + " | ".join(
        f">+{t}" for t in thr_keys) + " |"
    sep = "|---|---|---|" + "---|" * len(thr_keys)
    md.append(header)
    md.append(sep)
    for name, m in ok_models.items():
        label = _NMME_MODEL_LABELS.get(name, name)
        fa = m.get("frac_above", {})
        cells = " | ".join(f"{fa.get(k, 0):.0f}%" for k in thr_keys)
        md.append(f"| {label} | {m.get('n_members', '?')} | "
                  f"{m.get('ensemble_mean_peak', float('nan')):.2f}°C | {cells} |")
    # Consensus row (equal model weight)
    cons_fa = nmme.get("ensemble_frac_above", {})
    cons_cells = " | ".join(f"{cons_fa.get(k, 0):.0f}%" for k in thr_keys)
    md.append(f"| **Consensus (equal model wt)** | {len(ok_models)} models | "
              f"**{nmme.get('ensemble_mean_peak', float('nan')):.2f}°C** | {cons_cells} |")
    md.append("")

    # Interpretive note tying it back to the CPC-anchored headline.
    cons_25 = cons_fa.get("2.5")
    cons_30 = cons_fa.get("3.0")
    note_bits = []
    if cons_25 is not None:
        note_bits.append(
            f"The multi-model consensus puts {cons_25:.0f}% of members above "
            f"+2.5°C (1997/2015 magnitude)")
    if cons_30 is not None:
        note_bits.append(
            f"{cons_30:.0f}% above +3.0°C, which would exceed every event in "
            f"the instrumental record (1997 ~2.4, 2015 ~2.6, 1877 ~2.5 on "
            f"HadISST)")
    if note_bits:
        md.append("**Consensus read:** " + ", and ".join(note_bits) + ". "
                  "These are directly-counted member fractions, not tail "
                  "extrapolations. As of methodology v1.8 the NMME suite "
                  "feeds the section-1 headline directly: the multi-model "
                  "consensus deflection blends these models with ECMWF SEAS5 "
                  "at weight 0.85. This panel shows the per-model breakdown "
                  "behind that consensus, including the spread between the hot "
                  "models (CFSv2, NCAR) and the cooler outliers (CanESM5).")
        md.append("")

    # Caveats specific to the panel.
    md.append("**Panel caveats:**")
    md.append("")
    md.append(f"- NMME updates monthly (around the 8th). This init "
              f"({nmme.get('init', 'n/a')}) predates the late-May model runs "
              f"discussed publicly; the next init will capture those.")
    md.append("- Consensus is equal-weighted by model, so small-ensemble "
              "models (NCAR CCSM4/CESM1, 10 members each) carry the same "
              "weight as larger ones. Member-weighting lowers the upper-tail "
              "fractions by a few points. NCAR CESM1 is a known warm outlier.")
    md.append("")
    return md


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

    # v1.8: smoothed headline (CPC anchor + multi-model consensus deflection).
    # Internal brief reports anchor, consensus, and smoothed; public template
    # decides on its own how to display these.
    seas5_per_lead = fetched.get("ecmwf_seas5", {}).get("per_lead", []) or []
    smoothed = probs.smoothed_headline_buckets(
        fetched["cpc_strength"]["table"], seas5_per_lead,
        "NDJ 2026-27", offset=offset, nmme=fetched.get("nmme"))

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
        ("Beyond instrumental record (>+3.0°C peak)", "record_>3.0"),
        ("Far beyond record (>+3.5°C peak)", "record_>3.5"),
    ]:
        s = smoothed.get(key, {})
        smoothed_pct = s.get("mid")
        anchor_pct = s.get("anchor")
        deflection = s.get("deflection")
        if smoothed_pct is not None and anchor_pct is not None:
            if abs(deflection or 0) >= 0.5:
                mode = s.get("mode")
                if mode == "consensus":
                    n_models = s.get("n_models")
                    consensus_pct = s.get("consensus")
                    md.append(f"- **{label}**: {smoothed_pct}% "
                              f"(CPC anchor {anchor_pct}%, {n_models}-model "
                              f"consensus {consensus_pct}%, deflection "
                              f"{deflection:+.1f} ppt)")
                else:
                    md.append(f"- **{label}**: {smoothed_pct}% "
                              f"(CPC anchor {anchor_pct}%, SEAS5 deflection "
                              f"{deflection:+.1f} ppt)")
            else:
                md.append(f"- **{label}**: {smoothed_pct}%")
        else:
            md.append(f"- {fmt_bucket(label, headline[key])}")
    md.append("")
    # Estimator description: reflect whichever mode actually ran this issue.
    _mode = next((v.get("mode") for v in smoothed.values()
                  if v.get("mode") in ("consensus", "seas5_fallback")), None)
    if _mode == "consensus":
        _wt = next((v.get("weight") for v in smoothed.values()
                    if v.get("weight")), probs.CONSENSUS_WEIGHT)
        md.append(f"Headline values use the v1.8 smoothed estimator: a CPC "
                  f"anchor (monthly cadence) plus a deflection toward an "
                  f"equal-weight multi-model consensus (ECMWF SEAS5 + the "
                  f"NMME suite). The consensus carries weight {_wt:g}, so the "
                  f"headline is consensus-led with CPC as a minor anchor. "
                  f"This replaces the v1.5 SEAS5-only deflection (weight 0.2) "
                  f"and was adopted because a multi-model consensus past the "
                  f"spring predictability barrier, corroborated by subsurface "
                  f"heat and WWB peak amplitude, is more informative than CPC's "
                  f"lagging monthly table alone. The anchor and consensus are "
                  f"shown alongside the smoothed value. See methodology.html "
                  f"for the full rule and the rationale.")
    else:
        md.append("Headline values use the smoothed estimator in its v1.5 "
                  "fallback mode (SEAS5-only deflection, weight 0.2, capped at "
                  "±10 ppt per bucket): the NMME multi-model consensus was "
                  "unavailable this issue, so the headline reverts to the "
                  "conservative CPC-anchored estimate. See methodology.html.")
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
    # Caveat 3 updated for v1.9 (2026-07-06): the spring predictability
    # barrier is behind us, so the old "treat all numbers as preliminary"
    # framing would understate current skill. The residual uncertainty has
    # migrated to the top of the distribution.
    md.append("3. Forecast skill note: mid-year forecasts for the DJF peak "
              "are past the boreal-spring predictability barrier and carry "
              "materially narrower error bars than the April-May issuances "
              "did. The remaining uncertainty is concentrated in peak "
              "magnitude at the top of the distribution (the +3.0 and +3.5 "
              "buckets), not in whether a strong-to-super event occurs.")
    rec = smoothed.get("record_>3.0", {})
    rec35 = smoothed.get("record_>3.5", {})
    if rec.get("mid") is not None:
        rec_anchor = rec.get("anchor")
        r35_clause = ""
        if rec35.get("mid") is not None:
            r35_clause = (f" The +3.5°C bucket ({rec35.get('mid')}%, added "
                          f"2026-07-06 once the July SEAS5 run pushed the top "
                          f"of the distribution past where +3.0 discriminates) "
                          f"is even more model-driven: its CPC anchor "
                          f"({rec35.get('anchor')}%) is effectively zero (that "
                          f"threshold is ~+3.0 RONI, far past CPC's top bin), "
                          f"so it is almost entirely direct model member counts "
                          f"above +3.5. Read it as 'where the hot models "
                          f"cluster,' not a calibrated probability, and note it "
                          f"leans hardest on the July ECMWF run.")
        md.append(f"4. The +3.0°C and +3.5°C buckets are the most "
                  f"model-dependent numbers in the headline. +3.0°C exceeds "
                  f"every event in the instrumental record (1997 ~2.4, 2015 "
                  f"~2.6, 1877 ~2.5 on HadISST), and it sits beyond CPC's "
                  f"published strength bins (which top out at >=2.0 RONI), so "
                  f"its CPC anchor ({rec_anchor}%) is a deep skew-normal tail "
                  f"extrapolation. Under the consensus weighting the +3.0 "
                  f"bucket ({rec.get('mid')}%) is driven mostly by direct model "
                  f"member counts, not that extrapolation.{r35_clause}")
    md.append("")

    # --------- Section 2: Physical state panel ---------
    md.append("## 2. Physical state panel")
    md.append("")
    # Header names the actual observation week rather than a hardcoded
    # April date, and the analog columns are same-week values pulled from
    # the same CPC weekly file (see the heat-content note: a column headed
    # "same week" must actually be the same week).
    _n34_live = phys.get("nino34_analogs_same_week") or {}
    _cur_week = (phys.get("issued") or S.BRIEF_DATE.isoformat())
    md.append(f"| Indicator | Current (week of {_cur_week}) | 1997 same week | "
              "2015 same week |")
    md.append("|---|---|---|---|")
    if _n34_live.get("1997") and _n34_live.get("2015"):
        _n97 = f"{_n34_live['1997']['anom']:+.1f}°C"
        _n15 = f"{_n34_live['2015']['anom']:+.1f}°C"
    else:
        _n97 = f"{analog_same['1997_apr22_nino34_weekly']:+.1f}°C (Apr basis)"
        _n15 = f"{analog_same['2015_apr22_nino34_weekly']:+.1f}°C (Apr basis)"
    md.append(f"| Niño 3.4 weekly (traditional) | "
              f"{phys['nino34_weekly_traditional']:+.1f}°C | {_n97} | {_n15} |")
    md.append(f"| Niño 3.4 weekly (RONI) | "
              f"{phys['nino34_weekly_roni']:+.1f}°C | n/a (pre-RONI) | "
              f"n/a (pre-RONI) |")
    hc_fresh = freshness.get("heat_content", {})
    hc_live = hc_fresh.get("ok") and not hc_fresh.get("used_fallback")
    hc_label = (f"{phys['heat_content_0_300m_estimate']:+.2f}°C (CPC monthly, "
                f"180W-100W, vs 1981-2010 climo)" if hc_live
                else f"~{phys['heat_content_0_300m_estimate']:+.1f}°C "
                     f"(qualitative; placeholder)")
    _hc97, _hc15, _hc_basis = _hc_analogs(phys, analog_same)
    md.append(f"| 0-300m heat content anomaly | {hc_label} | "
              f"{_hc97:+.2f}°C | {_hc15:+.2f}°C |")
    wwe_fresh = freshness.get("era5_wwe", {})
    # Display gates on ok, NOT on used_fallback: a cache fallback carries a
    # full valid payload (the fixed fetch_all merge puts it in phys), and
    # hiding it while the WWB row renders from the same cached outage made
    # the 2026-07-20 CDS-outage brief internally inconsistent. Fallback is
    # disclosed in the note text instead of by omission.
    wwe_ok = bool(wwe_fresh.get("ok"))
    wwe_cached = bool(wwe_fresh.get("used_fallback"))
    cwwa_value = phys.get("cwwa_ms_days") if wwe_ok else None
    cwwa_analogs = phys.get("cwwa_analogs", {}) if wwe_ok else {}

    def _analog_value_at(year_int_or_str: int | str, target_iso: str) -> float | None:
        ser = cwwa_analogs.get(year_int_or_str) or cwwa_analogs.get(str(year_int_or_str))
        if not ser:
            return None
        target_md = target_iso[5:]
        for d_iso, v in ser:
            if d_iso[5:] == target_md:
                return float(v)
        return float(ser[-1][1])

    if wwe_ok and cwwa_value is not None:
        target_iso = wwe_fresh.get("issued") or ""
        a97 = _analog_value_at(1997, target_iso)
        a15 = _analog_value_at(2015, target_iso)
        cached_tag = " (cached)" if wwe_cached else ""
        cell_curr = (f"{cwwa_value:.0f} m/s·days (CWWA, ERA5 130E-150W, "
                     f"vs 1991-2020 climo){cached_tag}")
        cell_97 = f"{a97:.0f}" if a97 is not None else "n/a"
        cell_15 = f"{a15:.0f}" if a15 is not None else "n/a"
    else:
        cell_curr = "(CWWA fetch failed; not computed this run)"
        cell_97 = "n/a"
        cell_15 = "n/a"
    md.append(f"| Cumulative westerly wind anomaly since Mar 1 | "
              f"{cell_curr} | {cell_97} | {cell_15} |")
    md.append("")
    # The static heat_content_qualitative seed was removed 2026-07-27 (it
    # went stale in April and contradicted the computed comparison). The
    # computed sentence below carries the analog comparison.
    md.append(f"**Heat content note:** {_heat_content_compare(phys.get('heat_content_0_300m_estimate'), _hc97, _hc15).strip()}")
    md.append("")
    if wwe_ok and cwwa_value is not None:
        ranking = _cwwa_ranking(cwwa_value, cwwa_analogs, wwe_fresh.get("issued"))
        lead_in = ("Live ERA5" if not wwe_cached else
                   "ERA5 (live fetch failed this run; carried from the "
                   "last-good pull)")
        md.append(f"**CWWA note:** {lead_in} daily 850 hPa zonal wind through "
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
        # Generated from this run's state, not a static seed. The old
        # seed published an April paragraph on the 2026-08-03 page.
        _wwe_err = (freshness.get("era5_wwe", {}) or {}).get("error")
        md.append(
            "**CWWA note:** Not computed this run: the ERA5 cumulative "
            "westerly wind anomaly could not be fetched and no usable "
            "cached series was available"
            + (f" ({_wwe_err})." if _wwe_err else ".")
            + " The WWB row below is the independent wind-forcing "
              "indicator and is unaffected when it renders."
        )
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

    # --------- Section 2b: Multi-model consensus (NMME) ---------
    md.extend(build_nmme_panel_markdown(fetched.get("nmme", {})))

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
                md.append(f"- **{display}**: NO USABLE DATA. Live fetch failed "
                          f"and no cache was readable, so this source fell back "
                          f"to sources.py seed values. Error: {info.get('error')}.")
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


def _about_section(num: str, label: str, body: str, aside: str = "",
                   edge: str = "") -> str:
    """One numbered About section.

    `edge` marks the first and last sections explicitly rather than
    relying on :first-of-type, which matches the first element of its
    TYPE among siblings: one <section> added above these would leave
    every one of them without an opening rule.
    """
    aside_html = f'<p class="about-aside">{aside}</p>' if aside else ""
    cls = f"about-sec {edge}".strip()
    return (
        f'<section class="{cls}">'
        f'<div><span class="about-num">{h(num)}</span>'
        f'<h2>{label}</h2></div>'
        f'<div class="about-body">{body}{aside_html}</div>'
        '</section>'
    )


def build_about_html(root_prefix: str = "", methodology_href="methodology.html",
                     briefs_href: str = "briefs/") -> str:
    """The About page.

    A credibility surface, not boilerplate. It leads with refusals: the
    headline names both halves and section 02 is what the site does not
    do, ahead of where the numbers come from. Putting the limits before
    the credentials is what makes the credentials believable.

    Copy is drawn from published material (theses.md T9 to T11, the
    decision ledger, methodology.md) so it reads as consistent with the
    rest of the site rather than newly asserted here.
    """
    title = f"What this is, and what it is not \u00b7 {SITE_NAME}"
    desc = ("The Long Swell answers one question about events in the "
            "climate: how big is this, actually? What the site does, and "
            "what it refuses to do.")

    swell = (
        '<dl class="swell-rows">'
        '<div class="swell-row"><dt>The swell</dt>'
        '<dd>Climate change. Decades of accumulated energy, the ground '
        'everything else happens on.</dd></div>'
        '<div class="swell-row"><dt>The wave</dt>'
        '<dd>The 2026-27 El Ni&ntilde;o. One large wave riding the swell, '
        'this season.</dd></div>'
        '<div class="swell-row"><dt>The break</dt>'
        '<dd>The events reaching the news now. A fire week, a flood, a '
        'harvest.</dd></div>'
        '</dl>')

    secs = []
    secs.append(_about_section(
        "01", "The question",
        '<p>Not what caused it, and not what happens next. <strong>How '
        'big</strong>, measured against a computable historical baseline, '
        'with the sources named and dated.</p>'
        '<p>Three things are distinguished throughout, and the site never '
        'collapses them:</p>' + swell,
        'The swell raised the ground the break happened on. That is a '
        'different claim from saying the wave caused it, and this site '
        'only makes the first.',
        edge="about-open"))

    secs.append(_about_section(
        "02", "What we do not do",
        '<dl class="refusals">'
        '<div class="refusal"><dt>No rival forecast</dt>'
        '<dd>The headline probabilities are agency and model-ensemble outputs, recombined by arithmetic we publish. We do not issue a competing forecast of our own.</dd></div>'
        '<div class="refusal"><dt>No causal attribution</dt>'
        '<dd>We report whether an event falls inside a window where El Ni&ntilde;o shifts the odds. Formal attribution is a separate scientific exercise and we defer to it.</dd></div>'
        '<div class="refusal"><dt>No price forecasts</dt>'
        '<dd>Where a physical quantity reaches a market we state the quantity and cite named analysis. We do not originate the number, and we make no trade recommendations.</dd></div>'
        '<div class="refusal"><dt>No averaging away disagreement</dt>'
        '<dd>When forecast centers disagree, the disagreement is the finding, and it is shown.</dd></div>'
        '</dl>'))

    secs.append(_about_section(
        "03", "Where the numbers come from",
        '<p>Every input is a public agency or model output, fetched '
        'directly and carrying the date its publisher issued it, which is '
        'kept distinct from the date we retrieved it. An agency that has '
        'gone quiet reads as quiet rather than as current.</p>'
        '<p>Where a published source exists, we use it. Where none exists '
        'and the question still matters, we build the measure ourselves, '
        'publish the working, and label the result as ours so it is never '
        'mistaken for an agency number.</p>'
        f'<p>The full source list and the arithmetic are on the '
        f'<a href="{h(methodology_href)}">methodology page</a>.</p>'))

    secs.append(_about_section(
        "04", "The methodology is versioned",
        '<p>Every issue records the methodology version that produced it. '
        'When the arithmetic changes the version changes with it, and '
        'week-over-week comparisons that straddle a change are suppressed '
        'rather than quietly shown.</p>',
        'The current version is always shown on the methodology page.'))

    secs.append(_about_section(
        "05", "The archive is immutable",
        '<p>Once an issue publishes it is frozen. Numbers are not revised '
        'in place, prose is not tidied, and the design it shipped with '
        'stays with it. Improvements apply to later issues only.</p>'
        f'<p>Every issue is in the <a href="{h(briefs_href)}">archive</a>, '
        f'including the ones a later week proved wrong.</p>'))

    secs.append(_about_section(
        "06", "Attribution is stated, never implied",
        '<p>Every event carries one of exactly three statuses, and it is '
        'visible on the item rather than buried in a footnote. A site '
        'built around El Ni&ntilde;o trains readers to assume it is '
        'behind everything, so each item has to say what it is not.</p>'
        + "".join(
            f'<p style="margin-top:14px">{_attr_tag(k)} '
            f'<span style="color:var(--ink-soft)">{h(ATTR_GLOSS[k])}</span></p>'
            for k in ("enso", "non_enso", "pending"))))

    secs.append(_about_section(
        "07", "The channels",
        '<p>Each channel reads one domain against its own baselines, as '
        'its own publication. A channel ships only once it has a baseline '
        'it can be measured against, which is why the list is short.</p>'
        '<p><strong>El Ni&ntilde;o 2026-27</strong>, a weekly probability '
        'brief. <strong>Fires</strong>, hotspot activity against same-week '
        'satellite baselines, first issue 3 August 2026. Floods and a '
        'cross-channel damage ledger are planned and not yet '
        'published.</p>'))

    # Ratified byline. An anonymous-collective framing was considered and
    # rejected: falsifiable on the first "which scientists?", weaker for
    # citation because reporters cite named authors, and it matches the
    # pattern of agenda sites that hide authorship. Upgrade path is named
    # advisors.
    who = ('<p>The Long Swell is an independent publication, written and '
           'edited by <a href="' + h(AUTHOR_CONTACT_URL) + '">'
           + h(AUTHOR_NAME) + '</a>. The methodology is shared with '
           'working climate scientists for external review. Contact '
           'details are in the footer.</p>')
    secs.append(_about_section("08", "Who writes this", who))

    # Ratified. The earlier "nothing is edited in place" was falsifiable
    # from this repo's own history; this version is a stronger promise
    # precisely because it survives an audit.
    corr = ('<p>Past issues are never edited. A genuine rendering error on '
            'the current issue is fixed the day it is found, in a public '
            'commit; everything older is frozen for good.</p>')
    secs.append(_about_section(
        "09", "Corrections",
        corr,
        'This follows from the archive rule in section 05: an archive that '
        'can be edited is not a record.',
        edge="about-close"))

    head = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<meta name="twitter:card" content="summary_large_image">
<style>{T.font_faces_css(root_prefix + "fonts/")}</style>
{_favicon_links(root_prefix)}<style>{PUBLIC_CSS}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
'''
    head += _masthead_html(root_prefix, methodology_href, briefs_href,
                           active="")
    home = root_prefix if root_prefix else "./"
    return (head
            + '<div class="shell"><main class="body">'
            + '<div class="issue-head">'
            + '<h1>What this is, and what it is not.</h1>'
            + '<p class="lede">One question, asked of whatever is in the '
              'news: how big is this, actually? The limits come first, '
              'because they are what makes the rest believable.</p>'
            + '</div>'
            + "".join(secs)
            + '</main></div>\n'
            + '<footer class="field"><div class="field-shell"><div class="foot">'
            + '<div class="foot-top">'
            + f'<a class="brand" href="{h(home)}" aria-label="{h(SITE_NAME)}, home">'
            + f'{_mark_svg(26)}<span class="brand-name">{h(SITE_NAME)}</span></a>'
            + '</div>'
            + '<p class="foot-cite">'
            + f'<b>By <a href="{h(AUTHOR_CONTACT_URL)}">{h(AUTHOR_NAME)}</a>.</b> '
            + f'Licensed <a href="{h(LICENSE_URL)}">{h(LICENSE_NAME)}</a>. '
            + f'<a href="https://{h(T.SITE_HOST_DISPLAY)}/">'
            + f'{h(T.SITE_HOST_DISPLAY)}</a><br>'
            + 'Every issue archived, immutable. Disagreements are surfaced, '
              'not averaged.'
            + '</p></div></div></footer>\n</body>\n</html>\n')


# Thresholds shown on the archive trend, in ladder order. The visual
# treatment is lifted straight from LADDER so a reader who learned the
# ladder on an issue page reads this chart without re-learning: solid
# for the calibrated rungs, losing substance for the two beyond the
# instrumental record.
# Derived, so the archive can never disagree with the ladder again.
ARCHIVE_SERIES = [(k, BUCKET_LABEL[k]) for k in BUCKET_ORDER]


def _archive_rows() -> list[dict]:
    """Every published issue, oldest first, from its frozen meta.json."""
    rows = []
    for meta_path in sorted((DOCS_DIR / "briefs").glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        rows.append({
            "date": meta.get("date", meta_path.parent.name),
            "version": meta.get("methodology_version"),
            "buckets": meta.get("headline_buckets", {}),
        })
    return rows


def _archive_trend_svg(rows: list[dict]) -> str:
    """The trend across issues, which is the whole point of an archive.

    Drawn as inline SVG rather than a matplotlib PNG so it follows the
    theme and needs no build artefact. A rung that did not exist yet
    starts where it was introduced instead of being backfilled with
    zeros: two of these were added because the event outgrew the scale,
    and pretending otherwise would invent readings nobody published.
    """
    if len(rows) < 2:
        return ""
    W, H = 760, 250
    PAD_L, PAD_R, PAD_T, PAD_B = 46, 14, 16, 30
    n = len(rows)

    def x(i):
        return PAD_L + i * (W - PAD_L - PAD_R) / (n - 1)

    def y(v):
        return PAD_T + (100 - v) * (H - PAD_T - PAD_B) / 100

    grid = "".join(
        f'<line class="ar-grid" x1="{PAD_L}" y1="{y(v):.1f}" x2="{W - PAD_R}" '
        f'y2="{y(v):.1f}"/><text class="ar-ax" x="{PAD_L - 8}" y="{y(v) + 3:.1f}" '
        f'text-anchor="end">{v}%</text>'
        for v in (0, 50, 100))

    # Methodology-version bumps. Deltas across one are not comparable
    # (invariant 3), so an archive that hides them is hiding the caveat.
    bumps = []
    for i in range(1, n):
        prev, cur = rows[i - 1]["version"], rows[i]["version"]
        if cur and prev and cur != prev:
            bumps.append(
                f'<line class="ar-bump" x1="{x(i):.1f}" y1="{PAD_T}" '
                f'x2="{x(i):.1f}" y2="{H - PAD_B}"/>'
                f'<text class="ar-bump-lb" x="{x(i):.1f}" y="{PAD_T - 4}" '
                f'text-anchor="middle">v{h(str(cur))}</text>')

    lines = []
    for key, _label in ARCHIVE_SERIES:
        spec = T_LADDER.get(key, {})
        pts = [(x(i), y(r["buckets"].get(key, {}).get("mid")))
               for i, r in enumerate(rows)
               if r["buckets"].get(key, {}).get("mid") is not None]
        if len(pts) < 2:
            continue
        d = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        dash = spec.get("dash")
        dash_attr = (f' stroke-dasharray="{dash[0]} {dash[1]}"'
                     if dash else "")
        colour = spec.get("bar", T.NINO)
        lines.append(
            f'<polyline class="ar-line" points="{d}" '
            f'stroke="{colour}"{dash_attr}/>'
            f'<circle class="ar-end" cx="{pts[-1][0]:.1f}" '
            f'cy="{pts[-1][1]:.1f}" r="3" fill="{colour}"/>')

    first, last = rows[0]["date"], rows[-1]["date"]
    return (
        f'<svg class="ar-chart" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Probability of each threshold across every published '
        f'issue, {h(first)} to {h(last)}">'
        f'{grid}{"".join(bumps)}{"".join(lines)}'
        f'<text class="ar-ax" x="{PAD_L}" y="{H - 8}">{h(first)}</text>'
        f'<text class="ar-ax" x="{W - PAD_R}" y="{H - 8}" '
        f'text-anchor="end">{h(last)}</text>'
        f'</svg>')


def build_archive_html(root_prefix: str = "../",
                       methodology_href: str = "../methodology.html") -> str:
    """The archive index.

    The credential surface. A bare table of percentages hid the one thing
    an archive is for: what changed, when, and whether anything was
    quietly revised. The trend leads, the version bumps are marked
    because deltas across one are not comparable, and every issue links
    to the frozen copy that produced its numbers.
    """
    rows = _archive_rows()
    title = f"Archive, {PRODUCT_NAME} \u00b7 {SITE_NAME}"
    desc = (f"Every issue of {PRODUCT_NAME}, {len(rows)} so far, each "
            f"frozen as published.")

    # Oldest issue that carries a methodology version, and how many
    # predate it. Both derived, never hardcoded: back-filling a version
    # onto an issue that never carried one would be a quiet revision of
    # the record, which is the exact thing this page exists to rule out.
    versioned = [r for r in rows if r.get("version")]
    first_ver = versioned[0]["version"] if versioned else None
    first_ver_date = versioned[0]["date"] if versioned else ""
    n_unversioned = len(rows) - len(versioned)
    unversioned_word = {1: "one", 2: "two", 3: "three", 4: "four",
                        5: "five", 6: "six"}.get(n_unversioned,
                                                 str(n_unversioned))

    DASH = "\u2013"
    items = []
    for i, r in enumerate(reversed(rows)):
        prev = rows[len(rows) - i - 2] if i < len(rows) - 1 else None
        bumped = (prev and r["version"] and prev["version"]
                  and r["version"] != prev["version"])
        cells = "".join(
            f'<span class="ar-val num">'
            f'{r["buckets"].get(k, {}).get("mid", DASH)}'
            f'{"%" if r["buckets"].get(k, {}).get("mid") is not None else ""}'
            f'</span>'
            for k, _ in ARCHIVE_SERIES)
        ver = (f'<span class="ar-ver{" bumped" if bumped else ""}">'
               f'v{h(str(r["version"]))}</span>' if r["version"] else
               '<span class="ar-ver">' + DASH + '</span>')
        items.append(
            f'<a class="ar-row" href="{h(r["date"])}/">'
            f'<span class="ar-date num">{h(r["date"])}</span>'
            f'<span class="ar-vals">{cells}</span>'
            f'{ver}</a>')

    head = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<style>{T.font_faces_css(root_prefix + "fonts/")}</style>
{_favicon_links(root_prefix)}<style>{PUBLIC_CSS}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
'''
    head += _masthead_html(root_prefix, methodology_href, "./", active="elnino")
    home = root_prefix if root_prefix else "./"
    def _swatch(key):
        spec = T_LADDER.get(key, {})
        colour = spec.get("bar", T.NINO)
        dash = spec.get("dash")
        if not dash:
            return f"background:{colour}"
        on, off = dash
        return (f"background:repeating-linear-gradient(90deg,{colour} 0 "
                f"{on}px,transparent {on}px {on + off}px)")

    legend = "".join(
        f'<span class="ar-key"><span class="ar-swatch" '
        f'style="{_swatch(k)}"></span>{lb}</span>'
        for k, lb in ARCHIVE_SERIES)
    return (head
        + '<div class="shell"><main class="body">'
        + '<div class="issue-head">'
        + '<h1>Every issue, exactly as it was published.</h1>'
        + f'<p class="lede">{len(rows)} issues since {h(rows[0]["date"])}. '
          'Nothing here has been edited after the fact, including the '
          'weeks a later issue proved wrong. That is what makes the '
          'trend below worth reading.</p>'
        + '</div>'
        + '<section class="about-sec about-open about-close">'
        + '<div><span class="about-num">01</span><h2>The trend</h2></div>'
        + f'<div class="about-body">{_archive_trend_svg(rows)}'
        + f'<div class="ar-legend">{legend}</div>'
        + '<p class="about-aside">Line weight and dash carry the same '
          'meaning as on the ladder: the two upper thresholds are beyond '
          'the instrumental record and are drawn as less solid because '
          'they are less certain. A threshold begins where it was first '
          'published rather than at zero, because two of these were '
          'added as the event outgrew the scale. Vertical rules mark '
          'methodology-version changes, across which week-over-week '
          'deltas are not comparable.</p></div>'
        + '</section>'
        + '<section><h2>Issues</h2>'
        + '<p class="section-sub">Newest first. Each links to the frozen '
          'copy that produced its numbers.</p>'
        + '<div class="ar-head"><span>Issue</span><span class="ar-vals">'
        + "".join(f'<span>{lb}</span>' for _, lb in ARCHIVE_SERIES)
        + '</span><span>Method</span></div>'
        + f'<div class="ar-list">{"".join(items)}</div>'
        + '<p class="buckets-note">The +1.0 and +1.5 thresholds reached '
          '100% in June and were retired from the public ladder; the '
          'event outgrew the bottom of the scale. Their full history '
          'stays in each issue\u2019s own page.</p>'
        # A dash means two different things in this table and neither was
        # explained, so four rows read as missing data on the one page
        # whose argument is that nothing goes unrecorded. Both the first
        # versioned issue and the count of older ones are read from the
        # frozen meta.json files, so this cannot drift out of step with
        # the table above it.
        + (('<p class="buckets-note">A dash in a probability column means '
            'that threshold was not yet published that week; the two '
            'upper ones were added as the event outgrew the scale. A '
            'dash under Method means the issue predates methodology '
            f'versioning, which begins at v{h(first_ver)} on '
            f'{h(first_ver_date)}. The {h(unversioned_word)} earlier '
            'issues are unrevised originals; they are shown as published '
            'rather than back-filled with a version they never '
            'carried.</p>') if first_ver else '')
        + '</section>'
        + '</main></div>\n'
        + '<footer class="field"><div class="field-shell"><div class="foot">'
        + '<div class="foot-top">'
        + f'<a class="brand" href="{h(home)}" aria-label="{h(SITE_NAME)}, home">'
        + f'{_mark_svg(26)}<span class="brand-name">{h(SITE_NAME)}</span></a>'
        + '</div>'
        + '<p class="foot-cite">'
        + f'<b>By <a href="{h(AUTHOR_CONTACT_URL)}">{h(AUTHOR_NAME)}</a>.</b> '
        + f'Licensed <a href="{h(LICENSE_URL)}">{h(LICENSE_NAME)}</a>. '
        + f'<a href="https://{h(T.SITE_HOST_DISPLAY)}/">'
        + f'{h(T.SITE_HOST_DISPLAY)}</a><br>'
        + 'Every issue archived, immutable. Disagreements are surfaced, '
          'not averaged.'
        + '</p></div></div></footer>\n</body>\n</html>\n')


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

            def _cell(key):
                # Issues published before a bucket existed (e.g. +3.0
                # pre-06-01, +3.5 pre-07-06) show a plain dash rather
                # than implying a probability was computed and hidden.
                mid = h.get(key, {}).get("mid")
                return f"{mid}%" if mid is not None else "-"

            rows.append(
                f"| [{d}]({d}/) | {_cell('moderate_>1.0')} | "
                f"{_cell('strong_>1.5')} | {_cell('super_>2.0')} | "
                f"{_cell('9715_>2.5')} | {_cell('record_>3.0')} | "
                f"{_cell('record_>3.5')} |"
            )

    md = [
        "# Past briefs",
        "",
        "Weekly El Niño probability tracker, archive of past issues. "
        "Latest brief is on the [front page](../index.html); methodology "
        "overview is [here](../methodology.html).",
        "",
        "| Date | At least moderate (>+1.0°C) | Strong (>+1.5°C) | "
        "Super (>+2.0°C) | 1997/2015 magnitude (>+2.5°C) | "
        "Beyond record (>+3.0°C) | Far beyond record (>+3.5°C) |",
        "|---|---|---|---|---|---|---|",
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
                live_oni_by_year=live_oni_by_year,
                # v1.9: prefer the equal-model-weight pooled NMME trajectory
                # (true member-pool band) for the extension; CFSv2-only is
                # the fallback for pre-v1.9 caches. Same {calendar, median,
                # p25, p75} shape either way.
                cfsv2_median=(fetched.get("nmme", {}).get("pooled_trajectory")
                              or fetched.get("nmme", {}).get("cfsv2_trajectory")))

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
    # v1.8: smoothed headline (CPC anchor + multi-model consensus deflection)
    # for the public ladder and the archive meta.json. Internal
    # build_markdown computes its own smoothed locally; we keep the legacy
    # `headline` variable above so editorial.generate keeps its current
    # input shape.
    seas5_per_lead = fetched.get("ecmwf_seas5", {}).get("per_lead", []) or []
    headline_smoothed = probs.smoothed_headline_buckets(
        fetched["cpc_strength"]["table"], seas5_per_lead,
        "NDJ 2026-27", offset=offset, nmme=fetched.get("nmme"))
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
    # Version-aware prior headline drives the ladder delta. Returns an info
    # dict {buckets, date, label} where label is "vs last month" for the
    # primary ≥28-day-back path or "since first issue" for the brief's
    # first-month fallback. None when no comparable prior exists at all.
    prev_headline_smoothed_month = _load_month_prior_headline_smoothed(S.BRIEF_DATE)

    archive_rel = f"briefs/{S.BRIEF_DATE.isoformat()}/"
    public_html_index = build_public_html(
        fetched, freshness, headline_smoothed,
        methodology_href="methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/",
        og_image_url=f"{PAGES_BASE_URL}/card.png",
        world_map_href="world-map.svg",
        prev_headline=prev_headline_smoothed,
        prev_snapshot=prev,
        prev_headline_month=prev_headline_smoothed_month,
        root_prefix="",
        is_front=True,
    )
    public_html_archive = build_public_html(
        fetched, freshness, headline_smoothed,
        methodology_href="../../methodology.html",
        brief_date_iso=S.BRIEF_DATE.isoformat(),
        canonical_url=f"{PAGES_BASE_URL}/{archive_rel}",
        og_image_url=f"{PAGES_BASE_URL}/{archive_rel}card.png",
        world_map_href="../../world-map.svg",
        prev_headline=prev_headline_smoothed,
        prev_snapshot=prev,
        prev_headline_month=prev_headline_smoothed_month,
        briefs_href="../",
        root_prefix="../../",
        is_front=False,
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
    (DOCS_DIR / "briefs" / "index.html").write_text(build_archive_html())
    print(f"wrote: {DOCS_DIR / 'briefs' / 'index.html'}")

    # 7b. About page. A credibility surface: it leads with what the site
    # refuses to do, ahead of where the numbers come from.
    (DOCS_DIR / "about.html").write_text(build_about_html())
    print(f"wrote: {DOCS_DIR / 'about.html'}")

    # 8. Methodology overview HTML, regenerated from methodology.md if present
    meth_md = Path(__file__).parent / "methodology.md"
    if meth_md.exists():
        meth_html = DOCS_DIR / "methodology.html"
        meth_html.write_text(render_html(
            meth_md.read_text(),
            title=f"Methodology, {PRODUCT_NAME} · {SITE_NAME}",
            root_prefix="", analytics=True))
        print(f"wrote: {meth_html}")

    # 9. Weekly situation card (card.py, public-side): a one-page PNG
    # summary composed entirely from the artifacts written above, so it is
    # reproducible from the archive alone. docs/card.png is the rolling
    # front-page artifact (also linked from the brief); the per-issue copy
    # freezes with its archive like everything else in it. Non-fatal per
    # invariant #1: a card failure must never kill the Monday brief.
    try:
        import card
        card.render(S.BRIEF_DATE.isoformat(), DOCS_DIR / "card.png")
        shutil.copyfile(DOCS_DIR / "card.png", docs_brief_dir / "card.png")
        print(f"wrote: {docs_brief_dir / 'card.png'}")
    except Exception as e:
        print(f"situation card failed (non-fatal, brief unaffected): {e}")


if __name__ == "__main__":
    main()
