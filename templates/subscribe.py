"""The /subscribe and /subscribed pages.

## Do not describe the product, show it

Product's organising rule and it decides the whole layout. We can offer
something most newsletters cannot at the point of asking: a public
archive of every issue we have sent. A reader deciding whether to
subscribe can read four real issues first, which beats any description
and costs nothing because `docs/briefs/` already exists.

## The issues block leads with the PROBABILITY, not the headline

Because the headline is identical on every issue. All four recent briefs
carry "How likely is a super El Nino this winter?", which is the
channel's standing QUESTION rather than a per-issue title, so rendering
"the last four issues with their real headlines" would produce four
identical lines. That reads as the same page linked four times and
argues against subscribing at the moment the archive is supposed to be
the proof.

Nor the RONI, which was my own first proposal and wrong: it repeats,
1.3 / 1.4 / 1.4 / 1.5, so two rows would collide and rebuild the same
defect with different numbers. Product caught that.

The headline probability is the derived value, it moves every week, and
four different numbers is a self-evident advert for a tracker in a way
no sentence is. D-091 stood the ENSO chat down on emitting it: the copy now leads on
findings rather than on the archive, so the four issues are no longer
the argument and the block is no longer a dependency. It renders
nothing without the field and the code stays, because Notes will want
the same shape and a working block with no data beats rebuilding one.

## What is deliberately not here

No testimonials, no subscriber count, no logos, no social proof of any
kind. We do not have the numbers, and a site whose pitch is measurement
must not lead with an unmeasured claim about itself.

And no modal, exit-intent, scroll trigger, sticky bar, nav slot or
sidebar anywhere on the site. Scored as a negative on trust rather than
treated as taste: an interruption on a site whose pitch is that we do
not hype the reader spends the credibility everything else accumulates.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tokens as T                                            # noqa: E402
from run_brief import (ANALYTICS_SNIPPET, EMAIL_CAPTURE_PROMISE,   # noqa: E402
                       EMAIL_FORM_CSS, email_capture_form,
                       SITE_MASTHEAD_CSS,
                       AUTHOR_NAME, PAGES_BASE_URL, SITE_NAME, h,
                       site_masthead)

# Editor's copy, accepted unchanged 2026-08-06. Not to be edited here:
# the words are editor's and this module renders them.
# D-091. Kristjan rejected the previous copy and the fault was the
# brief rather than editor: product's section 4 asked them to lead on
# "we tell you when nothing is happening", so the page led on an
# absence. Six of its first lines were negations before a reader
# learned what they GET.
#
# The corrected framing, now in the ledger: the value of calibration is
# not that we report quiet weeks, it is that YOU CAN BELIEVE US WHEN WE
# SAY SOMETHING IS HAPPENING. Same fact, stated the right way round, and
# a reason to subscribe rather than a reason not to.
# Read from run_brief rather than restated here, so the front-page slot
# and this page cannot drift apart. Same words, one definition.
PROMISE_H = EMAIL_CAPTURE_PROMISE
# DATED, not live. Editor's rule via product: evergreen copy carries
# DATED findings and never live figures. A payload-fresh number typed
# into a page written once and read for months is correct on the day
# and wrong the following week. Dating it fixes that permanently and
# needs no live binding.
#
# My previous draft said "when Greece burns at twelve times its
# average", which was true of the payload that morning and undated,
# which is exactly the defect.
DATED_FINDING = {
    "text": ("In the week to 5 August, Greece burned at 12.1 times its "
             "average for that week of the year."),
    "region": "Greece", "stat": "12.1x", "as_of": "2026-08-05",
}
PROMISE_P = ("Fires, crops, heat and El Ni&ntilde;o, each measured against its "
             "own record rather than against a feeling. "
             + DATED_FINDING["text"] + " We show the working.")
PROMISE_FINE = "One email a week. Posts on the site do not email you."
PROMISE_FINE2 = "Confirmation email required. One-click unsubscribe."


def verify_dated_findings(events) -> None:
    """Check a dated finding against the payload WHILE the payload still
    covers its date, and skip once it has moved on.

    Product asked for build-time verification of every quoted figure,
    and they are right about the failure: the Greece number was handled
    four ways in one day by four people passing it around in prose.
    Nobody miscalculated; it moved underneath all of us.

    But a DATED finding and a LIVE payload diverge by design. Verifying
    on every build would pass this week and fail next Monday on copy
    that is still true, which trains everyone to ignore the check. So
    this asserts only while the payload still describes that date, and
    goes quiet afterwards. The finding stays true; the evidence for it
    moves into the archive.
    """
    f = DATED_FINDING
    cur = next((e for e in (events or []) if e.get("region") == f["region"]), None)
    if not cur or f["as_of"] not in str(cur.get("date", "")):
        return                      # payload has moved past it; copy stands
    if str(cur.get("stat")) != f["stat"]:
        raise SystemExit(
            f"subscribe copy quotes {f['region']} at {f['stat']} as of "
            f"{f['as_of']}, and the payload for that same date says "
            f"{cur.get('stat')}. Fix the copy or the date, do not ship both.")


def _issues_block(issues) -> str:
    """The last four issues, each led by its own headline probability.

    Renders NOTHING when the probability is unavailable. A visibly
    unfinished conversion device is worse than an absent one, and a row
    reading "issue of 3 August" with no number is exactly the four
    identical lines problem in a quieter costume.
    """
    usable = [i for i in (issues or []) if i.get("probability") and i.get("href")]
    if len(usable) < 2:
        return ""
    rows = "".join(
        f'<a class="isr" href="{h(i["href"])}">'
        f'<span class="isp">{h(i["probability"])}</span>'
        f'<span class="isd">{h(i["date_pretty"])}</span></a>'
        for i in usable[:4])
    return f"""
      <p class="seclab">The last four issues</p>
      <p class="secsub">Read them before you decide. Each figure is the
        headline probability as it stood that week; the point of a
        tracker is that it moves.</p>
      <div class="iss">{rows}</div>"""


def render_subscribe(issues=None, form_embed="", root_prefix="") -> str:
    """`form_embed` is platform's Beehiiv script. Empty renders a slot.

    Beehiiv offers no plain HTML form, confirmed in their dashboard, so
    the script is the only route and placement is the only lever. That
    is platform's to supply and mine to place.
    """
    # The slot is gone. It existed because the form was a third-party
    # script that platform supplied and might not have supplied yet; the
    # form is our own markup now, so there is no state in which this page
    # renders without one. An explanatory placeholder for a thing that
    # cannot be missing is just a way to ship a broken page quietly.
    form = form_embed or email_capture_form()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subscribe | {h(SITE_NAME)}</title>
<meta name="description" content="{h(PROMISE_H)}">
<style>{_css(root_prefix)}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="")}
<main>
  <h1>{h(PROMISE_H)}</h1>
  <p class="stand">{PROMISE_P}</p>
  {form}
  <p class="fine">{h(PROMISE_FINE)}</p>
  <p class="fine">{h(PROMISE_FINE2)}</p>

  {_issues_block(issues)}

  <p class="seclab">What arrives</p>
  <ul class="plain">
    <li>What the instruments recorded this week, and what it is unusual
      against.</li>
    <li>Every figure names its source and its baseline, so you can check
      it.</li>
    <li>When a week is ordinary we say that too, which is what makes the
      other weeks worth reading.</li>
  </ul>

  <p class="seclab">What we do with your address</p>
  <p class="plainp">Nothing. It is not shared, not sold, and not used for
    anything except sending you the weekly issue. One-click unsubscribe
    in every email.</p>

  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.
    <a href="{h(PAGES_BASE_URL)}/">{h(PAGES_BASE_URL.split("//")[-1])}</a>
  </div>
</main>
</body>
</html>
"""


def render_subscribed(latest_href="briefs/", latest_label="the most recent issue",
                      root_prefix="") -> str:
    """Where the double opt-in link lands.

    Product's gap and their catch: the redirect pointed at the front
    page, so the last step of subscribing dropped a reader somewhere
    with no acknowledgement that anything had happened. That reads as
    broken at the exact moment they have done what we asked.

    "Mondays" is safe HERE and deliberately absent from the subscribe
    copy. This reader has converted and is being oriented; that one had
    not and would have been promised a weekday we do not guarantee.
    """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>You are subscribed | {h(SITE_NAME)}</title>
<style>{_css(root_prefix)}</style>
{ANALYTICS_SNIPPET}
</head>
<body>
{site_masthead(root_prefix, active="")}
<main>
  <h1>You are subscribed.</h1>
  <p class="stand">The next issue arrives Monday. In the meantime:</p>
  <ul class="plain">
    <li><a href="{h(root_prefix + latest_href)}">Read {h(latest_label)}</a></li>
    <li><a href="{h(root_prefix)}briefs/">Every issue we have sent</a></li>
  </ul>
  <p class="plainp">If you did not mean to subscribe, every email has a
    one-click unsubscribe link.</p>
  <div class="foot">{h(AUTHOR_NAME)} (2026). {h(SITE_NAME)}.</div>
</main>
</body>
</html>
"""


def _css(root_prefix) -> str:
    return f"""
{T.font_faces_css(root_prefix + "fonts/")}
:root {{ {T.css_variables()} }}
@media (prefers-color-scheme: dark) {{ :root {{ {T.css_variables(dark=True)} }} }}
* {{ box-sizing:border-box; }}
:root {{ --shell-max:800px; --shell-pad:24px; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font-family:"{T.FONT_PROSE}",Georgia,serif; font-size:16.5px; line-height:1.55; }}
main {{ max-width:660px; margin:0 auto; padding:24px 24px 80px; }}
{SITE_MASTHEAD_CSS}
h1 {{ font-size:30px; font-weight:500; line-height:1.2; margin:26px 0 12px;
  letter-spacing:-0.015em; max-width:24ch; text-wrap:balance; }}
.stand {{ color:var(--ink-soft); margin:0 0 20px; max-width:58ch; }}
.fine {{ font-family:"{T.FONT_DATA}",monospace; font-size:11.5px;
  color:var(--ink-faint); margin:8px 0 0; }}
{EMAIL_FORM_CSS}
.seclab {{ font-family:"{T.FONT_DATA}",monospace; font-size:11px;
  letter-spacing:{T.TRACK_LABEL}em; text-transform:uppercase;
  color:var(--ink); margin:40px 0 4px; padding-bottom:8px;
  border-bottom:2.4px solid var(--rule-45); }}
.secsub {{ font-size:13.5px; color:var(--ink-soft); margin:0 0 6px;
  max-width:60ch; }}
/* The issues block. The PROBABILITY leads each row, because the
   headline is identical on every issue and the number is the only
   thing that moves. Four different numbers is the advert. */
.iss {{ margin-top:6px; }}
.isr {{ display:grid; grid-template-columns:5.5rem 1fr; gap:14px;
  padding:11px 0; border-bottom:1px solid var(--rule);
  text-decoration:none; color:inherit; align-items:baseline; }}
.isp {{ font-family:"{T.FONT_DATA}",monospace; font-size:20px;
  font-weight:600; color:var(--nino); font-variant-numeric:tabular-nums; }}
.isd {{ font-size:14.5px; }}
.isr:hover .isd {{ text-decoration:underline; }}
.plain {{ margin:10px 0 0; padding-left:20px; max-width:60ch; }}
.plain li {{ margin-bottom:6px; }}
.plainp {{ margin:10px 0 0; max-width:60ch; }}
.foot {{ margin-top:48px; padding-top:14px; border-top:1px solid var(--ink);
  font-family:"{T.FONT_DATA}",monospace; font-size:11.5px;
  color:var(--ink-faint); }}
"""
