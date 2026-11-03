#!/usr/bin/env python3
"""Keep the dropped apps' identity pages out of the search index, without deleting them.

Five apps were dropped from the lineup on 2026-11-03: MileTruth, TentClock, Foldbook,
Steadychart and FlipStage. Their landing, support, privacy and terms pages are the exact
shape that the guideline 4.3 warning was about -- near-identical per-app pages, one slug
apart, on a single domain -- and they now describe products that are not being taken
forward, so there is nothing to gain by leaving them indexable.

What this does, and what it deliberately does not:

  * It sets `noindex,follow` on each app's own identity pages and drops them from
    sitemap.xml. `follow` rather than `nofollow`, so the pages still pass link equity to
    the free tools below, and the files stay in git history and keep resolving -- FlipStage
    is live on the App Store (app id 6816274152) with /flipstage/support/ and
    /flipstage/privacy/ registered in App Store Connect, and `noindex` does not break a URL.
    Deleting those files would. Do not delete them while that listing is live.

  * It leaves the standalone browser tools and guides indexed. Those are substantive,
    one-of-a-kind pages (mileage and net-pay calculators, the 2026 split-rate explainer,
    the speaking-time planner); they are not part of the duplicate-page problem, and
    de-indexing them would throw away the only organic search assets on the domain for
    no 4.3 benefit. They do still link to dropped apps, which is a content decision for
    a human rather than something to silently rewrite here.

Usage:  python3 scripts/noindex-dropped-apps.py [--check]
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# app slug -> the identity pages to de-index ("" is the landing page itself)
DROPPED = {
    "miletruth": ["", "support", "privacy", "terms"],
    "tentclock": ["", "support", "privacy"],
    "foldbook": ["", "support", "privacy"],
    "steadychart": ["", "support", "privacy", "terms"],
    "flipstage": ["", "support", "privacy"],
}

MARKER = "dropped from the lineup 2026-11-03"
NOTE = (
    f"<!-- noindex: {MARKER}. The page is kept, and keeps resolving, because a live App\n"
    "     Store listing or an in-app link may still point at it; it is only removed from\n"
    "     the search index and from sitemap.xml. See scripts/noindex-dropped-apps.py. -->\n"
)
ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*"\s*/?>', re.IGNORECASE)


def targets() -> list[tuple[pathlib.Path, str]]:
    out = []
    for slug, leaves in DROPPED.items():
        for leaf in leaves:
            rel = f"{slug}/{leaf}/index.html" if leaf else f"{slug}/index.html"
            out.append((ROOT / rel, rel))
    return out


def rewrite(text: str) -> str:
    if MARKER not in text:
        text = text.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + NOTE, 1)
    if ROBOTS_RE.search(text):
        return ROBOTS_RE.sub('<meta name="robots" content="noindex,follow">', text, count=1)
    # no robots meta at all: add one straight after the charset declaration
    return re.sub(
        r'(<meta\s+charset="[^"]*"\s*/?>)',
        r'\1\n<meta name="robots" content="noindex,follow">',
        text,
        count=1,
        flags=re.IGNORECASE,
    )


def strip_from_sitemap(check: bool) -> int:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    before = text
    for slug, leaves in DROPPED.items():
        for leaf in leaves:
            url = (
                f"https://bakerventuresstudio.com/{slug}/{leaf}/"
                if leaf
                else f"https://bakerventuresstudio.com/{slug}/"
            )
            text = re.sub(
                r"\s*<url>\s*<loc>" + re.escape(url) + r"</loc>.*?</url>",
                "",
                text,
                flags=re.DOTALL,
            )
    if text == before:
        print("  sitemap.xml already clean")
        return 0
    removed = before.count("<url>") - text.count("<url>")
    if check:
        print(f"  STALE  sitemap.xml still lists {removed} dropped-app URL(s)")
        return 1
    path.write_text(text, encoding="utf-8")
    print(f"  sitemap.xml: removed {removed} dropped-app URL(s)")
    return 0


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = 0
    for path, rel in targets():
        if not path.exists():
            print(f"  missing     {rel}  (nothing to do)")
            continue
        have = path.read_text(encoding="utf-8")
        want = rewrite(have)
        if have == want:
            print(f"  already     {rel}")
            continue
        stale += 1
        if check:
            print(f"  STALE       {rel} is still indexable")
        else:
            path.write_text(want, encoding="utf-8")
            print(f"  de-indexed  {rel}")
    stale += strip_from_sitemap(check)
    if check and stale:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
