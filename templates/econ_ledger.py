"""The ECON ledger: every published figure for one event, none of them added.

The hard constraint, and the reason the layout looks like this: a
firefighting bill, direct damage and foregone output are different
categories, and adding them double-counts. A stacked bar is the natural
treatment and would be a factual error, so this template has no code
path for a stack, no total row and no summed column. The payload has no
`total` field and ECON's validator refuses to emit one. Between those
two the error is hard to make rather than merely forbidden.

Grouping by `kind` IS the enforcement. Rows never interleave across
categories, so two figures a reader might add are never adjacent, and
the section heading says what kind of quantity is below it before any
number appears.

Three things the payload marks that a renderer must not drop, because
ignoring any of them produces a false page rather than a plain one:

  scope           the evacuation figure is SPAIN AND FRANCE COMBINED and
                  must never read as a Spain number
  kind=reference  EU Solidarity Fund money is GRANTED, not damage
                  estimated, so it never shares a section with a loss
  uncounted       what nobody has measured, at the same weight as what
                  has been. Naming the uncounted is what stops a reader
                  treating a partial ledger as the cost of the event.

Absence is rendered, not omitted. Four reasons a figure is missing look
identical in a payload and mean opposite things, and all four have to
read as findings rather than as apologies, which is the same problem as
"not ENSO-linked" not looking like a caveat.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                          # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,  # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)

TAG_TEXT = {"enso_loaded": "ENSO-loaded window",
            "not_enso_linked": "not ENSO-linked",
            "pending": "attribution pending"}
TAG_SLUG = {"enso_loaded": "loaded", "not_enso_linked": "notlink",
            "pending": "pending"}

# Sections, in reading order. The heading states the KIND of quantity
# before any number appears, so a reader knows what they are looking at
# before they can start adding.
SECTIONS = [
    ("hazard", "What was measured",
     "The physical event. These are the only figures here that two "
     "independent bodies measured the same way."),
    ("money", "What the response has cost so far",
     "Money spent fighting the fires. Not damage, and not a loss "
     "estimate."),
    ("impact", "Who was affected",
     "Counts of people and property. Read the scope on each row."),
    ("analog", "What comparable events were estimated to cost",
     "Other events, other years. Here for scale, and never added to "
     "anything above."),
    ("reference", "Money granted, not damage estimated",
     "Public funds awarded after an event. A grant is a decision "
     "someone made, not a measurement of what was lost."),
]

# The four reasons a figure is absent. They look identical in a payload
# and mean opposite things, so each gets its own words and none is
# styled as a warning: a gap in the record is a finding about the
# record, not a failure of the page.
ABSENCE = {
    "not estimated by anyone":
        ("Nobody has produced a figure", "no_one"),
    "flagged, not quantified":
        ("Named as a loss, with no figure attached", "flagged"),
    "no estimator covers this":
        ("No estimator covers this hazard here", "outside"),
    "too early":
        ("Too early; a figure is expected", "early"),
}


def _money(row) -> str:
    cur = row.get("currency", "")
    scale = row.get("scale", "")
    unit = f"{cur} " if cur else ""
    tail = f" {scale}" if scale else ""
    if row.get("value_low") is not None:
        return f'{unit}{row["value_low"]:,.0f} to {row["value_high"]:,.0f}{tail}'
    v = row.get("value")
    return f"{unit}{v:,.1f}{tail}" if v is not None else ""


def _quantity(row) -> str:
    if row.get("kind") == "money" or row.get("currency"):
        return _money(row)
    v = row.get("value")
    if v is None:
        return ""
    q = row.get("value_qualifier")
    units = row.get("units", "")
    lead = f'{q} ' if q else ""
    return f'{lead}{v:,.0f} {units}'.strip()


def _row(row) -> str:
    # A scope note is not a footnote. The evacuation figure covers two
    # countries and the page is about one, so the qualification travels
    # with the number or the number is wrong.
    bits = []
    if row.get("scope"):
        # Rendered whole. It used to be parsed: the field carried reader
        # copy and a directive to the renderer in one string, so this
        # split on "Must never" and kept the first half, which meant a
        # renderer guessing which part of a field was publishable. ECON
        # has split the field, so the directive now lives in a reserved
        # `_scope_render` key that no renderer prints and the guard
        # enforces. The prose-parsing is gone rather than left as a
        # belt-and-braces, because a workaround kept after its cause is
        # fixed is a second thing to maintain and a place for the two to
        # disagree.
        bits.append(f'<span class="scope">{h(row["scope"])}</span>')
    for k in ("method_note", "corroboration_note"):
        if row.get(k):
            bits.append(f'<span class="rnote">{h(row[k])}</span>')
    cmp_ = row.get("comparison") or {}
    if cmp_.get("note"):
        bits.append(f'<span class="rnote">{h(cmp_["note"])}, '
                    f'{h(cmp_.get("basis", ""))}</span>')
    basis = row.get("evidence_basis", "")
    src = row.get("estimator_note", "")
    url = row.get("source_url")
    src_html = (f'<a href="{h(url)}">{h(src)}</a>' if url and src
                else h(src))
    return f"""
      <div class="lrow">
        <div class="lq">{h(_quantity(row))}</div>
        <div class="lmain">
          <div class="llabel">{h(row.get("label", ""))}</div>
          {''.join(bits)}
          <div class="lsrc">{src_html}{
            f' &middot; issued {h(str(row.get("issued")))}' if row.get("issued") else ''}</div>
        </div>
        <div class="lbasis"><span class="basis basis-{h(basis)}">{h(basis)}</span></div>
      </div>"""


def _uncounted(rows, absence) -> str:
    out = []
    for r in rows:
        label, slug = ABSENCE.get(r.get("reason", ""),
                                  (r.get("reason", ""), "other"))
        out.append(f"""
      <div class="lrow uncounted">
        <div class="lq"><span class="nofig nofig-{slug}">{h(label)}</span></div>
        <div class="lmain">
          <div class="llabel">{h(r.get("label", ""))}</div>
          <span class="rnote">{h(r.get("note", ""))}</span>
        </div>
        <div class="lbasis"></div>
      </div>""")
    tail = ""
    if absence and absence.get("note"):
        tail = (f'<p class="absence"><b>Why there is no insured-loss '
                f'figure.</b> {h(absence["note"])}</p>')
    return "".join(out) + tail


def render(doc: dict, root_prefix: str = "../../") -> str:
    tag = doc.get("attribution_tag", "pending")
    slug = TAG_SLUG.get(tag, "pending")
    geo = doc.get("geography") or {}
    per = doc.get("period") or {}
    layers = doc.get("layers") or []
    hc = doc.get("headline_candidate") or {}

    sections = ""
    for kind, title, blurb in SECTIONS:
        rows = [r for r in layers if r.get("kind") == kind]
        if not rows:
            continue
        sections += (f'<p class="seclab">{h(title)}</p>'
                     f'<p class="secsub">{h(blurb)}</p>'
                     + "".join(_row(r) for r in rows))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{h(doc.get("label", ""))} | {h(SITE_NAME)}</title>
<style>
{T.font_faces_css(root_prefix + "fonts/")}
:root {{
{T.css_variables()}
}}
@media (prefers-color-scheme: dark) {{ :root {{
{T.css_variables(dark=True)}
}} }}
:root[data-theme="dark"] {{
{T.css_variables(dark=True)}
}}
* {{ box-sizing: border-box; }}
:root {{ --shell-max: 900px; --shell-pad: 26px; }}
body {{ margin: 0; background: var(--paper); color: var(--ink);
  font-family: "{T.FONT_PROSE}", Georgia, serif; font-size: 16.5px;
  line-height: 1.55; }}
main {{ max-width: 900px; margin: 0 auto; padding: 26px 26px 80px; }}
{SITE_MASTHEAD_CSS}
.mono, .eyebrow, .lq, .lsrc, .basis, .seclab, .nofig, .foot {{
  font-family: "{T.FONT_DATA}", ui-monospace, monospace; }}
.eyebrow {{ font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink-faint); margin: 24px 0 10px; }}
h1 {{ font-size: 38px; font-weight: 500; line-height: 1.14;
  letter-spacing: -0.018em; margin: 0 0 14px; max-width: 20ch;
  text-wrap: balance; }}
.stand {{ color: var(--ink-soft); max-width: 58ch; margin: 0 0 10px; }}

/* The spine of the page, stated before any number. */
.notot {{ margin: 22px 0 30px; padding: 14px 0 0;
  border-top: 3px solid var(--ink); color: var(--ink-soft);
  font-size: 14.5px; max-width: 66ch; }}
.notot b {{ color: var(--ink); font-weight: 500; }}

.seclab {{ font-size: 11px; letter-spacing: {T.TRACK_LABEL}em;
  text-transform: uppercase; color: var(--ink); margin: 40px 0 4px;
  padding-bottom: 8px; border-bottom: 2.4px solid var(--rule-45); }}
.secsub {{ font-size: 13.5px; color: var(--ink-soft); margin: 0 0 6px;
  max-width: 60ch; }}
.lrow {{ display: grid; grid-template-columns: 12.5rem 1fr 6.5rem;
  gap: 20px; align-items: baseline; padding: 15px 0;
  border-bottom: 1px solid var(--rule); }}
.lq {{ font-size: 17px; font-weight: 600; color: var(--damage);
  font-variant-numeric: tabular-nums; line-height: 1.35; }}
.llabel {{ font-size: 16.5px; }}
/* Scope travels with the number. The evacuation row covers two
   countries on a page about one, and a footnote would not survive a
   screenshot. */
.scope {{ display: block; margin-top: 4px; font-size: 13px;
  color: var(--ink); border-left: 2.4px solid var(--damage);
  padding-left: 10px; }}
.rnote {{ display: block; margin-top: 4px; font-size: 13.5px;
  color: var(--ink-soft); max-width: 62ch; }}
.lsrc {{ display: block; margin-top: 6px; font-size: 11.5px;
  color: var(--ink-faint); }}
.lsrc a {{ color: inherit; }}
.basis {{ font-size: 10px; letter-spacing: 0.04em; padding: 2px 7px;
  text-transform: uppercase; background: var(--paper-sunk);
  color: var(--ink-soft); white-space: nowrap; }}

/* Absence, at the same weight as presence. A gap in the record is a
   finding about the record, never an apology for the page, so none of
   these is a warning colour and none is faded. */
.uncounted .lq {{ color: var(--ink); font-weight: 500; }}
.nofig {{ font-size: 12px; line-height: 1.4; display: block;
  padding-left: 10px; border-left: 2.4px solid var(--rule-45); }}
.nofig-no_one {{ border-left-color: var(--ink); }}
.nofig-flagged {{ border-left-style: dashed; border-left-color: var(--ink); }}
.nofig-outside {{ border-left-color: var(--ink-faint);
  border-left-style: double; border-left-width: 4px; padding-left: 9px; }}
.nofig-early {{ border-left-color: var(--ink-faint);
  border-left-style: dotted; }}
.absence {{ margin: 20px 0 0; font-size: 14px; color: var(--ink-soft);
  max-width: 68ch; padding-left: 14px;
  border-left: 1px solid var(--rule); }}
.absence b {{ color: var(--ink); font-weight: 500; }}

.tagrow {{ display: flex; justify-content: flex-end; margin: 30px 0 0; }}
.tag {{ font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 10.5px; letter-spacing: 0.04em; padding: 3px 8px; }}
.tag-loaded {{ background: var(--tag-loaded-bg); color: var(--tag-loaded-fg); }}
.tag-notlink {{ background: var(--tag-notlink-bg); color: var(--tag-notlink-fg); }}
.tag-pending {{ background: var(--tag-pending-bg); color: var(--tag-pending-fg); }}

.cand {{ margin-top: 44px; padding: 16px 0 0;
  border-top: 2.4px solid var(--rule-45); }}
.cand .lab {{ font-family: "{T.FONT_DATA}", ui-monospace, monospace;
  font-size: 10px; letter-spacing: {T.TRACK_LABEL}em; text-transform: uppercase;
  color: var(--ink-faint); }}
.cand blockquote {{ margin: 10px 0; padding: 0 0 0 16px;
  border-left: 3px solid var(--damage); font-size: 19px;
  line-height: 1.4; color: var(--ink); max-width: 56ch; }}
.cand .guard {{ font-size: 13.5px; color: var(--ink-soft); max-width: 64ch; }}
.foot {{ margin-top: 46px; padding-top: 14px;
  border-top: 1px solid var(--ink); font-size: 11.5px;
  color: var(--ink-faint); }}
@media (max-width: 720px) {{
  .lrow {{ grid-template-columns: 1fr; gap: 6px; }}
  .lbasis {{ margin-top: 4px; }}
  h1 {{ font-size: 28px; max-width: none; }}
}}
</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="damage")}
<main>
  <p class="eyebrow">{h(geo.get("country", ""))} &middot;
     {h(per.get("from", ""))} to {h(per.get("to", ""))}</p>
  <h1>{h(doc.get("label", ""))}</h1>
  <p class="stand">{h(per.get("status_note", ""))}</p>

  <p class="notot"><b>Nothing on this page is added up, and there is no
    total.</b> The figures below are different categories measured by
    different bodies: what burned, what the response cost, who was
    moved, what other events were estimated to cost, and what was
    granted afterwards. Summing them would count the same event more
    than once and would produce a number that measures nothing. Each
    section says what kind of quantity it holds before the first
    figure appears.</p>

  {sections}

  <p class="seclab">What nobody has counted</p>
  <p class="secsub">These carry the same weight as the figures above.
    A ledger that showed only what has been measured would read as the
    cost of the event, and it is not.</p>
  {_uncounted(doc.get("uncounted") or [], doc.get("absence_meaning"))}

  <div class="tagrow"><span class="tag tag-{slug}">
    {h(TAG_TEXT.get(tag, TAG_TEXT["pending"]))}</span></div>

  <div class="cand">
    <p class="lab">Headline candidate &middot; not approved copy</p>
    <blockquote>{h(hc.get("text", ""))}</blockquote>
    <p class="guard"><b>Guardrail.</b> {h(hc.get("guardrail", ""))}</p>
  </div>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}, Damages.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
    &middot; evidence basis {h(doc.get("evidence_basis", ""))},
    authorship {h(doc.get("authorship", ""))}</div>
</main>
</body>
</html>
"""
