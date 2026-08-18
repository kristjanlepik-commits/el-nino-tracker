"""Three instrument maps per country page, from the France card's argument.

Kristjan ruled the socials France card a better visual than the boxes that
shipped, and product ranked its properties. Socials asked explicitly that
the ARGUMENT be kept and their layout discarded, so this is a fresh
rendering of five properties rather than a port:

  the lead sentence, generated from the data and never authored (D-124)
  three panels, not one
  colour and outline carrying DIFFERENT facts, said out loud
  no comparison across panels, because the units differ
  the disagreeing instrument disclosed in words rather than dropped

COLOUR is distance from that region's OWN normal, using the per-region
baseline_mean in the payload. OUTLINE is that region's worst in 26 years,
rank 1. A region can be dark without an outline, or outlined without being
darkest, and the legend says so. Two channels, two facts, which is what
lets both be read at once.

PANEL ORDER is the payload's own instrument order minus the omitted one,
never resorted (D-182). Socials noted it happens to run strongest first,
which avoids the escalation reading CRO flagged on the UK card, where
least-to-most extreme made a sequence look like a mechanism.

GEOMETRY IS SHARED ACROSS THE THREE PANELS. Each region's outline is
defined once in <defs> and drawn three times with <use>, so a third panel
costs fills rather than coordinates. France is 22 regions at about 20 KB
of path data, once.

THE OMITTED PANEL IS A RENDERING DECISION, NOT A DATA ONE, and it is the
part to be careful with. Once colour means distance-from-normal, a
near-normal instrument renders almost blank, and an empty map is
indistinguishable from a missing one. That is this project's own recurring
defect, absent is not zero, arriving from the other direction. So the
instrument is dropped from the panels and stated in the footnote, with its
rank and the reason it moves last.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES = os.path.join(os.path.dirname(HERE), "crops", "geom", "shapes")

# The instrument left out of the panels, and why. Cumulative vegetation
# integrates from the start of the season, so it is structurally the last
# to move and reads calmest exactly when a fast deterioration is under way.
OMIT = "zfparc"

# Units differ, so the scales differ, and nothing is comparable between
# panels. Each is the value at which colour saturates.
SATURATE = {"zfpar": -2.5, "wsi": -40.0, "spi3": -2.5, "temp": 2.5}


def shapes_for(p):
    """Geometry for one payload place, looked up by asap0_id.

    By id, never by name: the reference set spells Turkiye with a double
    acute where the payload uses a diaeresis, and it has a unit called
    "China/India" that is not a filename at all.
    """
    cid = p.get("asap0_id")
    if cid is None:
        return None
    f = os.path.join(SHAPES, "%d.json" % int(cid))
    if not os.path.exists(f):
        return None
    with open(f) as fh:
        return json.load(fh)["regions"]


_WORD = ("no", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")


def _word(n):
    return _WORD[n] if n < len(_WORD) else str(n)


def _project(regions, shapes, w, h, pad=6):
    """Equirectangular, x scaled by cos(mean latitude). Country-sized only."""
    import math
    xs, ys = [], []
    for name in regions:
        for ring in shapes[name]["rings"]:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    lat0 = math.radians((min(ys) + max(ys)) / 2.0)
    k = math.cos(lat0) or 1.0
    x0, x1 = min(xs) * k, max(xs) * k
    y0, y1 = min(ys), max(ys)
    sx = (w - 2 * pad) / (x1 - x0) if x1 > x0 else 1.0
    sy = (h - 2 * pad) / (y1 - y0) if y1 > y0 else 1.0
    s = min(sx, sy)
    ox = pad + ((w - 2 * pad) - (x1 - x0) * s) / 2.0
    oy = pad + ((h - 2 * pad) - (y1 - y0) * s) / 2.0

    def pt(x, y):
        return (ox + (x * k - x0) * s, oy + (y1 - y) * s)
    return pt


def _defs(regions, shapes, pt, prefix):
    """Every outline once. Three panels then cost fills, not coordinates."""
    out = []
    for i, name in enumerate(regions):
        d = []
        for ring in shapes[name]["rings"]:
            if len(ring) < 3:
                continue
            for j, (x, y) in enumerate(ring):
                px, py = pt(x, y)
                d.append("%s%.1f %.1f" % ("M" if j == 0 else "L", px, py))
            d.append("Z")
        out.append('<path id="%s%d" d="%s"/>' % (prefix, i, "".join(d)))
    return "".join(out)


def _shade(v, base, sat):
    """0 at this region's own normal, 1 at a shortfall of `sat` from it.

    SAT IS A DELTA, NOT A LEVEL. Written the other way first, dividing by
    (sat - base), which quietly rescaled every region by its own baseline
    and made the water panel read a quarter as severe as it is: France is
    28 points below its normal on a 40-point ramp, 0.7, and it rendered
    at 0.25. It looked like a plausible map, which is the problem.
    """
    if v is None or base is None or not sat:
        return None
    return max(0.0, min(1.0, (v - base) / sat))


def _fill(t):
    # Paper to the channel red. Absent stays grey and is never a light red,
    # because a pale region must not read as a mild one.
    if t is None:
        return "#d9d5cd"
    a = (0.945, 0.937, 0.925)
    b = (0.667, 0.161, 0.125)
    return "#%02x%02x%02x" % tuple(
        int(round(255 * (a[i] + (b[i] - a[i]) * t))) for i in range(3))


def _panel(p, key, regions, shapes, pt, prefix, w, h, label):
    """One instrument. Colour is distance from normal, outline is a record."""
    sat = SATURATE.get(key)
    at_record = 0
    body = []
    for i, name in enumerate(regions):
        ri = _region(p, name)
        ins = (ri or {}).get("instruments", {}).get(key) or {}
        v, base = ins.get("value"), ins.get("baseline_mean")
        t = _shade(v, base, sat)
        rec = ins.get("rank") == 1
        at_record += 1 if rec else 0
        title = "%s. %s" % (name, ins.get("statement") or "not measured")
        body.append(
            '<use href="#%s%d" fill="%s" stroke="%s" stroke-width="%s">'
            '<title>%s</title></use>' % (
                prefix, i, _fill(t), "#1a1a1a" if rec else "#b7b1a6",
                "1.6" if rec else "0.5", _esc(title)))
    return at_record, (
        '<svg class="cmap" viewBox="0 0 %d %d" role="img" '
        'aria-label="%s">%s</svg>' % (w, h, _esc(label), "".join(body)))


def _region(p, name):
    for r in p.get("regions", []):
        if r.get("region", "").strip() == name:
            return r
    return None


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# The payload names its country-level instruments and keys its region-level
# ones, and nothing joins the two. Mapping by name is a renderer inferring
# meaning it does not own, so the map is asserted rather than trusted: if
# CRO renames an instrument this raises at build time instead of labelling
# a panel with the wrong instrument's figure. Asked them for a `key` on the
# country instruments; until it lands, this is the honest version.
NAME_OF = {
    "zfparc": "Vegetation, cumulative",
    "zfpar": "Vegetation, current",
    "wsi": "Water satisfaction",
    "spi3": "Rainfall, 3-month",
    "temp": "Temperature",
}


def _country_instrument(p, key):
    want = NAME_OF[key]
    hit = [i for i in p.get("instruments", []) if i.get("name") == want]
    if len(hit) != 1:
        raise ValueError(
            "crops_region_map: %r matched %d country instruments named %r "
            "on %s. The name map is stale; fix it rather than rendering a "
            "panel under the wrong label." % (key, len(hit), want, p["place"]))
    return hit[0]


def _panel_keys(p):
    """Payload order, minus the omitted one. Never resorted (D-182)."""
    order = [k for k in ("zfpar", "wsi", "spi3") if k != OMIT]
    have = []
    for k in order:
        ins = _country_instrument(p, k)
        if ins.get("available") is False:
            continue
        if any((r.get("instruments", {}).get(k) or {}).get("value") is not None
               for r in p.get("regions", [])):
            have.append(k)
    return have


def _country_line(p, key):
    """The country figure in the instrument's own units.

    The payload's `statement` is CRO's phrasing and it is correct, but it
    is the same twenty-word rank sentence on all three panels, so stacked
    it reads as boilerplate and the actual numbers never appear. This says
    the number and keeps the rank in the heading above it.
    """
    ins = _country_instrument(p, key)
    v, base, unit = ins.get("value"), ins.get("baseline_mean"), ins.get("unit")
    name = "the UK" if p["place"].startswith("U.K.") else p["place"]
    if v is None:
        return ""
    if unit == "percent":
        return ("%s: %.0f%% of crop water need met, normally %.0f%%"
                % (name, v, base if base is not None else 0))
    if base is None:
        return "%s: %.2f %s" % (name, v, unit or "")
    d = v - base
    word = "below" if d < 0 else "above"
    if unit == "SPI":
        return ("%s: %.2f standard deviations %s normal" % (name, abs(d), word))
    return "%s: %.2f standard deviations %s normal" % (name, abs(d), word)


def _lead(p, key, units):
    """The finding, generated from the data, never authored (D-124).

    The calm case gets a sentence of its own rather than a hedge, because
    a page that only reads clearly when the news is bad is an amplifier
    (D-043). "No region is at its worst" is a finding.

    "AS THEY DO TODAY" IS LOAD-BEARING, not padding. The standfirst
    directly above this on the page says France has NO region at a record
    low, naming the harvest measure as it does so, and this sentence says
    nineteen have never looked worse. Both are true of different
    instruments and, stacked, they read as a contradiction and therefore
    as an error. The standfirst carries its qualifier; without one this
    sentence was the half of the pair that did not (D-051).
    """
    name = "the UK" if p["place"].startswith("U.K.") else p["place"]
    poss = name + ("'" if name.endswith("s") else "'s")
    n = sum(1 for r in p.get("regions", [])
            if (r.get("instruments", {}).get(key) or {}).get("rank") == 1)
    if n == 0:
        return ("No crop region in %s is at its worst in 26 years for this "
                "point in the season." % name)
    if n == 1 and units == 1:
        return ("%s single crop region has never looked worse than it does "
                "today." % poss.capitalize())
    if n == 1:
        return ("One of %s %d crop regions has never looked worse than it "
                "does today." % (poss, units))
    return ("%s of %s %d crop regions have never looked worse than they do "
            "today." % (_word(n).capitalize(), poss, units))


def _omitted_note(p, keys):
    """The instrument that is not shown, in words rather than dropped.

    This is the part of the card that mattered most: a page that hides its
    disagreeing instrument looks worse than the full picture, and this
    channel's posture is disclosure over averaging.

    BUT THE DISAGREEMENT IS MEASURED, NOT ASSUMED. On France the cumulative
    index reads calm while the panels read records, which is what made the
    footnote necessary. On another country it may be the WORST instrument,
    and a fixed sentence saying it disagrees would then be false on a page
    that is otherwise careful. So the note states the rank either way and
    only claims disagreement when the ranks actually diverge.
    """
    ins = _country_instrument(p, OMIT)
    if not ins or ins.get("rank") is None:
        return ""
    r, of = ins["rank"], ins.get("of")
    lows = sum(1 for x in p.get("regions", [])
               if (x.get("instruments", {}).get(OMIT) or {}).get("rank") == 1)
    rec = ("no region at a record" if lows == 0 else
           "one region at a record" if lows == 1 else
           "%s regions at a record" % _word(lows))
    shown = [_country_instrument(p, k).get("rank") for k in keys]
    shown = [x for x in shown if x is not None]
    # Disagreement means the omitted instrument sits clearly calmer than
    # every panel on screen. Equal ranks are not a disagreement.
    diverges = bool(shown) and r > max(shown) + 2

    head = ("A fourth instrument is not shown here and it disagrees with "
            "these three. " if diverges else
            "A fourth instrument is not shown here. ")
    tail = ("It is left off the panels because it is close to normal, so it "
            "renders almost blank, and an empty map looks like a missing "
            "one. Stated here rather than dropped silently, since without "
            "it these panels look worse than the full picture."
            if diverges else
            "It is left off the panels to keep three maps comparable in "
            "kind; it is on the page in full below.")
    return (head + "Cumulative vegetation, the crop-outcome measure closest "
            "to yield, reads %s of %s for this country with %s. It "
            "integrates from the start of the season, so it is structurally "
            "the last to move and reads calmest exactly when a fast "
            "deterioration is under way. %s"
            % (_ord(r), of, rec, tail))


def _ord(n):
    if n is None:
        return "?"
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


CSS = """
.cmw{margin:26px 0 8px}
.cmlead{font-family:var(--serif);font-size:29px;line-height:1.18;
  letter-spacing:-.011em;margin:0 0 6px}
.cmsub{font-size:13.5px;line-height:1.45;color:var(--ink-3);margin:0 0 16px;
  max-width:60ch}
.cmg{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.cmp h3{font-size:13.5px;letter-spacing:.02em;margin:0 0 3px;font-weight:600}
.cmp .cmn{font-size:12.5px;color:var(--ink-2);margin:0 0 1px}
.cmp .cmf{font-size:12.5px;color:var(--ink-3);margin:0 0 8px}
.cmap{width:100%;height:auto;display:block}
.cmleg{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;
  margin:14px 0 0;font-size:12px;line-height:1.5;color:var(--ink-3)}
.cmleg b{font-weight:600;color:var(--ink-2);letter-spacing:.02em;
  text-transform:uppercase;font-size:11px}
.cmramp{height:9px;border-radius:1px;margin:4px 0 3px;
  background:linear-gradient(90deg,#f1efec,#aa2920)}
.cmends{display:flex;justify-content:space-between;font-size:11px}
.cmnote{font-size:12.5px;line-height:1.55;color:var(--ink-3);
  margin:16px 0 0;max-width:78ch}
@media(max-width:720px){
  .cmlead{font-size:23px}
  .cmg{grid-template-columns:1fr;gap:22px}
  .cmleg{grid-template-columns:1fr;gap:10px}
  /* Stacked, three full-width maps run to about four and a half screens
     of map before the legend that explains them. Held to 74% they still
     read at arm's length and the section stays one scroll. */
  .cmap{width:74%;margin:0 auto}
}
"""


def block(p, w=300, h=300):
    """The three-panel region view for one country page.

    Returns "" when the country has no shapes on disk or no region-level
    instrument to draw, so a missing geometry file degrades to the rest of
    the page rather than to a broken figure.
    """
    shapes = shapes_for(p)
    if not shapes:
        return ""
    regions = [r["region"].strip() for r in p.get("regions", [])
               if r["region"].strip() in shapes]
    if len(regions) < 2:
        return ""
    keys = _panel_keys(p)
    if not keys:
        return ""

    pt = _project(regions, shapes, w, h)
    if pt is None:
        return ""
    prefix = "r%d_" % (p.get("asap0_id") or 0)
    units = len(p.get("regions", []))

    # Every outline once, in a zero-size SVG, then referenced by all three
    # panels. Repeating the coordinates per panel would triple the page's
    # path data for no visual gain.
    defs = ('<svg width="0" height="0" aria-hidden="true" '
            'style="position:absolute">%s</svg>'
            % _defs(regions, shapes, pt, prefix))

    panels = []
    for k in keys:
        ci = _country_instrument(p, k)
        n, svg = _panel(p, k, regions, shapes, pt, prefix, w, h,
                        "%s by region, %s" % (NAME_OF[k], p["place"]))
        panels.append(
            '<div class="cmp"><h3>%s</h3><p class="cmn">%s of %d regions at '
            'their own record</p><p class="cmf">%s</p>%s</div>'
            % (_esc(NAME_OF[k]), n, len(regions),
               _esc(_country_line(p, k)), svg))

    lead = _lead(p, keys[0], units)
    note = _omitted_note(p, keys)
    shown = len(regions)
    sub = ("%s instruments, %d regions, one day. Each region against its own "
           "%s years, never against another region."
           % (_word(len(keys)).capitalize(), shown,
              _country_instrument(p, keys[0]).get("of") or "26"))
    missing = units - shown
    if missing:
        # Absent is not zero: a region without geometry is named, not
        # quietly left off a map that otherwise looks complete.
        sub += (" %d of this country's %d regions have no boundary in ASAP's "
                "reference set and are not drawn; they are in the table "
                "below." % (missing, units))

    return (
        '<section class="cmw">%s'
        '<h2 class="cmlead">%s</h2>'
        '<p class="cmsub">%s</p>'
        '<div class="cmg">%s</div>'
        '<div class="cmleg">'
        '<div><b>Colour</b><div class="cmramp"></div>'
        '<div class="cmends"><span>at this region\'s normal</span>'
        '<span>far below</span></div></div>'
        '<div><b>Outline</b><br>A heavy outline is that region\'s worst in '
        '%s years. Different facts: a region can be dark without an outline, '
        'meaning far from normal but it has been worse, or outlined without '
        'being darkest, a record but a narrow one.</div>'
        '<div><b>Do not compare panels</b><br>Water satisfaction is measured '
        'in percentage points and the others in standard deviations. Colour '
        'is comparable within a panel, never between.</div>'
        '</div>%s</section>'
        % (defs, _esc(lead), _esc(sub), "".join(panels),
           _country_instrument(p, keys[0]).get("of") or "26",
           '<p class="cmnote">%s</p>' % note if note else ""))
