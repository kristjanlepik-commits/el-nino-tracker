# crosscheck: verification only, never a published source

Nothing in this directory may be rendered, quoted or derived from for
publication. It exists so a published number can be checked against an
independent record.

## Why this is a path and not a note

`city_histories_ECAD.json` is built from ECA&D. The published payload
(`heat/data/city_nights.json`) is built from AEMET and Meteo-France.

Those are **different source bases by design**, not a stale file. Two things
follow that a note at the top of the file would not have prevented:

1. **ECA&D is non-commercial.** Anything derived from it and published
   carries a licence we cannot honour once a sponsor exists. AEMET permits
   commercial reuse; Meteo-France is Licence Ouverte 2.0; GeoSphere is CC0.
2. **The numbers legitimately differ.** French cities are cut at 3 August and
   Spanish at 2 August, because the sources have different lags. Marseille
   reads 20.9 here and 21.5 in the payload. Both are correct. Paris agrees at
   1.5 in both **by rounding** (1.467 against 1.533), which is worse than
   disagreeing, because a file that agrees gets trusted.

A note is read by whoever opens the file. A path is read by everyone who
lists the directory.

## Status

Deprecated 2026-08-06. Delete after 2026-08-17.

Retained until then because removing a file underneath design mid-build is
risk with no upside. The `sd` values design derived from it for VD's
instrument are being regenerated on the published AEMET basis.
