"""ASAP's own reference table: cropland area per GAUL1 unit.

WHY THIS EXISTS. Every country figure on this channel is an UNWEIGHTED
mean over its regions, so the UK's four regions each carry 25% of the
national number whatever their cropland. England holds 85.6% of UK
cropland and Northern Ireland 0.6%, so Northern Ireland is over-weighted
about 42-fold. That is tls-internal#16, open since launch, and it could
not be fixed because we had no cropped area per unit.

ASAP publishes it. `gaul1_asap_v05.zip` carries a shapefile whose
attribute table has `km2_crop`, "crop area according to ASAP crop mask",
per unit. The 106 MB crop-mask raster is NOT needed for this: the zonal
statistics have already been done by the people who made the mask.

NO GEOSPATIAL DEPENDENCY. The repo has no rasterio, GDAL, geopandas,
shapely or fiona, and adding them is platform's call rather than a thing
to slip in. A dBase III attribute table is a fixed-width format that
needs 30 lines to read, so this reads it directly and never touches the
.shp geometry.

DECODE AS UTF-8, NOT LATIN-1, AND STRIP BOTH SIDES. The shapefile ships
a `.cpg` file whose entire contents are the string "UTF-8", and it was
sitting in the same zip I was reading. latin-1 does not raise on UTF-8
bytes, it silently produces mojibake, so every accented name failed to
join and those regions got no cropland area at all: Hungary lost all
seven, Turkiye all 79, Cote d'Ivoire all 14, and ten more countries lost
some. Design found it by testing crop_areas() rather than a copy of its
logic. A region with no area is the exact input that silently turns a
weighted mean back into something else, and Hungary is one of the
countries the gate ruling has just put in front of readers.

The dbf is fixed width, so names come back padded: "Ryazanskaya " and
"Carlos Ibanez " lost 34 more regions in Russia and Chile.

JOIN ON `name1_shr`, NOT `name1`. The indicator CSVs use ASAP's SHORT
names: "Champagne", "Languedoc R.", "Nord Pas Cala", "Provence". Joining
France on the full name silently drops 4 of its 22 regions and quietly
changes the country figure. Same shape as the U.K.-of-Great-Britain join
this file warned about, and it caught me on the first attempt.

Does NOT fetch. Reads crops/.cache/asap_reference/, which is gitignored.
"""
import os
import struct
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(HERE, ".cache", "asap_reference", "gaul1_asap_v05.zip")
MEMBER = "gaul1_asap.dbf"


def _read_dbf(buf: bytes):
    """dBase III: fixed-width, documented, no library needed."""
    nrec, hlen, rlen = struct.unpack_from("<IHH", buf, 4)
    fields, off = [], 32
    while buf[off] != 0x0D:
        fields.append((buf[off:off + 11].split(b"\x00")[0].decode("utf-8", "replace"),
                       buf[off + 16]))
        off += 32
    out = []
    for i in range(nrec):
        rec = buf[hlen + i * rlen: hlen + (i + 1) * rlen]
        if not rec or rec[:1] == b"*":
            continue
        pos, row = 1, {}
        for name, flen in fields:
            row[name] = rec[pos:pos + flen].decode("utf-8", "replace").strip()
            pos += flen
        out.append(row)
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def crop_areas() -> dict:
    """{asap0_id: {region_short_name: km2_crop}}, or {} if absent.

    KEYED ON asap0_id, NOT ON THE COUNTRY NAME, and that is the second
    name-join failure inside this one function. ASAP spells its own
    country two different ways in two of its own files: the indicator
    CSVs say "Türkiye" with a u-diaeresis (U+00FC) and this shapefile
    says "Tűrkiye" with a u-double-acute (U+0171). All 79 Turkish
    regions matched; the COUNTRY did not, so all 79 were dropped.

    No encoding fix reaches that, because both spellings are valid UTF-8
    of different characters. An id cannot be misspelled. The regions
    still join on name1_shr because the dbf carries no region id the
    indicator CSVs share.

    Returns empty rather than raising, so a build without the reference
    data behaves exactly as it did before rather than failing.
    """
    if not os.path.exists(ZIP):
        return {}
    with zipfile.ZipFile(ZIP) as z:
        rows = _read_dbf(z.read(MEMBER))
    out = {}
    for r in rows:
        km2 = _num(r.get("km2_crop"))
        cid = _num(r.get("asap0_id"))
        if km2 is None or cid is None:
            continue
        out.setdefault(str(int(cid)), {})[r.get("name1_shr", "")] = km2
    return out


if __name__ == "__main__":
    import json as _json
    a = crop_areas()
    print(f"{len(a)} countries, {sum(len(v) for v in a.values())} units")
    _p = _json.load(open(os.path.join(HERE, "data", "stress_current.json")))
    _ids = {x["place"]: str(x["asap0_id"]) for x in _p["places"]}
    for c in ("U.K. of Great Britain and Northern Ireland", "France"):
        w = a.get(_ids.get(c, ""), {})
        tot = sum(w.values())
        print(f"\n{c}: {len(w)} units, {tot:,.0f} km2")
        for k, v in sorted(w.items(), key=lambda kv: -kv[1])[:5]:
            print(f"   {k:18s} {v:>9,.0f} km2  {100*v/tot:5.1f}%")
