# ASO estimate: editor's notes

Notes on `copy/aso_estimate_draft.md`. Kept out of that file because it
is read by eye and a comment block at the top renders as text in most
viewers. **The draft file is the text and nothing else.**

## Status

**NOT published.** The posture call is Kristjan's. Science relayed a yes
on 2026-09-06; a relayed approval is not one, and he has since asked to
review the draft himself. That review is the gate.

## Verified against the repo, not against Science's brief

    JJA 2026 +1.80, top of 76      data/oni_full_history.csv @ ec2c8384
    ASO record 1997 +2.04,
      2015 +2.02, across 76        same file
    CPC ASO table 75/24/1          snapshots/2026-09-01.json

## The lower bound's reason was wrong once

It first cited 1987 as peaking at ASO. **That is true and argues the
opposite way**: a year that peaks at ASO has a HIGH ASO, so it cannot
justify widening the bound downward. The property that applies is that
1987's ASO came in 0.06 below its own August, as 1991's did by 0.11.
Same case, same bound, right reason. Science's catch.

## Open: the working is not reproducible from the repo

The August weekly +2.60, the four analog gains, and the 1987 and 1991
shortfalls all come from CPC's weekly file through `.fetch_cache`, which
is gitignored. **For the first number we author rather than cite, the
working should be checkable from a committed file.** Science shipped
`august_means` for the Mediterranean piece on exactly this argument.

## Genre is carried twice (D-191)

**"We expect"** is the first two words of the body and survives the text
being extracted into a quote, an RSS item or a screen reader. **Design's
dateline** sits in the figure position and survives the layout being seen
but not read. Neither covers the other's case. Do not drop either.

## Must not say

Science's list, with mine at the top:

- not more reliable than the agencies whose data it rests on
- not a forecast of the peak
- not settled by the winds
- no impact claim attached to an index value
