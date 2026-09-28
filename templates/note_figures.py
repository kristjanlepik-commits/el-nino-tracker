"""An editor's note's chart is a figure, not part of the note's text (D-309).

ONE IMPLEMENTATION, TWO SURFACES. /elnino/ and the dated weekly brief both
render the same editorial_note.md, and science lifted the chart out of the
note box on /elnino/ on 2026-09-28 while the brief still boxed it at 517px
against 744px for its other charts. Two copies of a rule is how the two
pages came to disagree on the unstamped-note case three weeks ago: the
FILE was single-source and the RULE was implemented twice. So the rule
lives here and each surface decides only where the lifted figures go.
"""
import re

_IMG_PARA = re.compile(r"<p>\s*(<img\b[^>]*>)\s*</p>")


def lift_image_paragraphs(html):
    """Remove every paragraph that holds only an image.

    Returns (html_without_them, [img_tag, ...]) in document order. A
    paragraph with prose and an image in it stays where it is: that is a
    sentence with a picture in it, and lifting the picture would strand
    the sentence.
    """
    figs = []

    def _take(m):
        figs.append(m.group(1))
        return ""

    return _IMG_PARA.sub(_take, html), figs
