"""One map per channel, projected at build time. No runtime dependency.

VD's design, implemented. Their own argument for it is that the site is
static and a map needs neither tiles nor an API key: the geometry is
public domain and 180 country polygons are already in this repo at
fires/data/countries.geo.json, so the projection happens here and the page
receives inline SVG.

TWO LAYERS WITH DIFFERENT ALPHABETS, which is the whole proposal. A
choropleth has one visual channel and this map needs two: a VALUE where we
have one, and an honest account of the map where we do not.

  the value layer is HUE, on a diverging ramp
  the ground layer is TEXTURE, and takes no hue at all,
  because an unmeasured country has not earned any

THREE GROUNDS, ordinal on purpose so a reader who never reads the legend
still reads open, ruled, ruled out:

  open        the polygon carries its own value
  ruled       we cannot answer YET. Transient, and the texture is
              a surface prepared and not written on
  cross-ruled we can never answer. A tropical station with 1.3 C of
              annual amplitude has no summer to calibrate against

THE RAMP IS DIVERGING AND THAT IS THE POINT. Marker area cannot draw this
week: area is one-signed, so Bolivia at 0.13x its normal fire week would
draw at zero and a finding would be deleted. VD's amendment, and it is
right. Hue carries the sign, distance from the middle carries the size, so
Cuba at 11.08x and Bolivia at 0.13x are both far out in opposite
directions and neither recedes (D-043).

CHOROPLETH RATHER THAN MARKERS FOR COUNTRY-UNIT CHANNELS, and this is why
the table failed. Seven adjacent discs read as a cluster, which is the
same false object as seven consecutive rows: it looks like a grouping
someone chose. Seven adjacent FILLED POLYGONS share borders, so the
corridor is drawn rather than asserted and no caption needs the word.

CROPS IS COLOURED ON ranking_key.value, NOT ON RANK. Kristjan's call. Rank
ties five countries at 2 of 26, so six of them took two steps on a nine
step ramp and the map could not say which was worst. ranking_key is
continuous with zero ties across all twenty, and it is comparable across
countries AND across channels, which rank is not. The cost is that the
corridor's worst country changes from Guatemala to Nicaragua, because the
two fields answer different questions.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The channel ramp, cold below normal to warm above, neutral on paper.
RAMP = ["#0A4A57", "#417785", "#85A7B0", "#C3D2D5", "#E8E7E2",
        "#EFC9BD", "#DC957E", "#C05B3D", "#8E240A"]


def _albers(lat0=-12.0, lon0=-76.0, p1=-32.0, p2=8.0):
    """Albers equal area conic. Equal area so adjacency and shape read.

    Hand-rolled because this repo has no geospatial dependency and adding
    one is platform's call, not a thing to slip in behind a map. It is
    thirty lines of trigonometry and the alternative is a build step.
    """
    r1, r2 = math.radians(p1), math.radians(p2)
    n = (math.sin(r1) + math.sin(r2)) / 2.0
    c = math.cos(r1) ** 2 + 2 * n * math.sin(r1)
    r0 = math.sqrt(c - 2 * n * math.sin(math.radians(lat0))) / n

    def project(lon, lat):
        th = n * math.radians(lon - lon0)
        v = c - 2 * n * math.sin(math.radians(lat))
        rho = math.sqrt(max(v, 0.0)) / n
        return rho * math.sin(th), r0 - rho * math.cos(th)
    return project


# The 24, with the name each appears under in countries.geo.json. Joined by
# NAME because that file carries only a name property; every one is checked
# at build time and a miss raises rather than silently dropping a country
# from a map whose whole subject is coverage.
LATAM = [
    ("Mexico", "Mexico"), ("Belize", "Belize"), ("Guatemala", "Guatemala"),
    ("El Salvador", "El Salvador"), ("Honduras", "Honduras"),
    ("Nicaragua", "Nicaragua"), ("Costa Rica", "Costa Rica"),
    ("Panama", "Panama"), ("Cuba", "Cuba"), ("Haiti", "Haiti"),
    ("Dominican Republic", "Dominican Republic"), ("Jamaica", "Jamaica"),
    ("Colombia", "Colombia"), ("Venezuela", "Venezuela"),
    ("Guyana", "Guyana"), ("Suriname", "Suriname"), ("Ecuador", "Ecuador"),
    ("Peru", "Peru"), ("Brazil", "Brazil"), ("Bolivia", "Bolivia"),
    ("Paraguay", "Paraguay"), ("Chile", "Chile"),
    ("Argentina", "Argentina"), ("Uruguay", "Uruguay"),
]


def _rings(geom):
    t = geom.get("type")
    if t == "Polygon":
        return geom["coordinates"]
    if t == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


def _load_shapes():
    d = json.loads((ROOT / "fires/data/countries.geo.json").read_text())
    return {f["properties"]["name"]: f["geometry"] for f in d["features"]}


def _paths(names, W, H, pad=10):
    """Project the subject countries and fit them to the frame.

    The extent is computed from the SUBJECT only, so the region fills the
    frame; context countries are drawn on the same transform and simply
    run off the edge, which is what context should do.
    """
    shapes = _load_shapes()
    proj = _albers()
    miss = [n for _, n in names if n not in shapes]
    if miss:
        raise SystemExit(
            "REFUSING TO BUILD: no geometry for %s. A country missing from "
            "the map is indistinguishable from a country we do not measure, "
            "which is the one confusion this map exists to prevent." % miss)

    pts = []
    for _, n in names:
        for ring in _rings(shapes[n]):
            for lon, lat in ring:
                pts.append(proj(lon, lat))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    sx = (W - 2 * pad) / (max(xs) - min(xs))
    sy = (H - 2 * pad) / (max(ys) - min(ys))
    s = min(sx, sy)
    ox = pad + ((W - 2 * pad) - (max(xs) - min(xs)) * s) / 2 - min(xs) * s
    oy = pad + ((H - 2 * pad) - (max(ys) - min(ys)) * s) / 2 + max(ys) * s

    def to_path(geom, tol=0.25):
        out = []
        for ring in _rings(geom):
            pr = [(ox + proj(lo, la)[0] * s, oy - proj(lo, la)[1] * s)
                  for lo, la in ring]
            # Drop points closer than a quarter pixel. At this scale that
            # is invisible and it halves the page weight.
            k = [pr[0]]
            for p in pr[1:]:
                if abs(p[0] - k[-1][0]) + abs(p[1] - k[-1][1]) > tol:
                    k.append(p)
            if len(k) < 3:
                continue
            out.append("M" + "L".join("%.1f %.1f" % p for p in k) + "Z")
        return "".join(out)

    return shapes, to_path


ISO = {"Mexico": "MEX", "Belize": "BLZ", "Guatemala": "GTM",
       "El Salvador": "SLV", "Honduras": "HND", "Nicaragua": "NIC",
       "Costa Rica": "CRI", "Panama": "PAN", "Cuba": "CUB", "Haiti": "HTI",
       "Dominican Republic": "DOM", "Jamaica": "JAM", "Colombia": "COL",
       "Venezuela": "VEN", "Guyana": "GUY", "Suriname": "SUR",
       "Ecuador": "ECU", "Peru": "PER", "Bolivia": "BOL", "Brazil": "BRA",
       "Paraguay": "PRY", "Chile": "CHL", "Argentina": "ARG",
       "Uruguay": "URY"}


def _step(dep):
    """Signed departure, clamped, to a ramp index. Neutral is the middle."""
    d = max(-3.5, min(3.5, dep))
    return max(0, min(8, int(round(4 + d / (3.5 / 4.0)))))


def readings():
    """Every country, every channel, with its state. Reads the ROSTER.

    Fires publishes a country page only where a country qualified, so the
    page list would show five loud countries and call the other seven
    absent. current_week.json carries all 94 with counts and means.
    """
    crops = json.loads((ROOT / "crops/data/stress_current.json").read_text())
    cby = {p["place"]: p for p in crops["places"]}
    fires = json.loads((ROOT / "fires/data/current_week.json").read_text())
    fby = fires["countries"]

    out = {}
    for _, n in LATAM:
        row = {}
        p = cby.get(n)
        rk = (p or {}).get("ranking_key") or {}
        if p is None:
            # BELIZE, THE DOMINICAN REPUBLIC AND JAMAICA ARE IN THE ASAP
            # ROSTER. They are excluded by OUR minimum: the sub-national
            # method needs three crop units and ASAP gives each of them
            # fewer. That is closer to permanent than to unbuilt, since it
            # changes only if JRC re-cuts its crop mask, so it takes the
            # cross-ruled ground rather than the ruled one. CRO's ruling.
            row["crops"] = {"state": "na",
                            "read": "ASAP reports too few crop units here "
                                    "to rank sub-nationally"}
        elif not rk.get("available"):
            # A THIRD STATE, AND CRO FOUND IT BECAUSE I ASKED WHY 21 AND 20
            # DISAGREED. Suriname is published with a severity rank and has
            # no usable key: four readings of a possible 28, because six of
            # its seven regions have no cropland in the mask. Measured, and
            # too thin to place on this ramp.
            row["crops"] = {"state": "thin",
                            "read": "measured, but too thin to place: %s of "
                                    "%s readings"
                                    % (rk.get("readings"),
                                       rk.get("readings_possible"))}
        elif rk.get("value") is not None:
            # 0.5 is the median position, 1.0 the worst on its own record,
            # so the signed departure is symmetric about the middle.
            row["crops"] = {"state": "value", "v": rk["value"],
                            "step": _step((rk["value"] - 0.5) * 2 * 3.5),
                            "read": "%.2f of the way into its own extremes"
                                    % rk["value"]}
        else:
            row["crops"] = {"state": "pend"}

        e = fby.get(ISO[n])
        if e and e.get("mean"):
            m = e["count"] / e["mean"]
            # THE CROPLAND READING IS ALREADY PER COUNTRY and fire is right
            # that a page showing Cuba at 11.08x without it is worse than
            # the index for the same country. Reading it here rather than
            # asking them to re-emit anything.
            cl = e.get("cropland") or {}
            lu = ""
            if cl.get("reading") == "enriched":
                lu = (", %.2f× more often on farmland than chance"
                      % cl.get("ratio", 0))
            elif cl.get("reading") == "depleted":
                lu = (", %.2f× less often on farmland than chance"
                      % cl.get("ratio", 0))
            # n_compared is not emitted; the history itself carries it, and
            # it is not 14 everywhere: some countries lost 2022 windows.
            yrs = len(e.get("hist") or {})
            row["fires"] = {"state": "value", "v": m,
                            "step": _step(math.log(m, 2)),
                            "read": "%.2f× its own normal week, %d years%s"
                                    % (m, yrs, lu)}
        else:
            row["fires"] = {"state": "pend"}

        # Heat covers zero of these 24: every city on that channel is
        # European. Whether a tropical station could EVER qualify is heat's
        # ruling and they have not given it, so the whole continent is
        # ground 2 rather than ground 3. VD proposed splitting it and said
        # themselves it was not their call.
        row["heat"] = {"state": "pend"}
        # Floods publishes by catchment. One LatAm basin exists, the Lima
        # coast, and a basin is not a country, so no national figure can be
        # honest here.
        row["floods"] = {"state": "pend"}
        out[n] = row
    return out


CHANNELS = [("crops", "Crops", "how far into its own extremes, this dekad"),
            ("fires", "Fires", "this week against its own same-week mean"),
            ("heat", "Heat", "summer nights above a local threshold"),
            ("floods", "Floods", "river-basin rainfall against its own record")]

W, H = 470, 520

CSS = """
.rmgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:26px 22px;margin:18px 0 0}
.rmcell{display:flex;flex-direction:column}
.rmttl{display:flex;align-items:baseline;gap:10px;padding-bottom:9px}
.rmttl .nm{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink)}
.rmttl .ct{font-family:"__D__",ui-monospace,monospace;font-size:10.5px;
  color:var(--ink-faint);margin-left:auto;font-variant-numeric:tabular-nums}
.rmfr{border-top:3px solid var(--ink)}
svg.rmap{display:block;width:100%;height:auto}
.rmcap{padding-top:9px;border-top:1px solid var(--rule);font-size:12px;
  line-height:1.6;color:var(--ink-faint);min-height:3.2em}
.rmcap b{color:var(--ink);font-weight:600}
/* A country you can open is a country you can see is openable. Cursor and
   a hover outline, no hue change: hue is the value and must not double as
   an interaction state. */
a.rmlink use{cursor:pointer}
a.rmlink:hover use,a.rmlink:focus-visible use{stroke:var(--ink);
  stroke-width:1.6}
a.rmlink:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.rmramp{display:flex;height:13px;margin-top:4px}
.rmramp div{flex:1}
.rmkeyfoot{display:flex;justify-content:space-between;
  font-family:"__D__",ui-monospace,monospace;font-size:9.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);
  padding-top:5px}
.rmlegend{display:flex;flex-wrap:wrap;gap:10px 22px;margin:14px 0 0;
  font-family:"__D__",ui-monospace,monospace;font-size:10.5px;
  color:var(--ink-faint);align-items:center}
.rmsw{width:26px;height:15px;display:inline-block;vertical-align:-3px;
  margin-right:7px;border:1px solid var(--rule-45)}
@media(max-width:760px){.rmgrid{grid-template-columns:minmax(0,1fr)}}
"""


def _defs(shapes, to_path):
    """Every outline once. Four maps then cost fills, not coordinates."""
    out = ['<pattern id="rmpend" width="6" height="6" '
           'patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
           '<rect width="6" height="6" fill="#F1F0EC"/>'
           '<line x1="0" y1="0" x2="0" y2="6" stroke="#8E8E88" '
           'stroke-width="1"/></pattern>',
           '<pattern id="rmna" width="6" height="6" '
           'patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
           '<rect width="6" height="6" fill="#F1F0EC"/>'
           '<line x1="0" y1="0" x2="0" y2="6" stroke="#8E8E88" '
           'stroke-width="1"/>'
           '<line x1="0" y1="0" x2="6" y2="0" stroke="#8E8E88" '
           'stroke-width="1"/></pattern>']
    for i, (_, n) in enumerate(LATAM):
        out.append('<path id="rc%d" d="%s"/>' % (i, to_path(shapes[n])))
    return "".join(out)


def _slug(n):
    return n.lower().replace(" ", "-").replace("'", "")


def _href(channel, name, root_prefix):
    """Where clicking this country goes, or None.

    THE MAP IS THE NAVIGATION, so a country we can answer for has to be
    reachable from it. Kristjan's structure, and without this the map is
    decoration with a tooltip.

    The destination is that channel's own country page, because the
    cross-channel country page does not exist yet: /fires/france/ and
    /crops/france/ are separate pages from separate templates. When the
    merged page is built this becomes one target instead of four.

    A COUNTRY WITHOUT A PAGE IS NOT A LINK. Fires publishes a page only
    where a country qualified, so five of its twelve measured countries
    have one. A dead link on a map whose subject is coverage would be the
    same lie as an empty cell.
    """
    d = ROOT / "docs" / channel / _slug(name)
    if not (d / "index.html").exists():
        return None
    return "%s%s/%s/" % (root_prefix, channel, _slug(name))


def _fill(cell):
    st = cell["state"]
    if st == "value":
        return RAMP[cell["step"]]
    return "url(#rmna)" if st == "na" else "url(#rmpend)"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def block(root_prefix="../"):
    """The four maps, the ramp, and the legend for the three grounds."""
    shapes, to_path = _paths(LATAM, W, H)
    data = readings()
    ctx = [g for n, g in _load_shapes().items()
           if n not in {x for _, x in LATAM}]

    # Context: outside the twenty-four this map makes no claim either way,
    # so those countries are outline only and never filled.
    ctx_d = "".join(to_path(g, tol=0.9) for g in ctx)
    ctx_paths = ('<use href="#rmctx" fill="none" stroke="var(--rule-20)" '
                 'stroke-width="0.7" stroke-opacity="0.5"/>')

    cells = []
    for key, name, unit in CHANNELS:
        shp = []
        n_val = 0
        for i, (_, cn) in enumerate(LATAM):
            cell = data[cn][key]
            if cell["state"] == "value":
                n_val += 1
            title = ("%s: %s" % (cn, cell["read"])
                     if cell["state"] == "value" else
                     "%s: not measured. This is a gap in our coverage, not a "
                     "quiet week." % cn)
            use = ('<use href="#rc%d" fill="%s" stroke="var(--rule-45)" '
                   'stroke-width="0.7"><title>%s</title></use>'
                   % (i, _fill(cell), _esc(title)))
            href = (_href(key, cn, root_prefix)
                    if cell["state"] == "value" else None)
            if href:
                use = ('<a href="%s" class="rmlink"><g>%s</g></a>'
                       % (_esc(href), use))
            shp.append(use)
        cells.append(
            '<div class="rmcell"><div class="rmttl"><span class="nm">%s</span>'
            '<span class="ct">%d of %d measured</span></div>'
            '<div class="rmfr"><svg class="rmap" viewBox="0 0 %d %d" '
            'role="img" aria-label="%s">%s%s</svg></div>'
            '<p class="rmcap"><b>%s</b> %s</p></div>'
            % (name, n_val, len(LATAM), W, H,
               _esc("%s across Latin America: each country either carries a "
                    "value on the diverging ramp, or is ruled where we do "
                    "not measure it." % name),
               ctx_paths, "".join(shp), name, unit))

    ramp = "".join('<div style="background:%s"></div>' % c for c in RAMP)
    return (
        '<svg width="0" height="0" aria-hidden="true" '
        'style="position:absolute"><defs>%s'
        '<path id="rmctx" d="%s"/></defs></svg>'
        '<div class="rmgrid">%s</div>'
        '<div class="rmramp">%s</div>'
        '<div class="rmkeyfoot"><span>far below its own normal</span>'
        '<span>its own normal</span><span>far above</span></div>'
        '<div class="rmlegend">'
        '<span><i class="rmsw" style="background:url(#rmpend)"></i>'
        'ruled: we do not measure here yet</span>'
        '<span>Grey outlines are context. Outside these twenty-four this '
        'map makes no claim either way.</span></div>'
        % (_defs(shapes, to_path), ctx_d, "".join(cells), ramp))
