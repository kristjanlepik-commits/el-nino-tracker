"""A world map of the countries above their own recent maximum.

## Country level, never unit level

The crops index says in its own footer that a map at 2,122-unit
resolution shows dozens of record lows every week for reasons that have
nothing to do with the weather. Drawing that map would undo the
baseline work in the same scroll: 81 scattered dots reads as a crisis
in any week, including the quietest one on record.

So this plots COUNTRIES beyond their own recent maximum, which is one
to six in a normal dekad. Product's call and it is right.

## The emptiness is the statement

Which creates the problem this component actually has to solve. A world
map with six dots on it looks like a map that failed to load, and the
crops null piece already taught us that a mostly-empty object reads as
broken rather than as a result.

Same answer as the null envelope: draw the thing that makes the
emptiness legible. Here that is the DENOMINATOR. Every country we
measure is marked, faintly, so a reader sees 123 places being watched
and six of them lit. The quiet is then visibly the finding rather than
missing data, because the watching is visible too.

That is the difference between "six countries have a problem" and "we
looked at 123 countries and six have a problem", and only the second is
what the page means.

## Positions are cartography, not science

Centroids live in design/country_centroids.json rather than in the
channel payload, because they are positions on a shared basemap rather
than measurements. The build FAILS on a missing centroid rather than
dropping the country, since a country silently absent from a map of
record lows is the worst failure this component could have.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import h                                       # noqa: E402

CENTROIDS = json.loads(
    (ROOT / "design" / "country_centroids.json").read_text())["centroids"]


def _xy(place: str) -> tuple[float, float]:
    """Country to (left%, top%) on the equirectangular basemap.

    docs/world-map.svg is equirectangular over the full globe at viewBox
    800x400, so the projection is the identity on degrees and a percent
    position needs no trigonometry.
    """
    lat, lon = CENTROIDS[place]
    return (lon + 180.0) / 360.0 * 100.0, (90.0 - lat) / 180.0 * 100.0


def map_block(all_places, lit, map_href: str = "../world-map.svg",
              hrefs: dict | None = None) -> str:
    """all_places: every place name measured. lit: [(place, label)] flagged.

    `hrefs` maps a place to its country page. The map is the way IN to
    the country page rather than an end in itself: the global view
    answers "where is it worst" and the country page answers "how bad is
    it here", so a dot that cannot be clicked stops the reader halfway
    through the question. Places without a page stay unlinked rather
    than pointing at a 404.
    """
    missing = sorted(set(all_places) - set(CENTROIDS))
    if missing:
        # Loudly, at build time. A country quietly absent from this map
        # would be indistinguishable from a country that is fine.
        raise SystemExit(
            "design/country_centroids.json is missing: "
            + ", ".join(missing)
            + "\nAdd them rather than letting the map drop a country.")

    lit_names = {p for p, _ in lit}
    dots = []
    # The denominator first, underneath: every place we watch. Without
    # it six dots read as a broken map rather than as a quiet week.
    hrefs = hrefs or {}
    for p in sorted(all_places):
        if p in lit_names:
            continue
        left, top = _xy(p)
        style = f'left:{left:.2f}%;top:{top:.2f}%'
        if hrefs.get(p):
            dots.append(f'<a class="cm-q cm-a" style="{style}" '
                        f'href="{h(hrefs[p])}" aria-label="{h(p)}, within '
                        f'its own normal range"></a>')
        else:
            dots.append(f'<span class="cm-q" style="{style}"></span>')
    for p, label in sorted(lit, key=lambda t: t[0]):
        left, top = _xy(p)
        style = f'left:{left:.2f}%;top:{top:.2f}%'
        inner = (f'<span class="cm-d"></span>'
                 f'<span class="cm-t">{h(label)}</span>')
        if hrefs.get(p):
            dots.append(f'<a class="cm-l" style="{style}" '
                        f'href="{h(hrefs[p])}" aria-label="{h(p)}, above its '
                        f'own recent maximum">{inner}</a>')
        else:
            dots.append(f'<span class="cm-l" style="{style}">{inner}</span>')

    n_lit, n_all = len(lit), len(all_places)
    return (
        f'<figure class="cm">'
        f'<div class="cm-wrap">'
        f'<img class="cm-bg" src="{h(map_href)}" alt="" loading="lazy"/>'
        + "".join(dots) +
        f'</div>'
        f'<figcaption class="cm-cap">Every country we measure is marked. '
        f'The {n_lit} in colour are above their own recent maximum; the '
        f'other {n_all - n_lit} are within their own normal range, which '
        f'is what most of the map looks like in most weeks.</figcaption>'
        f'</figure>')


CROPS_MAP_CSS = f"""
.cm {{ margin:22px 0 0; }}
.cm-wrap {{ position:relative; width:100%; }}
.cm-bg {{ width:100%; height:auto; display:block; }}
/* The countries we watch and that are fine. Faint, but PRESENT: they
   are the denominator, and without them six dots read as a map that
   failed to load rather than as a quiet week. */
.cm-q {{ position:absolute; width:4px; height:4px; margin:-2px 0 0 -2px;
  border-radius:50%; background:var(--ink-faint); opacity:.42; }}
/* A linked quiet dot gets a larger invisible hit area, because 4px is
   below any reasonable touch target and the dot itself must not grow:
   its size is carrying "this country is fine". */
.cm-a {{ box-shadow:0 0 0 7px transparent; }}
.cm-a:hover, .cm-a:focus {{ opacity:1; background:var(--ink); }}
.cm-l {{ position:absolute; margin:-5px 0 0 -5px; text-decoration:none; }}
.cm-l:focus-visible .cm-d, .cm-a:focus-visible {{
  outline:2px solid var(--crop); outline-offset:3px; }}
/* Ring outside the radius, never a stroke on it, so the mark's size
   still carries its meaning (D-023/D-026 applied to a map dot). */
.cm-d {{ display:block; width:10px; height:10px; border-radius:50%;
  background:var(--crop); box-shadow:0 0 0 2.5px var(--paper); }}
.cm-t {{ position:absolute; left:14px; top:-3px; white-space:nowrap;
  font-family:"{T.FONT_DATA}",monospace; font-size:10.5px;
  color:var(--ink); paint-order:stroke;
  text-shadow:0 0 3px var(--paper), 0 0 3px var(--paper),
    0 0 3px var(--paper); }}
.cm-cap {{ margin:10px 0 0; font-size:13px; color:var(--ink-soft);
  max-width:64ch; }}
@media (max-width:600px) {{ .cm-t {{ display:none; }} }}
"""
