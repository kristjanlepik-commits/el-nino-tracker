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
import subprocess
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache", "asap_reference")
ZIP = os.path.join(CACHE, "gaul1_asap_v05.zip")
MEMBER = "gaul1_asap.dbf"

# WHERE THESE CAME FROM. Recorded because they were not, and fires built
# a published cropland gate on the raster below without being able to
# reproduce it: crops/.cache is gitignored, so the file existed on one
# laptop and nowhere else, and nothing in this module said where to get
# another. Same shape as the London MIDAS baseline that turned out to
# live in a release rather than the repo.
#
# The download page is JavaScript-driven, so curl sees no links and a
# guess at the endpoint returns HTML with HTTP 200. That is how fires
# got HTML back rather than a TIFF. The real files sit under /files/.
BASE = "https://agricultural-production-hotspots.ec.europa.eu/files"
SOURCES = {
    # what we weight with: cropland area per GAUL1 unit, already zonal
    "gaul1_asap_v05.zip": f"{BASE}/gaul1_asap_v05.zip",
    # the raster itself, which fires uses per detection
    "asap_mask_crop_v04.tif": f"{BASE}/asap_mask_crop_v04.tif",
    "asap_mask_rangeland_v04.tif": f"{BASE}/asap_mask_rangeland_v04.tif",
    "crop_calendar_gaul1.zip": f"{BASE}/crop_calendar_gaul1.zip",
}

# VINTAGE IS IN THE FILENAME AND THAT IS THE ONLY VERSIONING JRC GIVES.
# The mask is v04 and the boundaries v05; the files carry no internal
# date and the endpoint returns no useful Last-Modified we should rely
# on. So a published ratio computed against v04 is a claim about v04,
# and if JRC ships v05 of the mask that is a DIFFERENT claim rather than
# a refreshed one. Pin by filename, and if the name changes, treat every
# number computed from it as needing recomputation rather than carrying
# forward.
VINTAGE = {"crop_mask": "v04", "boundaries": "v05"}
RETRIEVED = "2026-08-18"


def ensure(name: str, quiet: bool = False) -> str:
    """Return a local path for one reference file, downloading if absent.

    So the capability is a pipeline one rather than a laptop one. Does
    nothing when the file is already cached, and never runs inside a
    publish: reference data is fetched deliberately, like the indicator
    pull, not as a side effect of building a page.
    """
    if name not in SOURCES:
        raise KeyError(f"{name} is not an ASAP reference file; "
                       f"known: {sorted(SOURCES)}")
    dest = os.path.join(CACHE, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(CACHE, exist_ok=True)
    tmp = dest + ".partial"
    # .partial then rename, so a failed or truncated download never
    # replaces a good file. Same rule as the indicator puller.
    code = subprocess.run(
        ["curl", "-sSL", "--max-time", "1800", "-o", tmp,
         "-w", "%{http_code}", SOURCES[name]],
        capture_output=True, text=True).stdout.strip()
    if code != "200" or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise RuntimeError(f"{name}: HTTP {code}, refusing to cache")
    os.replace(tmp, dest)
    if not quiet:
        print(f"fetched {name} ({os.path.getsize(dest)/1048576:.1f} MB) "
              f"from {SOURCES[name]}")
    return dest


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
