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
  R6 UNBACKED-EXCLUSION  a page asserts the data is EXCLUDED from iCloud/device backup while
                         the repo registers no mechanism that could do that.

Every page a listing links to, not just the privacy one
-------------------------------------------------------
Added 2026-10-14, second pass. The first version of this file checked one URL per app -- the
Privacy Policy -- and that is exactly why `/hatchwindow/terms/`, `/vocabdrift/terms/`,
`/hormonelog/support/`, `/miletruth/support/` and `/rsuvest/privacy/` went unexamined while
carrying the same class of sentence. A check that cannot see a page cannot fail on it. The
manifest is now one entry per PAGE, and an app contributes as many entries as it publishes.

What this check still cannot tell you, stated plainly
-----------------------------------------------------
R1-R3 compare the published page against the repo. They catch a page and a repo that disagree.
They CANNOT catch a sentence that is false in both -- which is what six pages turned out to be on
2026-10-14. Only installing the Release build, driving it until it holds real data and reading the
backup-exclusion xattr off the container settles that; see
/Users/ryanbaker/backup-claims-measured-2026-10-14.md for the measurements and
/Users/ryanbaker/VERIFICATION-LESSON.md for why it has to be the artefact. R6 is the one rule here
that reaches toward the mechanism, and even it reads the repo's intent rather than the binary.

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
    # --- NoticeGuard -------------------------------------------------------
    {
        "app": "noticeguard",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/noticeguard/privacy/",
        "local": "noticeguard/privacy/index.html",
        "repo": f"{HOME}/lienclock",
        "sources": ["docs/privacy-policy.md", "src/app/privacy.tsx"],
    },
    # --- DenialDesk --------------------------------------------------------
    {
        "app": "denialdesk",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/denialdesk/privacy/",
        "local": "denialdesk/privacy/index.html",
        "repo": f"{HOME}/denialfighter",
        "sources": ["docs/privacy-policy.md", "src/app/privacy.tsx"],
    },
    # --- MoveWitness -------------------------------------------------------
    {
        "app": "movewitness",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/rentcheck/privacy/",
        "local": "rentcheck/privacy/index.html",
        "repo": f"{HOME}/movewitness",
        # No docs/privacy-policy.md exists: the hosted page IS the policy. The
        # repo's corrected position on the backup is in the Terms and in the
        # App Privacy determination, so those are the source of truth here.
        "sources": ["docs/terms.md", "docs/app-privacy-determination.md"],
    },
    # --- Steadychart -------------------------------------------------------
    # All three Steadychart pages are KNOWN-FAILING and are meant to stay that
    # way until the backup-exclusion fix (symptom-tracker 1bb1c79) is merged,
    # rebuilt from a fresh prebuild, and resubmitted. The binary in App Review
    # still backs up, so republishing the repo's wording would swap one false
    # sentence for a different false sentence. See
    # /Users/ryanbaker/live-pages-fix-2026-10-14.md section 6. A visible
    # problem is better than a hidden one, so they are listed, not skipped.
    {
        "app": "steadychart",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/steadychart/privacy/",
        "local": "steadychart/privacy/index.html",
        "repo": f"{HOME}/symptom-tracker",
        "sources": ["docs/PRIVACY.md"],
    },
    {
        "app": "steadychart",
        "page": "terms",
        "url": "https://bakerventuresstudio.com/steadychart/terms/",
        "local": "steadychart/terms/index.html",
        "repo": f"{HOME}/symptom-tracker",
        "sources": ["docs/terms.md", "src/app/terms.tsx"],
    },
    {
        "app": "steadychart",
        "page": "support",
        "url": "https://bakerventuresstudio.com/steadychart/support/",
        "local": "steadychart/support/index.html",
        "repo": f"{HOME}/symptom-tracker",
        # No support/FAQ document exists in the repo. The app's own screens are
        # the repo's position on what it tells a user about their data, so they
        # are the source here rather than nothing.
        "sources": [
            "docs/PRIVACY.md",
            "src/app/settings.tsx",
            "src/app/export.tsx",
            "src/components/privacy-disclosure.tsx",
        ],
    },
    # --- PolicyReady -------------------------------------------------------
    {
        "app": "policyready",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/policyready/privacy/",
        "local": "policyready/privacy/index.html",
        "repo": f"{HOME}/cyberclose",
        "sources": ["docs/privacy-policy.md"],
    },
    # --- Vocabdrift --------------------------------------------------------
    {
        "app": "vocabdrift",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/vocabdrift/privacy/",
        "local": "vocabdrift/privacy/index.html",
        "repo": f"{HOME}/lockscreen-learn",
        "sources": ["src/screens/PrivacyScreen.tsx"],
    },
    {
        "app": "vocabdrift",
        "page": "terms",
        "url": "https://bakerventuresstudio.com/vocabdrift/terms/",
        "local": "vocabdrift/terms/index.html",
        "repo": f"{HOME}/lockscreen-learn",
        "sources": ["docs/terms.md", "src/screens/TermsScreen.tsx"],
    },
    # --- Hatch Window ------------------------------------------------------
    {
        "app": "hatchwindow",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/hatchwindow/privacy/",
        "local": "hatchwindow/privacy/index.html",
        "repo": f"{HOME}/flyfish",
        "sources": ["src/app/privacy.tsx"],
    },
    {
        "app": "hatchwindow",
        "page": "terms",
        "url": "https://bakerventuresstudio.com/hatchwindow/terms/",
        "local": "hatchwindow/terms/index.html",
        "repo": f"{HOME}/flyfish",
        "sources": ["docs/terms.md", "src/app/terms.tsx"],
    },
    # --- HormoneLog --------------------------------------------------------
    # HormoneLog keeps its published copy as a Next.js app under apps/web, so
    # that is the repo source, not a markdown file.
    {
        "app": "hormonelog",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/hormonelog/privacy/",
        "local": "hormonelog/privacy/index.html",
        "repo": f"{HOME}/hormonelog",
        "sources": ["apps/web/src/app/privacy/page.tsx"],
    },
    {
        "app": "hormonelog",
        "page": "support",
        "url": "https://bakerventuresstudio.com/hormonelog/support/",
        "local": "hormonelog/support/index.html",
        "repo": f"{HOME}/hormonelog",
        "sources": [
            "apps/web/src/app/faq/page.tsx",
            "apps/mobile/app/(tabs)/settings/index.tsx",
        ],
    },
    # --- MileTruth ---------------------------------------------------------
    {
        "app": "miletruth",
        "page": "support",
        "url": "https://bakerventuresstudio.com/miletruth/support/",
        "local": "miletruth/support/index.html",
        "repo": f"{HOME}/miletruth",
        # No docs/support.md: the app's own Settings copy and the store
        # listing metadata are what the repo says about where data lives.
        "sources": [
            "apps/mobile/src/app/(tabs)/settings/index.tsx",
            "apps/mobile/shipcheck.metadata.md",
        ],
    },
    # --- RSUvest -----------------------------------------------------------
    {
        "app": "rsuvest",
        "page": "privacy",
        "url": "https://bakerventuresstudio.com/rsuvest/privacy/",
        "local": "rsuvest/privacy/index.html",
        "repo": f"{HOME}/rsuvest",
        "sources": ["docs/privacy-policy.md", "src/app/privacy.tsx"],
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
    # Added 2026-10-14 after the terms/support pages came into scope. Each of
    # these was live on a page this check could not previously see.
    r"the only copy",
    r"on this device only",
    r"no backup to restore from",
]

# R6: the strong form -- a page claiming the data is positively EXCLUDED from
# the device backup. This is a claim about a native flag, so it is the one
# claim whose mechanism can be looked for. It deliberately does NOT include
# "no cloud copy" or "the only copy": Vocabdrift's pages carry those and they
# are true there, because @react-native-async-storage/async-storage sets
# isExcludedFromBackup on its own storage directory by default (measured
# 2026-10-14) -- a library default, not a repo mechanism, so requiring a
# plugin for those phrasings would raise a false alarm. (Spelled as the Swift
# property rather than the Foundation NSURL... constant on purpose: the
# constant's name is long enough and mixed-case enough that verify-push.sh's
# entropy rule reads it as a credential and refuses the push. Noted so nobody
# "fixes" that by loosening the scanner.)
EXCLUSION_ASSERTIONS = [
    r"excluded from (icloud )?backup",
    r"not in your icloud backup",
    r"kept out of (your |the )?(phone.s own |device |your device.s )?backups?",
    r"not copied (in)?to (your )?icloud",
]

# Directories that are build output, vendored code, or another platform --
# never the repo's own statement of intent.
_SKIP_DIRS = {
    "node_modules", ".git", "ios", "android", "Pods", "build", ".expo",
    "dist", ".next", "DerivedData", "vendor", ".yarn",
}
_MECHANISM_SUFFIXES = (".js", ".ts", ".tsx", ".mjs", ".cjs", ".swift", ".m", ".mm")
_CONFIG_NAMES = ("app.json", "app.config.ts", "app.config.js", "app.config.mjs")


def exclusion_mechanism(repo: str) -> tuple[str, str]:
    """Does this repo register something that excludes its data from backup?

    Returns (state, detail) where state is one of:
      "registered"  a file in the repo sets isExcludedFromBackup AND its name
                    appears in an Expo config, so `expo prebuild` will apply it
      "unregistered" the file exists but no config references it -- it will not
                    run, which is a worse failure than not having it
      "none"        nothing in the repo sets the flag

    This reads INTENT, not the artefact, and the difference is the whole lesson
    of 2026-10-14: Steadychart's plugin was registered in app.json and absent
    from the committed ios/ tree, so a local xcodebuild shipped the claim false
    while the config said otherwise. After prebuild, and before archiving, the
    artefact-level check is:

        grep -n "isExcludedFromBackup" ios/<App>/AppDelegate.swift

    and the real proof is installing the Release build and reading
    `xattr Documents/SQLite` on the running app.
    """
    hits: list[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if not name.endswith(_MECHANISM_SUFFIXES):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    if "isExcludedFromBackup" in fh.read():
                        hits.append(path)
            except OSError:
                continue
    hits = [h for h in hits if not h.endswith((".test.ts", ".test.tsx", ".test.js"))]
    if not hits:
        return "none", "no file in the repo sets isExcludedFromBackup"

    configs = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if name in _CONFIG_NAMES:
                try:
                    with open(os.path.join(root, name), encoding="utf-8", errors="replace") as fh:
                        configs.append(fh.read())
                except OSError:
                    continue
    config_text = "\n".join(configs)
    for hit in hits:
        stem = os.path.splitext(os.path.basename(hit))[0]
        if stem and stem in config_text:
            return "registered", f"{os.path.relpath(hit, repo)} (registered in the Expo config)"
    return (
        "unregistered",
        f"{os.path.relpath(hits[0], repo)} sets the flag but no app.json/app.config "
        "names it, so prebuild will not apply it",
    )

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


def key(entry: dict) -> str:
    """How an entry is named in output and on the command line: app/page."""
    return f"{entry['app']}/{entry.get('page', 'privacy')}"


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
    # Named/numeric entities for quotes and apostrophes. These appear LITERALLY in
    # JSX source -- `&ldquo;` in a .tsx file is not unescaped by anything upstream.
    # Getting this wrong is not cosmetic: an unconverted `&ldquo;` made the quoted
    # retraction in lienclock/src/app/privacy.tsx look like an assertion, and R1
    # reported NoticeGuard green for the wrong reason on 2026-10-14. See strip_quoted.
    for ent in ("&ldquo;", "&rdquo;", "&quot;", "&#34;", "&#x22;"):
        text = text.replace(ent, '"')
    for ent in ("&rsquo;", "&lsquo;", "&apos;", "&#39;", "&#x27;"):
        text = text.replace(ent, "'")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def strip_quoted(text: str) -> str:
    """Remove double-quoted spans, so a quoted retraction is not read as an assertion.

    Applied to BOTH sides. A retracted sentence gets quoted in the paragraph that
    retracts it, and that happens on the published page as often as in the repo:

        But "none of it ever leaves your device" was not an accurate sentence,
        so it is gone.

    If only the repo side were stripped, the page's own quoted retraction would read
    as the page still making the claim -- a false alarm. If neither were, the repo's
    retraction would satisfy the rule -- a false pass, which is worse. Strip both and
    the rule tests what each document actually asserts.
    """
    # Non-greedy and bounded, so one unbalanced quote swallows at most a short span
    # instead of resynchronising against every later quote in the document.
    return re.sub(r'"[^"\n]{0,400}?"', " ", text)


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
    live_unquoted = strip_quoted(live)
    for pattern in CLAIM_PATTERNS:
        on_live = re.search(pattern, live_unquoted)
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
            f'"...{excerpt(live_unquoted, on_live)}..." but {entry["repo"]} no longer '
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

    # --- R6 unbacked exclusion claim --------------------------------------
    asserted = next(
        (p for p in EXCLUSION_ASSERTIONS if re.search(p, live_unquoted)),
        None,
    )
    if asserted:
        state, detail = exclusion_mechanism(entry["repo"])
        if state == "registered":
            ok(f"R6 exclusion claim backed by {detail}")
        else:
            failures.append(
                f"R6 UNBACKED-EXCLUSION: the live page asserts the data is excluded from "
                f'backup ("...{excerpt(live_unquoted, re.search(asserted, live_unquoted))}...") '
                f"but {entry['repo']}: {detail}. A claim about a native flag needs something "
                "that sets the native flag."
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
    ap.add_argument(
        "--app",
        action="append",
        help='limit to these apps or pages, e.g. "hatchwindow" or "hatchwindow/terms"',
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    entries = MANIFEST
    if args.app:
        wanted = {a.lower() for a in args.app}
        # Accept either a whole app ("hatchwindow", all of its pages) or one
        # page of one app ("hatchwindow/terms").
        entries = [
            e for e in MANIFEST if e["app"] in wanted or key(e) in wanted
        ]
        if not entries:
            print(f"no app in the manifest matches {sorted(wanted)}", file=sys.stderr)
            return 2

    mode = "LOCAL WORKING TREE" if args.local else "LIVE PUBLISHED PAGES"
    print(f"Privacy page vs repo source check -- {mode}")
    print(f"{dt.datetime.now().astimezone().isoformat(timespec='seconds')}\n")

    total = 0
    for entry in entries:
        print(f"  {key(entry)}")
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
