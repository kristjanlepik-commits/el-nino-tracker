"""Reader-facing prose in a tracked file, with the figures assembled.

WHY THIS EXISTS. D-030 gives editor all reader-facing prose, and until now
there was physically no way for them to deliver it: the copy lived inside
Python f-strings in a file design owns. So they edited the rendered page in
`heat-preview/`, which is build output I regenerate several times an hour
and which is untracked. Their first pass survived because I happened to
diff before rebuilding. Their second was recovered from a snapshot taken
minutes before I would have destroyed it.

The seam we ratified did not exist in the repo. This is it.

HOW IT WORKS. `copy/*.md` holds prose in named blocks. A block may contain
`{placeholders}`, which the renderer fills from assembled values, so a
sentence stays readable as a sentence to the person writing it. Product's
ruling, and the reason: prose with the numbers injected structurally would
force editor to write around every figure, and pages that read as
assembled fragments are what we spent a day undoing.

THE GUARD FAILS IN BOTH DIRECTIONS, and that is the whole point:

    a slot the renderer wants and the file lacks   -> build error
    a slot in the file the renderer never uses     -> build error
    a {placeholder} with no value                  -> build error
    a value passed that nothing uses               -> build error

The first two are not symmetric niceties. A missing slot drops a paragraph
silently; an unused slot means editor wrote something that never reaches a
reader, which is the same loss wearing the opposite face. Neither is
visible on the page, so neither can be caught by looking.

MARKDOWN IS DELIBERATELY TINY. Bold, italic, and nothing else. Every extra
construct is a way for prose to carry layout, and layout is not editor's
surface. If a sentence needs structure the renderer should be giving it
structure.
"""
import re
from pathlib import Path

R = Path(__file__).resolve().parent.parent
SLOT = re.compile(r"^##\s+([a-z0-9_]+)\s*$", re.M)
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")


def load(name):
    """Parse copy/<name>.md into {slot: raw markdown}."""
    f = R / "copy" / f"{name}.md"
    if not f.exists():
        raise SystemExit(f"no copy file at {f}. Editor owns it; it is not "
                         f"optional and the renderer will not guess.")
    text = f.read_text()
    parts = SLOT.split(text)
    # parts[0] is whatever preceded the first heading: the file's own notes
    slots = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    if not slots:
        raise SystemExit(f"{f} has no '## slot' headings, so nothing in it "
                         f"can be rendered.")
    return slots


def _inline(md):
    """Bold and italic only. See the module docstring for why nothing else."""
    md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md, flags=re.S)
    md = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", md, flags=re.S)
    md = re.sub(r"\s+", " ", md).strip()
    # Editor writes "31.9 °C" and should not have to think about where a
    # line breaks. A unit stranded at the start of a line reads as a typo.
    return md.replace(" °C", "&nbsp;°C")


def render(name, values, wanted, withheld=()):
    """Return {slot: html} for exactly `wanted`, or raise saying why not.

    `values` are the assembled figures. `wanted` is what the renderer will
    actually place on the page, so a slot present in neither direction is
    an error rather than a default.

    `withheld` is {slot: reason} for copy the data says not to place on
    this build. It is still rendered, still guarded, and reported on
    stdout. Without it a renderer's own conditional would be
    indistinguishable from copy silently going missing, which is the thing
    this module exists to make impossible.
    """
    slots = load(name)
    f = f"copy/{name}.md"
    wanted = list(wanted) + list(withheld)

    missing = [s for s in wanted if s not in slots]
    if missing:
        raise SystemExit(
            f"{f} is missing {len(missing)} slot(s) the page needs: "
            f"{', '.join(missing)}. Add a '## <slot>' heading for each.")

    unused = [s for s in slots if s not in wanted]
    if unused:
        raise SystemExit(
            f"{f} has {len(unused)} slot(s) nothing renders: "
            f"{', '.join(unused)}. Prose that reaches no reader is the same "
            f"loss as prose that was dropped, and neither shows on the page.")

    out, seen = {}, set()
    for slot in wanted:
        raw = slots[slot]
        for key in PLACEHOLDER.findall(raw):
            if key not in values:
                raise SystemExit(
                    f"{f}, slot '{slot}': {{{key}}} has no value. Available: "
                    f"{', '.join(sorted(values))}.")
            seen.add(key)
        out[slot] = _inline(raw).format(**values)

    spare = sorted(set(values) - seen)
    if spare:
        raise SystemExit(
            f"{f} never uses {', '.join(spare)}. A figure the renderer "
            f"assembles and the copy ignores is either a slot that lost its "
            f"number or a value nobody needs; both want deciding rather than "
            f"leaving.")

    # Printed on every successful build, not just failures. Otherwise the
    # only way for editor to discover what {figures} exist is to break the
    # file deliberately and read the error, which is a discovery mechanism
    # that punishes you for using it.
    print(f"  copy: {f}, {len(out)} slots, figures available: "
          f"{', '.join(sorted(values))}")
    for slot, why in dict(withheld).items():
        print(f"  copy: '{slot}' written but not placed on this build ({why})")
    return out
