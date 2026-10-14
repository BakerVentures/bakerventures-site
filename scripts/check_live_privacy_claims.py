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
  R7 MEASURED-BACKUP     the page's backup claim disagrees with what was MEASURED on a
                         running build -- or no such measurement exists and the page
                         makes the claim anyway.

Why R7 had to be added (2026-10-14, third pass)
-----------------------------------------------
R1-R6 all compare a page with a REPO. That catches a page lagging its source, and nothing
else: a claim that is false on the page AND false in the repo is reported as agreement.
`/vocabdrift/privacy/` passed that way twice -- before the manifest went per-page and
after it -- while saying "none of it ever leaves your phone" about a store that is in the
user's device backup. Three separate reasons, all of them shapes VERIFICATION-LESSON.md
names:

  * R1 never fired, because every pattern said "device" and that page says "your PHONE".
    A rule whose vocabulary is narrower than the copy it polices cannot fail. `normalise`
    now folds phone/iPhone/handset to "device" on both sides.
  * R3 passed SILENTLY. The page said "Last updated: September 13, 2026"; the source says
    `const LAST_UPDATED = "September 23, 2026"`. The page was ten days stale and should
    have been red, but the date patterns only knew `last updated` with a space, so the
    TSX constant parsed as None -- and a None date skipped the rule without counting
    anything. A rule that cannot read one side must not report success: that case is now
    R3 UNREADABLE-DATE.
  * R2 did not apply, correctly: that repo source does not mention iCloud.
  * And with the first two fixed, R1 would have found the claim asserted on BOTH sides and
    called it agreement. Hence R7, which has no opinion about the repo at all.

R7 complements R6 rather than duplicating it. R6 asks the repo whether a mechanism exists,
which is the right question for a claim about a native flag -- but its own comment records
the case it cannot answer: Vocabdrift's exclusion comes from a LIBRARY DEFAULT, so no repo
mechanism exists to find. R7 answers it by reading the xattr off a running build instead.


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
# MEASURED (R7): what was observed on a RUNNING BUILD, per app.
#
# This is the one hand-maintained table in this file, and deliberately so. Everywhere
# else the expected content is read out of a repo at run time, because a hand-kept list
# of expected SENTENCES rots as fast as the pages did. A measurement is the opposite
# kind of fact: an observation with a date, a binary and a command behind it. It does
# not rot -- it either still describes the shipping binary or it needs re-taking, which
# is why every row carries its provenance and names the binary.
#
# `in_device_backup` answers one question asked of a running app: does the directory
# holding this data carry com.apple.metadata:com_apple_backup_excludeItem? No attribute
# means iOS backs it up. Intent in a config file is not an answer -- the Steadychart row
# is exactly why, and R6 above exists because the repo can only ever show intent.
#
# `holds_user_content` separates "your notes are in the backup" from "a precomputed
# slice of the bundled dictionary is in the backup". Both are in the backup; only the
# first falsifies a claim about YOUR data. `subject` is the phrase a page uses when it
# enumerates that store specifically: a page that lists the store by name and then says
# nothing of it ever leaves the device is wrong about it whatever the store holds. That
# distinction is what keeps /vocabdrift/terms/ (true, measured, left alone by the
# 1c7aa47 worker) passing while /vocabdrift/privacy/ (which enumerates the schedule)
# fails.
#
# An app with no row here is UNMEASURED, and R7 says so out loud rather than passing.
# ---------------------------------------------------------------------------
MEASURED = {
    "noticeguard": {
        "provenance": "~/guideline-audit-2026-10-14.md, table 'the backup behaviour, "
        "measured on the running apps' -- running Release build, 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/lienclock.db",
                "holds": "job names, jurisdictions, roles, dates, project facts",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs",
            }
        ],
    },
    "denialdesk": {
        "provenance": "~/guideline-audit-2026-10-14.md, same table, 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/denialfighter.db",
                "holds": "member name, claim number, provider, amounts, notes",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs",
            }
        ],
    },
    "movewitness": {
        "provenance": "~/guideline-audit-2026-10-14.md, same table, 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/rental-inspection.db (+ -wal, -shm), Documents/photos",
                "holds": "inspections, room notes and photographs of the home",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs",
            }
        ],
    },
    "steadychart": {
        # The row that proves why this table reads binaries and not config. The exclusion
        # plugin exists (symptom-tracker 1bb1c79) and works -- on a binary built AFTER a
        # fresh prebuild. That branch is unmerged and 1.0 is in App Review with the
        # pre-plugin binary, so the shipping answer is still "backed up".
        "provenance": "~/guideline-audit-2026-10-14.md -- RED on pre-plugin binary "
        "0147F599 (xattr | wc -l = 0), GREEN only on rebuilt binary 337B664B (= 1), "
        "which is not the binary in review. 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/symptomlog.db",
                "holds": "the symptom log",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs on the binary that is in App Review",
            }
        ],
    },
    "hatchwindow": {
        "provenance": "~/backup-claims-measured-2026-10-14.md s1 -- HatchWindow.app "
        "1.0.1 (1) built from flyfish 3ea20fe, installed, driven through its own UI, "
        "2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/flyfish.db",
                "holds": "the catch log, the custom spots and their coordinates, settings",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs on the directory and on the db; `strings` "
                "over the executable finds no isExcludedFromBackup at all",
            }
        ],
    },
    "hormonelog": {
        "provenance": "~/backup-claims-measured-2026-10-14.md s3 -- HormoneLog.app "
        "1.0.0 (1) prebuilt and built here, real symptom rows on disk, 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite (hormonelog.db, -wal, -shm)",
                "holds": "the health log",
                "in_device_backup": False,
                "holds_user_content": True,
                "evidence": "xattr -l -> com.apple.metadata:com_apple_backup_excludeItem "
                "= com.apple.MobileBackup on the directory; nm over the linked binary "
                "finds excludeHealthDataFromBackup and isExcludedFromBackup",
            }
        ],
    },
    "rsuvest": {
        "provenance": "~/backup-claims-measured-2026-10-14.md s4 -- rsuvest.app 1.0.0 (1) "
        "prebuilt and built here, a real grant entered through the UI, 2026-10-14",
        "stores": [
            {
                "path": "Documents/SQLite/rsuvest.db",
                "holds": "employer names, grant sizes and the whole vesting schedule",
                "in_device_backup": True,
                "holds_user_content": True,
                "evidence": "0 exclusion xattrs; nm over the linked binary finds 0 "
                "references to isExcludedFromBackup",
            }
        ],
    },
    "vocabdrift": {
        "provenance": "~/backup-claims-measured-2026-10-14.md s2 -- Vocabdrift.app "
        "1.0.1 (3), driven through its own UI, 2026-10-14. Applies to the live 1.0 "
        "binary too: the exclusion comes from "
        "@react-native-async-storage/async-storage 2.2.0's own default "
        "(ios/RNCAsyncStorage.mm _ensureSetup defaults the Info.plist key "
        "RCTAsyncStorageExcludeFromBackup to YES), that version is identical in the 1.0 "
        "tree (e496af6^) and on master, and the key is absent from the whole repo",
        "stores": [
            {
                "path": "Library/Application Support/<bundle id>/RCTAsyncLocalStorage_V1/",
                "holds": "quiz history, streak, favourites, review queue, cadence, "
                "onboarding flag",
                "in_device_backup": False,
                "holds_user_content": True,
                "evidence": "xattr -l -> com.apple.metadata:com_apple_backup_excludeItem "
                "= com.apple.MobileBackup (1 attribute)",
                # TRUE BY ACCIDENT. Nothing in lockscreen-learn asks for this exclusion:
                # it is @react-native-async-storage/async-storage's own default. Setting
                # the Info.plist key RCTAsyncStorageExcludeFromBackup to false, bumping
                # to a version whose default changes, or migrating this app to
                # expo-sqlite the way five siblings did, would silently make
                # /vocabdrift/terms/ ("there is no cloud copy ... including your
                # streak") and the backup section of /vocabdrift/privacy/ false. No test
                # and no comment in that repo would notice. R7 prints this on every run
                # that leans on it, so a published true sentence resting on a
                # third-party default is at least visible.
                "fragile": "the exclusion is @react-native-async-storage/async-storage "
                "2.2.0's own default (Info.plist key RCTAsyncStorageExcludeFromBackup "
                "absent -> YES), not a decision recorded anywhere in "
                "~/lockscreen-learn. If that default or that dependency changes, "
                "/vocabdrift/terms/ and /vocabdrift/privacy/ become false and nothing "
                "in the app repo will notice",
            },
            {
                "path": "Library/Preferences/group.com.bakerventures.vocabdrift.plist",
                "holds": "the widget rotation timeline -- 300 precomputed words from the "
                "bundled list, each with the date the chosen cadence puts it on",
                "in_device_backup": True,
                # Nothing the user typed. But a page that enumerates this store and then
                # says none of it ever leaves the device is still wrong about it, which
                # is what `subject` is for.
                "holds_user_content": False,
                "subject": r"rotation schedule",
                "evidence": "0 exclusion xattrs; nothing in the repo sets the exclusion "
                "flag on the App Group container in any build",
            },
        ],
    },
    # miletruth and policyready: deliberately absent until measured. R7 reports
    # UNMEASURED rather than inventing a verdict in either direction.
}


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
    # Added 2026-10-14 (third pass). lockscreen-learn's PrivacyScreen.tsx says "none of
    # it leaves the device" and /vocabdrift/privacy/ said "none of it ever leaves your
    # phone": the same claim, and with the patterns above alone neither matched anything.
    r"none of it (ever )?leaves (your|the|this) device",
    r"nothing (else )?leaves (your|the|this) device",
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
# The absolute form: "no copy of this exists anywhere but this handset". Derived from
# CLAIM_PATTERNS rather than copied, so adding a pattern above cannot leave this list
# behind. R7 needs the distinction: an absolute claim is about EVERYTHING, so one store
# in the backup falsifies it, whereas an exclusion claim is usually scoped to one store.
_EXCLUSION_SHAPED = {
    r"not in your icloud backup",
    r"not copied into your icloud",
    r"excluded from backup",
    r"kept out of (your )?icloud",
}

# Claims about the app's NETWORK behaviour. A device backup does not falsify these:
# "the app doesn't send your data anywhere" stays true while iOS copies the file into
# iCloud, because the app is not what sent it. Keeping them separate matters twice
# over -- R7 must not fail a page for a sentence that is true, and R1 must not read
# "doesn't send your data anywhere" in a repo as the same claim as "nothing leaves
# your device" on a page. Grouping them together did exactly that on 2026-10-14 and
# silenced a real R1 finding on /steadychart/support/.
TRANSMISSION_PATTERNS = {
    r"does not transmit anything",
    r"doesn.t transmit anything",
    r"does not send your data anywhere",
    r"doesn.t send your data anywhere",
}

# Claims about WHERE THE DATA IS. These are the ones a backup falsifies, and the ones
# R7 tests against the measurement. Derived from CLAIM_PATTERNS rather than copied, so
# adding a pattern above cannot leave this list behind.
NO_COPY_PATTERNS = [
    p
    for p in CLAIM_PATTERNS
    if p not in _EXCLUSION_SHAPED and p not in TRANSMISSION_PATTERNS
]


# A page that says any of this is at least TALKING about backups, which is the minimum
# R7 asks of a page whose data is measurably in one.
BACKUP_MENTION = re.compile(r"\bback(ed)?.?ups?\b|\bicloud\b", re.I)

EXCLUSION_ASSERTIONS = [
    r"excluded from (icloud )?backup",
    r"not in your icloud backup",
    r"kept out of (your |the )?(phone.s own |device |your device.s )?backups?",
    r"not copied (in)?to (your )?icloud",
]

# R7's own exclusion vocabulary: EXCLUSION_ASSERTIONS plus the wordings a page reaches
# for when the exclusion is real but comes from a library default. These are kept OUT of
# EXCLUSION_ASSERTIONS on purpose: R6 answers an exclusion claim by looking for a
# mechanism in the repo, and Vocabdrift has none to find -- the flag is set by
# @react-native-async-storage/async-storage's own default -- so adding them there would
# raise a false alarm on a true sentence, exactly as that rule's comment warns. R7 asks
# the binary instead, which is the only question with an answer in that case.
MEASURED_EXCLUSION_CLAIMS = EXCLUSION_ASSERTIONS + [
    r"not in your (icloud |device )?backups?",
    r"out of your (icloud |device )?backups?",
    r"backup.exclusion attribute",
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

# Only complain about an unparseable source date when the source is actually TRYING to
# state one. A support page whose sources are app screens has no "Last updated" to find,
# and reporting that as a finding is noise -- and a noisy check gets switched off, which
# is how a check stops catching anything.
LAST_UPDATED_TOKEN = re.compile(r"last[_ ]updated", re.I)

DATE_PATTERNS = [
    # Last updated: October 14, 2026
    # LAST_UPDATED = "October 14, 2026"   <- the TSX/JS constant form, added 2026-10-14.
    # Without it the SOURCE side parsed as None for every app whose policy lives in a
    # .tsx screen, and a None date skipped R3 without counting a failure: the live
    # /vocabdrift/privacy/ page was ten days behind its source and reported PASS.
    # `\W{0,6}` spans the ` = "` between the name and the month; `[_ ]` accepts the
    # underscore in the constant name.
    (
        re.compile(
            r"last[_ ]updated\W{0,6}(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})",
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
    text = text.lower()
    # Fold the synonyms a copywriter picks freely. /vocabdrift/privacy/ said "none of it
    # ever leaves your PHONE" while every pattern here said "device", so R1 matched
    # nothing and the page reported PASS while making the exact claim R1 exists to
    # catch. Applied to both sides, so the comparison is about what is asserted and not
    # about which noun the page happened to reach for.
    text = re.sub(r"\b(your|this|the|my) (phone|iphone|handset)\b", r"\1 device", text)
    return text


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


# A corrected page routinely NAMES the sentence it refuses to say:
#
#   "we are not going to tell you nothing leaves the device when that isn't accurate"
#   "we are not going to say nothing leaves the device when your backup holds a copy"
#
# Both are live right now on /denialdesk/privacy/ and /rentcheck/privacy/, neither is in
# quotation marks, so strip_quoted cannot see them. Reading those as assertions flags the
# two pages that were corrected FIRST -- the mirror image of the false pass this file
# exists to stop, and the fastest way to get a check switched off. (Found exactly that
# way: widening the vocabulary in A above turned both pages red until this was added.)
DISCLAIMER_CUES = re.compile(
    r"(?:not going to (?:tell you|say)|no longer says?|"
    r"(?:do not|don't|will not|won't|cannot|can't|wouldn't|would not) (?:say|tell you|claim)|"
    r"used to say|stopped saying|instead of saying|rather than say(?:ing)?|"
    r"was not an accurate|is not accurate to say)",
    re.I,
)


def strip_disclaimed(text: str, window: int = 140) -> str:
    """Blank the span after a disclaimer cue, so a named-and-refused sentence is not
    counted as an assertion. Bounded, so it cannot swallow the rest of a document."""
    return re.sub(
        DISCLAIMER_CUES.pattern + r".{0," + str(window) + r"}", " ", text, flags=re.I
    )


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


def check_measured_backup(entry: dict, live_unquoted: str, live: str, ok) -> list[str]:
    """R7: the live page's backup claim against a measurement off a RUNNING BUILD.

    Every other rule in this file compares a page with a repo, which catches a page
    lagging its source and nothing else -- a claim false in both passes as agreement.
    This rule has no opinion about the repo. It asks what was observed on a running
    build and fails the page for asserting more than the observation supports.

    The two directions are asymmetric, because the claims are:

      * a "no copy of this exists off the handset" is a claim about
        EVERYTHING, so one measured store sitting in the device backup falsifies it --
        provided that store either holds something the user put there, or is itself
        enumerated on the page (`subject`);
      * "this is kept out of the backup" is usually scoped to one store, so it fails
        only when NOTHING measured is excluded. R6 asks the repo for a mechanism; this
        asks the binary for the result, which is the only question with an answer when
        the exclusion comes from a library default (Vocabdrift) rather than a plugin.

    And a page whose data is measurably in a backup must at least mention backups: the
    pre-fix /vocabdrift/privacy/ never used the word, which is how four separate commits
    could "fix the privacy policy" while the page a user reads said nothing.
    """
    failures: list[str] = []
    app = entry["app"]
    absolute_hits = [
        (p, m)
        for p in NO_COPY_PATTERNS
        for m in [re.search(p, live_unquoted)]
        if m
    ]
    absolutes = [p for p, _ in absolute_hits]
    exclusions = [p for p in MEASURED_EXCLUSION_CLAIMS if re.search(p, live_unquoted)]
    record = MEASURED.get(app)

    if record is None:
        if absolutes or exclusions:
            claimed = ", ".join(f"/{p}/" for p in absolutes + exclusions)
            failures.append(
                f"R7 UNMEASURED-CLAIM: the live page asserts {claimed}, which a user can "
                "disprove from Settings, and nobody has measured this app's backup "
                "behaviour. Add a row to MEASURED once a Release build has been driven "
                "through its own UI and the exclusion xattr read off the live container. "
                "'Nobody looked' must not read the same as 'it is fine'."
            )
        else:
            ok("R7 no falsifiable backup claim on the page, and none needed")
        return failures

    # How far after a claim a list it introduces can still be running. Direction is
    # what does the work, not the number: the sentence that ENUMERATES a store is the
    # one claiming nothing in the list leaves the device, and it introduces that list
    # (it ends in a colon). /vocabdrift/privacy/ names the rotation schedule 243
    # characters AFTER its claim, inside that list. /vocabdrift/terms/ mentions the
    # same words 638 characters BEFORE its own claim, in a different section about what
    # the app is -- which is not a claim about that store, and is why the 1c7aa47
    # worker measured that page true and left it alone. A mere mention anywhere on the
    # page would have overturned their verdict as a side effect.
    ENUMERATION_WINDOW = 600

    def relevant(store: dict) -> bool:
        """Does this in-backup store bear on what THIS page claims?"""
        if store.get("holds_user_content", True):
            return True
        subject = store.get("subject")
        if not subject:
            return False
        return any(
            claim.end() <= sm.start() <= claim.end() + ENUMERATION_WINDOW
            for _, claim in absolute_hits
            for sm in re.finditer(subject, live_unquoted)
        )

    in_backup = [st for st in record["stores"] if st["in_device_backup"]]
    excluded = [st for st in record["stores"] if not st["in_device_backup"]]
    bearing = [st for st in in_backup if relevant(st)]

    if absolutes and bearing:
        # One finding per store, not per pattern: several wordings of one claim on one
        # page are one defect, and a rule that multiplies them reads like several.
        claimed = ", ".join(f"/{p}/" for p in absolutes)
        for store in bearing:
            failures.append(
                f"R7 MEASURED-CONTRADICTION: the live page asserts {claimed}, but "
                f"{store['path']} holds {store['holds']} and is IN the user's device "
                f"backup ({store['evidence']}). Measured: {record['provenance']}"
            )

    if exclusions and not excluded:
        failures.append(
            "R7 UNSUPPORTED-EXCLUSION: the live page claims the data is kept out of the "
            f"backup ({', '.join('/' + p + '/' for p in exclusions)}), but no measured "
            f"store of this app is excluded. Measured: {record['provenance']}"
        )

    if bearing and not BACKUP_MENTION.search(live):
        failures.append(
            "R7 UNDISCLOSED-BACKUP: "
            + "; ".join(f"{st['path']} ({st['holds']})" for st in bearing)
            + " is in the user's device backup, and this published page never mentions a "
            f"backup or iCloud at all. Measured: {record['provenance']}"
        )

    # Not a failure, and printed whether or not -v is on: a page whose true sentence
    # depends on something nobody in the app repo chose is one somebody will break
    # without meaning to. Silence here is how a true claim becomes a false one.
    if absolutes or exclusions:
        for store in excluded:
            if store.get("fragile"):
                print(
                    f"    NOTE R7 fragile basis: this page's claim holds because "
                    f"{store['path']} is excluded from backup, but {store['fragile']}."
                )

    if not failures:
        claims = (
            f"{len(absolutes)} no-copy claim(s), {len(exclusions)} exclusion claim(s)"
            if (absolutes or exclusions)
            else "no falsifiable backup claim"
        )
        ok(
            f"R7 page agrees with the measurement -- {claims}; {len(excluded)} store(s) "
            f"excluded, {len(in_backup)} in the backup, {len(bearing)} of those bearing "
            "on this page"
        )
    return failures


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
    src_unquoted = strip_disclaimed(strip_quoted(src))

    if verbose:
        print(f"    page {where}")
        print(f"    src  {entry['repo']} :: {', '.join(read)}")

    # --- R1 retracted claim ----------------------------------------------
    live_unquoted = strip_disclaimed(strip_quoted(live))
    for pattern in CLAIM_PATTERNS:
        on_live = re.search(pattern, live_unquoted)
        if not on_live:
            continue
        if re.search(pattern, src_unquoted):
            ok(f"R1 '{pattern}' asserted on both page and source")
            continue
        # The page and the source can assert the SAME claim in different words ("none of
        # it ever leaves your phone" vs "none of it leaves the device"). That is not a
        # retraction, and calling it one sends the next worker to edit a repo that never
        # changed -- a red for the wrong reason misleads as badly as a green for the
        # wrong reason. Whether the claim is TRUE is R7's question, not this rule's.
        if pattern in _EXCLUSION_SHAPED:
            group = EXCLUSION_ASSERTIONS
        elif pattern in TRANSMISSION_PATTERNS:
            group = sorted(TRANSMISSION_PATTERNS)
        else:
            group = NO_COPY_PATTERNS
        equivalents = [q for q in group if q != pattern and re.search(q, src_unquoted)]
        if equivalents:
            ok(
                f"R1 '{pattern}' on the page, '{equivalents[0]}' in the source -- the "
                "same claim in different words, so nothing was retracted (see R7)"
            )
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
    elif live_date and not src_date and LAST_UPDATED_TOKEN.search(src):
        # Not a pass. The source side could not be read, so R3 did not run -- and until
        # 2026-10-14 that printed nothing and counted nothing, which is how a page ten
        # days behind its source came back PASS. A rule that could not run must say so.
        failures.append(
            f"R3 UNREADABLE-DATE: the page says Last updated {live_date}, and the source "
            "declares a 'last updated' of its own that no pattern here could parse, but no "
            f"'Last updated' date could be parsed out of {', '.join(read)} in "
            f"{entry['repo']}, so the staleness comparison never ran. Give the source a "
            "parseable date, or point `sources` at a file that has one."
        )
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

    # --- R7 measured backup behaviour -------------------------------------
    failures.extend(check_measured_backup(entry, live_unquoted, live, ok))

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
