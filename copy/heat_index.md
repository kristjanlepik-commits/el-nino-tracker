<!--
  EDITOR OWNS THIS FILE. Design does not edit the prose below; if a
  sentence is wrong on the page, that is a message to editor, not a fix.

  Each `## name` block is one piece of copy the heat index places. The
  {braces} are figures assembled from heat's payload, so the numbers are
  never typed here and cannot drift from the data.

  To see a change:

      .venv/bin/python design/make_heat_index.py
      .venv/bin/python design/preview_sync.py

  then open heat-preview/index.html. The build fails loudly if a block
  goes missing, gains a block nothing renders, or uses a {figure} that
  does not exist. It will not quietly drop a paragraph.

  **bold** and *italic* are the only formatting. Anything structural is
  design's side of the seam.
-->

## headline

How hot has the summer been?

## lead

**{records} of these {of_cities} cities have had more hot days in their
latest summer than in any year on record.**

## method

A hot day means hot *for that city*: {hot_hi_c} °C in {hot_hi}, {hot_lo_c} °C
in {hot_lo}. Each is measured against its own thermometer and its own
history, never against the others. Where a city's summer is already over,
the latest complete one is the one counted.

## map_note

**This is {n_cities} thermometers, not a temperature map.** Nothing between
the marks means anything. Bigger mark, bigger margin over that city's own
record.

## strip_label

How far from normal, city by city

## strip_intro

Each row is one city's entire record, one mark per summer. **{lead_city}'s
{lead_days} hot days beat all {lead_years} summers it has on file.
{tail_city}'s {tail_days} beat {tail_pct} in 100 of its own.** A crowded row
is just a longer record.

## contrast_label

Hot days and hot nights are different summers

## two_instruments

If one measure could stand in for the other, these two would lean the same
way. They lean opposite ways. **{gated} cities show no night figure at
all.** They average under two hot nights a year, and dividing by a base that
small gives you a big number and no evidence.
