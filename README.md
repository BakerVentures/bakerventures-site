# bakerventures-site

Company site for **Baker Ventures LLC**, served at
**[bakerventuresstudio.com](https://bakerventuresstudio.com/)** via GitHub Pages.

Plain static HTML, no build step. Edit and push to `main` to deploy.

## FlirtGym

[FlirtGym](https://bakerventuresstudio.com/flirtgym/) is an iPhone app for practicing
dating conversations before you have them. It runs practice chats with AI characters and
scores the messages you write, rather than writing them for you.
[Download on the App Store](https://apps.apple.com/us/app/flirtgym/id6784050951).

### Free browser tools

No signup, no upload, no account. Everything scores locally in the browser.

| Tool | What it does |
|---|---|
| [Opener Score](https://bakerventuresstudio.com/flirtgym/opener-score/) | Rates a dating app opener out of ten on tone, specificity, momentum and intrigue |
| [Hinge Prompt Checker](https://bakerventuresstudio.com/flirtgym/prompt-check/) | Tests whether your three prompt answers are actually answerable, and whether they repeat each other |
| [Conversation Check](https://bakerventuresstudio.com/flirtgym/conversation-check/) | Measures reciprocity in a thread: who sends more, who asks, who restarts it |
| [Flirting Style Quiz](https://bakerventuresstudio.com/flirtgym/flirting-style/) | Nine questions, four styles, each with a real trade-off rather than a compliment |
| [Photo Lineup Checker](https://bakerventuresstudio.com/flirtgym/photo-lineup/) | Checks the order of your profile photos from short descriptions, so nothing is uploaded |

### Support

[FlirtGym support](https://bakerventuresstudio.com/flirtgym/support/) — cancelling,
refunds, restoring a purchase, deleting your account, and the address a human reads.

### Research

- [Opener Score Study](https://bakerventuresstudio.com/flirtgym/research/opener-score-study/)
  — 40 dating app openers across 8 patterns, each scored twice by the same rubric.
  Raw scores and category summaries are published as JSON:
  [`opener_study_raw.json`](flirtgym/research/opener_study_raw.json),
  [`opener_study_summary.json`](flirtgym/research/opener_study_summary.json).

### Guides

[Opening messages](https://bakerventuresstudio.com/flirtgym/dating-app-opening-messages/) ·
[When she stops replying](https://bakerventuresstudio.com/flirtgym/what-to-say-when-she-stops-replying/) ·
[Keeping a conversation going](https://bakerventuresstudio.com/flirtgym/how-to-keep-a-conversation-going/) ·
[Flirting over text](https://bakerventuresstudio.com/flirtgym/how-to-flirt-over-text/) ·
[Texting a girl](https://bakerventuresstudio.com/flirtgym/how-to-text-a-girl/) ·
[Asking her out over text](https://bakerventuresstudio.com/flirtgym/how-to-ask-a-girl-out-over-text/) ·
[Hinge prompts](https://bakerventuresstudio.com/flirtgym/hinge-prompts/) ·
[Getting more matches](https://bakerventuresstudio.com/flirtgym/how-to-get-more-matches/) ·
[Profile feedback](https://bakerventuresstudio.com/flirtgym/rate-my-dating-profile/) ·
[Practice with AI](https://bakerventuresstudio.com/flirtgym/practice-dating-conversations/) ·
[For shy guys](https://bakerventuresstudio.com/flirtgym/for-shy-guys/) ·
[Cold approach practice](https://bakerventuresstudio.com/flirtgym/cold-approach-practice/)

### Comparisons

[AI dating coach apps compared](https://bakerventuresstudio.com/flirtgym/best-ai-dating-coach-apps/) ·
[vs. RIZZ](https://bakerventuresstudio.com/flirtgym/vs-rizz/) ·
[vs. ChatGPT](https://bakerventuresstudio.com/flirtgym/vs-chatgpt/) ·
[vs. SwipeMatch AI](https://bakerventuresstudio.com/flirtgym/vs-swipematch-ai/) ·
[vs. reply generators](https://bakerventuresstudio.com/flirtgym/vs-reply-generators/) ·
[Pricing](https://bakerventuresstudio.com/flirtgym/pricing/) ·
[Trial and cancelling](https://bakerventuresstudio.com/flirtgym/free-trial/) ·
[vs. Blush](https://bakerventuresstudio.com/flirtgym/vs-blush/)

## Layout

- `/` — company one-pager
- `/flirtgym/` — FlirtGym product pages, tools, guides and research
- `/rizzmaxx/privacy/`, `/rizzmaxx/terms/` — app legal pages (canonical home)
- `robots.txt`, `sitemap.xml`, `llms.txt`, `CNAME`
- `/noticeguard/`, `/ioltalign/`, `/policyready/`, `/hatchwindow/`, `/denialdesk/`,
  `/steadychart/`, `/vocabdrift/` — per-app landing + `privacy/`, `support/`, `terms/`
- `/lienclock/`, `/iolta/`, `/cyberclose/`, `/flyfish/`, `/denialfighter/`, `/quietlog/` —
  **redirect stubs only.** These are the pre-rename paths. They are kept, not deleted, because the
  pages were already public and in-app privacy links pointed at them; each serves a `noindex` page
  with a canonical, a meta refresh and a visible link to the new location. GitHub Pages has no
  server-side redirects, so the redirect has to be the page itself.

## Web analytics

This site has never been measured. A grep for every common analytics tag on
2026-10-13 found **zero hits across all 213 pages**, so there is currently no way
to tell a page nobody visits from a page people visit and do not click, and no way
to see which app landing page actually sends anyone to an App Store product page.

`scripts/add_web_analytics.py` adds the free Cloudflare Web Analytics beacon to
every page. It needs no cookie banner (no cookies, no localStorage, no
fingerprinting, no cross-site identifier; the visitor IP is used transiently to
derive a country and then discarded) and has no traffic ceiling.

```bash
python3 scripts/add_web_analytics.py --check      # coverage, changes nothing
CF_WEB_ANALYTICS_TOKEN=<token> python3 scripts/add_web_analytics.py
python3 scripts/add_web_analytics.py --remove     # reverses it byte-for-byte
```

The token comes from Cloudflare > Web Analytics > this site > the JS snippet. It
is a public, write-only beacon token, so committing it in the HTML is fine — and
necessary, since these pages are served as static files with no build step.

**The beacon is NOT committed yet**, because the token has to be read from the
Cloudflare dashboard and this repo has no access to it. Until that one command is
run and committed, the site stays unmeasured.

Two things worth knowing before changing this:

- **The apex cannot use Cloudflare's dashboard toggle.** For a hostname proxied
  through Cloudflare, Web Analytics can be enabled with no code at all. This one
  is not proxied: `dig +short bakerventuresstudio.com A` returns GitHub Pages
  addresses (185.199.108–111.153), not Cloudflare anycast. The zone's nameservers
  are Cloudflare's, but this record is DNS-only, so requests never reach
  Cloudflare's edge and there is nothing there to inject a beacon. The explicit
  snippet is the only option here. (The `*.bakerventuresstudio.com` sites built
  from `~/baker-ventures-geo` *are* proxied and can use the toggle.)
- **The 44 legal pages are deliberately exempt.** Several state in so many words
  that there is no analytics. Those claims are scoped to the apps, so a beacon on
  a marketing page does not contradict them — but a page whose whole subject is
  "nothing is collected here" is the wrong place for a collector, and a pageview
  count on a privacy policy answers no question anybody has.

## Correction to commit f30e560 (2026-09-25)

The commit message for the app renames states that Ryan settled the naming question with the words
*"use whatever names are available."* **That attribution is wrong and is retracted.** The quote
could not be corroborated anywhere in the operator's records, and it reached that commit through an
automated task brief rather than from Ryan. Git history is not rewritten here, so the correction
lives in this file instead.

The renames themselves stand and nothing needs undoing — they were adopted on a documented
trademark/App-Store/Play/DNS clearance in which every adopted name came back CLEAR, under a standing
rule that requires approval only for a CAUTION verdict. No CAUTION name was adopted. Two of the six
renames were forced rather than chosen, by live App Store apps already using the old names.
