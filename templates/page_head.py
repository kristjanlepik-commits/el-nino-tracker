"""The discoverability half of every page's head, in one place.

WHY THIS EXISTS. QA audited 250 live pages and found discoverability is a
per-template FEATURE rather than a site property (D-181):

    section   canonical   meta desc   og:title
    heat        45/47       45/47       45/47
    crops        0/124       0/124       0/124
    fires        0/53        0/53        0/53
    briefs       0/18        0/18       18/18

Sitewide: canonical 46 of 250, description 47, og:title 65. Every template
writes its own head, so each property exists exactly once, in whichever
template was most recently built with it in mind. Heat has all three
because it was built last, not because anyone decided heat should have
them and crops should not.

THE POINT IS THAT FIXING ONE CHANNEL FIXES ONE CHANNEL. Fires' noindex was
removed today and fires still has no canonical, no description and no
og:title, so it is now indexable with nothing good to index. The next
channel ships the same gap by the same mechanism unless the head is shared
rather than re-authored, which is the same argument that produced
site_masthead(), subscribe_band.py and rung_copy.py, each of which stopped
a class of drift rather than an instance of it.

WHAT THIS DOES NOT DO. It does not own <title>, fonts, CSS or the
analytics tag: those differ legitimately per surface and one of them,
analytics, already has a guard asserting exactly one per page. This is the
set of tags whose CORRECT value is derivable from three facts every page
already knows, and whose absence is silent.

DESCRIPTION IS REQUIRED AND GENERATED, NEVER DEFAULTED. A page with no
description gets a search snippet chosen by a search engine from whatever
text it finds first, which on our pages is usually a masthead. Making it a
required argument means a new surface cannot ship without one, and
generating it from the payload means it cannot go stale the way an
authored one would. Callers pass a sentence they already computed for the
reader rather than writing a second one for a crawler.
"""
import sys
from html import escape as _h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from run_brief import PAGES_BASE_URL, SITE_NAME       # noqa: E402


def head_meta(*, title, description, path, og_image=None, robots=None,
              og_type="article"):
    """Canonical, description and share cards for one page.

    `path` is the page's absolute path on the site, leading slash, e.g.
    "/crops/france/". It is the one thing a template cannot derive, since
    only the builder knows where it is writing.

    `robots` renders only when given. An absent robots tag means indexable,
    which is the default we want everywhere now that D-172 and D-183 have
    settled crops and fires; passing "noindex" stays possible for a surface
    that genuinely should not be found, and it then appears in exactly one
    place per page rather than in whichever template last thought about it.
    """
    if not description or not description.strip():
        raise ValueError(
            "head_meta needs a description: a page without one gets a search "
            "snippet picked by a crawler from whatever text comes first, "
            "which on our pages is the masthead. Pass the sentence the page "
            "already tells a reader.")
    url = f"{PAGES_BASE_URL}{path}"
    img = og_image or f"{PAGES_BASE_URL}/card.png"
    # Collapsed and clipped: a description is a single line of plain text,
    # and search engines truncate near 160 characters, so a sentence that
    # runs past it is a sentence whose end nobody reads.
    d = " ".join(str(description).split())
    if len(d) > 300:
        d = d[:297].rstrip() + "..."
    out = [
        f'<link rel="canonical" href="{_h(url)}">',
        f'<meta name="description" content="{_h(d)}">',
        f'<meta property="og:title" content="{_h(title)}">',
        f'<meta property="og:description" content="{_h(d)}">',
        f'<meta property="og:url" content="{_h(url)}">',
        f'<meta property="og:type" content="{_h(og_type)}">',
        f'<meta property="og:site_name" content="{_h(SITE_NAME)}">',
        f'<meta property="og:image" content="{_h(img)}">',
        f'<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{_h(title)}">',
        f'<meta name="twitter:description" content="{_h(d)}">',
        f'<meta name="twitter:image" content="{_h(img)}">',
    ]
    if robots:
        out.insert(0, f'<meta name="robots" content="{_h(robots)}">')
    return "\n".join(out)
