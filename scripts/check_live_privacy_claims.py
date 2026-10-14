#!/usr/bin/env python3
"""Compare each app's PUBLISHED privacy page against that app's repo source.

Why this exists
---------------
On 2026-10-14 four apps shipped commits correcting in-app copy that claimed user data
never leaves the device, because `expo-sqlite` puts the database under `Documents/`,
which iOS includes in iCloud Backup by default. Every one of those commits fixed the
in-app screen and the repo markdown and stopped there. The published pages that the
App Store listings' Privacy Policy URL fields point at were never updated, so a commit
"fixed the privacy policy" while the privacy policy a user actually reads stayed wrong.
Across all seven published pages the words "iCloud" and "backup" appeared zero times.

Nothing compared the two. This does.

    Check the artefact, not the description of the artefact.
    The published page is the artefact; the repo markdown is the description.
    -- /Users/ryanbaker/VERIFICATION-LESSON.md

What it checks, and what it deliberately does not
-------------------------------------------------
It is NOT a full text diff. The hosted page is hand-written HTML in a different
register from the repo's markdown or TSX, so a whole-document comparison would be all
noise and would be switched off within a week. It tests the class of defect that
actually bit, which is a falsifiable negative claim:

  R1 RETRACTED-CLAIM     a falsifiable "nothing ever leaves your device"-shaped
                         sentence is asserted on the live page while the repo source
                         no longer asserts it.
  R2 MISSING-DISCLOSURE  the repo source discloses the iCloud backup and the live page
                         says nothing about iCloud at all.
  R3 STALE-DATE          the live page's "Last updated" is older than the repo
                         source's, i.e. the source moved and the page did not.
  R4 NO-SOURCE           a published page has no repo source to compare against.
                         That is a finding, not a skip -- an unowned page is exactly
                         how this happened.
  R5 UNREACHABLE         the listed URL does not return a usable page.

Rule R1 ignores any phrase that appears inside quotation marks in the repo source,
because a retracted sentence is routinely quoted in the paragraph that retracts it
("'none of it ever leaves your device' was not an accurate sentence, so it is gone").
Without that, the retraction itself would satisfy the check -- a tool reassuring
itself, which is the failure mode this script exists to stop being.

Usage
-----
    python3 scripts/check_live_privacy_claims.py            # fetch the live pages
    python3 scripts/check_live_privacy_claims.py --local     # use the local working
                                                             # tree instead of the
                                                             # network, to test a fix
                                                             # before deploying
    python3 scripts/check_live_privacy_claims.py --app noticeguard
    python3 scripts/check_live_privacy_claims.py -v          # show every rule result

Exit 0 = every page agrees with its repo source. Exit 1 = at least one disagreement.
Exit 2 = the check itself could not run (bad manifest path, no network).

This check has been shown RED before it was ever trusted GREEN; see
/Users/ryanbaker/live-pages-fix-2026-10-14.md for the recorded red run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import re
import sys
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Manifest: which published page belongs to which repo.
#
# Only the mapping is hard-coded. The expected *content* is never hard-coded --
# it is read out of the repo at run time, which is the whole point: a hand-kept
# list of expected sentences rots exactly as fast as the pages did.
#
# `sources` may name several files when an app has no single privacy markdown;
# they are concatenated. MoveWitness is the example: its hosted page is the only
# privacy policy it has, so its repo-side truth about the backup lives in the
# Terms and in the privacy-label determination.
# ---------------------------------------------------------------------------
MANIFEST = [
    {
        "app": "noticeguard",
        "url": "https://bakerventuresstudio.com/noticeguard/privacy/",
        "local": "noticeguard/privacy/index.html",
        "repo": f"{HOME}/lienclock",
        "sources": ["docs/privacy-policy.md", "src/app/privacy.tsx"],
    },
    {
        "app": "denialdesk",
        "url": "https://bakerventuresstudio.com/denialdesk/privacy/",
        "local": "denialdesk/privacy/index.html",
        "repo": f"{HOME}/denialfighter",
        "sources": ["docs/privacy-policy.md", "src/app/privacy.tsx"],
    },
    {
        "app": "movewitness",
        "url": "https://bakerventuresstudio.com/rentcheck/privacy/",
        "local": "rentcheck/privacy/index.html",
        "repo": f"{HOME}/movewitness",
        # No docs/privacy-policy.md exists: the hosted page IS the policy. The
        # repo's corrected position on the backup is in the Terms and in the
        # App Privacy determination, so those are the source of truth here.
        "sources": ["docs/terms.md", "docs/app-privacy-determination.md"],
    },
    {
        "app": "steadychart",
        "url": "https://bakerventuresstudio.com/steadychart/privacy/",
        "local": "steadychart/privacy/index.html",
        "repo": f"{HOME}/symptom-tracker",
        "sources": ["docs/PRIVACY.md"],
    },
    {
        "app": "policyready",
        "url": "https://bakerventuresstudio.com/policyready/privacy/",
        "local": "policyready/privacy/index.html",
        "repo": f"{HOME}/cyberclose",
        "sources": ["docs/privacy-policy.md"],
    },
    {
        "app": "vocabdrift",
        "url": "https://bakerventuresstudio.com/vocabdrift/privacy/",
        "local": "vocabdrift/privacy/index.html",
        "repo": f"{HOME}/lockscreen-learn",
        "sources": ["src/screens/PrivacyScreen.tsx"],
    },
    {
        "app": "hatchwindow",
        "url": "https://bakerventuresstudio.com/hatchwindow/privacy/",
        "local": "hatchwindow/privacy/index.html",
        "repo": f"{HOME}/flyfish",
        "sources": ["src/app/privacy.tsx"],
    },
]

# ---------------------------------------------------------------------------
# R1 patterns. Each one is a *falsifiable negative*: a sentence a user can
# disprove from Settings -> iCloud -> Manage Storage. These are the worst kind
# of claim to get wrong and they are the only kind this rule polices.
# ---------------------------------------------------------------------------
CLAIM_PATTERNS = [
    r"never leaves your device",
    r"never leaves the device",
    r"ever leaves your device",
    r"nothing leaves your device",
    r"nothing ever leaves this device",
    r"does not transmit anything",
    r"doesn.t transmit anything",
    r"does not send your data anywhere",
    r"doesn.t send your data anywhere",
    r"there is no cloud copy",
    r"no cloud copy",
    r"not in your icloud backup",
    r"not copied into your icloud",
    r"excluded from backup",
    r"kept out of (your )?icloud",
]

ICLOUD_DISCLOSURE = re.compile(r"icloud", re.I)

MONTHS = (
    "january february march april may june july august september october "
    "november december"
).split()

DATE_PATTERNS = [
    # Last updated: October 14, 2026
    (
        re.compile(
            r"last updated:?\s*\**\s*(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})",
            re.I,
        ),
        "monthname",
    ),
    # Last updated: 2026-10-14   /   LAST_UPDATED = '2026-10-14'
    (re.compile(r"last[_ ]updated\W{0,4}\s*\**\s*(\d{4})-(\d{2})-(\d{2})", re.I), "iso"),
]


def strip_html(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    # Keep the meta description: it is user-facing in search results and it
    # carried the false claim too.
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def normalise(text: str) -> str:
    """Lower-case, collapse whitespace, flatten smart punctuation.

    The hosted pages use curly apostrophes and the repo markdown uses straight
    ones, so a literal comparison would miss on punctuation alone.
    """
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " - ").replace("–", " - ")
    text = text.replace("&apos;", "'").replace("&quot;", '"')
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def strip_quoted(text: str) -> str:
    """Remove double-quoted spans, so a quoted retraction cannot satisfy R1."""
    return re.sub(r'"[^"]{0,400}"', " ", text)


def parse_last_updated(text: str) -> dt.date | None:
    for pattern, kind in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if kind == "monthname":
                month = MONTHS.index(m.group(1).lower()) + 1
                return dt.date(int(m.group(3)), month, int(m.group(2)))
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "bakerventures-privacy-claim-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def read_sources(entry: dict) -> tuple[str, list[str], list[str]]:
    """Return (concatenated text, files read, files missing)."""
    chunks: list[str] = []
    read: list[str] = []
    missing: list[str] = []
    for rel in entry["sources"]:
        path = os.path.join(entry["repo"], rel)
        if not os.path.isfile(path):
            missing.append(rel)
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            chunks.append(fh.read())
        read.append(rel)
    return "\n\n".join(chunks), read, missing


def check_app(entry: dict, use_local: bool, verbose: bool) -> list[str]:
    """Return a list of failure strings; empty means this app agrees."""
    failures: list[str] = []
    app = entry["app"]

    def ok(msg: str) -> None:
        if verbose:
            print(f"    ok   {msg}")

    # --- the published artefact ------------------------------------------
    if use_local:
        local_path = os.path.join(SITE_ROOT, entry["local"])
        if not os.path.isfile(local_path):
            return [f"R5 UNREACHABLE: no local file {entry['local']}"]
        with open(local_path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        where = f"local:{entry['local']}"
    else:
        try:
            status, raw = fetch(entry["url"])
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            return [f"R5 UNREACHABLE: {entry['url']} -> {exc}"]
        if status != 200:
            return [f"R5 UNREACHABLE: {entry['url']} -> HTTP {status}"]
        where = entry["url"]

    live = normalise(strip_html(raw))

    # --- the repo description --------------------------------------------
    src_raw, read, missing = read_sources(entry)
    if not read:
        return [
            "R4 NO-SOURCE: the published page at "
            f"{entry['url']} has no repo source to compare against "
            f"(looked for {', '.join(entry['sources'])} under {entry['repo']}). "
            "An unowned published page is how the 2026-10-14 defect happened."
        ]
    if missing:
        failures.append(
            f"R4 NO-SOURCE: missing source file(s) {', '.join(missing)} under {entry['repo']}"
        )

    src = normalise(src_raw)
    src_unquoted = strip_quoted(src)

    if verbose:
        print(f"    page {where}")
        print(f"    src  {entry['repo']} :: {', '.join(read)}")

    # --- R1 retracted claim ----------------------------------------------
    for pattern in CLAIM_PATTERNS:
        on_live = re.search(pattern, live)
        if not on_live:
            continue
        if re.search(pattern, src_unquoted):
            ok(f"R1 '{pattern}' asserted on both page and source")
            continue
        quoted_only = bool(re.search(pattern, src))
        detail = (
            " (the source only mentions it inside quotation marks, i.e. it is "
            "retracting the sentence, not making it)"
            if quoted_only
            else ""
        )
        failures.append(
            f"R1 RETRACTED-CLAIM: the live page still says "
            f'"...{excerpt(live, on_live)}..." but {entry["repo"]} no longer '
            f"asserts /{pattern}/{detail}"
        )

    # --- R2 missing disclosure -------------------------------------------
    if ICLOUD_DISCLOSURE.search(src_unquoted) and not ICLOUD_DISCLOSURE.search(live):
        failures.append(
            "R2 MISSING-DISCLOSURE: the repo source discusses iCloud "
            "(backup behaviour is disclosed there) but the published page "
            "does not mention iCloud anywhere"
        )
    elif ICLOUD_DISCLOSURE.search(src_unquoted):
        ok("R2 iCloud disclosed in both")

    # --- R3 stale date ----------------------------------------------------
    live_date = parse_last_updated(live)
    src_date = parse_last_updated(src)
    if live_date and src_date:
        if live_date < src_date:
            failures.append(
                f"R3 STALE-DATE: published page says Last updated {live_date}, "
                f"repo source says {src_date} -- the source moved and the page did not"
            )
        else:
            ok(f"R3 date page={live_date} source={src_date}")
    elif verbose:
        print(
            f"    note no comparable Last-updated date "
            f"(page={live_date}, source={src_date})"
        )

    return failures


def excerpt(text: str, match: re.Match, width: int = 60) -> str:
    start = max(0, match.start() - width)
    end = min(len(text), match.end() + width)
    return text[start:end].strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check published privacy pages against their repo sources."
    )
    ap.add_argument(
        "--local",
        action="store_true",
        help="read the local working tree instead of fetching (pre-deploy dry run)",
    )
    ap.add_argument("--app", action="append", help="limit to these app keys")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    entries = MANIFEST
    if args.app:
        wanted = {a.lower() for a in args.app}
        entries = [e for e in MANIFEST if e["app"] in wanted]
        if not entries:
            print(f"no app in the manifest matches {sorted(wanted)}", file=sys.stderr)
            return 2

    mode = "LOCAL WORKING TREE" if args.local else "LIVE PUBLISHED PAGES"
    print(f"Privacy page vs repo source check -- {mode}")
    print(f"{dt.datetime.now().astimezone().isoformat(timespec='seconds')}\n")

    total = 0
    for entry in entries:
        print(f"  {entry['app']}")
        failures = check_app(entry, args.local, args.verbose)
        if failures:
            total += len(failures)
            for f in failures:
                print(f"    FAIL {f}")
        else:
            print("    PASS")
        print()

    if total:
        print(f"FAIL: {total} disagreement(s) between published pages and repo sources.")
        print(
            "A published page is the artefact a user and a reviewer read. "
            "Fix the page, deploy it, then re-run this against the live URL."
        )
        return 1

    print(f"PASS: {len(entries)} page(s) agree with their repo sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
