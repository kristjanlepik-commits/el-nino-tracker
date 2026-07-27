"""The Long Swell visual language v1.0 "Bulletin". Single source of truth.

Drives the static site generator and matplotlib alike, so nothing here
is expressible only in CSS. Role-named, never blue1.

Adopted 2026-07-26 as D-016 from the visual-language task chat, with
four design-chat amendments recorded in that entry:
  1. Wordmark register inverted: house in Spectral at natural fit,
     product names in tracked Plex Mono. Supersedes D-003's split.
  2. TAG_PENDING_FG corrected for WCAG AA (delivered value was 3.14:1
     on its own background, which fails for 9.5px text).
  3. Trajectory traces corrected to the real methodology years and
     extended to cover the forecast fan and the wind panel.
  4. Channel hue marks channel identity only; physical anomaly
     magnitude uses the diverging scale, so an ENSO datum can never
     read as a Fire datum.

Two rules that outrank convenience:
  Color is earned by departure from a baseline. An unremarkable number
  stays in INK. Coloring a figure to make a page look designed breaks
  the only signal the palette carries.
  Nothing is ever enclosed on four sides. RADIUS is 0 and SHADOW is
  None so a contributor has to delete a line rather than add one.

No em-dashes anywhere, including these comments.
"""

# The venv runs Python 3.9, so PEP 604 unions in annotations need this.
from __future__ import annotations

# ---------------------------------------------------------------------------
# Color: light theme, the reading environment
# ---------------------------------------------------------------------------

PAPER = "#F1F0EC"        # bone reading ground
PAPER_SUNK = "#E7E6DF"   # tracker strip, table zebra, the only fill allowed
INK = "#1A1A18"          # display, headings, heavy rules
INK_SOFT = "#3A3A36"     # body prose
INK_FAINT = "#6E6E67"    # labels, baselines, folios. 4.50:1, see note
RULE = "#CFCEC7"         # hairlines, non-text only

# INK_FAINT clears WCAG AA against PAPER with no margin at all (4.50).
# Cap it at 11px and above, and never let it carry a sentence the
# reader has to follow. Standalone 9.5px labels use INK_SOFT.

# ---------------------------------------------------------------------------
# Color: dark theme. The override plus masthead and footer furniture,
# not the reading environment. Hue is held constant between themes and
# only lightness moves, so channel identity survives a theme switch.
# ---------------------------------------------------------------------------

PAPER_DARK = "#1A1A18"
PAPER_SUNK_DARK = "#252521"
INK_DARK = "#EDECE6"
INK_SOFT_DARK = "#B4B3AB"
INK_FAINT_DARK = "#86857D"
RULE_DARK = "#3A3A36"

# ---------------------------------------------------------------------------
# Channels: one flat saturated hue per variable, used at full strength
# in small doses. All five clear AA as body text on PAPER in both
# directions, deliberately, so a hue may set a word and not only fill
# a rectangle.
# ---------------------------------------------------------------------------

NINO = "#173F9E"     # El Nino 2026-27
FIRE = "#B32E10"     # Fire
FLOOD = "#0A5C66"    # Floods
CROP = "#2E5C16"     # Crops
DAMAGE = "#5C2C96"   # cross-channel damage ledger

NINO_DARK = "#6E97E8"
FIRE_DARK = "#E8714E"
FLOOD_DARK = "#4CB3BF"
CROP_DARK = "#7CB84E"
DAMAGE_DARK = "#A87BE8"

CHANNEL = {"nino": NINO, "fire": FIRE, "flood": FLOOD, "crop": CROP,
           "damage": DAMAGE}

# ---------------------------------------------------------------------------
# Attribution tags. Exactly three states, worded verbatim, never
# removed or softened to tidy a layout. Prominence descends with claim
# strength.
# ---------------------------------------------------------------------------

TAG_LOADED_BG = NINO
TAG_LOADED_FG = PAPER
TAG_NOTLINK_BG = "#E3E2DB"
TAG_NOTLINK_FG = INK_SOFT
TAG_PENDING_BG = "#EAE9E3"
TAG_PENDING_FG = "#66665F"   # amendment 2: was #83837B at 3.14:1

# ---------------------------------------------------------------------------
# Diverging anomaly scale. Nine steps, symmetric, index 4 neutral and
# sitting within 1.09 of PAPER so an unremarkable value visually
# disappears into the page. That is the color rule made literal.
#
# Amendment 4: this scale, not a channel hue, carries physical anomaly
# magnitude. Ocean heat, SST departure, and similar quantities read
# from here.
# ---------------------------------------------------------------------------

ANOMALY = [
    "#0A4A57", "#417785", "#85A7B0", "#C3D2D5",
    "#E8E7E2",
    "#EFC9BD", "#DC957E", "#C05B3D", "#8E240A",
]
ANOMALY_NEUTRAL = ANOMALY[4]
COLD = ANOMALY[0]
WARM = ANOMALY[8]

# Which text colour, if any, may legally print ON each step. Computed,
# not estimated: the pairs below are the WCAG AA survivors at 4.5:1.
#
#   step 0  #0A4A57   PAPER 8.65   INK 1.77   -> PAPER
#   step 1  #417785   PAPER 4.38   INK 3.49   -> NEITHER
#   step 2  #85A7B0   PAPER 2.26   INK 6.77   -> INK
#   step 3  #C3D2D5   PAPER 1.36   INK 11.20  -> INK
#   step 4  #E8E7E2   PAPER 1.09   INK 14.08  -> INK
#   step 5  #EFC9BD   PAPER 1.34   INK 11.42  -> INK
#   step 6  #DC957E   PAPER 2.13   INK 7.17   -> INK
#   step 7  #C05B3D   PAPER 3.83   INK 3.99   -> NEITHER
#   step 8  #8E240A   PAPER 7.65   INK 2.00   -> PAPER
#
# Note this is NOT "only the two end steps": five middle steps take INK
# comfortably. The two that take nothing are 1 and 7, one on each flank,
# where the fill is dark enough to kill INK and light enough to kill
# PAPER. On those, print the value beside the fill rather than inside it.
ANOMALY_TEXT = [PAPER, None, INK, INK, INK, INK, INK, None, PAPER]


# Full-scale for every ocean temperature anomaly on the site, in degrees
# C. One number, because the SST index on the map and the 0-300 m heat
# content in the issue hero are both degrees of ocean temperature
# departure, and rendering them on different scales made +2.10 and +2.26
# land on different steps: a reader comparing the two pages saw a
# contradiction that was purely an artefact of the divisor.
#
# 3.0 rather than 4.0 because it is the domain: observed ONI has never
# exceeded about 2.8, and heat content runs to roughly 2.5. A wider scale
# pushes real extremes toward the middle of the ramp and wastes both
# flanks. anomaly_color clamps, so the +3.5 ladder rung still saturates.
OCEAN_SCALE = 3.0


def anomaly_fill(value: float, full_scale: float = OCEAN_SCALE):
    """Diverging step for a value, with the text colour it can carry.

    Returns (fill, text_colour). text_colour is None when no legal text
    colour exists for that step, which means: print the value BESIDE the
    fill, never inside it. Use this instead of anomaly_color() anywhere a
    number might end up on top of the swatch, so a future call site
    cannot inherit a contrast failure by accident.
    """
    fill = anomaly_color(value, full_scale)
    return fill, ANOMALY_TEXT[ANOMALY.index(fill)]


def anomaly_color(value: float, full_scale: float = OCEAN_SCALE) -> str:
    """Diverging-scale step for an anomaly in degrees C.

    full_scale is the magnitude that saturates the ramp. Values beyond
    it clamp rather than wrapping, because a saturated color must not
    imply a value it does not have.
    """
    if full_scale <= 0:
        return ANOMALY_NEUTRAL
    t = max(-1.0, min(1.0, value / full_scale))
    idx = int(round(4 + t * 4))
    return ANOMALY[max(0, min(8, idx))]


# ---------------------------------------------------------------------------
# Trajectory chart (amendment 3).
#
# The rule from the delivered language: only the current year carries a
# hue. Peers separate by line weight and dash so the chart survives
# being screenshotted, reposted, printed grey, or read with a color
# vision deficiency, and so the peers read as context rather than five
# competing claims.
#
# The delivered spec covered four line styles. The production chart
# needs the set below. Dash tuples are matplotlib specifications and
# translate to stroke-dasharray without reinterpretation. Peer years
# are the real methodology years; 1982 is not in the dataset.
# ---------------------------------------------------------------------------

TRACE_CURRENT = {"color": NINO, "lw": 2.4, "dash": "solid"}

TRACE_PEERS = {
    2015: {"color": INK_SOFT, "lw": 1.3, "dash": "solid",
           "label": "2015-16 (super, peak 2.8)"},
    1997: {"color": INK_SOFT, "lw": 1.3, "dash": (0, (6, 3)),
           "label": "1997-98 (super, peak 2.4)"},
    2023: {"color": INK_FAINT, "lw": 1.2, "dash": (0, (2, 3)),
           "label": "2023-24 (recent super, peak 2.1)"},
    2025: {"color": INK_FAINT, "lw": 1.1, "dash": (0, (1, 2, 4, 2)),
           "label": "2025-26 (La Nina, peak -0.5)"},
}

# The forecast continues the current-year line, so it keeps NINO and
# separates by dash: dashed while multi-member and well constrained,
# dotted once past the SEAS5 horizon or bridging a gap.
TRACE_FORECAST = {"color": NINO, "lw": 1.8, "dash": (0, (5, 2))}
TRACE_EXTENSION = {"color": NINO, "lw": 1.8, "dash": (0, (1, 2))}
# The connector bridges a gap in OBSERVATION; the extension is a
# projection past the model horizon. Different meanings, so they must
# not look the same: these were both (0, (1, 2)) in NINO, separated only
# by alpha, which is not a distinction a reader can make. The connector
# is now much sparser, because nothing at all was measured across it.
TRACE_CONNECTOR = {"color": NINO, "lw": 1.2, "dash": (0, (1, 5)),
                   "alpha": 0.6}
BAND_OUTER_ALPHA = 0.08   # 5 to 95 percentile
BAND_INNER_ALPHA = 0.16   # 25 to 75 percentile

TRACE_BASELINE = {"color": "#8B8B83", "lw": 0.8, "dash": "solid"}

# Chart furniture. Structural, never decorative.
CHART_GRID = RULE
CHART_ZERO = INK
CHART_THRESHOLD = INK_FAINT     # gridlines and their labels
CHART_TARGET_BAND = PAPER_SUNK  # DJF peak-season window
CHART_TODAY = INK_FAINT

# ---------------------------------------------------------------------------
# Probability ladder. Confidence is rendered, not stated: the bar loses
# substance as certainty falls and the text steps down the ink ramp
# alongside it. The two upper rungs are beyond the instrumental record
# and must never look as solid as the two below.
# ---------------------------------------------------------------------------

# Keys are the methodology's bucket identifiers from probs.py, not
# design names, and they are written into 13 published meta.json files
# that are immutable. "9715" is 1997/2015, the two super events the
# +2.5 threshold marks. It reads oddly against this file's role-naming
# rule, and it stays: renaming it would break the archive contract, and
# the vocabulary belongs to the methodology chat rather than this one.
LADDER = {
    "super_>2.0":  {"bar": NINO, "dash": None, "text": INK, "weight": 600},
    "9715_>2.5":   {"bar": NINO, "dash": None, "text": INK, "weight": 600},
    "record_>3.0": {"bar": NINO, "dash": (4, 4), "text": INK_SOFT,
                    "weight": 500},
    "record_>3.5": {"bar": "#7B88AF", "dash": (2, 6), "text": INK_FAINT,
                    "weight": 400},
}

# ---------------------------------------------------------------------------
# Type. The same font files feed CSS and matplotlib.
#
# Spectral never sets a figure. Every number, unit, date, percentage,
# multiple, issue stamp, source line and attribution tag sets in Plex
# Mono. Plex Mono is monospaced so tabular figures are structural, but
# tabular-nums is set anyway so the intent survives a font fallback.
#
# Amendment 1: the house wordmark sets in Spectral at natural fit;
# product names set in Plex Mono uppercase tracked 0.18em, which keeps
# the house and its channels visibly different in kind.
# ---------------------------------------------------------------------------

FONT_PROSE = "Spectral"        # SIL OFL 1.1
FONT_DATA = "IBM Plex Mono"    # SIL OFL 1.1

SERIF_FAMILY = FONT_PROSE      # names kept for existing call sites
MONO_FAMILY = FONT_DATA

SERIF_STACK = '"Spectral", "Iowan Old Style", Palatino, Georgia, serif'
MONO_STACK = ('"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, '
              '"DejaVu Sans Mono", monospace')

# Six steps, no more. px for CSS, pt for matplotlib, one ladder.
SIZE_DISPLAY = 50
SIZE_HEADING = 20
SIZE_PROSE = 17.5
SIZE_FIGURE = 40
SIZE_DATUM = 13
SIZE_LABEL = 9.5
TRACK_LABEL = 0.22      # em, uppercase only
TRACK_PRODUCT = 0.18    # em, product names in mono

SIZE_DISPLAY_SM = 34
SIZE_PROSE_SM = 17

LEADING_DISPLAY = 1.10
LEADING_HEADING = 1.30
LEADING_PROSE = 1.62
MEASURE_PROSE = 62      # ch, hard maximum

# ---------------------------------------------------------------------------
# Space and rules. One unit, 4px, everything a multiple.
# ---------------------------------------------------------------------------

UNIT = 4
GUTTER = 40
GUTTER_SM = 20
COLUMN_GAP = 56
COLUMN_SECOND = 300
BREAKPOINT = 760
SHELL_MAX = 1180

# The attenuation ratio is a system property, not a logo property
# (visual language v1.0 addendum). The mark's 3 / 2.4 / 1.8 strokes at
# 100% / 45% / 20% carry into section rules, list dividers and the
# tracker keyline, so a cropped screenshot with no logo in frame is
# still recognizable.
#
# One hard limit: the ratio applies to FURNITURE ONLY, never to a mark
# that carries data. Concentric rings on a map marker would read as an
# epicenter, which is a causal claim the text does not make. Map
# markers stay plain discs whose area encodes magnitude.
ATTENUATION = [(3.0, 1.0), (2.4, 0.45), (1.8, 0.2)]

# What each step actually does, because an unused third of a three-part
# ratio gets reinvented by whoever finds it next.
#
#   step 1, 3px at 100%   RULE_MASTHEAD, opens a section or a list
#   step 2, 2.4px at 45%  RULE_STEP, divides items within a list
#   step 3, 1.8px at 20%  COLOUR ONLY. Its opacity is RULE_20, which is
#                         the table hairline and LAND_LINE. Its 1.8px
#                         WIDTH is deliberately not used: at table-row
#                         density 1.8px reads as a divider rather than a
#                         hairline, which would collapse the distinction
#                         between step 2 and step 3. The hairline is 1px.
#
# So the ratio governs three opacities and two widths, on purpose.
RULE_WEIGHTS = {"masthead": 3.0, "step": 2.4, "hairline": 1.0}

RULE_HAIR = 1        # table row, printable hairline
RULE_STEP = 2.4      # list divider, at 45%
RULE_MASTHEAD = 3    # full, opens a section or list
RULE_SECTION = 2.4   # retained name for the step weight
RULE_45 = "#8E8E88"  # INK at 45% composited over PAPER
RULE_20 = "#C6C5C2"  # INK at 20% composited over PAPER
# Coastlines are the same weight of statement as a table hairline, so
# they take the same value rather than one two units away from it.
LAND = "#D9D8D0"
LAND_LINE = RULE_20
LAND_DARK = "#2E2E2A"
LAND_LINE_DARK = "#333330"

RADIUS = 0           # not a variable
SHADOW = None        # not a variable

# ---------------------------------------------------------------------------
# "The mark reports the week" (visual language v1.0 addendum).
#
# The reach of the signal is set by the largest magnitude published that
# week, computed in the same pass that builds the page. Stroke widths
# never change; only opacity moves.
#
# RULING (D-017, Kristjan delegated the call): the opacity bands are
# adopted; the channel-hue-at-record rule is NOT. Three reasons the mark
# stays ink at every band:
#
#  1. Attribution leak. A record fire week would turn the HOUSE mark red
#     site-wide, including on the El Nino page, directly above items
#     tagged "not ENSO-linked". The mark and the tag would make opposite
#     claims and the mark is larger. That is the over-attribution risk
#     T9 exists to prevent, arriving through the logo rather than copy.
#  2. Brand architecture. The house/product split is the thing the type
#     split makes visible (D-001, D-016). A house mark wearing a
#     channel's hue collapses it.
#  3. The mark is also the favicon. Tab identity should be stable; a
#     weekly color change reads as a different site.
#
# `allow_hue` is kept as a parameter so the decision is reversible in one
# place, and defaults to False. Nothing in production passes it.
#
# The band input is the largest multiple among EVENT-channel items only.
# El Nino has no multiple: its magnitude is an anomaly in degrees, not a
# ratio. Passing an ONI value would read +2.1 degrees as merely
# "notable", which is wrong by a wide margin.
# ---------------------------------------------------------------------------

MARK_BANDS = [
    # (floor multiple, arc opacities inner to outer, record band)
    (0.0, (1.0, 0.16, 0.16), False),   # quiet
    (2.0, (1.0, 0.75, 0.16), False),   # notable
    (6.0, (1.0, 0.75, 0.55), True),    # record
]


def mark_band(max_multiple: float, channel: str | None = None,
              allow_hue: bool = False):
    """Arc opacities and ink color for a week's mark.

    max_multiple is the largest multiple among event-channel items, so
    fires and floods but never an ONI anomaly. channel names the channel
    that drove it. Returns (opacities, color) where color is None to
    mean "inherit currentColor", the default.
    """
    opacities, is_record = MARK_BANDS[0][1], MARK_BANDS[0][2]
    for floor, ops, record in MARK_BANDS:
        if max_multiple >= floor:
            opacities, is_record = ops, record
    color = CHANNEL.get(channel) if (is_record and allow_hue) else None
    return opacities, color

# ---------------------------------------------------------------------------
# Site identity printed on distributed images.
#
# The card and the citable chart travel off-site, so this is the string
# in the whole system that most needs to be right. It lived as a bare
# literal in two modules and went stale the moment D-011 made
# thelongswell.com canonical; now there is one copy.
#
# The VALUE is the platform chat's to change (they own the domain
# migration). The design chat only owns that the images read from here
# rather than hardcoding it.
# ---------------------------------------------------------------------------

SITE_HOST_DISPLAY = "thelongswell.com"

# ---------------------------------------------------------------------------
# CSS emission
# ---------------------------------------------------------------------------

_VAR_NAMES = [
    "PAPER", "PAPER_SUNK", "INK", "INK_SOFT", "INK_FAINT", "RULE",
    "NINO", "FIRE", "FLOOD", "CROP", "DAMAGE",
]


def css_variables(dark: bool = False, indent: str = "    ") -> str:
    """Custom properties for one theme.

    Names are the constants lowercased and hyphenated: PAPER becomes
    --paper, INK_SOFT becomes --ink-soft. The dark theme emits the same
    property names with the _DARK values, so no stylesheet rule needs a
    theme conditional.
    """
    suffix = "_DARK" if dark else ""
    lines = []
    for name in _VAR_NAMES:
        value = globals()[name + suffix]
        prop = name.lower().replace("_", "-")
        lines.append(f"{indent}--{prop}: {value};")
    if not dark:
        lines.append(f"{indent}--serif: {SERIF_STACK};")
        lines.append(f"{indent}--mono: {MONO_STACK};")
        lines.append(f"{indent}--tag-loaded-bg: {TAG_LOADED_BG};")
        lines.append(f"{indent}--tag-loaded-fg: {TAG_LOADED_FG};")
        lines.append(f"{indent}--tag-notlink-bg: {TAG_NOTLINK_BG};")
        lines.append(f"{indent}--tag-notlink-fg: {TAG_NOTLINK_FG};")
        lines.append(f"{indent}--tag-pending-bg: {TAG_PENDING_BG};")
        lines.append(f"{indent}--tag-pending-fg: {TAG_PENDING_FG};")
        lines.append(f"{indent}--rule-45: {RULE_45};")
        lines.append(f"{indent}--rule-20: {RULE_20};")
        # Map land: a step off PAPER, so coastlines read without the
        # map competing with the markers on it.
        lines.append(f"{indent}--land: {LAND};")
        lines.append(f"{indent}--land-line: {LAND_LINE};")
        lines.append(f"{indent}--shell: {SHELL_MAX}px;")
    else:
        # Tag surfaces need dark equivalents; hue holds, lightness moves.
        # The loaded chip was previously omitted here, so it inherited the
        # light NINO while every other blue on the page lightened, and read
        # as noticeably heavier than its surroundings. PAPER_DARK on
        # NINO_DARK is 6.02:1.
        lines.append(f"{indent}--tag-loaded-bg: {NINO_DARK};")
        lines.append(f"{indent}--tag-loaded-fg: {PAPER_DARK};")
        lines.append(f"{indent}--tag-notlink-bg: #2E2E2A;")
        lines.append(f"{indent}--tag-notlink-fg: {INK_SOFT_DARK};")
        lines.append(f"{indent}--tag-pending-bg: #262622;")
        lines.append(f"{indent}--tag-pending-fg: {INK_FAINT_DARK};")
        # Emitted in both branches so a standalone dark block is complete
        # rather than silently depending on the light block preceding it.
        lines.append(f"{indent}--serif: {SERIF_STACK};")
        lines.append(f"{indent}--mono: {MONO_STACK};")
        lines.append(f"{indent}--shell: {SHELL_MAX}px;")
        lines.append(f"{indent}--rule-45: #6A6A64;")
        lines.append(f"{indent}--rule-20: #333330;")
        lines.append(f"{indent}--land: {LAND_DARK};")
        lines.append(f"{indent}--land-line: {LAND_LINE_DARK};")
    return "\n".join(lines)


# Older call sites in run_brief.py used these two names.
def css_vars_light() -> str:
    return css_variables(dark=False)


def css_vars_dark() -> str:
    return css_variables(dark=True)


_FACES = [
    (FONT_PROSE, "normal", "400", "spectral-400.woff2"),
    (FONT_PROSE, "italic", "400", "spectral-400-italic.woff2"),
    (FONT_PROSE, "normal", "500", "spectral-500.woff2"),
    (FONT_DATA, "normal", "400", "plexmono-400.woff2"),
    (FONT_DATA, "italic", "400", "plexmono-400-italic.woff2"),
    (FONT_DATA, "normal", "500", "plexmono-500.woff2"),
    (FONT_DATA, "normal", "600", "plexmono-600.woff2"),
]


def font_faces_css(prefix: str = "fonts/") -> str:
    """@font-face block for the self-hosted faces.

    prefix is the path from the page to docs/fonts/, so "fonts/" for a
    root page and "../../fonts/" for an archive issue page.
    """
    out = []
    for family, style, weight, fname in _FACES:
        out.append(
            "@font-face {\n"
            f'  font-family: "{family}";\n'
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            f'  src: url("{prefix}{fname}") format("woff2");\n'
            "}"
        )
    return "\n".join(out)
