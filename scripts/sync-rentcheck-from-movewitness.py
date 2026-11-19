#!/usr/bin/env python3
"""Regenerate /rentcheck/{support,privacy,terms}/ from the canonical /movewitness/ pages.

MoveWitness shipped under the project name "rentcheck". The live App Store Connect record
for app id 6816228166 still names /rentcheck/support/ and /rentcheck/privacy/ in its
Support URL and Privacy Policy URL fields, so those two URLs must keep serving the real
document rather than a redirect stub: a reviewer who clicks the field has to land on the
page, not on a note about where it moved.

That leaves one app with two copies of each page, which is exactly the shape of duplicate
that a guideline 4.3 review reads badly -- so the duplicate is managed rather than ignored:

  * the /rentcheck/ copy is generated from the /movewitness/ one, never edited by hand, so
    the two can never say different things (which they did until 2026-11-03);
  * it carries `noindex` and a canonical pointing at /movewitness/, so only one copy is
    indexable and crawlers are told which one counts;
  * it is absent from sitemap.xml.

To remove the duplicate entirely: change those two fields in App Store Connect to the
/movewitness/ paths, then replace these files with the same redirect stub the other six
renamed apps use (/lienclock/, /iolta/, /cyberclose/, /flyfish/, /denialfighter/,
/quietlog/). Do not stub them before that field is changed.

Usage:  python3 scripts/sync-rentcheck-from-movewitness.py [--check]
--check exits non-zero if a copy is out of date instead of rewriting it.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEAVES = ("support", "privacy", "terms")

NOTE = """<!--
  Why this page exists, and why it is a copy.

  MoveWitness shipped under the project name "rentcheck", and the App Store Connect record
  for app id 6816228166 still names /rentcheck/support/ and /rentcheck/privacy/ in its
  Support URL and Privacy Policy URL fields. Those URLs therefore have to keep serving a
  real support page and a real policy, not a redirect stub -- a reviewer clicking the field
  must land on the document, not on a note about where it moved.

  So this file is generated from the canonical page under /movewitness/ and carries the
  same text. It is noindex with a canonical pointing at /movewitness/, so only one copy is
  indexable and search engines are told which one counts.

  To collapse this duplicate: change the two URL fields in App Store Connect to the
  /movewitness/ paths, then replace these files with the same redirect stub the other
  renamed apps use (see /lienclock/, /iolta/, /cyberclose/, /flyfish/, /denialfighter/,
  /quietlog/). Until that field is changed, deleting or stubbing this page breaks a live
  App Store listing.

  Regenerate with: python3 scripts/sync-rentcheck-from-movewitness.py
-->
"""


def render(leaf: str) -> str:
    src = (ROOT / "movewitness" / leaf / "index.html").read_text(encoding="utf-8")
    src = src.replace(
        '<meta name="robots" content="index,follow,max-snippet:-1">',
        '<meta name="robots" content="noindex,follow">',
    )
    if 'content="noindex,follow"' not in src:
        sys.exit(f"movewitness/{leaf}/: the robots meta is not the expected one; fix this script")
    canonical = f'rel="canonical" href="https://bakerventuresstudio.com/movewitness/{leaf}/"'
    if canonical not in src:
        sys.exit(f"movewitness/{leaf}/: expected a canonical pointing at itself")
    src = re.sub(r'href="\.\./([a-z0-9-]+)/"', r'href="/movewitness/\1/"', src)
    src = src.replace('href="../"', 'href="/movewitness/"')
    return src.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + NOTE, 1)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = 0
    for leaf in LEAVES:
        want = render(leaf)
        dest = ROOT / "rentcheck" / leaf / "index.html"
        have = dest.read_text(encoding="utf-8") if dest.exists() else None
        if have == want:
            print(f"  up to date  rentcheck/{leaf}/")
            continue
        stale += 1
        if check:
            print(f"  STALE       rentcheck/{leaf}/ differs from movewitness/{leaf}/")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(want, encoding="utf-8")
            print(f"  written     rentcheck/{leaf}/")
    if check and stale:
        print(f"\n{stale} copy/copies out of date. Run without --check to regenerate.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
