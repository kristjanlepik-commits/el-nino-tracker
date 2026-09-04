"""Sub-national fire regions, for places a country total hides.

WHY THIS EXISTS. Science flagged the northern Amazon as the live risk
for this event: Roraima's July and August detections are all-time
records for those months, the Rio Branco sits at minimums for the date,
and Chen et al. 2017 puts the Northern Hemisphere South America fire
response about nine months after onset, which lands Jan-Apr 2027.

This channel could not see any of it. The roster is national and
Brazil's national figure is dominated by the SOUTHERN Amazon, which is
having a record-quiet season: 4,140,039 ha burnt to week 34 against a
14-year mean of 10,472,910, the lowest of fifteen. Reading Brazil as an
Amazon signal would have said the opposite of what the north is doing.
A country total is not a small version of its regions.

GEOMETRY COMES FROM ASAP'S GAUL1 SHAPEFILE, which crops already has at
`crops/.cache/asap_reference/gaul1_asap_v05.zip`, read with crops' own
parser. Three reasons, in order: it needs no download, it is the same
provenance as the crops channel so a region means the same thing on
both, and the units are the ones ASAP reports in, so a future crops
join is identity rather than judgement.

FULL RESOLUTION, NOT THE SIMPLIFIED SHAPES crops draws with. Measured
on a 0.02 degree grid (~2.2 km, comparable to a VIIRS pixel), the
simplified Roraima disagrees with the full one on 3.43% of the state,
812 cells in one direction and 747 in the other. Net area is within
0.14%, so the simplification is fine for drawing and even for an
anomaly, where the same polygon serves baseline and current year and a
constant bias cancels in the ratio. It is simply free to be exact here:
the zip is already on disk and 4,114 vertices is nothing to test a few
thousand points against.

VALIDATION, and the part worth reading. The extracted Roraima ring
computes to 225,159 km2 against the shapefile's own km2_tot of 223,721
and IBGE's 224,300, a 0.4% agreement. Seven of eight named-point checks
pass, including every negative control: Manaus, Santa Elena de Uairen,
Georgetown, Macapa and Porto Velho all read outside.

The eighth is instructive and is recorded rather than fixed. A point I
took for Rorainopolis reads 8 km OUTSIDE the boundary. I first read that
as a geometry defect and started sizing a southern shortfall of 45 to 65
km, which was wrong: it came from comparing an official shapefile
against a coordinate I had recalled rather than sourced. The
full-resolution polygon excludes that point too, and its area matches
the official figure to 0.4%, so the coordinate is the weaker evidence.
A half-remembered number is not ground truth for a boundary.

KEYS ARE ISO3-SUBDIVISION, e.g. BRA-RR, deliberately unlike the plain
ISO3 the national roster uses, so a sub-national unit can never be
mistaken for a country by a consumer iterating either set.
"""
import importlib.util
import json
import math
import os
import struct
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(REPO, "crops", ".cache", "asap_reference",
                   "gaul1_asap_v05.zip")
OUT = os.path.join(REPO, "fires", "data", "subnational")

# The registry. asap0_id and name1 are the join into GAUL1; both are
# checked on extraction rather than trusted, because a silent name miss
# is how crops lost ten countries once.
REGIONS = {
    "BRA-RR": {"name": "Roraima", "country": "Brazil",
               "asap0_id": 191, "name1": "Roraima",
               "known_km2": 224300,
               "why": ("Northern Amazon. Its dry season is Dec-Apr, "
                       "opposite the southern Amazon's, so a national "
                       "total averages the two into silence.")},

    # ISLANDS ARE UNIONS OF PROVINCES, not GAUL1 units of their own, so
    # `name1` may be a LIST. Sumatra is ten provinces and Kalimantan
    # four; a reader in Kuala Lumpur or Singapore asks which island the
    # smoke is from, and Indonesia's national total cannot answer.
    #
    # KALIMANTAN UTARA IS ABSENT FROM THIS VINTAGE. It was split out of
    # Kalimantan Timur in 2012 and GAUL1 v05 predates the split, so the
    # union is the island as it was drawn then. That is fine for a fire
    # boundary, which follows the coast, and it must not be captioned
    # with a five-province list.
    "IDN-SUM": {"name": "Sumatra", "country": "Indonesia",
                "asap0_id": None,
                "name1": ["Nangroe Aceh Darussalam", "Sumatera Utara",
                          "Sumatera Barat", "Riau", "Jambi", "Bengkulu",
                          "Sumatera Selatan", "Lampung",
                          "Bangka Belitung", "Kepulauan-riau"],
                "known_km2": 482286,
                "why": ("Peatland haze source for Malaysia and Singapore "
                        "as well as Indonesia. The transboundary question "
                        "is which island, and a national total cannot "
                        "answer it.")},

    "IDN-KAL": {"name": "Kalimantan", "country": "Indonesia",
                "asap0_id": None,
                "name1": ["Kalimantan Barat", "Kalimantan Tengah",
                          "Kalimantan Selatan", "Kalimantan Timur"],
                "known_km2": 544150,
                "why": ("Indonesian Borneo. The other half of the haze "
                        "question, and a different peat regime from "
                        "Sumatra's.")},
}


def _shapefile():
    spec = importlib.util.spec_from_file_location(
        "_bs", os.path.join(REPO, "crops", "geom", "build_shapes.py"))
    bs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bs)
    z = zipfile.ZipFile(ZIP)
    rows = bs._dbf(z.read("gaul1_asap.dbf"))
    shx = z.read("gaul1_asap.shx")
    idx = [struct.unpack_from(">ii", shx, 100 + 8 * i)
           for i in range(len(rows))]
    return bs, z, rows, idx


def ring_area_km2(rings):
    """Shoelace with a cosine correction at each ring's mean latitude.

    Good to a fraction of a percent at this size and latitude, which is
    all it is for: a check that the polygon is the region it claims to
    be, not a published figure.
    """
    tot = 0.0
    for ring in rings:
        lat0 = sum(p[1] for p in ring) / len(ring)
        k = math.cos(math.radians(lat0))
        s = sum(ring[j][0] * ring[(j + 1) % len(ring)][1]
                - ring[(j + 1) % len(ring)][0] * ring[j][1]
                for j in range(len(ring)))
        tot += abs(s) / 2 * k * (111.32 ** 2)
    return tot


def extract(key):
    """Pull one region's full-resolution rings out of GAUL1 and check it."""
    spec = REGIONS[key]
    bs, z, rows, idx = _shapefile()
    wanted = (spec["name1"] if isinstance(spec["name1"], list)
              else [spec["name1"]])
    blob = z.open("gaul1_asap.shp").read()
    rings, found = [], []
    for want in wanted:
        hits = [i for i, r in enumerate(rows)
                if str(r.get("name1", "")).strip() == want
                and (spec["asap0_id"] is None
                     or str(r.get("asap0_id", "")).strip()
                     == str(spec["asap0_id"]))]
        # EVERY named unit must match EXACTLY once. A province that
        # silently fails to join makes an island smaller without making
        # anything fail, which is the shape crops lost ten countries to.
        if len(hits) != 1:
            raise SystemExit(
                f"{key}: expected exactly one GAUL1 record named "
                f"{want!r}, got {len(hits)}. Refusing to guess.")
        i = hits[0]
        off, ln = idx[i]
        rings.extend(bs._rings(blob[off * 2 + 8: off * 2 + 8 + ln * 2]))
        found.append(i)
    i = found[0]

    area = ring_area_km2(rings)
    dbf_km2 = sum(float(rows[j]["km2_tot"]) for j in found)
    # A polygon that is not the right SIZE is not the right region, and
    # this is the only automatic check available: the alternative is
    # trusting a name join, which is what it is meant to catch.
    if abs(area - spec["known_km2"]) / spec["known_km2"] > 0.05:
        raise SystemExit(
            f"{key}: extracted polygon is {area:,.0f} km2 against a known "
            f"{spec['known_km2']:,} km2, more than 5% out. Wrong record, "
            f"or the source changed.")

    lons = [p[0] for r in rings for p in r]
    lats = [p[1] for r in rings for p in r]
    return {
        "key": key,
        "name": spec["name"],
        "country": spec["country"],
        "asap0_id": spec["asap0_id"],
        "asap1_id": ([int(str(rows[j]["asap1_id"]).strip())
                      for j in found] if len(found) > 1
                     else int(str(rows[i]["asap1_id"]).strip())),
        "units": wanted,
        "why_tracked": spec["why"],
        "source": ("ASAP GAUL1 reference shapefile v05, full resolution, "
                   "read from crops/.cache/asap_reference/. Same units "
                   "the crops channel reports in."),
        "area_km2_computed": round(area, 1),
        "area_km2_shapefile": dbf_km2,
        "area_km2_official": spec["known_km2"],
        "vertices": sum(len(r) for r in rings),
        "box": [[min(lons), min(lats), max(lons), max(lats)]],
        "rings": rings,
    }


def load(key):
    """The stored polygon, or extract and store it on first use."""
    path = os.path.join(OUT, f"{key}.json")
    if not os.path.exists(path):
        os.makedirs(OUT, exist_ok=True)
        json.dump(extract(key), open(path, "w"))
    return json.load(open(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    for key in REGIONS:
        doc = extract(key)
        json.dump(doc, open(os.path.join(OUT, f"{key}.json"), "w"))
        print(f"  {key} {doc['name']}: {doc['vertices']:,} vertices, "
              f"{doc['area_km2_computed']:,.0f} km2 computed vs "
              f"{doc['area_km2_official']:,} official "
              f"({doc['area_km2_computed']/doc['area_km2_official']:.1%})")
        print(f"    bbox {doc['box'][0]}")


if __name__ == "__main__":
    main()
