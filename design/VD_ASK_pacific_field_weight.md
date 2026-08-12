# Design ask for VD: the Pacific field is too heavy on the front page

Design, 2026-08-12. One question. Everything else on the new front page is
either shipped or already answered in your review.

## The question

**Should the front page carry a quieter VARIANT of the SST ramp, rather
than the same ramp at lower strength?**

## What is live now

The new front page is at https://thelongswell.com/ and the field is the
map's ground layer, drawn under 16 data marks, at 92% opacity. It is the
same nine-step diverging ramp the El Niño page uses, from
`design/make_pacific_sst.py`, rendered to `docs/pacific-sst.png` and placed
by its own extent from `docs/pacific-sst.json`.

This follows your own ratified line, "the SST field is that channel's
marker on the landing map", so the field being there is settled. What is
not settled is its weight.

## Why we are asking rather than adjusting

Kristjan's words: too aggressive. We agree, and we do not think opacity is
the fix.

**On the El Niño page that ramp is the subject and earns its weight. On the
front page it is the ground layer beneath the page's actual subject**,
which is the sixteen marks that each carry a per-place claim. Right now the
loudest object on the page is the one carrying no claim at all: the Pacific
outshouts Georgia at 5.3x its own record week.

**Dropping opacity uniformly fades the cold tongue as hard as the warm
pool, and the warm pool is the finding.** That is why this is a palette
question rather than a slider, and why it is yours rather than ours.

Possible shapes, none of them a recommendation: fewer steps; a lighter warm
end; the cold half pulled back so the ramp is asymmetric on this surface;
or a different treatment entirely.

## Two constraints on any answer

1. **It is a matplotlib PNG, not CSS.** A variant means a second colormap
   in `design/make_pacific_sst.py`, not an opacity value. We can build
   whatever you specify.

2. **D-043 applies.** Whatever the ramp does, it must still read as
   ORDINARY in a calm year rather than merely paler. A quieter ramp that
   still reads as alarming when the anomaly is unremarkable has solved the
   wrong problem.

## Not part of this question

Your review's other six findings are done and live: the heat row's subject
is the subset rather than the set, the Niño 3.4 bracket is drawn as the
actual 5°N-5°S box rather than hanging south of the equator, the Notes rail
was broken by a CSS class collision and is fixed, Paris appears once rather
than twice, "the bar" is no longer used above its definition, and labels
carry leader lines when the collision pass moves them off their default
side.

Your first finding, that the wave block authors a figure, is with Kristjan
and science. It is a question about what the site may publish rather than
about how it looks, so it is not ours to resolve in a template.

## Why this arrived late

We sent it to product on the assumption it would reach you. Product
confirmed the routing and the question still did not land anywhere you
could read it. Filed here instead, which is where your other exchanges
live.
