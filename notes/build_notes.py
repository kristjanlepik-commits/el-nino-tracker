"""Build every Note and the index.

CONTENT IS EDITOR'S AND KRISTJAN'S, in notes/*.md. This file is the
renderer and owns none of the prose, the same seam as copy/heat_index.md.

THE DATE. Each Note's front matter carries no date. It is minted on first
publish and read back from the published page on every run afterwards, so
a rebuild in September cannot redate an August piece. See
templates/note.py for why that is not a nicety: a Note freezes under
invariant 5 when it publishes, so a wrong date there is permanent.

    .venv/bin/python notes/build_notes.py              publish new, keep old
    .venv/bin/python notes/build_notes.py --date X     mint at X, first run only
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run_brief import h                                  # noqa: E402
from templates.note import (read_frozen_date, render_index,  # noqa: E402
                            render_note)

SRC = ROOT / "notes"
OUT = ROOT / "docs/notes"


def lead_of(body, authored=None):
    """The standfirst for the index.

    Kristjan: a blog shows a lead, not only a title. I first derived it
    from the first paragraph, on the argument that a hand-written summary
    is a second copy of the opening that can drift from it.

    VD's objection is better and I concede it: the first paragraph of the
    first Note is the WONDERING, not the finding, so the index advertises
    the least informative sentence in the piece it is selling. It is also
    the paragraph carrying the ENSO-juxtaposition problem, so one string
    ships that defect twice.

    So an authored `lead:` line wins when there is one, and the first
    paragraph is the fallback. The line is Kristjan's under D-093 like
    every other word of a Note; this only gives it somewhere to live.
    Drift is the price and it is the smaller one: a preview that
    undersells the piece costs every reader who does not click.
    """
    if authored:
        return authored
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if para and not para.startswith(("!", ">", "#")):
            plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)
            plain = re.sub(r"[*_]", "", plain).replace("\n", " ")
            return re.sub(r"\s+", " ", plain).strip()
    return ""


def parse(path):
    """`# Title`, then body. Markdown kept deliberately small: bold, italic,
    links, images, blockquote-as-pull, and a `## Sources` tail."""
    text = path.read_text()
    m = re.match(r"#\s+(.+)", text)
    if not m:
        raise SystemExit(f"{path}: no '# Title' on the first line.")
    title, rest = m.group(1).strip(), text[m.end():]
    # An optional `lead: ...` line directly under the title, which the
    # index previews instead of the opening paragraph.
    lead = None
    lm = re.match(r"\s*\nlead:\s*(.+)", rest)
    if lm:
        lead, rest = lm.group(1).strip(), rest[lm.end():]
    body, _, src = rest.partition("\n## Sources")
    return title, body.strip(), src.strip(), lead


def inline(md):
    md = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
                r'<figure><img src="\2" alt="\1"></figure>', md)
    md = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', md)
    md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md, flags=re.S)
    return re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", md, flags=re.S)


def blocks(md):
    out = []
    for para in re.split(r"\n\s*\n", md):
        para = para.strip()
        if not para:
            continue
        if para.startswith("> "):
            out.append(f'<p class="pull">'
                       f'{inline(para[2:].replace(chr(10) + "> ", " "))}</p>')
        elif para.startswith("!["):
            out.append(inline(para))
        else:
            out.append(f"<p>{inline(para)}</p>")
    return "\n".join(out)


def main(mint=None):
    OUT.mkdir(parents=True, exist_ok=True)
    notes = []
    for md in sorted(SRC.glob("*.md")):
        slug = md.stem
        d = OUT / slug
        title, body, src, authored = parse(md)

        frozen = read_frozen_date(d)
        if frozen:
            published_on = frozen
            if mint and mint != frozen:
                raise SystemExit(
                    f"{slug} was published on {frozen} and --date says "
                    f"{mint}. Refusing: a published Note is frozen "
                    f"(invariant 5) and its date is not editable.")
        else:
            if not mint:
                raise SystemExit(
                    f"{slug} has never been published and no --date was "
                    f"given. Pass --date YYYY-MM-DD to publish it. The date "
                    f"is never taken from the clock, so that a rebuild "
                    f"cannot redate a piece.")
            published_on = mint

        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            # slug and lead reach the template so the head can carry a
            # canonical and a description: only the builder knows the
            # directory it is writing, and the lead is the sentence the
            # index already shows for this piece.
            render_note(title, published_on, blocks(body), blocks(src),
                        slug=slug, lead=lead_of(body, authored)))
        notes.append({"slug": slug, "title": title,
                      "published_on": published_on, "lead": lead_of(body, authored)})
        print(f"  {slug}: {published_on}{' (minted)' if not frozen else ''}")

    if not notes:
        raise SystemExit("no notes/*.md to build")
    (OUT / "index.html").write_text(render_index(notes))
    print(f"wrote {OUT}/index.html | {len(notes)} note(s)")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[a.index("--date") + 1] if "--date" in a else None)
