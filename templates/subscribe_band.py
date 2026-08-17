"""The subscribe unit, for any page. One component, every surface.

WHY IT EXISTS. Business measured the first real week: about 800 uniques,
roughly 47 of the ~51 social post URLs pointing at /heat or /heat/<city>,
and the form living only on docs/index.html at line 470 of 485. So about
90% of a hard-won week landed on pages where subscribing was IMPOSSIBLE,
and the few who reached a form had to scroll to the bottom of the front
page to find it. Four subscribers from eight hundred visitors is not a weak
ask, it is an absent one.

Kristjan's own closing line is why this matters more than it looks: the
effort is not repeatable. Without capture, every unit of that effort decays
to zero the day after he spends it.

THE CONTEXT IT HAS TO WORK IN, which is Business's constraint rather than
their solution: a cold social link, on a city page, very likely on a phone.
Not a reader browsing the site. Someone who followed a link about their own
city, got their answer, and is one flick from gone.

So on a city page it sits AFTER the finding and the chart and BEFORE the
source footer. A reader who has just seen their own city's record is at the
only moment they will ever be interested; the footer is where interest goes
to die, and that is exactly where the front page put it.

ONE UNIT, NOT FOUR. The form, the promise and the CSS all come from
run_brief, and this wraps them once. Three surfaces carrying three copies
of one promise is how they end up saying three different things, and the
promise is editor's under D-091 rather than anybody's to restate.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import tokens as T                                          # noqa: E402
from run_brief import (email_capture_form, h,               # noqa: E402
                       EMAIL_CAPTURE_PROMISE, EMAIL_FORM_CSS,
                       PAGES_BASE_URL)


def band(fine=None, label="Subscribe"):
    """The unit. `fine` is the small print, which differs by surface only
    in what it promises about THAT surface staying free.

    THE FINE PRINT CARRIES THE ONLY LINK TO /subscribe/. Platform's orphan
    check found that page indexable and unreachable: nothing on the site
    linked it, because every surface posts straight to the Kit form. Three
    fixes were possible and Kristjan chose this one.

    Why here rather than the nav: the masthead already takes 163px before
    content on a phone and wraps to two rows, so a seventh item would spend
    the exact screen-space product is trying to recover. This costs no
    vertical space and sits where a reader is already deciding whether to
    give us an address. The footer was the third option and would have
    satisfied the checker while being clicked by nobody.

    ABSOLUTE, NOT RELATIVE. The band renders at three depths: the site root,
    a channel directory, and a city page beside it. One relative href cannot
    be right at all three, and the failure is silent because a wrong link
    still resolves to a 404 page that looks like a page.
    """
    fine = fine or ("Confirmation email required. No spam, and every figure "
                    "here stays free and public whether you subscribe or not.")
    return (
        '<div class="ebd">'
        '<div><div class="ebk">One email a week</div>'
        '<p class="ebp">%s</p></div>'
        '<div>%s<p class="ebf">%s <a class="ebl" href="%s/subscribe/">'
        'What you get, and how often &rarr;</a></p></div></div>'
        % (h(EMAIL_CAPTURE_PROMISE), email_capture_form(label=label), h(fine),
           PAGES_BASE_URL))


def css():
    """Paired with band(). Includes run_brief's own form CSS so a caller
    cannot ship the markup without the styling, which is how the Notes
    index went out on white with a system serif."""
    return """
.ebd { margin:38px 0 0; border-top:3px solid var(--ink); padding-top:17px;
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  gap:18px 44px; align-items:start; }
.ebk { font-family:"%s",monospace; font-size:9.5px; letter-spacing:.22em;
  text-transform:uppercase; color:var(--ink); }
.ebp { margin:9px 0 0; font-size:18px; line-height:1.45; color:var(--ink);
  max-width:34ch; text-wrap:pretty; }
.ebf { margin:9px 0 0; font-family:"%s",monospace; font-size:10.5px;
  line-height:1.7; color:var(--ink-faint); max-width:52ch; }
.ebl { color:var(--ink); text-decoration:none;
  border-bottom:1px solid var(--rule); white-space:nowrap; }
/* THE PHONE IS THE CASE THAT MATTERS. Business's constraint: the traffic
   that converted worst arrived on a city page from a cold social link, very
   likely on a phone. Two columns become one, and the field goes full width
   rather than sharing a row with the button at 340px. */
@media (max-width:640px) {
  .ebd { grid-template-columns:1fr; gap:14px; margin-top:30px; }
  .ebp { font-size:17px; }
}
%s
""" % (T.FONT_DATA, T.FONT_DATA, EMAIL_FORM_CSS)
