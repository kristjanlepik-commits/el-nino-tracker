#!/usr/bin/env python3
"""A channel's methodology page, from that channel's markdown.

Kristjan asked for methodology pages on every channel, "like the El Nino
has". Measured 2026-08-30: /fires/methodology, /crops/methodology and
/floods/methodology were all absent while /methodology.html and
/heat/methodology.html served.

TEMPLATE-FIRST (D-030 condition 1). One renderer, one per-channel entry,
so a fourth channel is a markdown file and a line in CHANNEL_DOCS rather
than a fourth page builder.

THE NUMBERS COME FROM THE PAYLOAD, NOT THE PROSE. Fire's instruction and
their reason is heat's: three consumers retyped one of heat's fields and
all three were wrong within days. So a channel's thresholds render from
its emitted method block, and if a figure can be read it is read. A
sync script is only needed for claims that are genuinely prose.

Fire kept every threshold OUT of their markdown for exactly this reason,
which is why this page generates the table rather than substituting into
a sentence.

WHAT THIS PAGE MUST NOT BECOME. Both fire and product asked for the same
thing independently: the standing limits are the substance, not an
appendix. A methodology page that leads with the method and buries the
caveats is weaker than the channel page it explains, because the channel
page already carries its qualification next to each number. The ordering
is the channel's, in their own markdown, and fires puts the limits third
of five with the strongest one first. This renderer does not reorder.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# channel key -> (markdown source, output path, nav key, title)
CHANNEL_DOCS = {
    "fires": ("fires/methodology.md", "docs/fires/methodology.html",
              "fire", "Fires: how these numbers are made"),
    "crops": ("crops/methodology.md", "docs/crops/methodology.html",
              "crop", "Crops: how these numbers are made"),
    "floods": ("floods/methodology.md", "docs/floods/methodology.html",
               "flood", "Floods: how these numbers are made"),
}

# Where each channel emits the machine-readable thresholds, and the label
# each key gets. The LABEL is presentation and lives here; the VALUE is
# science and never does.
METHOD_SOURCES = {
    "fires": ("data/events.json", ("method",)),
}

_LABELS = {
    "noise_floor_detections":
        "Detections below which a country cannot qualify at all",
    "record_rank": "Rank that counts as a record",
    "strong_multiple": "Multiple described as strong",
    "cropland_enriched_above":
        "Cropland ratio above which detections are called enriched",
    "cropland_depleted_below":
        "Cropland ratio below which they are called depleted",
    "cropland_min_detections_on_crop":
        "Detections ON cropland required before an enriched ratio is stated",
    "persistence_recur_pct_above":
        "Recurrence in the same cell, above which heat looks persistent",
    "persistence_night_pct_above": "Night share, above which likewise",
    "persistence_frp_median_below": "Median radiative power, below which",
    "persistence_peak_to_median_at_or_below": "Peak-to-median, at or below",
    "baseline_years": "Baseline",
}


# A channel that emits its methodology version machine-readably. Where it
# does, the prose is CHECKED against it rather than trusted.
VERSION_SOURCES = {
    "crops": ("crops/data/stress_current.json", "methodology_version"),
    "floods": ("floods/data/payload_*.json", "methodology_version"),
}

_VERSION_HEADINGS = ("version history", "methodology change log",
                     "change log", "version log")


def _version_section(md):
    """The version-history section's body, or None if there is none."""
    lines = md.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("#") and any(
                h in ln.lower() for h in _VERSION_HEADINGS):
            start = i + 1
            break
    if start is None:
        return None
    body = []
    for ln in lines[start:]:
        if ln.startswith("## "):
            break
        body.append(ln)
    return "\n".join(body).strip()


def _check_version(channel, md):
    """Every methodology page carries a version history, and it is current.

    Kristjan's requirement, 2026-08-30: every channel's methodology page
    tracks its changes the way the El Nino page does, which keeps a dated
    change log tied to METHODOLOGY_VERSION.

    ENFORCED RATHER THAN REMEMBERED. A requirement that lives only in a
    conversation is one a future channel launches without, and nothing
    would fail: the page would simply render, complete-looking and
    silent about what changed.

    THE TEXT IS THE CHANNEL'S. This refuses and names them; it does not
    draft a history, because a change log written by whoever rendered the
    page is a record of what they could infer rather than what happened.
    """
    body = _version_section(md)
    if not body:
        raise SystemExit(
            "REFUSING TO BUILD %s: its methodology has no version history.\n"
            "Every methodology page tracks its own changes, as the El Nino "
            "page does. Add a '## Version history' section to the channel's "
            "markdown, newest first, each entry saying what changed and "
            "what it affects.\n"
            "The text is the channel's, not design's: ask %s to write it."
            % (channel, channel))

    spec = VERSION_SOURCES.get(channel)
    if not spec:
        return
    path, key = spec
    try:
        if "*" in path:
            cands = sorted((ROOT).glob(path), reverse=True)
            want = None
            for f in cands:
                v = json.loads(f.read_text()).get(key)
                if v is not None:
                    want = str(v)
                    break
            if want is None:
                return
        else:
            want = str(json.loads((ROOT / path).read_text())[key])
    except (OSError, KeyError, ValueError):
        return
    if want not in body:
        raise SystemExit(
            "REFUSING TO BUILD %s: the payload reports methodology version "
            "%s and the version history does not mention it.\n"
            "A page whose change log stops short of the version that "
            "produced its numbers is worse than none: it dates the method "
            "to the last time someone remembered to write it down."
            % (channel, want))


def _method(channel):
    """The channel's emitted thresholds, or None if it publishes none."""
    spec = METHOD_SOURCES.get(channel)
    if not spec:
        return None
    path, keys = spec
    try:
        d = json.loads((ROOT / path).read_text())
    except (OSError, ValueError):
        return None
    for k in keys:
        d = (d or {}).get(k)
        if d is None:
            return None
    return d if isinstance(d, dict) else None


def _thresholds_md(channel):
    """The thresholds table, generated, or "" when a channel emits none.

    RETURNS MARKDOWN so it joins the channel's own document in one render
    rather than being a second styled block bolted underneath. A reader
    should not be able to tell which paragraphs were written and which
    were generated; they should only be able to tell that the numbers
    match the pages.
    """
    m = _method(channel)
    if not m:
        return ""
    rows, unknown = [], []
    for k, v in sorted(m.items()):
        if k not in _LABELS:
            if not k.startswith("_"):
                unknown.append(k)
            continue
        rows.append("| %s | `%s` | %s |" % (_LABELS[k], k, v))
    if unknown:
        print("  NOTE: %s emits %d threshold(s) with no label here, so they "
              "are not on the page: %s.\n  Add a label in _LABELS rather "
              "than letting a key name become reader copy."
              % (channel, len(unknown), ", ".join(unknown)),
              file=sys.stderr)
    if not rows:
        return ""
    out = [
        "",
        "## The thresholds, as the code applies them",
        "",
        "Read from the channel's own emitted method block rather than "
        "typed here, so this table cannot drift from the pages. The key "
        "is printed beside each value so a figure on a page can be traced "
        "to the field that set it.",
        "",
        "| What it sets | Field | Value |",
        "| --- | --- | --- |",
    ]
    out.extend(rows)
    return "\n".join(out)


def render(channel, root_prefix="../"):
    sys.path.insert(0, str(ROOT))
    from run_brief import render_html

    spec = CHANNEL_DOCS.get(channel)
    if not spec:
        raise SystemExit("no methodology entry for channel %r" % channel)
    src, out, nav, title = spec
    doc = ROOT / src
    if not doc.exists():
        raise SystemExit(
            "%s does not exist. The methodology text is the CHANNEL's, not "
            "design's: ask %s to write it rather than drafting it here."
            % (src, channel))

    md = doc.read_text()
    _check_version(channel, md)
    extra = _thresholds_md(channel)
    if extra:
        md = md.rstrip() + "\n" + extra + "\n"

    return render_html(
        md, title=title, root_prefix=root_prefix, analytics=True,
        nav_active=nav, canonical_path="/" + out[len("docs/"):],
        description=title)


PREVIEW_DIR = Path("/private/tmp/claude-505/"
                   "-Users-admin-Documents-Claude-Projects-El-Nino-Tracker/"
                   "963b8065-d8cb-408a-9195-33d00aeda096/scratchpad")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    channel = args[0] if args else None
    if channel not in CHANNEL_DOCS:
        raise SystemExit("usage: methodology_page.py <%s> [--publish]"
                         % "|".join(sorted(CHANNEL_DOCS)))
    html = render(channel)

    if "--publish" not in sys.argv:
        out = PREVIEW_DIR / ("preview_%s_methodology.html" % channel)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
        print("preview: %s\n"
              "  Not in docs/. An uncommitted page under docs/ fails "
              "qa_check for every chat in this tree while appearing in "
              "nobody's diff.\n"
              "  Use --publish once %s has signed the page off."
              % (out, channel))
        return

    out = ROOT / CHANNEL_DOCS[channel][1]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print("PUBLISHED %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
