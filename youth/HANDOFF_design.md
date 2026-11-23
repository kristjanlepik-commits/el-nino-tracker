# Youth country pages: two blocks for design to build (2026-11-23)

From TLS Youth. Kristjan wants the youth pages live so he can ask friends for
feedback. The pages already come from your `templates/youth_page.py`; two blocks
are missing. Rendered as a stopgap in the mock-up (claude.ai/artifact/YZUSL7pSq5iQUxh1K2qxEo,
open any country). The layout there is mine and a placeholder; yours replaces it.

## 1. What stands out (D-351)

Data: `youth/data/standouts.json`, key `countries`, by page code (Greece is EL).
27 of 28 pages; Italy has none, so the block is simply absent there.

    {"state": "...", "items": [{"figure", "text", "against", "source", "finding_id"}]}

Up to three items. `figure` is the big number; `text` follows it as one sentence;
`against` is the comparison line; `source` is the citation. `finding_id` is for
our audit and is not shown to readers. Placement: top of the page, above block 2.

## 2. Also worth knowing (D-354)

Data: `youth/data/also.json`, same shape, with `note` in place of `against`.
25 pages; Estonia, Latvia and Lithuania have none. Placement: directly under
What stands out, or at the top where there is no box (Italy).

It must look plainly lighter than the box. The box says "this stands out against
a comparison"; these items are not shown to stand out, and the page must not imply
they are. The `state` line under each heading is mine as a placeholder; editor
owns the final words for both headings and both lines.

## Not in this handoff

The stress-index map waits on Kristjan's call on blending (D-353). Until then the
map stays as built.

## After you merge

Platform adds `youth/data/standouts.json` and `youth/data/also.json` to the youth
sign-off inputs, then I approve on a preview (D-200).
