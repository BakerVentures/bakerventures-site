#!/usr/bin/env python3
"""Add (or remove) the Cloudflare Web Analytics beacon across this site.

WHY THIS EXISTS
---------------
On 2026-10-13 a grep of this repo for every common analytics tag found zero
hits across all 217 pages. Nothing here has ever been measured: there is no way
to tell a page nobody visits from a page people visit and do not click, and no
way to see which of the app landing pages actually sends anyone to an App Store
product page. That is one whole stage of the funnel, and it was dark.

WHY THIS IS A SCRIPT AND NOT A BUILD STEP
-----------------------------------------
This site has no build step. GitHub Pages serves the committed HTML verbatim, so
the tag has to be IN the files -- there is no template to change once and no
generator to re-run. 217 pages is also too many to edit by hand without missing
some, and a partially tagged site produces numbers that look real and are wrong.

WHY NOT THE CLOUDFLARE DASHBOARD TOGGLE
---------------------------------------
For a hostname proxied through Cloudflare, Web Analytics can be switched on with
no code at all -- Cloudflare injects this beacon at the edge. That is how the
*.bakerventuresstudio.com sites in ~/baker-ventures-geo should be done, because
they are Cloudflare Pages projects and their hostnames resolve to Cloudflare
anycast addresses (104.21.x / 172.67.x).

The apex is different, and this was checked rather than assumed:

    $ dig +short bakerventuresstudio.com A
    185.199.108.153  185.199.111.153  185.199.109.153  185.199.110.153

Those are GitHub Pages addresses. The zone's nameservers are Cloudflare's, but
this record is DNS-only (grey cloud), so requests never touch Cloudflare's edge
and there is nothing there to inject the beacon. The explicit snippet is the only
option for this site.

WHY CLOUDFLARE WEB ANALYTICS
----------------------------
Free with no traffic ceiling, and it needs no cookie banner: no cookies, no
localStorage, no fingerprinting, no cross-site identifier, and the visitor's IP
is used transiently to derive a country and then discarded. It reports the one
thing that is actually wanted here -- pageviews, referrers and countries per
path -- and nothing that would require a consent dialog on a marketing site.

USAGE
-----
    CF_WEB_ANALYTICS_TOKEN=<token> python3 scripts/add_web_analytics.py
    python3 scripts/add_web_analytics.py --check     # report coverage, change nothing
    python3 scripts/add_web_analytics.py --remove    # strip every beacon

The token comes from Cloudflare > Web Analytics > this site > the JS snippet. It
is a public, write-only beacon token (the same class of value as a PostHog
project key), so it is safe in the committed HTML -- which it has to be, since
these pages are served as static files.

Idempotent: a page that already carries a beacon with the same token is left
alone; one with a different token is updated in place. Re-running is safe.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Legal pages are deliberately left unmeasured. Several of them state in so many
# words that there is no analytics; those claims are scoped to the APP, so a
# beacon on the marketing site does not contradict them, but a page whose whole
# subject is "nothing is collected here" is the wrong place to put a collector,
# and a pageview count on a privacy policy answers no question anybody has.
NO_BEACON = ("privacy", "terms", "legal", "eula", "subscription-terms")

# Directories that are not the published site.
SKIP_DIRS = {".git", ".github", "node_modules", "scripts"}

BEACON_RE = re.compile(
    r'\n?<script defer src="https://static\.cloudflareinsights\.com/beacon\.min\.js"[^>]*></script>'
)


def beacon(token):
    return ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
            'data-cf-beacon=\'{"token": "%s"}\'></script>' % token)


def is_legal(rel):
    parts = rel.replace(os.sep, "/").lower().split("/")
    return any(os.path.splitext(p)[0] in NO_BEACON for p in parts)


def pages():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            if name.endswith(".html"):
                full = os.path.join(dirpath, name)
                yield full, os.path.relpath(full, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report coverage, change nothing")
    ap.add_argument("--remove", action="store_true", help="strip every beacon")
    args = ap.parse_args()

    token = os.environ.get("CF_WEB_ANALYTICS_TOKEN", "").strip()
    if not args.check and not args.remove and not token:
        sys.exit(
            "CF_WEB_ANALYTICS_TOKEN is not set, so there is nothing to inject and\n"
            "every page on this site stays unmeasured.\n\n"
            "Get it from Cloudflare > Web Analytics > this site > the JS snippet, then:\n"
            "  CF_WEB_ANALYTICS_TOKEN=<token> python3 scripts/add_web_analytics.py\n\n"
            "Use --check to see current coverage without a token."
        )

    tagged = untagged = legal = changed = 0
    for full, rel in pages():
        text = open(full, encoding="utf-8").read()
        has = "static.cloudflareinsights.com" in text
        if is_legal(rel):
            legal += 1
            if has and not args.check:   # a legal page should never carry one
                open(full, "w", encoding="utf-8").write(BEACON_RE.sub("", text))
                changed += 1
            continue

        if args.check:
            tagged += has
            untagged += not has
            if not has:
                print("  UNMEASURED  %s" % rel)
            continue

        if args.remove:
            if has:
                open(full, "w", encoding="utf-8").write(BEACON_RE.sub("", text))
                changed += 1
            continue

        tag = beacon(token)
        if tag in text:
            tagged += 1
            continue
        # Replace any existing beacon (e.g. a rotated token) rather than stacking.
        if has:
            text = BEACON_RE.sub("", text)
        # Before </body> so it never delays first paint; `defer` means it also
        # never blocks parsing. Fall back to </html> for the few pages that have
        # no </body>, and append for anything with neither.
        if "</body>" in text:
            text = text.replace("</body>", tag + "\n</body>", 1)
        elif "</html>" in text:
            text = text.replace("</html>", tag + "\n</html>", 1)
        else:
            text = text.rstrip() + "\n" + tag + "\n"
        open(full, "w", encoding="utf-8").write(text)
        changed += 1

    total = tagged + untagged + legal + changed
    if args.check:
        print("\n%d pages: %d measured, %d UNMEASURED, %d legal pages exempt"
              % (total, tagged, untagged, legal))
        return 1 if untagged else 0
    verb = "stripped from" if args.remove else "added to"
    print("beacon %s %d pages (%d already current, %d legal pages exempt)"
          % (verb, changed, tagged, legal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
