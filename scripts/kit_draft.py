#!/usr/bin/env python3
"""Create a Kit broadcast DRAFT from a published Note. Never sends.

    scripts/kit_draft.py <slug> [--dry-run]

THE LAST STEP STAYS HUMAN, and that is the whole design rather than a
caution bolted on. Everything else in this pipeline is recoverable: a
wrong page is republished, a wrong number is corrected, a bad commit is
reverted, and this week we did all three. An email cannot be unsent. So
this script creates a draft and stops; Kristjan reviews subject,
rendering and links in Kit, and clicks send himself.

There is no --send flag and there should never be one. A flag that
exists gets passed by a script that was only meant to test something.

WHAT IT REFUSES TO DO, each guard from a failure we have already had:

  the Note is not live          Checked by FETCHING the URL and looking
                                for the title IN the page, not by
                                checking a file exists and not by
                                trusting HTTP 200. Issue #22: CEDA served
                                a directory listing unauthenticated while
                                the files behind it 302'd, and a probe on
                                the listing reported healthy for a day.
                                LAADS and LANCE return HTML at 200 too.

  a broadcast already exists    Idempotent. Re-running must not produce a
                                second draft of the same issue, because
                                two drafts is how the wrong one gets sent.

  a relative link               Email is the one place a relative link is
                                guaranteed broken: there is no page to be
                                relative to.

OUR LINKS ARE UTM-TAGGED AND NOBODY ELSE'S ARE. 313 of last week's 800
visits were unattributable Direct, against 273 Mobile App visitors, and
in-app browsers strip referrers. Email strips them too, so an untagged
newsletter link is guaranteed to land in that pile. Tagging a third
party's domain would be putting our parameters on someone else's
analytics, so the rewrite is scoped to thelongswell.com.

Credentials: ~/.kit_api_key, v4, header X-Kit-Api-Key. Outside the repo
and mode 600 because nine chats share this working tree.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import urljoin
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://thelongswell.com"
API = "https://api.kit.com/v4"
KEY_FILE = Path.home() / ".kit_api_key"


def key() -> str:
    env = (os.environ.get("KIT_API_KEY") or "").strip()
    if env:
        return env
    if not KEY_FILE.exists():
        raise SystemExit(
            f"No Kit key. Set KIT_API_KEY or write {KEY_FILE} (mode 600). "
            f"Refusing to continue rather than failing later inside an API "
            f"call, where the error would look like a Kit problem.")
    return KEY_FILE.read_text().strip()


def api(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    cmd = ["curl", "-sS", "-X", method, "-w", "\n%{http_code}",
           "-H", f"X-Kit-Api-Key: {key()}",
           "-H", "Content-Type: application/json", f"{API}{path}"]
    if payload is not None:
        cmd += ["-d", json.dumps(payload)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    body, _, code = out.rpartition("\n")
    try:
        return int(code), (json.loads(body) if body.strip() else {})
    except (ValueError, json.JSONDecodeError):
        return int(code or 0), {"_raw": body[:400]}


def tag(url: str, slug: str) -> str:
    """UTM only on our own links, and never doubled."""
    if not url.startswith(SITE):
        return url
    if "utm_source=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return (f"{url}{sep}utm_source=newsletter&utm_medium=email"
            f"&utm_campaign={slug}")


def to_html(md: str, slug: str) -> tuple[str, list[str]]:
    """Markdown to HTML with absolute, tagged links. Returns (html, problems)."""
    problems = []

    # RESOLVED AGAINST THE NOTE'S OWN PAGE, not the site root. The links
    # in a Note are relative to /notes/<slug>/, so "../charts/x.png" is
    # /notes/charts/x.png. My first version stripped "./" and produced
    # /charts/x.png, which is a 404, UTM-tagged, in an email nobody can
    # recall. urljoin does this correctly and I do not.
    base = f"{SITE}/notes/{slug}/"

    def absolute(href: str) -> str:
        if href.startswith(("http://", "https://", "mailto:")):
            return href
        return urljoin(base, href)

    # IMAGES FIRST. The link pattern also matches the ![alt](src) inside
    # an image, so running it first turned every chart into an anchor
    # containing the alt text and dropped the picture.
    def image(m):
        alt, src = m.group(1), absolute(m.group(2).strip())
        return (f'<p><img src="{src}" alt="{alt}" '
                f'style="max-width:100%;height:auto"></p>')

    def link(m):
        text, href = m.group(1), m.group(2).strip()
        if href.startswith("#"):
            problems.append(f"in-page anchor {href!r} has no page in an email")
            return text
        return f'<a href="{tag(absolute(href), slug)}">{text}</a>'

    body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image, md)
    body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, body)
    out = []
    for para in body.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if p.startswith("# "):
            continue                       # the title becomes the subject
        if p.startswith("## "):
            out.append(f"<h2>{p[3:].strip()}</h2>")
        else:
            out.append(f"<p>{p}</p>")
    return "\n".join(out), problems


def live_check(url: str, title: str) -> None:
    """FETCH it, and look for the title inside it."""
    r = subprocess.run(["curl", "-sS", "-w", "\n%{http_code}", url],
                       capture_output=True, text=True).stdout
    page, _, code = r.rpartition("\n")
    if code.strip() != "200":
        raise SystemExit(
            f"REFUSING: {url} returned HTTP {code.strip()}. The Note is not "
            f"live, and a broadcast whose link 404s is worse than a late one.")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    if title.lower()[:40] not in text.lower():
        raise SystemExit(
            f"REFUSING: {url} returns 200 but does not contain the Note's "
            f"title. A status code is not evidence the right page is there; "
            f"CEDA served a healthy listing over files that 302'd for a day, "
            f"and LAADS returns HTML at 200. Checked the shape, not the code.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="note slug, e.g. 2026-08-10-how-bad-is-it")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the payload and exit, touching nothing")
    args = ap.parse_args()

    src = ROOT / "notes" / f"{args.slug}.md"
    if not src.exists():
        raise SystemExit(f"No such note: {src}")
    md = src.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", md, re.M)
    if not m:
        raise SystemExit(f"{src} has no '# Title' line; the subject comes "
                         f"from it and guessing one is not this script's job.")
    title = m.group(1).strip()
    url = f"{SITE}/notes/{args.slug}/"

    html, problems = to_html(md, args.slug)
    if problems:
        for p in problems:
            print(f"  WARNING: {p}", file=sys.stderr)

    html += (f'\n<p><a href="{tag(url, args.slug)}">Read this on the web</a>'
             f'</p>')

    if args.dry_run:
        print(f"subject : {title}")
        print(f"url     : {url}")
        print(f"content : {len(html)} chars, "
              f"{html.count('<a href=')} link(s)")
        for a in re.findall(r'<a href="([^"]+)"', html):
            print(f"    {a}")
        print("\n--dry-run: nothing fetched, nothing created.")
        return 0

    live_check(url, title)

    code, existing = api("GET", "/broadcasts")
    if code != 200:
        raise SystemExit(f"REFUSING: cannot list broadcasts (HTTP {code}). "
                         f"Without that list this cannot tell a first draft "
                         f"from a duplicate, and guessing makes two.")
    for b in existing.get("broadcasts", []):
        if b.get("subject") == title:
            raise SystemExit(
                f"REFUSING: a broadcast with this subject already exists "
                f"(id {b.get('id')}, status {b.get('public') and 'public' or 'draft'}). "
                f"Two drafts of one issue is how the wrong one gets sent.")

    code, created = api("POST", "/broadcasts",
                        {"subject": title, "content": html,
                         "description": f"Note {args.slug}"})
    if code not in (200, 201):
        raise SystemExit(f"Kit refused the draft (HTTP {code}): "
                         f"{json.dumps(created)[:300]}")
    bid = (created.get("broadcast") or {}).get("id")
    print(f"DRAFT created, id {bid}. Nothing has been sent.")
    print(f"Review it in Kit and send it there: subject, rendering, links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
