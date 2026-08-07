"""Generate a plain inventory of the heat payload for visual design.

Not a design and not a proposal. It answers one question: what data
exists, what does each field mean, and what may a renderer not do with
it. Generated from the payload so it cannot drift from the truth.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "heat/data/city_nights.json").read_text())
C, H = D["cities"], D["headline"]
rows = sorted(C.items(), key=lambda kv: (kv[1]["rank"]["value"],
                                         -(kv[1]["record_margin_nights"] or 0)))
m = C["Madrid"]
L = []
w = L.append

w("# Heat: what data we actually have\n")
w("For visual design. Generated from `heat/data/city_nights.json`, so every")
w("number below is the live payload rather than a description of it.\n")
w("**This is an inventory, not a proposal.** No layout is implied.\n")

w("## What the channel measures\n")
w(f"**{D['definition']['name']}**: {D['definition']['rule']}.\n")
w(f"{D['definition']['standard']}\n")
w(f"> {D['_readme']}\n")
w(f"**Coverage.** {D['coverage_note']}\n")
w(f"**Attribution tag.** `{D['attribution']}` (one of three permitted strings).")
w(f"**Evidence basis.** {D['evidence_basis']}.\n")

w("## Scope\n")
w(f"- **{len(C)} cities**, Spain and France")
w(f"- **{H['records']} at an outright record**, {H['lead']['in_top_5pct']} in the "
  f"warmest twentieth of their own history, {H['lead']['in_top_10pct']} in the warmest tenth")
w(f"- Station records run from **{min(v['record_from'] for v in C.values())}** "
  f"to {max(v['record_to'] for v in C.values())}; the longest is "
  f"{max(v['rank']['of_years'] for v in C.values())} years, the shortest "
  f"{min(v['rank']['of_years'] for v in C.values())}")
w(f"- Two sources: {', '.join(sorted({v['source']['who'] for v in C.values()}))}. "
  "Both permit commercial reuse.")
w(f"- Featured cities, chosen by the channel: **{', '.join(D['featured_cities'])}**\n")
w(f"{D['sources_note']}\n")

w("## THREE separate time series per city, and they are not interchangeable\n")
w("This is the part most likely to be missed. Every city carries three")
w("full histories, and only one of them is currently drawn anywhere.\n")
w("| series | what it is | length (Madrid) | currently used |")
w("|---|---|---|---|")
w(f"| `series_to_same_date.values` | nights so far, every prior year cut at the "
  f"same calendar day | {len(m['series_to_same_date']['values'])} years | yes |")
w(f"| `full_year_series` | nights across the whole year, complete seasons only | "
  f"{len(m['full_year_series'])} years | **no** |")
w(f"| `warmest_night_c` | the single warmest night of each year, in degrees | "
  f"{len(m['warmest_night_c'])} years | **no** |\n")
w("`warmest_night_c` is a different quantity entirely: an intensity in degrees")
w("rather than a count of nights. Madrid's runs 25.7, 25.7, 26.1 for 2023 to 2025.")
w("It answers \"how hot did the hottest night get\" where the counts answer")
w("\"how many hot nights were there\". Nothing on the site uses it.\n")
w("`full_year_series` versus the to-date series is the honest way to show that")
w(f"2026 is unfinished: Madrid has {m['nights_2026']} nights to "
  f"{m['as_of']}, its to-date record was {m['nights_2026'] - m['record_margin_nights']}, "
  f"and its full-year 2025 was {m['full_year_series']['2025']}.\n")

w("## Per city, everything emitted\n")
w("| city | nights 2026 | rank | of years | normally | margin | source | as of | cov |")
w("|---|---|---|---|---|---|---|---|---|")
for name, v in rows:
    r = v["rank"]
    marg = f"+{v['record_margin_nights']}" if v["record_margin_nights"] is not None else "n/a"
    w(f"| {name} | {v['nights_2026']} | {r['value']} | {r['of_years']} | "
      f"{v['mean_1991_2020_to_date']['value']} | {marg} | "
      f"{v['source']['who'].split(',')[0]} | {v['as_of']} | {v['coverage_pct']}% |")
w("")
w("`margin` is nights beyond that city's own previous record, and is **null**")
w("rather than 0 where no record was set. Null means \"did not beat it\"; 0 would")
w("mean \"tied it\".\n")

w("## What a renderer may NOT do\n")
w("These ride with the data as fields, not as conventions. Each is a build")
w("failure in the mockup rather than something to remember.\n")
w(f"**`rank.requires_series: true`.** {m['rank']['requires_series_note']}\n")
w(f"**`headline_requires_baseline: true`.** The count of {H['records']} may not")
w("appear without its baseline: a typical year produces "
  f"{H['baseline']['typical_year_records']}, and with no trend the expected number "
  f"is {H['baseline']['expected_no_trend']}.\n")
w(f"**`may_not_say`.** {H['may_not_say']}\n")
w(f"**`series_to_same_date.cut_note`.** {m['series_to_same_date']['cut_note']}\n")
w(f"**`rank.matched_note`.** {m['rank']['matched_note']}\n")
w("**Never open `heat/crosscheck/city_histories_ECAD.json`.** It is ECA&D, which")
w("is non-commercial and is used for verification only. The payload is AEMET and")
w("Meteo-France. Mixing them puts two sources inside one figure.\n")

w("## Why the lead is not the record count\n")
w(f"The channel emits its own lead: **\"{H['lead']['claim']}\"**\n")
w(f"> {H['lead']['why_this_leads']}\n")

w("## What is NOT in the payload\n")
w("- No standard deviation, so no z. Only rank and percentile.")
w("- No sub-annual detail: no daily or monthly values, only annual counts.")
w("- No cities outside Spain and France, and the metric does not travel north.")
w("- No projection, no forecast, no attribution beyond the single tag.")
w("- No population or exposure figures, so nothing supports a harm claim.\n")

out = ROOT / "design/review/heat-data-overview.md"
out.write_text("\n".join(L) + "\n")
print(f"wrote {out} ({len(L)} lines, {len(C)} cities)")
