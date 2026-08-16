"""The words beside each ladder rung. One copy, two surfaces.

WHY THIS FILE EXISTS. The dated brief and the /elnino/ channel page each
held their own descriptor list, and they had drifted: the same rung read
"Beyond the instrumental record" in one and "beyond the observed record"
in the other. Nobody chose that; it is what two copies of a string do.
Editor ruled on the wording and the divergence itself was the defect, so
there is now one map and both surfaces read it.

EDITOR'S RULING, 2026-08-16, on the +4.0 rung that joins the ladder on
2026-08-17. Kristjan proposed "this is scary", and then "outer cosmos
levels"; design objected; editor ruled against both and adopted
"nothing to compare it to". Recorded here in full because the reasoning
is the useful part and it applies to the next rung too:

  IT COMPLETES THE COLUMN'S LOGIC RATHER THAN ESCALATING IT. The sequence
  is comparable, beyond, far beyond, and then the terminus of that same
  idea: no comparison exists. Every alternative restated "beyond" a fourth
  time, and "outside the record entirely" is true of +3.0 as well, so it
  fails to distinguish the rung it labels.

  THE MARGIN FORM WAS REJECTED FOR THE OPPOSITE REASON to the one you
  would expect. "1.4 °C past the record" is exactly true and reads SMALLER
  than it is, because degrees of ONI anomaly are not intuitive: a lay
  reader takes 1.4 as a modest gap when it is 54% beyond the largest event
  ever measured. A technically precise phrase that undersells is hedging
  drift, which is the failure mode nobody objects to.

  AND ON KRISTJAN'S LINE, which is most of the idea and right about the
  cadence: two descriptive rungs and then a short hard beat, because the
  vocabulary genuinely has run out at 3.5. What does not ship is telling
  the reader how to feel. It puts our only subjective phrase on our only
  unanchored number, and T12 says our reader distrusts doom and dismissal
  equally: they believe the figures because we never tell them how to
  react to one. Editor's sentence, worth keeping: that line is scary, and
  it is scary because it is true. The reader supplies the feeling.

CASE IS THE SURFACE'S. Stored lower, capitalised by the brief, which sets
its rung labels in sentence case. One string, so they cannot drift again.
"""

# Keyed by bucket key. A rung with no entry renders no descriptor rather
# than a phrase invented by a renderer: what a rung beyond the record is
# beyond is a claim about magnitude, not a label.
NOTE = {
    "9715_>2.5":   "1997 / 2015 magnitude",
    "record_>3.0": "beyond the observed record",
    "record_>3.5": "far beyond it",
    "record_>4.0": "nothing to compare it to",
}

# The uncertainty pill, on the rungs that carry one.
#
# +4.0 IS NOT "MOST UNCERTAIN", and editor's reasoning is why it is not
# simply the next word up: the uncertainty column has run out for the same
# reason the descriptors have. "model spread only" says WHY rather than HOW
# MUCH, and it puts the anchor problem where the reader meets the number.
# CPC's table does not reach +4.0, so 39% is model consensus over a tail
# extrapolation with two of five models holding no members above it at all.
# The descriptor stays about the world; the pill carries the instrument.
TAG = {
    "record_>3.0": "highly uncertain",
    "record_>3.5": "most uncertain",
    "record_>4.0": "model spread only",
}


def note(key, sentence_case=False):
    n = NOTE.get(key, "")
    return (n[:1].upper() + n[1:]) if (sentence_case and n) else n


def tag(key):
    return TAG.get(key)
