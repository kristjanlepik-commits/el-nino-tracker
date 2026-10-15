# VD review: "How a flood is made" (floods explainer)

From design, 16 October 2026, 01:30. **Paste this in full; VD cannot read the
repo (D-125).** Screenshots: `design/proto/explainer_contact_sheet_v2.jpg`
(attach it). The page is not live yet, so there is no URL to open.

## What we want from you

A visual review before Friday-morning publish (D-328): what to change so the
page reads as one designed piece and as The Long Swell. Ranked list, most
important first. Three questions in particular:

1. **Does the 3D sit inside the house style or fight it?** This is the first
   time the site ships 3D (D-327, Kristjan's call). It is drawn on our paper
   ground with our ink, floods teal and anomaly ramp, but it is new
   vocabulary.
2. **Rhythm.** Kristjan flagged chapter 07 as "off the rhythm"; it is now a
   scroll stage like 01 and 05. Do the seven chapters alternate well
   (stage, figure, stage...) or does one still break step?
3. **The chapter words.** Each chapter opens with one huge numbered word.
   Too loud? Right size?

## The piece

A reader explainer of how the 3 October Barcelona rain happened, published
before the second storm forecast for 17 to 20 October. Not a forecast of
ours, not El Niño. Every number is from measured data (ERA5, AEMET, HANZE);
anything illustrative is labelled on the figure. Words are the editor's;
figures and layout are design's. Order and visual direction are Kristjan's.

## Structure, top to bottom

Header: kicker "Floods · explainer · 16 October 2026", H1 "How a flood is
made" (editor's, may change), standfirst.

Then seven chapters, each opening with a **chapter word**: a numbered mono
label ("01", 13 px, floods teal #0A5C66, tracking .2em), the word in Spectral
500 at clamp(64px, 13vw, 156px), line-height .9, tracking -.035em, ink
#1A1A18, and a mono subtitle (12 px, uppercase, #6E6E67). The word rises
28 px into place as it arrives.

| # | Word | Scene | Form |
|---|---|---|---|
| 01 | Rain | A 1 m glass cube fills to 159.1 mm, to scale, as you scroll; rain streaks and splash rings; counter "0.0 to 159.1 mm"; stamp "Barcelona · Fabra observatory · 3 October 2026"; small Iberia locator, Barcelona ringed | 3D, scroll-driven, 420vh |
| 02 | Heat | Map of Europe, each month May to September 2026 against its own 1991-2020 mean, morphing continuously (9 s run, 3.5 s hold on September); big month stamp; 5-segment month bar that fills | Canvas, autoplay when visible |
| 03 | Sea | Two seas side by side, western Mediterranean, normal September 23.6 °C against 2026's 26.0 °C (warmest in 87 years). The 2026 sea is drawn more agitated: rougher waves, heat shimmer, far more vapour. "MOTION ILLUSTRATIVE" on the figure | Canvas, loops |
| 04 | Air | One dot per September since 1940, global water vapour vs normal; 2026 is the rule across the record and the only square; "No September in this record reaches it." Dots appear one year at a time | SVG record strip (our fast-reaction form) |
| 05 | Pump | The western Mediterranean as a slab coloured by September sea heat; a translucent cold-air layer at "5 km" crossfading through ERA5 frames; wind as ~3,000 flowing streaks at "1.5 km"; Barcelona pin through both levels. The clock (27 Sep to 3 Oct, snapped to 12-hourly fields) is pinned to the five captions. On 3 Oct a bold ink arrow comes in off the sea: "Onshore: from the SE, 10 m/s" | 3D, scroll-driven, 640vh |
| 06 | Ground | Two cut-away hillside blocks under identical rain; the front face is a live soak-or-run-off cross-section; runoff flows to a river channel at each foot; the wet block's river fills to ~85%, the dry block's to ~10%. Earth tones #C2B497 / #A99C80. "Same rain on both · illustrative" | 3D, autoplay loop |
| 07 | Weekend | Full-height map of Spain's Mediterranean coast; three layers arrive with three captions: floods since 1982 (dots labelled by year), wet ground now (teal boxes clipped to land), AEMET's warnings for 17 to 20 October (yellow #F2C94C at AEMET's own level, 40 zones) | SVG, scroll-driven, 360vh |

Close: **Heat + Sea + Air + Pump + Ground = Flood**, assembled word by word,
Spectral 500 at clamp(34px, 6.4vw, 84px), "+" and "=" in #6E6E67, "Flood" in
floods teal.

## Tokens used (all from tokens.py)

Paper #F1F0EC, ink #1A1A18, ink-soft #3A3A36, ink-faint #6E6E67, rule
#CFCEC7, land #D9D8D0, floods #0A5C66. Anomaly ramp, 9 steps:
#0A4A57 #417785 #85A7B0 #C3D2D5 #E8E7E2 #EFC9BD #DC957E #C05B3D #8E240A, at
±3 °C full scale. Fonts: Spectral (serif), IBM Plex Mono.

**Off-token, flagged for your call:** the ground blocks' earth tones
(#C2B497, #A99C80), AEMET's yellow (#F2C94C, kept as AEMET's level colour),
and the 3D scenes' slight darkening of the paper during the storm (to
#C9CCCA at peak).

## Fixed, please do not change

- Labels that carry a data caveat: "Drawn to scale", "Motion illustrative",
  "Same rain on both · illustrative", "Heights exaggerated · every layer is a
  measured field", the AEMET stamp. They are what keep illustrative figures
  honest.
- AEMET's warning colour and one shape per zone (stacked fills read as a
  higher level, CPO caught it).
- The pump captions' dates and the scene clock move together.

## Known rough edges

- The wind streaks are 1 px lines; thicker ribbons would read better.
- At phone width the 3D scenes are small; the stages stack, but the cube and
  slab could fill more of the screen.
- No share card yet for this page.

Reply with a ranked list; design will take it from there tonight.
