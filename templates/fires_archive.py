#!/usr/bin/env python3
"""Every country the fire channel has assessed, current or not.

WHY IT EXISTS. 49 country pages existed and 18 were linked. The other 31
were reachable only by knowing the URL, and four of them are stories we
published: Belgium's national record, Serbia's record week that socials
posted, Bosnia, Macedonia. Somebody who read the post, or found a search
result, landed on a page nothing on the site linked to.

Fire was about to noindex them and looked first. Blanket noindex would
have hidden four pieces we actively promoted, including the one Kristjan
graded our clearest failure of the week for arriving late. Having arrived
late, hiding it afterwards is worse.

THE REFRAME THAT MAKES THIS EASY IS FIRE'S. A country leaving the
qualifying set is not a page expiring. The page is an archived assessment
with a date on it, and it already says so on its own face. Falling out of
the gate is a reason to stop presenting it as current, not a reason to
stop linking it.

THE LABEL IS NOT "LAST ASSESSED", AND THAT IS THE ONE THING TO GET RIGHT
HERE. The field is called last_assessed and it records when a country last
QUALIFIED. We check all 97 every day. If the page says "last assessed" a
reader hears "last looked at", and the archive would then quietly assert
that we stopped watching 31 countries. Fire flagged the wording as mine
before I could get it wrong, so it reads "last qualified" throughout, with
the daily check stated in prose above the list.

NAMES ARE NOT DERIVED FROM SLUGS. A slug is not a name: "republic-of-
serbia" is the roster's own spelling and title-casing it produces
something we do not call the country anywhere else. 48 of 49 slugs happen
to invert cleanly against the roster and the 49th, Ethiopia, is not in the
roster at all, which is exactly the kind of near-miss that makes a derived
join look safe until it silently is not. So the name is required in the
payload and the build fails loudly without it.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "fires" / "data" / "country_archive.json"

_MON = ("January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December")


def _pretty(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return "%d %s" % (d, _MON[m - 1])


def _load():
    doc = json.loads(ARCHIVE.read_text())
    rows = doc["countries"]

    # SAME SHAPE AS crops_map's CENTROID GUARD, and for the same reason:
    # a country silently missing from a list of every country we have
    # looked at is the worst failure this component has available.
    missing = sorted(r["slug"] for r in rows if not r.get("name"))
    if missing:
        raise SystemExit(
            "fires/data/country_archive.json has no `name` on %d row(s): "
            "%s.\nThe name is not derived here on purpose. A slug is not a "
            "name, and title-casing 'republic-of-serbia' invents a spelling "
            "we use nowhere else. Emit `name` per row rather than have this "
            "template guess it."
            % (len(missing), ", ".join(missing)))

    for r in rows:
        if not r.get("last_assessed"):
            raise SystemExit(
                "row %r has no last_assessed. An undated row in an archive "
                "reads as current, which is the thing this page exists to "
                "prevent." % r["slug"])
    rows.sort(key=lambda r: (not r.get("current"), r["name"]))
    return doc, rows


def _row_html(r, root_prefix):
    cur = bool(r.get("current"))
    return (
        '<li class="fa%s">'
        '<a class="faa" href="%s%s">%s</a>'
        '<span class="fastate">%s</span>'
        '<span class="fadate">last qualified %s</span>'
        '</li>'
        % (" facur" if cur else "",
           root_prefix, r["href"], r["name"],
           "qualifying this week" if cur else "not current",
           _pretty(r["last_assessed"])))


CSS = """
.fawrap{max-width:820px;margin:0 auto;padding:26px 24px 80px}
.falede{font-family:var(--serif);font-size:30px;line-height:1.2;
  letter-spacing:-.012em;margin:16px 0 12px;max-width:24ch}
.fastand{font-size:17px;line-height:1.6;color:var(--ink-soft);
  max-width:64ch;margin:0 0 8px}
.fasec{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  font-weight:600;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-faint);margin:34px 0 0;padding-bottom:8px;
  border-bottom:1px solid var(--ink)}
/* The distinction the whole page turns on, at the weight of a finding. */
.falimit{border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);
  padding:14px 0 15px;margin:22px 0 0;max-width:64ch}
.falimit b{font-family:var(--serif);font-size:18px;line-height:1.35;
  display:block;margin-bottom:6px}
.falimit span{font-size:14.5px;line-height:1.55;color:var(--ink-soft)}
ul.falist{list-style:none;margin:0;padding:0}
.fa{display:grid;grid-template-columns:1fr auto auto;gap:0 16px;
  align-items:baseline;border-bottom:1px solid var(--rule);padding:11px 0}
.faa{font-family:var(--serif);font-size:17px;color:var(--ink);
  text-decoration:none}
.faa:hover{text-decoration:underline}
/* D-043: a country that is not qualifying is drawn at full weight, not
   greyed. "Not current" is a value a reader should see, not an absence
   they skip past. */
.fastate{font-family:"__D__",ui-monospace,monospace;font-size:10px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft)}
.facur .fastate{color:var(--fire);font-weight:600}
.fadate{font-family:"__D__",ui-monospace,monospace;font-size:11px;
  color:var(--ink-faint);white-space:nowrap;font-variant-numeric:tabular-nums}
.fanote{font-size:14.5px;line-height:1.55;color:var(--ink-soft);
  max-width:64ch;margin:16px 0 0}
@media(max-width:620px){
  .falede{font-size:24px}
  .fa{grid-template-columns:1fr auto;gap:2px 12px}
  .fadate{grid-column:1/-1}
}
"""


def render(root_prefix="../"):
    sys.path.insert(0, str(ROOT))
    import tokens as T
    from templates.page_head import head_meta
    from run_brief import (site_masthead, SITE_MASTHEAD_CSS,
                           ANALYTICS_SNIPPET)
    from templates.subscribe_band import band as sub_band, css as sub_css

    doc, rows = _load()
    n, cur = len(rows), sum(1 for r in rows if r.get("current"))

    # DERIVED, NEVER TYPED (D-124). All three of these move every week.
    lede = "Every country this channel has assessed."
    stand = (
        "%d countries have had a fire assessment published. %d of them "
        "cleared the anomaly gate in the week just measured; the other %d "
        "did not, and their pages carry the last week they did. Every one "
        "is listed, because a country dropping out of a week's findings is "
        "not the same as our never having looked at it."
        % (n, cur, n - cur))

    body = """
<div class="falimit"><b>A date here is when a country last qualified, not
when we last looked at it.</b><span>All 97 countries with a baseline are
checked every day. A country appears in the week's findings only when it
clears the anomaly gate, so "not current" means its most recent week was
ordinary by its own standards, not that it stopped being measured.</span>
</div>
<p class="fasec">%d countries, %d qualifying this week</p>
<ul class="falist">
%s
</ul>
<p class="fanote">Pages for countries that are not currently qualifying
stay published and say so on their own face. Four of them carry pieces we
published at the time, so removing or hiding them would break links that
readers and search results still follow.</p>
""" % (n, cur, "\n".join(_row_html(r, root_prefix) for r in rows))

    css = (CSS.replace("__D__", T.FONT_DATA) + sub_css() + SITE_MASTHEAD_CSS)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
%s
<title>Countries assessed | Fires | The Long Swell</title>
<style>
%s
:root {{ {vars} }}
</style>
</head>
<body>
%s
<main class="fawrap">
  <p class="fasec" style="border:0;margin-top:6px">Fires</p>
  <h1 class="falede">%s</h1>
  <p class="fastand">%s</p>
  %s
  %s
</main>
</body>
</html>
""".replace("{vars}", T.css_variables()) % (
        head_meta(title="Countries assessed | Fires | The Long Swell",
                  description=lede, path="/fires/countries/"),
        ANALYTICS_SNIPPET, css, site_masthead(root_prefix), lede, stand,
        body, sub_band())


def main():
    out = ROOT / "docs" / "fires" / "countries" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(root_prefix="../../"))
    print("wrote %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
