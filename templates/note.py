"""Notes: a named human interpreting the instruments, and the index of them.

WHY THIS SURFACE EXISTS AT ALL (D-093). The channel pages are the
instrument. A Note is a person reading it. Kristjan writes every one
himself and the editor chat reviews rather than drafts, because a drafted
Note makes the premise false. That is why the byline is not decoration
here: it is the thing the surface is for.

THE PUBLICATION DATE IS STAMPED ONCE AND FROZEN. This is the part most
likely to be got wrong by someone in a hurry, including me.

`date.today()` in a generator looks correct on the day and silently
redates the piece on every later rebuild. A Note freezes under invariant 5
the moment it publishes, so a September rebuild of an August piece would
write a permanent, uncorrectable lie into the one field whose entire job
is telling a reader how current the piece is.

So: the date is read from the published page if one exists, and only
minted when there is none. `published_on` is passed in rather than
computed here, and `read_frozen_date()` is the thing that keeps it honest.

THE PUBLICATION DATE IS NOT THE MEASUREMENT CUT, and both are shown. The
Note says "31 hot days by 8 August"; the piece may go out days later. A
reader needs both to know what a running total means, and collapsing them
would be the two-bases collision on the field whose job is currency.

NO SIGN-OFF SLOT. Editor's instruction, and the reasoning is worth
keeping: the byline already names him, a sign-off repeats it four hundred
words later, and an empty structural element gets filled because it
exists. Same reason the "form is not yet wired" placeholder came out of
the subscribe page.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, SITE_MASTHEAD_CSS,   # noqa: E402
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)

MON = ["January", "February", "March", "April", "May", "June", "July",
       "August", "September", "October", "November", "December"]
_STAMP = re.compile(r"<!-- published (\d{4}-\d{2}-\d{2}) -->")


def long_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MON[int(m) - 1]} {y}"


def read_frozen_date(out_dir: Path) -> str | None:
    """The date this Note was published, from the Note itself.

    The published page is the record. Not a sidecar file, not a manifest,
    because those can drift from the thing they describe and this cannot:
    if the page exists, the date it carries IS the date it went out.
    """
    p = out_dir / "index.html"
    if not p.exists():
        return None
    m = _STAMP.search(p.read_text())
    if not m:
        raise SystemExit(
            f"{p} exists but carries no published stamp. Refusing to guess "
            f"its date: a Note is frozen under invariant 5 and re-minting "
            f"the date would silently redate a published piece.")
    return m.group(1)


CSS = f"""
:root {{ color-scheme: light dark; }}
{{VARS}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink-soft);
  font-family:"{T.FONT_PROSE}",Georgia,serif; font-size:18px; line-height:1.68;
  -webkit-font-smoothing:antialiased; }}
main {{ max-width:660px; margin:0 auto; padding:24px 24px 90px; }}
{SITE_MASTHEAD_CSS}
h1 {{ font-family:"{T.FONT_PROSE}",Georgia,serif; font-weight:400;
  font-size:38px; line-height:1.12; letter-spacing:-0.016em; color:var(--ink);
  margin:30px 0 0; max-width:22ch; text-wrap:pretty; }}
/* THE BYLINE IS AT THE TOP because attribution is what makes a piece
   citable (T10) and a journalist should not scroll to find who wrote it. */
.byline {{ font-family:"{T.FONT_DATA}",monospace; font-size:11.5px;
  letter-spacing:{T.TRACK_LABEL}em; text-transform:uppercase;
  color:var(--ink-faint); margin:18px 0 0; padding-bottom:20px;
  border-bottom:1px solid var(--rule); }}
.byline .who {{ color:var(--ink); }}
.note p {{ margin:20px 0; max-width:62ch; text-wrap:pretty; }}
.note a {{ color:var(--ink); text-decoration:none;
  border-bottom:1px solid var(--rule); }}
.note a:hover {{ border-bottom-color:var(--ink); }}
.note strong {{ color:var(--ink); font-weight:500; }}
.pull {{ font-size:23px; line-height:1.42; color:var(--ink);
  border-left:2.4px solid var(--ink); padding:2px 0 2px 18px;
  margin:26px 0; max-width:52ch; }}
.note figure {{ margin:30px 0; }}
.note figure img {{ width:100%; height:auto; display:block; }}
/* The source footer is 5a-required and may not be collapsible or
   truncatable: it is what makes review a lookup rather than an audit. */
.src {{ font-family:"{T.FONT_DATA}",monospace; font-size:11.5px;
  line-height:1.72; color:var(--ink-faint); margin-top:38px; padding-top:18px;
  border-top:2.4px solid var(--ink); max-width:70ch; }}
.src b {{ color:var(--ink); font-weight:400; }}
.foot {{ font-family:"{T.FONT_DATA}",monospace; font-size:11px;
  color:var(--ink-faint); margin-top:44px; padding-top:16px;
  border-top:1px solid var(--rule); }}
.foot a {{ color:var(--ink-faint); }}
.idx {{ list-style:none; padding:0; margin:26px 0 0; }}
.idx li {{ border-top:1px solid var(--rule); padding:16px 0; }}
.idx li:last-child {{ border-bottom:1px solid var(--rule); }}
.idx a {{ font-size:21px; color:var(--ink); text-decoration:none;
  border-bottom:1px solid var(--rule); }}
.idx a:hover {{ border-bottom-color:var(--ink); }}
.idx .when {{ display:block; font-family:"{T.FONT_DATA}",monospace;
  font-size:11px; letter-spacing:{T.TRACK_LABEL}em; text-transform:uppercase;
  color:var(--ink-faint); margin-top:7px; }}
.stand {{ color:var(--ink-soft); max-width:58ch; margin:14px 0 0; }}
"""


def _css() -> str:
    return (CSS.replace("{VARS}", T.css_vars_light() + "\n" +
                        T.css_vars_dark()))


def render_note(title, published_on, body_html, sources_html,
                root_prefix="../../") -> str:
    """One Note. `published_on` is frozen by the caller, never minted here."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)} | {h(SITE_NAME)}</title>
<style>{_css()}</style>
{ANALYTICS_SNIPPET}
</head>
<!-- published {published_on} -->
<body>
{site_masthead(root_prefix, active="notes",
               methodology_href=root_prefix + "methodology.html",
               briefs_href=root_prefix + "briefs/")}
<main>
<h1>{h(title)}</h1>
<p class="byline"><span class="who">{h(AUTHOR_NAME)}</span> &middot;
  {h(long_date(published_on))}</p>
<div class="note">
{body_html}
</div>
<div class="src">{sources_html}</div>
<div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.
  <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
</div>
</main>
</body>
</html>
"""


def render_index(notes, root_prefix="../") -> str:
    """The list. One row today, and that is exactly why it exists.

    Product scoped an index out and reversed it when Notes went into the
    nav, on editor's argument: a nav pointing straight at a single Note
    breaks the moment there is a second one, and breaks SILENTLY, with the
    nav still resolving to the first piece forever. An index of one row
    needs no pagination and no design language of its own.
    """
    rows = "".join(
        f'<li><a href="{h(n["slug"])}/">{h(n["title"])}</a>'
        f'<span class="when">{h(long_date(n["published_on"]))}</span></li>'
        for n in sorted(notes, key=lambda n: n["published_on"], reverse=True))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notes | {h(SITE_NAME)}</title>
<style>{_css()}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="notes",
               methodology_href=root_prefix + "methodology.html",
               briefs_href=root_prefix + "briefs/")}
<main>
<h1>Notes</h1>
<p class="stand">The channel pages are the instrument. These are written by
  hand, about what the instruments are showing.</p>
<ul class="idx">{rows}</ul>
<div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.
  <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
</div>
</main>
</body>
</html>
"""
