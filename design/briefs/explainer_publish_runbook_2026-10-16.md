# Publish runbook: "How a flood is made" + "Así se forma una inundación"

Friday 16 October 2026, target ~09:30 (D-331). Design runs this; Kristjan
said not to wait for him on anything. Every step is a command or a check.

## 0. Inputs due before publish

- [ ] FLO: `pump_weekend` refreshed from ECMWF's **Fri 00 UTC** run (out ~09:00),
      with a yes/no on whether it still shows a cold pool and onshore flow.
      Check: `git fetch && git show origin/main:floods/data/explainer_2026-10.json | python3 -c "import json,sys;print(json.load(sys.stdin)['pump_weekend']['run'])"`
      must read `2026-10-16T00:00`.
- [ ] AEMET warnings refreshed (06:30 job): `fetched_utc` in
      `floods/data/aemet_warnings_latest.json` is Friday morning; else run
      `.venv/bin/python floods/fetch_aemet_warnings.py`.
- [ ] Editor: `weekend` slot rewritten in both languages for the new order
      (asked 16 Oct overnight). If the new run moved the forecast figures,
      `pump-wk-1/2` back to the editor (EN and ES).
- [ ] FLO sign-off on the rendered page; CPO approval (D-318 pass done;
      usability/flow review asked overnight).

## 1. Build

```
HEAT_MONTHS_NC=<scratch>/heat_months.nc .venv/bin/python design/make_explainer_assets.py
.venv/bin/python design/make_flood_explainer.py --preview
.venv/bin/python design/make_flood_explainer.py --preview --lang es
```
If `heat_months.nc` is gone: `.venv/bin/python design/fetch_heat_months.py <scratch>/heat_months.nc`
(ERA5 monthly, a few minutes). Without it the heat chapter falls back to the
September still, which is acceptable but not the moving version.

Check in the browser (pane VISIBLE, or animations pause): pump clock vs
captions in 05; forecast stage in 07 (run time on the stamp, AEMET note);
weekend map layers; Spanish page labels and decimal commas; phone width.

## 2. Publish build

```
.venv/bin/python design/make_flood_explainer.py
.venv/bin/python design/make_flood_explainer.py --lang es
.venv/bin/python templates/floods_index.py
.venv/bin/python scripts/build_sitemap.py
.venv/bin/python scripts/qa_check.py
```
The publish build REFUSES if any prose slot is empty or a pump caption
does not start with its date.

## 3. Commit (pathspec on the commit, never -A)

```
git add docs/vendor docs/floods/how-a-flood-is-made docs/floods/asi-se-forma-una-inundacion docs/floods/index.html docs/sitemap.xml
git commit docs/vendor docs/floods/how-a-flood-is-made docs/floods/asi-se-forma-una-inundacion docs/floods/index.html docs/sitemap.xml -m "..."
```
Message names three@0.160.0 and motion@11.11.13 (platform asked for the
versions in the commit) and D-327/D-328/D-331.

## 4. Verify live

`curl -sI https://thelongswell.com/floods/how-a-flood-is-made/` and read
`age` / `x-cache` (a query string does NOT bust the cache; treat any age
older than the publish as unverified, in BOTH directions). Then open both
pages and check the 3D stages render and the vendor files load (no CDN).

## 5. After

- Regenerate the GIFs from the new run:
  `.venv/bin/python design/make_social_gifs.py <scratch>/social all`
- Tell FLO, CPO, editor, platform (vendor folder now live), socials (GIFs).
- Log the publish in the ledger if anything was decided on the way.
