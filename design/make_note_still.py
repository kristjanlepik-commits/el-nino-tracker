"""Still for Kristjan's Note "How is a flood made?" (16 Oct 2026).

One measured frame of the explainer's pump: the warm sea, the cold air 5 km
up arriving over it, and the wind 1.5 km up turning onshore at Barcelona.
His Note says the warm sea is a precondition and the cold air and wind are
what set it off; this is the one frame that shows all three at once.

Same layers and drawing code as the social GIFs (design/make_social_gifs.py),
saved as a full-colour PNG for the Note page and the Kit email, not as a
64-colour GIF frame. Every layer is ERA5, measured.

Run:  .venv/bin/python design/make_note_still.py OUT.png [YYYY-MM-DDTHH]
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

out = Path(sys.argv[1])
when = sys.argv[2] if len(sys.argv) > 2 else "2026-10-03T00"
sys.argv = [sys.argv[0], "/tmp"]                # the GIF module reads OUT from argv
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_social_gifs as G                    # noqa: E402

G.set_box((-24.0, 9.6, 33.0, 58.0))             # the Atlantic, where the cold pool sat
P = G.P
sea = G.crop(Image.open(G.ASSETS / P["sea"]["img"]).convert("RGB"))
colds = [G.crop(Image.open(G.ASSETS / f["img"]).convert("RGBA"), 0.5) for f in P["cold"]["frames"]]
times = [G.ts(f["time"]) for f in P["cold"]["frames"]]
W, WF = P["wind"], P["wind"]["frames"]
t0w, stw = G.ts(WF[0]["time"]), G.ts(WF[1]["time"]) - G.ts(WF[0]["time"])
start = G.ts("2026-09-28T00:00:00+00:00")
target = G.ts(when + ":00:00+00:00")

# run the particles up to the target so the trails are the wind of that moment
flow = G.Flow(seed=5)
N = 40
for f in range(N + 1):
    tm = start + (target - start) * f / N
    flow.step(lambda lo, la: G.wind_at(W, WF, t0w, stw, lo, la, tm), 1 / 10)
tm = target
wind = lambda lo, la: G.wind_at(W, WF, t0w, stw, lo, la, tm)
for _ in range(8):                               # settle the trails on the final field
    flow.step(wind, 1 / 10)

k = max(0, min(len(times) - 2, int((tm - times[0]) // (times[1] - times[0]))))
a = max(0, min(1, (tm - times[k]) / (times[k + 1] - times[k])))
fr = Image.alpha_composite(sea.copy().convert("RGBA"), Image.blend(colds[k], colds[k + 1], a))
fr = Image.alpha_composite(fr, flow.layer())
d = ImageDraw.Draw(fr)
G.cities(d)
o = G.onshore(wind(3.0, 41.0), 100, 165)
if o:
    w = wind(3.0, 41.0)
    G.arrow(d, 2.75, 41.1, w[0], w[1], "onshore · from the %s · %.0f m/s" % (G.COMPASS[round(o[1] / 45) % 8], o[0]))
dt = datetime.fromtimestamp(tm, timezone.utc)
G.header(d, "MEASURED · ERA5", "%d %s, %02d:00 UTC" % (dt.day, G.MON[dt.month - 1], dt.hour),
         "cold air 5 km up (blue) · wind 1.5 km up · sea, September vs normal")
G.footer(d, "ERA5, 2026 preliminary · every layer measured")
fr.convert("RGB").save(out, optimize=True)
print(out, "onshore" if o else "NO onshore arrow", fr.size)
