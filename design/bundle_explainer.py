"""One self-contained HTML file of the flood explainer, for review.

VD cannot read the repo or reach a local preview (D-125), so this inlines
everything the preview build loads: fonts, the vendored three.js and Motion,
the scene modules, the data files and the images, as data: URLs. The page's
own asset requests ("assets/x.png", fetch("assets/x.json"), Image.src) are
redirected to the inlined copies by a small shim that runs first.

For review only. Never publish this file: the real page loads the same
files from docs/ and is what the guards check. Writes to OUT (first
argument), which should be outside the repo: the bundle is several MB and
an untracked file over 5 MB trips qa_check for every chat.

Run:  .venv/bin/python design/make_flood_explainer.py --preview
      .venv/bin/python design/bundle_explainer.py OUT.html
"""
import base64
import json
import mimetypes
import re
import sys
from pathlib import Path

PAGE = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/el_nino_preview/floods/how-a-flood-is-made")
ROOT = PAGE.parent.parent                     # /tmp/el_nino_preview
OUT = Path(sys.argv[1])


def data_url(path, mime=None):
    mime = mime or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).endswith((".js", ".mjs")):
        mime = "text/javascript"
    return "data:%s;base64,%s" % (mime, base64.b64encode(Path(path).read_bytes()).decode())


html = (PAGE / "index.html").read_text()

# fonts
html = re.sub(r'url\(["\']?\.\./\.\./fonts/([^"\')]+)["\']?\)',
              lambda m: 'url("%s")' % data_url(ROOT / "fonts" / m.group(1), "font/woff2"), html)

# import map: three and its addons as data URLs (addons import a bare
# "three", which the same map resolves)
imap = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S).group(1))
addons = ROOT / "vendor/three-0.160.0/addons"
new_map = {"three": data_url(ROOT / "vendor/three-0.160.0/three.module.min.js")}
for f in addons.rglob("*.js"):
    new_map["three/addons/" + f.relative_to(addons).as_posix()] = data_url(f)
html = re.sub(r'<script type="importmap">.*?</script>',
              '<script type="importmap">%s</script>' % json.dumps({"imports": new_map}),
              html, count=1, flags=re.S)

# Motion (UMD) inline
html = re.sub(r'<script src="\.\./\.\./vendor/motion-11\.11\.13/motion\.js"></script>',
              lambda m: "<script>%s</script>" % (ROOT / "vendor/motion-11.11.13/motion.js").read_text(),
              html)

# scene modules inline
html = re.sub(r'<script type="module" src="(scene_\w+\.js)\?v=\w+"></script>',
              lambda m: '<script type="module">%s</script>' % (PAGE / m.group(1)).read_text(),
              html)

# assets: every file the page or its scripts name
assets = {}
for f in (PAGE / "assets").iterdir():
    name = "assets/" + f.name
    if name in html:
        assets[name] = data_url(f)
# Every image the scene data names. A fixed list missed the forecast act's
# textures (pump_wk_*), which then rendered black in the bundle (Kristjan).
for js in ("pump.json", "heat_morph.json"):
    jp = PAGE / "assets" / js
    if jp.exists():
        for name in set(re.findall(r'"([\w.-]+\.png)"', jp.read_text())):
            if (PAGE / "assets" / name).exists():
                assets["assets/" + name] = data_url(PAGE / "assets" / name)
for name in ("pump_sea.png", "heat_lines.png", "pump.json", "heat_morph.json"):
    if (PAGE / "assets" / name).exists():
        assets["assets/" + name] = data_url(PAGE / "assets" / name)
html = re.sub(r'src="(assets/[^"]+)"', lambda m: 'src="%s"' % assets.get(m.group(1), m.group(1)), html)

shim = """<script>
// Review bundle: route the page's asset requests to the inlined copies.
(function () {
  var A = %s;
  var f = window.fetch;
  window.fetch = function (u, o) { return f.call(window, A[u] || u, o); };
  var d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  Object.defineProperty(HTMLImageElement.prototype, "src", {
    get: d.get, set: function (v) { d.set.call(this, A[v] || v); }, configurable: true });
})();
</script>""" % json.dumps(assets)
html = html.replace("<head>", "<head>\n" + shim, 1)

# the analytics tag has no business in a review file
html = re.sub(r'<script[^>]*plausible[^>]*>.*?</script>', "", html, flags=re.S)
html = re.sub(r'<script>\s*window\.plausible.*?</script>', "", html, flags=re.S)

OUT.write_text(html)
print("wrote", OUT, "%.1f MB" % (OUT.stat().st_size / 1e6), "| assets inlined:", len(assets))
