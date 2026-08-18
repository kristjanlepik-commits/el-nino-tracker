"""ASAP's own GAUL1 region outlines, simplified, for the crops country pages.

WHY ASAP'S SHAPES AND NOT A TIDIER SOURCE. The card that started this used
Eurostat NUTS-2 with a hand-written map from 22 ASAP region names to 22
NUTS ids, verified by an assert. That is correct for France and does not
generalise: the other 122 countries are not NUTS, and a hand map per
country is 123 chances to paint the wrong region dark. These shapes ARE
the units the numbers are reported in, so the join is identity rather
than judgement.

NO GEOSPATIAL DEPENDENCY, following crops/asap_reference.py, which reads
the .dbf by hand for the same reason: this repo has no shapely, fiona,
geopandas or GDAL, and adding one is platform's call rather than a thing
to slip in behind a chart. A shapefile is a documented fixed-width format.

TWO JOIN TRAPS, both already paid for once.

Decode the .dbf as UTF-8, which is what its own .cpg file says. Reading it
as latin-1 costs 10 countries silently: Quebec, Andalucia, all seven of
Hungary's regions. Nothing errors, the names simply fail to match and the
regions vanish from the result.

Strip both sides. The .dbf is fixed-width so its names come back padded,
and the payload keeps the pad on a few: "Ryazanskaya ", "Carlos Ibanez ".
Unstripped, that is 34 more regions gone from Russia and Chile.

Join on `name1_shr`, ASAP's SHORT name, never `name1`. CRO's file records
this one: the indicator CSVs use the short form, so joining France on the
full name drops 4 of its 22.

SIMPLIFICATION is Douglas-Peucker on lon/lat, tolerance in degrees, plus
a floor so a small region never collapses to a triangle. Rings that fall
below four points after simplification are kept at their original
resolution instead, because a dropped island reads as a data gap.
"""
import json
import math
import os
import struct
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(os.path.dirname(HERE), ".cache", "asap_reference",
                   "gaul1_asap_v05.zip")
OUT = os.path.join(HERE, "shapes")


def _dbf(buf):
    nrec, hlen, rlen = struct.unpack_from("<IHH", buf, 4)
    fields, off = [], 32
    while buf[off] != 0x0D:
        fields.append((buf[off:off + 11].split(b"\0")[0].decode("utf-8"),
                       buf[off + 16]))
        off += 32
    rows = []
    for i in range(nrec):
        q, rec = hlen + i * rlen + 1, {}
        for nm, w in fields:
            rec[nm] = buf[q:q + w].decode("utf-8").strip()
            q += w
        rows.append(rec)
    return rows


def _rings(rec):
    """One shapefile record to a list of rings. Type 5 is polygon."""
    typ = struct.unpack_from("<i", rec, 0)[0]
    if typ != 5:
        return []
    nparts, npoints = struct.unpack_from("<ii", rec, 36)
    parts = struct.unpack_from("<%di" % nparts, rec, 44)
    base = 44 + 4 * nparts
    pts = struct.unpack_from("<%dd" % (2 * npoints), rec, base)
    out = []
    for k in range(nparts):
        a = parts[k]
        b = parts[k + 1] if k + 1 < nparts else npoints
        out.append([(pts[2 * i], pts[2 * i + 1]) for i in range(a, b)])
    return out


RENDER_PX = 300  # the panel width the country pages draw into
BUDGET = 24000   # bytes of coordinates per country, before JSON overhead


def _weight(feats):
    return sum(len(r) for f in feats.values() for r in f["rings"]) * 13


def _simplify(recs, blob, idx, ctol, min_ring):
    feats = {}
    for i, r in recs:
        off, ln = idx[i]
        rec = blob[off * 2 + 8: off * 2 + 8 + ln * 2]
        rings = []
        for ring in _rings(rec):
            sr = _dp(ring, ctol)
            if len(sr) < min_ring:
                sr = _bbox_ring(ring)
            if sr:
                rings.append(sr)
        if not rings:
            rings = [_bbox_ring(sum(_rings(rec), []))]
        feats[r["name1_shr"].strip()] = {
            "id": int(r["asap1_id"]),
            "rings": [[[round(x, 3), round(y, 3)] for x, y in ring]
                      for ring in rings],
        }
    return feats


def _extent(recs, blob, idx):
    """Widest side of the country's bounding box, in degrees."""
    lo = hi = None
    for i, _ in recs:
        off, ln = idx[i]
        rec = blob[off * 2 + 8: off * 2 + 8 + ln * 2]
        if struct.unpack_from("<i", rec, 0)[0] != 5:
            continue
        x0, y0, x1, y1 = struct.unpack_from("<4d", rec, 4)
        b = (x0, y0, x1, y1)
        lo = b if lo is None else (min(lo[0], x0), min(lo[1], y0), lo[2], lo[3])
        hi = b if hi is None else (hi[0], hi[1], max(hi[2], x1), max(hi[3], y1))
    if lo is None:
        return None
    return max(hi[2] - lo[0], hi[3] - lo[1])


def _bbox_ring(ring):
    if not ring:
        return []
    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _dp(ring, tol):
    """Douglas-Peucker. Iterative, because deep coastlines blow the stack."""
    if len(ring) < 3:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        x0, y0 = ring[a]
        x1, y1 = ring[b]
        dx, dy = x1 - x0, y1 - y0
        norm = math.hypot(dx, dy)
        far, fd = -1, tol
        for i in range(a + 1, b):
            x, y = ring[i]
            if norm == 0:
                d = math.hypot(x - x0, y - y0)
            else:
                d = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / norm
            if d > fd:
                far, fd = i, d
        if far > 0:
            keep[far] = True
            stack.append((a, far))
            stack.append((far, b))
    return [p for p, k in zip(ring, keep) if k]


def build(only_ids=None, tol=0.04, min_ring=4):
    """Emit one file per country, KEYED BY asap0_id.

    NOT BY NAME. The docstring above says the join is identity rather than
    judgement and the first version of this function joined on name0
    anyway, which cost two countries. ASAP has a unit literally called
    "China/India", so the name is not even a safe filename. And the
    shapefile spells Turkiye with U+0171, a double acute, where the
    indicator payload uses U+00FC, a diaeresis, so the two strings are
    simply different and no amount of case folding joins them. Both files
    carry asap0_id. That is the join.
    """
    z = zipfile.ZipFile(ZIP)
    rows = _dbf(z.read("gaul1_asap.dbf"))
    shx = z.read("gaul1_asap.shx")
    idx = [struct.unpack_from(">ii", shx, 100 + 8 * i) for i in range(len(rows))]

    wanted = {}
    for i, r in enumerate(rows):
        cid = r["asap0_id"].strip()
        if only_ids is not None and int(cid) not in only_ids:
            continue
        wanted.setdefault(cid, []).append((i, r))

    os.makedirs(OUT, exist_ok=True)
    with open(ZIP.replace(".zip", ".shp"), "rb") if False else z.open("gaul1_asap.shp") as fh:
        blob = fh.read()

    written = []
    for cid, recs in sorted(wanted.items(), key=lambda kv: int(kv[0])):
        # TOLERANCE IS RELATIVE TO WHAT GETS DRAWN, not absolute degrees.
        # Every country renders into the same 300px panel, so a fixed
        # angular tolerance oversamples large ones enormously: France
        # spans about 12 degrees, where 0.04 is roughly a pixel, and
        # Russia spans 170, where the same number is a fourteenth of a
        # pixel and buys nothing a reader can see. Fixed at 0.04 the
        # Russia page carried 166 KB of coordinates. Half a pixel at the
        # rendered width is the budget.
        ext = _extent(recs, blob, idx)
        ctol = max(ext / (RENDER_PX * 2.0), 1e-4) if ext else tol

        # HALF A PIXEL IS THE RULE, THE BUDGET IS THE BACKSTOP. Extent
        # alone does not bound the result: Guinea-Bissau is two degrees
        # wide, so it earns a fine tolerance, and the Bijagos archipelago
        # then spends it on dozens of islets that are sub-pixel anyway.
        # Every page carries its country's geometry, so the budget is a
        # page-weight promise rather than a nicety.
        for _ in range(6):
            feats = _simplify(recs, blob, idx, ctol, min_ring)
            if _weight(feats) <= BUDGET:
                break
            ctol *= 2.0
        c = recs[0][1]["name0"].strip()
        p = os.path.join(OUT, "%d.json" % int(cid))
        with open(p, "w") as f:
            json.dump({"country": c, "asap0_id": int(cid), "regions": feats},
                      f, separators=(",", ":"))
        written.append((c, len(feats), os.path.getsize(p)))
    return written


if __name__ == "__main__":
    # Only the countries the channel actually publishes. The reference set
    # has 220; carrying the other 98 would be committed weight nothing
    # renders.
    doc = json.load(open(os.path.join(os.path.dirname(HERE) if False else
                                      os.path.dirname(os.path.dirname(HERE)),
                                      "crops", "data", "stress_current.json")))
    ids = {p["asap0_id"] for p in doc["places"]
           if p.get("regions") and p.get("asap0_id") is not None}
    out = build(ids)
    print("  %d countries, %.1f MB" % (len(out), sum(b for _, _, b in out) / 1e6))
    for c, n, b in sorted(out, key=lambda x: -x[2])[:5]:
        print("     %-30s %3d regions %7.1f KB" % (c, n, b / 1024.0))
    got = {c for c, _, _ in out}
    miss = sorted(p["place"] for p in doc["places"]
                  if p.get("regions") and p["place"] not in got
                  and p.get("asap0_id") not in
                  {r for r in ids if os.path.exists(os.path.join(OUT, "%d.json" % r))})
    print("  payload countries with no shapes: %s" % (miss or "none"))
