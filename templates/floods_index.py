#!/usr/bin/env python3
"""The floods channel index.

WHY IT DID NOT EXIST UNTIL NOW, since that is the useful part. Every other
channel got an index because its pages were generated in a batch and the
batch needed a contents page. Floods publishes one region at a time, so
each piece was reachable at the moment it was written and nothing ever
forced the question of how anyone would find the second one.

The result, measured 2026-08-30: /floods/ returned 404 while the Pyrenees
piece sat live at HTTP 200 with ZERO inbound links from anywhere on the
site. A published story reachable only by knowing its URL. Fire reported
the same shape on 31 country pages the same afternoon, which is what
turned two separate oversights into one recognisable failure: a page falls
out of the thing that links it and nothing anywhere notices, because
nothing is broken.

ROWS ARE BUILT FROM piece_from, NOT FROM THE RENDERED HTML AND NOT RETYPED.
The index and the piece therefore cannot disagree about what a piece says,
which is a class of error this repo has hit often enough to design against:
the moment a headline is restated in a second place, the two drift and the
one nobody rebuilds is the one that goes stale.

WHAT THE CHANNEL CANNOT DO IS THE HEADER, NOT THE FOOTER. Product's
observation, and it is right: the strongest passage on any live page is
the fires cropland row, which states the instrument's limit next to the
number rather than beneath the fold. On this channel the limit IS the
subject. Every piece here measures rainfall; none of them measures
flooding; the channel is called Floods and the URL asserts a flood by
existing. That sentence belongs at the top of the index in the same weight
as the findings, not in a note under them.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pieces(today):
    """Every floods piece that has a published page, newest window first.

    Reads the payloads and derives each row through piece_from, so a row
    here is the same computation the page ran. A payload with no page is
    skipped rather than listed: piece_from refuses payloads that do not
    establish what they are about, and a refusal is not a publication.
    """
    sys.path.insert(0, str(ROOT))
    from floods.build_piece import piece_from

    out = []
    for src in sorted((ROOT / "floods" / "data").glob("payload_*.json")):
        try:
            payload = json.loads(src.read_text())
        except ValueError:
            continue
        try:
            piece = piece_from(payload, today)
        except SystemExit:
            continue          # refused to build; there is no page to list
        except Exception:
            continue
        page = ROOT / "docs" / piece["path"].strip("/") / "index.html"
        if not page.exists():
            continue
        piece["_end"] = payload["window"]["end"]
        # Carried so consumers can test WHERE a piece is without reading
        # the payload again, and without a typed list of region ids
        # deciding which region a basin belongs to.
        piece["location"] = payload.get("location") or {}
        out.append(piece)
    out.sort(key=lambda p: p["_end"], reverse=True)
    return out


def _extent_state(piece):
    """What the flood-extent instrument said, in three words or fewer.

    A SEPARATE COLUMN RATHER THAN A CAVEAT. On a channel where the
    headline number is always rainfall, whether we looked for standing
    water is the reader's second question and it currently has the same
    answer everywhere. Rendering it per row means the day it differs, the
    difference is visible without anyone rewriting the page.
    """
    for row in piece.get("instruments", []):
        if row.get("name") == "Flood extent":
            return row.get("value") or "not assessed"
    return "not assessed"


def _rows(pieces, root_prefix):
    out = []
    for p in pieces:
        out.append(
            '<li class="fx">'
            '<a class="fxa" href="%s%s">'
            '<span class="fxreg">%s</span>'
            '<span class="fxwin">%s</span>'
            '<span class="fxclaim">%s</span>'
            '</a>'
            '<span class="fxmeta">rainfall measured &middot; '
            'flood extent %s</span>'
            '</li>'
            % (root_prefix.rstrip("/"), p["path"], p["region"], p["window"],
               p["claim"], _extent_state(p)))
    return "\n".join(out)


CSS = """
.fxwrap{max-width:760px;margin:0 auto;padding:26px 24px 80px}
.fxlede{font-family:var(--serif);font-size:30px;line-height:1.2;
  letter-spacing:-.012em;margin:16px 0 12px;max-width:22ch}
.fxstand{font-size:17px;line-height:1.6;color:var(--ink-soft);
  max-width:62ch;margin:0 0 8px}
.fxsec{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-faint);margin:38px 0 0;padding-bottom:8px;
  border-bottom:1px solid var(--ink)}
/* The channel's limit, at the weight of a finding rather than a footnote.
   Ruled on both sides so it reads as a statement the page is making, not
   an aside it is hedging with. */
.fxlimit{border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);
  padding:14px 0 15px;margin:22px 0 0;max-width:62ch}
.fxlimit b{font-family:var(--serif);font-size:18px;line-height:1.35;
  display:block;margin-bottom:6px}
.fxlimit span{font-size:14.5px;line-height:1.55;color:var(--ink-soft)}
ul.fxlist{list-style:none;margin:0;padding:0}
.fx{border-bottom:1px solid var(--rule);padding:18px 0 15px}
.fxa{display:block;text-decoration:none;color:inherit}
.fxa:hover .fxclaim{text-decoration:underline}
.fxreg{display:block;font-family:"__D__",ui-monospace,monospace;
  font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--flood);font-weight:600}
.fxwin{display:block;font-family:"__D__",ui-monospace,monospace;
  font-size:10.5px;letter-spacing:.02em;color:var(--ink-faint);
  margin-top:3px}
.fxclaim{display:block;font-family:var(--serif);font-size:19px;
  line-height:1.35;color:var(--ink);margin-top:7px;max-width:54ch}
.fxmeta{display:block;font-family:"__D__",ui-monospace,monospace;
  font-size:10px;letter-spacing:.02em;color:var(--ink-faint);margin-top:8px}
.fxnote{font-size:14.5px;line-height:1.55;color:var(--ink-soft);
  max-width:62ch;margin:16px 0 0}
@media(max-width:620px){.fxlede{font-size:24px}.fxclaim{font-size:17px}}
"""


def render(root_prefix="../", today="2026-08-30"):
    sys.path.insert(0, str(ROOT))
    import tokens as T
    from templates.page_head import head_meta
    from run_brief import (site_masthead, SITE_MASTHEAD_CSS,
                           ANALYTICS_SNIPPET)
    from templates.subscribe_band import band as sub_band, css as sub_css

    pieces = _pieces(today)

    # DERIVED, NEVER TYPED (D-124). The count is the one number on this
    # page that would rot silently, because a new piece changes it and
    # nothing would fail.
    n = len(pieces)
    _W = ("no", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
          "Eight", "Nine", "Ten")
    word = _W[n] if n < len(_W) else str(n)
    lede = ("%s river basin%s measured against %s own record."
            % (word, "" if n == 1 else "s", "its" if n == 1 else "their"))

    assessed = sum(1 for p in pieces
                   if _extent_state(p) not in ("not assessed", ""))
    if assessed == 0:
        extent_note = (
            "Flood extent has not been assessed on any piece here. The "
            "satellite that would answer it needs a baseline per basin "
            "before it can say whether standing water is unusual, and "
            "those baselines do not exist yet. Every page says so on its "
            "own face.")
    else:
        extent_note = (
            "Flood extent is assessed on %d of these %d. Where it is not, "
            "the page says so rather than leaving the row out."
            % (assessed, n))

    body = """
<div class="fxlimit"><b>This channel measures rainfall. It does not
measure flooding.</b><span>Rain gauges and satellites can say how much
fell and how that compares with the same fortnight in every year since
2000. Neither says whether a river left its bed, whether anyone was
displaced, or whether a road is under water. Where we have checked a
gauge, the page says what it read. Where we have not, the page says that
instead of implying it.</span></div>
<p class="fxsec">Every basin we have measured</p>
<ul class="fxlist">
%s
</ul>
<p class="fxnote">%s</p>
__METHOD_LINK__
<p class="fxnote">An ordinary total is not evidence that nothing happened.
The instrument accumulates over a fortnight and severely under-reads rain
that falls in a few hours, which is the rain that floods. Each page
carries its own reading of how concentrated its fortnight was.</p>
""" % (_rows(pieces, root_prefix), extent_note)
    meth = ROOT / "docs" / "floods" / "methodology.html"
    body = body.replace(
        "__METHOD_LINK__",
        '<p class="fxnote"><a href="methodology.html">How these figures '
        'are built</a>, including what this channel cannot measure and '
        'why.</p>' if meth.exists() else "")

    css = (CSS.replace("__D__", T.FONT_DATA) + sub_css() + SITE_MASTHEAD_CSS)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
%s
<title>Floods | The Long Swell</title>
<style>
%s
:root {{ {vars} }}
</style>
</head>
<body>
%s
<main class="fxwrap">
  <p class="fxsec" style="border:0;margin-top:6px">Floods</p>
  <h1 class="fxlede">%s</h1>
  <p class="fxstand">Each piece compares one basin's rainfall with the
     same calendar fortnight in every year since 2000, and states what it
     could not see alongside what it could.</p>
  %s
  %s
</main>
</body>
</html>
""".replace("{vars}", T.css_variables()) % (
        head_meta(title="Floods | The Long Swell",
                  description=lede, path="/floods/"),
        # EVERY OTHER CHANNEL INDEX CARRIES THIS AND MINE DID NOT. Caught
        # by comparing against the three that already existed rather than
        # by any check: qa_check guards against more than one analytics
        # tag on a page, so a page with none passes silently and simply
        # goes uncounted.
        ANALYTICS_SNIPPET,
        css, site_masthead(root_prefix), lede, body, sub_band())


def main():
    out = ROOT / "docs" / "floods" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(root_prefix="../"))
    print("wrote %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
