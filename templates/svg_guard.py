#!/usr/bin/env python3
"""Parse every inline SVG as standalone XML, at build time.

FLOODS' PROPOSAL, 2026-09-01, and their reasoning is the whole point:
neither fault found on the Alto Beni hydrograph was reachable by
qa_check, and one of them is LEGAL inside an HTML document. `&sup3;` is
a named HTML entity, so a browser renders it happily while the SVG sits
in the page; it only breaks once that SVG is opened, downloaded or
embedded on its own, where there is no HTML DTD to define the name.

So the defect is invisible to every check that reads the page as HTML,
which is every check we have. The page is the wrong object to validate:
the SVG is a separate document that happens to be transported inside one.

WHY IT LIVES IN templates/ RATHER THAN scripts/. Design builds all front
end under D-030, so every inline SVG on the site is emitted by something
in here. A guard at this seam covers every channel without needing a
pass over docs/, and it fails the build that WROTE the defect rather
than a later run that merely finds it.

Numeric references are always safe (&#179;). Of the named ones only the
five XML built-ins survive outside HTML: amp, lt, gt, quot, apos.
"""
import re
import xml.etree.ElementTree as ET

_SVG = re.compile(r"<svg\b.*?</svg\s*>", re.S | re.I)
_XML_SAFE = {"amp", "lt", "gt", "quot", "apos"}
_NAMED = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")


def check_svgs(html, where):
    """Raise SystemExit on any inline SVG that is not standalone XML."""
    for i, m in enumerate(_SVG.finditer(html), 1):
        frag = m.group(0)

        # Named entities first, because ET reports them as a generic
        # "undefined entity" at a line offset inside the fragment, which
        # is useless for finding the character in a generated page.
        bad = sorted({e for e in _NAMED.findall(frag) if e not in _XML_SAFE})
        if bad:
            raise SystemExit(
                "%s: inline SVG %d uses HTML-named entit%s %s, undefined "
                "in standalone XML. %s correctly in the page and break%s the "
                "moment the SVG is opened on its own. Use a numeric "
                "reference: &sup3; -> &#179;."
                % (where, i, "y" if len(bad) == 1 else "ies",
                   ", ".join("&%s;" % b for b in bad),
                   "It renders" if len(bad) == 1 else "They render",
                   "s" if len(bad) == 1 else ""))
        try:
            ET.fromstring(frag)
        except ET.ParseError as exc:
            raise SystemExit(
                "%s: inline SVG %d is not well-formed XML: %s. It may still "
                "render, because an HTML parser recovers from things an XML "
                "parser refuses, which is exactly why this check reads it as "
                "XML." % (where, i, exc))
