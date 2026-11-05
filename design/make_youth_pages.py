"""Build the youth test page: /youth/ and one page per country.

    .venv/bin/python design/make_youth_pages.py              write docs/youth/
    .venv/bin/python design/make_youth_pages.py --preview D  write D, not docs/
    --show-grey   render every block on grey-level countries too. For checking
                  the layout before the data clears its checks; never for
                  publishing, since section 9 says grey shows an outline only.

Refuses to write a page that breaks the rules D-349 set: no "heat", no score,
tier or type, and block 6's survey question is never called protest. A guard,
because the first person to reintroduce one of these words will not be reading
the ruling. Indexable with no nav entry (D-350), so the sitemap finds it.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from templates.youth_page import render_country, render_map  # noqa: E402

BANNED = re.compile(r"\b(heat|score|scores|tier|tiers|hot|anger index)\b", re.I)


def visible(html):
    """The page's own words: head metadata and <main>, with titles,
    aria-labels and alt. NOT the shared masthead, whose nav links to the Heat
    channel on every page of the site; that is navigation, not this page
    describing itself, and the masthead must stay identical everywhere."""
    head = html[:html.index("</head>")]
    main = html[html.index("<main"):html.index("</main>")]
    both = re.sub(r"<script.*?</script>|<style.*?</style>", " ", head + main, flags=re.S)
    attrs = " ".join(re.findall(r'(?:aria-label|alt|title|content)="([^"]*)"', both))
    return re.sub(r"<[^>]+>", " ", both) + " " + attrs


def guard(path, html):
    hit = BANNED.findall(visible(html))
    if hit:
        raise SystemExit(f"REFUSING TO WRITE {path}: {sorted(set(hit))} on the page (D-349).")


def main():
    args = sys.argv[1:]
    out = ROOT / "docs" / "youth"
    if "--preview" in args:
        out = Path(args[args.index("--preview") + 1])
    show_grey = "--show-grey" in args
    if show_grey and "--preview" not in args:
        raise SystemExit("--show-grey is for previews only (section 9).")
    doc = json.loads((ROOT / "youth/data/map.json").read_text())
    geo = json.loads((ROOT / "fires/data/countries.geo.json").read_text())
    root = "../" if "--preview" not in args else "../"
    pages = {"index.html": render_map(doc, geo, root_prefix=root)}
    for iso, entry in doc["countries"].items():
        c = json.loads((ROOT / f"youth/data/countries/{iso}.json").read_text())
        # Flash 585 Q7a: a petition counts, so it is never called protest.
        b6 = c.get("block6_action_to_change_society") or {}
        # "not protest" is the data saying exactly that, so it passes.
        if re.search(r"(?<!not )\bprotests?\b", b6.get("wording") or "", re.I):
            raise SystemExit(f"REFUSING: {iso} block 6 calls Q7a protest.")
        pages[f"{iso.lower()}/index.html"] = render_country(
            c, entry, doc, root_prefix="../../", show_grey=show_grey)
    for rel, html in pages.items():
        guard(rel, html)
    for rel, html in pages.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html)
    print(f"wrote {len(pages)} pages to {out}")


if __name__ == "__main__":
    main()
