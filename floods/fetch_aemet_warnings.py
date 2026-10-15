"""AEMET's current weather warnings (Meteoalerta, CAP format) for rain and
thunderstorms, emitted with their polygons for the explainer's weekend map.

Source: AEMET OpenData avisos_cap/ultimoelaborado/area/esp, a tar of CAP XML
files, one per warning. Kept: the Spanish-language <info> of each warning
whose phenomenon is rain (PR) or thunderstorms (TO), any level. These are
AEMET's warnings, cited as AEMET's; FLO adds nothing to them.

A fetch that returns no warnings is written as zero warnings only if AEMET
answered and the archive parsed; any failure exits non-zero and writes
nothing, so the last good file stays in place.

Run:  .venv/bin/python floods/fetch_aemet_warnings.py
"""
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_intensity as V

NS = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
KEEP = {"PR", "TO"}                 # AEMET phenomenon codes: precipitation, thunderstorms
OUT = os.path.join(HERE, "data", "aemet_warnings_latest.json")


def fetch_tar():
    key = open(os.path.expanduser("~/.aemet_key")).read().strip()
    meta = json.loads(V._get(f"{V.AEMET}/avisos_cap/ultimoelaborado/area/esp", f"api_key: {key}"))
    if "datos" not in meta:
        raise SystemExit(f"AEMET refused: {meta.get('descripcion', '?')}")
    raw = subprocess.run(["curl", "-sS", "-L", "--max-time", "120", meta["datos"]],
                         capture_output=True).stdout
    if len(raw) < 1024:
        raise SystemExit(f"AEMET returned {len(raw)} bytes, not an archive; nothing written")
    return raw


def parse(raw):
    out = []
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        names = [m for m in tf.getmembers() if m.isfile() and m.name.endswith(".xml")]
        if not names:
            raise SystemExit("archive held no CAP files; nothing written")
        for m in names:
            root = ET.fromstring(tf.extractfile(m).read())
            sent = root.findtext("c:sent", namespaces=NS)
            for info in root.findall("c:info", NS):
                if not (info.findtext("c:language", namespaces=NS) or "").startswith("es"):
                    continue
                params = {p.findtext("c:valueName", namespaces=NS): p.findtext("c:value", namespaces=NS)
                          for p in info.findall("c:parameter", NS)}
                level = params.get("AEMET-Meteoalerta nivel", "")
                event = (info.findtext("c:event", namespaces=NS) or "").lower()
                # AEMET's phenomenon is the first code of "parametro" (e.g. "CO;Costeros;"); the event text
                # names it too ("Aviso de lluvias ...", "Aviso de tormentas ..."). Match either, so a change in
                # one field does not silently empty the map (a first version keyed on a field that does not
                # exist and kept 0 of 296 files).
                phen = (params.get("AEMET-Meteoalerta parametro", "") or "").split(";")[0]
                is_rain = phen in KEEP or "lluvia" in event or "tormenta" in event
                if not is_rain or level in ("", "verde"):
                    continue
                phen = phen or ("PR" if "lluvia" in event else "TO")
                for area in info.findall("c:area", NS):
                    polys = []
                    for p in area.findall("c:polygon", NS):
                        pts = [tuple(float(v) for v in pair.split(",")) for pair in (p.text or "").split()]
                        polys.append([[lon, lat] for lat, lon in pts])          # GeoJSON order
                    out.append({"file": m.name, "sent": sent, "event": info.findtext("c:event", namespaces=NS),
                                "level": level, "phenomenon": phen,
                                "threshold": params.get("AEMET-Meteoalerta parametro", ""),
                                "onset": info.findtext("c:onset", namespaces=NS),
                                "expires": info.findtext("c:expires", namespaces=NS),
                                "area": area.findtext("c:areaDesc", namespaces=NS),
                                "geocode": [g.findtext("c:value", namespaces=NS) for g in area.findall("c:geocode", NS)],
                                "polygons_lonlat": polys})
    return out, len(names)


def main():
    raw = fetch_tar()
    warnings, n_files = parse(raw)
    if n_files > 50 and not warnings:
        print("NOTE: no rain or storm warnings in force; check by eye that the filter still matches AEMET's fields")
    res = {"source": "AEMET OpenData, avisos_cap/ultimoelaborado/area/esp (Meteoalerta CAP)",
           "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
           "cap_files_in_archive": n_files, "kept": "Spanish <info>, phenomenon rain (PR) or thunderstorms (TO), "
                                                    "level yellow or above", "warnings": warnings}
    tmp = OUT + ".tmp"
    json.dump(res, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    by = {}
    for w in warnings:
        by.setdefault((w["level"], w["phenomenon"]), 0)
        by[(w["level"], w["phenomenon"])] += 1
    print(f"{n_files} CAP files; kept {len(warnings)} area-warnings: {by}")
    for w in sorted(warnings, key=lambda w: w["onset"] or "")[:12]:
        print(f"  {w['level']:9} {w['phenomenon']} {w['onset']} -> {w['expires']}  {w['area']}  [{w['threshold'][:50]}]")


if __name__ == "__main__":
    main()
