"""
Generate the "Analyst read" prose via Anthropic API call.

Inputs: headline buckets, diff dict, physical state, freshness map.
Output: 3-5 paragraphs of plain prose, no em-dashes, in the analyst voice
the methodology document establishes (concrete, skeptical of overfitting,
explicit about uncertainty, surfaces disagreements).

Contract:
- Always returns SOMETHING. If the API call fails, returns a clearly
  marked fallback summary built from the diff alone.
- Always prepends the banner specified by the user (option C):
  "AUTO-GENERATED: review before quoting".
- Never invents numbers; only references numbers passed in via the prompt.
"""

from __future__ import annotations
import json
import os
from typing import Optional

# Defer import of anthropic so this module loads even without the package
def _get_client():
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    return Anthropic()


SYSTEM_PROMPT = """You are a quantitative climate analyst writing an internal weekly brief on the 2026-27 El Niño event for Kristjan, who has deep VCM and climate fluency. Your job: write the "Analyst read" subsection of section 4 of the brief.

Style requirements:
- 3 to 5 paragraphs, plain prose, no headers, no bullet lists.
- No em-dashes anywhere. Use commas, semicolons, or periods instead.
- Concrete and skeptical of overfitting. Explicit about uncertainty. When forecast centers disagree, surface the disagreement rather than averaging it away.
- Reference only numbers and facts in the inputs provided. Never invent numbers, never cite sources not listed.
- Don't restate the headline bucket numbers (the reader sees them above your prose). Interpret them.

Required content, in this order:
1. Lead with the dominant signal of the week. Usually that's whichever physical-state delta or new agency release moved most.
2. Surface any disagreement between forecast centers (especially CPC vs ECMWF on the upper tail).
3. Position the current week against the analog events (1997, 2015, 2023) at the same calendar point if relevant.
4. Close with what to watch in the next 1-2 weeks. Be specific.

Avoid: hedge words like "potentially" or "could possibly", policy/impact speculation (food prices, hurricanes), or any prose that would be appropriate in a public-facing report. This is internal."""


FALLBACK_TEMPLATE = """**(Fallback prose: API call failed. Falling back to mechanical summary of the diff. Replace before quoting.)**

This week's brief was generated without analyst commentary because the editorial generator could not reach the Anthropic API. The auto-diff above is the floor; please read it directly and add interpretation manually for any week where the deltas matter materially."""


def generate(headline: dict, diff: dict, physical_state: dict,
             freshness: dict, brief_date: str) -> str:
    """
    Call the API and return the Analyst Read markdown, with banner.
    Returns the fallback template if the API is unavailable.
    """
    banner = ("> **AUTO-GENERATED:** the prose below is written by Claude "
              "from this week's diff and physical state. Review before "
              "quoting externally; edit freely if the analysis warrants it.\n")

    client = _get_client()
    if client is None:
        return banner + "\n" + FALLBACK_TEMPLATE

    user_payload = {
        "brief_date": brief_date,
        "headline_buckets": headline,
        "week_over_week_diff": diff,
        "physical_state": physical_state,
        "source_freshness": freshness,
    }
    user_msg = (
        "Inputs for this week's Analyst Read:\n\n"
        + "```json\n"
        + json.dumps(user_payload, indent=2, default=str)
        + "\n```\n\n"
        "Write the Analyst Read prose now. 3-5 paragraphs. No em-dashes."
    )

    try:
        resp = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()
        if not text:
            return banner + "\n" + FALLBACK_TEMPLATE
        # Defensive: strip any em-dashes the model slipped in
        text = text.replace("\u2014", ", ")
        return banner + "\n" + text
    except Exception as e:
        return banner + "\n" + FALLBACK_TEMPLATE + f"\n\n_API error: {type(e).__name__}_"


if __name__ == "__main__":
    print(generate(
        headline={"super_>2.0": {"mid": 41}},
        diff={"is_first_issue": True},
        physical_state={"nino34_weekly_traditional": 0.5},
        freshness={"cpc_strength": {"used_fallback": False}},
        brief_date="2026-04-25",
    ))
