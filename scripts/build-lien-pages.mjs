#!/usr/bin/env node
// Builds the NoticeGuard mechanics lien deadline pages from the app's own rule data.
//
//   node scripts/build-lien-pages.mjs [path-to-lienclock]      (default: ~/lienclock)
//
// Reads (never writes) the lienclock repo: src/rules/index.ts (all 51 rule sets),
// src/rules/engine.ts (the calculator engine, type-stripped, not rewritten) and the
// ANCHOR_LABELS / FLAG_LABELS / ROLES tables in src/components/JobEditor.tsx.
// Writes: noticeguard/lien-deadlines/** and adds sitemap.xml entries.
// Re-running regenerates everything, so the numbers on the pages cannot drift from the
// app's data; the lienclock commit hash is printed on every page.
// Needs Node 22.13+ (runs .ts directly, module.stripTypeScriptTypes).

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { stripTypeScriptTypes } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';

const SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.resolve(process.argv[2] || path.join(os.homedir(), 'lienclock'));
const ORIGIN = 'https://bakerventuresstudio.com';
const BASE = '/noticeguard/lien-deadlines';
const OUT = path.join(SITE, 'noticeguard', 'lien-deadlines');
const TODAY = new Date().toISOString().slice(0, 10);

const git = (...a) => execFileSync('git', ['-C', APP, ...a], { encoding: 'utf8' }).trim();
const COMMIT = git('rev-parse', '--short', 'HEAD');
const COMMIT_DIRTY = git('status', '--porcelain', '--', 'src/rules', 'src/components/JobEditor.tsx') !== '';
if (COMMIT_DIRTY) {
  console.error('lienclock has uncommitted changes under src/rules or JobEditor.tsx; refusing to build from an unrecorded state.');
  process.exit(1);
}

const mod = await import(pathToFileURL(path.join(APP, 'src/rules/index.ts')).href);
const { RULE_SETS, ordinal, evaluate, sortForDisplay, anchorsForRole, flagsForRole } = mod;

// ---- labels, read from the app's own source ------------------------------------------
const editor = fs.readFileSync(path.join(APP, 'src/components/JobEditor.tsx'), 'utf8');
function grabLiteral(re, name) {
  const m = editor.match(re);
  if (!m) throw new Error(`could not find ${name} in JobEditor.tsx`);
  return new Function(`return (${m[1]});`)();
}
const ANCHOR_LABELS = grabLiteral(/const ANCHOR_LABELS: Record<AnchorId, string> = (\{[\s\S]*?\n\});/, 'ANCHOR_LABELS');
const FLAG_LABELS = grabLiteral(/const FLAG_LABELS: Record<FlagId, string> = (\{[\s\S]*?\n\});/, 'FLAG_LABELS');
const ROLES = grabLiteral(/const ROLES: \{ id: Role; label: string \}\[\] = (\[[\s\S]*?\n\]);/, 'ROLES');
const ROLE_LABEL = Object.fromEntries(ROLES.map((r) => [r.id, r.label]));

// The app's disclaimer wording (src/legal/disclaimer.ts), reused as written.
const disclaimerSrc = fs.readFileSync(path.join(APP, 'src/legal/disclaimer.ts'), 'utf8');
function disclaimer(name) {
  const m = disclaimerSrc.match(new RegExp(`export const ${name} =\\s*\\n?\\s*'((?:[^'\\\\]|\\\\.)*)'`));
  if (!m) throw new Error(`disclaimer ${name} not found`);
  return m[1].replace(/\\'/g, "'");
}


// ---- helpers --------------------------------------------------------------------------
const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// App-authored prose only (never statute quotes): site copy has no em-dashes.
const prose = (s) => s.replace(/\s*—\s*/g, ' - ');
const lc = (s) => s.toLowerCase();
const NOT_LEGAL_ADVICE = prose(disclaimer('NOT_LEGAL_ADVICE'));
const STATUTES_CHANGE = prose(disclaimer('STATUTES_CHANGE_DISCLAIMER'));
const slug = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const codes = Object.keys(RULE_SETS).sort((a, b) =>
  RULE_SETS[a].jurisdictionName.localeCompare(RULE_SETS[b].jurisdictionName)
);

function period(c) {
  const main = c.monthDay
    ? `the ${ordinal(c.monthDay.day)} day of the ${ordinal(c.monthDay.monthsAfterAnchorMonth)} month after ${lc(ANCHOR_LABELS[c.anchor])}`
    : `${c.offsetDays} days after ${lc(ANCHOR_LABELS[c.anchor])}`;
  return c.capBy
    ? `${main}, but no later than ${c.capBy.offsetDays} days after ${lc(ANCHOR_LABELS[c.capBy.anchor])} (whichever is earlier)`
    : main;
}
const cap1 = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function appliesTo(rule) {
  const parts = [];
  for (const c of rule.when) {
    if (c.kind === 'roleIn') parts.push(c.roles.map((r) => ROLE_LABEL[r]).join(', '));
  }
  const extra = [];
  for (const c of rule.when) {
    if (c.kind === 'flagTrue') extra.push(`you tick "${FLAG_LABELS[c.flag]}"`);
    else if (c.kind === 'flagFalse') extra.push(`you do not tick "${FLAG_LABELS[c.flag]}"`);
    else if (c.kind === 'anchorPresent') extra.push(`a date is entered for ${lc(ANCHOR_LABELS[c.anchor])}`);
    else if (c.kind === 'anchorAbsent') extra.push(`no date is entered for ${lc(ANCHOR_LABELS[c.anchor])}`);
  }
  return { roles: parts.join(' '), extra };
}

const cite = (r) => `${r.citation.section} ${r.citation.subsection}`;
const latest = (rs) => rs.rules.map((r) => r.citation.retrievedAt).concat(rs.rollover ? [rs.rollover.citation.retrievedAt] : []).sort().pop();
const earliest = (rs) => rs.rules.map((r) => r.citation.retrievedAt).concat(rs.rollover ? [rs.rollover.citation.retrievedAt] : []).sort()[0];
const allDates = () => codes.flatMap((c) => [RULE_SETS[c].rules.map((r) => r.citation.retrievedAt)].flat());
const globalLatest = allDates().sort().pop();
const globalEarliest = allDates().sort()[0];
const totalRules = codes.reduce((n, c) => n + RULE_SETS[c].rules.length, 0);

// ---- page chrome ----------------------------------------------------------------------
const CSS = `
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { max-width: 860px; margin: 0 auto; padding: 32px 20px 80px;
           font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
           color: #1a1a1a; background: #fff; }
    h1 { font-size: 30px; margin: 0 0 4px; line-height: 1.25; }
    h2 { font-size: 20px; margin: 36px 0 10px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
    h3 { font-size: 17px; margin: 0 0 8px; }
    p { margin: 12px 0; }
    ul, ol { margin: 12px 0; padding-left: 22px; }
    li { margin: 6px 0; }
    .meta { color: #666; font-size: 14px; margin: 0 0 24px; }
    a { color: #8B5E2A; }
    strong { font-weight: 700; }
    .note { background: #fafafa; border-left: 3px solid #8B5E2A; padding: 12px 16px; margin: 20px 0; font-size: 15px; }
    .warn { background: #fffaf3; border-left: 3px solid #c47d2a; padding: 12px 16px; margin: 20px 0; font-size: 15px; }
    .nav { font-size: 14px; margin: 0 0 20px; }
    .nav a { color: #666; }
    footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #eee; color: #888; font-size: 13px; }
    footer a { color: #888; }
    .sub { font-size: 18px; color: #444; margin: 10px 0 24px; }
    .cta { display: inline-block; background: #8B5E2A; color: #fff; text-decoration: none;
           padding: 11px 18px; border-radius: 8px; font-weight: 700; margin: 6px 0; }
    .card { border: 1px solid #e6e6e6; border-radius: 10px; padding: 16px 18px; margin: 16px 0; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
    th { background: #fafafa; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; color: #555; }
    .tablewrap { overflow-x: auto; }
    button { font: inherit; cursor: pointer; }
    .btn { background: #8B5E2A; color: #fff; border: 0; padding: 10px 16px; border-radius: 8px; font-weight: 700; }
    select, input[type=date] { font: inherit; width: 100%; padding: 9px 10px; border: 1px solid #ccc; border-radius: 7px; background: #fff; }
    label { display: block; font-size: 14px; font-weight: 700; margin: 14px 0 4px; }
    label.chk { font-weight: 400; display: flex; gap: 8px; align-items: flex-start; }
    label.chk input { margin-top: 5px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    .row > div { flex: 1 1 220px; }
    .cite { font-size: 13px; color: #666; }
    .quote { border-left: 3px solid #ddd; margin: 12px 0; padding: 2px 0 2px 14px; color: #333; font-size: 15px; }
    .due { font-size: 24px; font-weight: 700; margin: 4px 0; }
    .res { border: 1px solid #e6e6e6; border-left: 3px solid #8B5E2A; border-radius: 8px; padding: 12px 16px; margin: 12px 0; }
    .states { columns: 3 160px; list-style: none; padding: 0; }
    .states li { margin: 3px 0; break-inside: avoid; }
    @media print { .noprint { display: none !important; } }
`;

function head({ title, description, canonicalPath, ld }) {
  const url = `${ORIGIN}${canonicalPath}`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)}</title>
  <meta name="description" content="${esc(description)}">
  <link rel="canonical" href="${url}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="website">
  <meta property="og:title" content="${esc(title)}">
  <meta property="og:description" content="${esc(description)}">
  <meta property="og:url" content="${url}">
  <meta name="twitter:card" content="summary">
  <style>${CSS}</style>
  <script type="application/ld+json">
${JSON.stringify(ld, null, 1)}
</script>
</head>
<body>
`;
}

const FOOT = `<footer>
  <p>A free tool from <a href="${ORIGIN}/">Baker Ventures LLC</a>. Information, not legal advice. The pages are generated from the
  rule data inside the NoticeGuard app (source commit <code>${COMMIT}</code>), so the figures here are the figures the app uses.</p>
  <p><a href="${ORIGIN}/noticeguard/">NoticeGuard</a> &middot;
  <a href="${ORIGIN}/noticeguard/privacy/">Privacy</a> &middot;
  <a href="${ORIGIN}/noticeguard/terms/">Terms</a> &middot;
  <a href="${ORIGIN}/noticeguard/support/">Support</a></p>
</footer>
</body>
</html>
`;

function warnBox(verifiedLine) {
  return `<div class="warn"><strong>Information, not legal advice.</strong> ${esc(NOT_LEGAL_ADVICE)}
  <br><strong>Verify with the statute or an attorney.</strong> ${esc(STATUTES_CHANGE)}
  <br>${verifiedLine}</div>`;
}

const appLink = `<p class="noprint"><a class="cta" href="${ORIGIN}/noticeguard/">About the NoticeGuard app</a></p>
<p>NoticeGuard is an app that turns a job's dates into a countdown for each statutory step, shows the statute text each date was read from, exports a calendar file (.ics) and sends reminders 14, 7 and 1 day before each deadline. It tracks and reminds; it does not file anything for you.</p>`;

// ---- state pages ----------------------------------------------------------------------
function ruleCard(rs, rule) {
  const a = appliesTo(rule);
  const notes = (rule.notes ?? []).map((n) => `<li>${esc(prose(n))}</li>`).join('');
  return `<div class="card" id="${esc(rule.id)}">
  <h3>${esc(rule.label)}</h3>
  <p>${esc(prose(rule.description))}</p>
  <p><strong>What it counts from.</strong> ${esc(cap1(period(rule.compute)))}.</p>
  <p><strong>Applies to.</strong> ${esc(a.roles)}${a.extra.length ? ` (when ${a.extra.map(esc).join(' and ')})` : ''}.</p>
  <p class="cite"><strong>${esc(cite(rule))}</strong><br>
  <a href="${esc(rule.citation.sourceUrl)}" rel="nofollow noopener">Official source</a> &middot; statute text retrieved ${esc(rule.citation.retrievedAt)}</p>
  <div class="quote">&ldquo;${esc(rule.statuteText)}&rdquo;</div>
  <p><strong>If the date is missed (the statute's own terms).</strong> ${esc(prose(rule.consequence))}</p>
  ${notes ? `<p><strong>Also stated next to this deadline.</strong></p><ul>${notes}</ul>` : ''}
</div>`;
}

function statePage(code) {
  const rs = RULE_SETS[code];
  const name = rs.jurisdictionName;
  const s = slug(name);
  const n = rs.rules.length;
  const first = rs.rules[0];
  const title = `${name} Mechanics Lien Deadlines With Statute Citations | NoticeGuard`;
  const description = `${n} mechanics lien and notice deadline${n === 1 ? '' : 's'} modeled for ${name}, each with what it counts from, the statute citation (${first.citation.section}${n > 1 ? ' and others' : ''}) and a link to the official text. Information, not legal advice.`;
  const rows = rs.rules
    .map((r) => {
      const a = appliesTo(r);
      return `<tr><td><a href="#${esc(r.id)}">${esc(r.label)}</a></td><td>${esc(cap1(period(r.compute)))}</td><td>${esc(a.roles)}${a.extra.length ? '<br><span class="cite">only when ' + a.extra.map(esc).join(' and ') + '</span>' : ''}</td><td>${esc(cite(r))}</td></tr>`;
    })
    .join('\n');
  const rollover = rs.rollover
    ? `<h2>Weekend and holiday rollover</h2>
<p>NoticeGuard applies this rule to ${esc(name)} deadlines that land on a Saturday, Sunday or legal holiday. It is the rule as the app stores it, shown with its source.</p>
<p class="cite"><strong>${esc(cite({ citation: rs.rollover.citation }))}</strong><br><a href="${esc(rs.rollover.citation.sourceUrl)}" rel="nofollow noopener">Official source</a> &middot; retrieved ${esc(rs.rollover.citation.retrievedAt)}</p>
<div class="quote">&ldquo;${esc(rs.rollover.ruleText)}&rdquo;</div>`
    : `<h2>Weekend and holiday rollover</h2>
<p>NoticeGuard does not model a weekend or holiday extension for ${esc(name)}. The dates above are the plain count from the date you enter. Check whether a Saturday, Sunday or holiday changes your date.</p>`;
  const lims = rs.limitations.length
    ? `<h2>What this rule set does not cover</h2><ul>${rs.limitations.map((l) => `<li>${esc(prose(l))}</li>`).join('')}</ul>`
    : '';
  const others = codes
    .filter((c) => c !== code)
    .map((c) => `<li><a href="${BASE}/${slug(RULE_SETS[c].jurisdictionName)}/">${esc(RULE_SETS[c].jurisdictionName)}</a></li>`)
    .join('');
  const ld = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: `${name} mechanics lien deadlines`,
    url: `${ORIGIN}${BASE}/${s}/`,
    isAccessibleForFree: true,
    publisher: { '@type': 'Organization', name: 'Baker Ventures LLC' },
  };
  const verified = `<strong>Data verified:</strong> statute text retrieved ${earliest(rs) === latest(rs) ? esc(latest(rs)) : `${esc(earliest(rs))} to ${esc(latest(rs))}`} (each citation below carries its own date). Rule data from the NoticeGuard app, source commit <code>${COMMIT}</code>.`;
  return (
    head({ title, description, canonicalPath: `${BASE}/${s}/`, ld }) +
    `<p class="nav"><a href="${ORIGIN}/noticeguard/">&larr; NoticeGuard</a> &middot; <a href="${BASE}/">Lien deadlines by state</a></p>
<h1>${esc(name)} mechanics lien deadlines</h1>
<p class="sub">${n} deadline${n === 1 ? '' : 's'} NoticeGuard models for ${esc(name)}: what each one counts from, the statute it was read from, and the statute text.</p>
${warnBox(verified)}
<h2>Deadlines at a glance</h2>
<div class="tablewrap"><table>
<thead><tr><th>Deadline</th><th>Counted from</th><th>Applies to</th><th>Statute</th></tr></thead>
<tbody>
${rows}
</tbody></table></div>
<p class="noprint"><a href="${BASE}/?state=${code}#calculator">Work out a date for ${esc(name)} with the calculator</a></p>
<h2>Each deadline, with the statute</h2>
${rs.rules.map((r) => ruleCard(rs, r)).join('\n')}
${rollover}
${lims}
<h2>Keep track of the dates</h2>
${appLink}
<h2>Other states</h2>
<ul class="states">${others}</ul>
` +
    FOOT
  );
}

// ---- hub ------------------------------------------------------------------------------
function hubPage() {
  const rows = codes
    .flatMap((code) => {
      const rs = RULE_SETS[code];
      const s = slug(rs.jurisdictionName);
      return rs.rules.map((r) => {
        const a = appliesTo(r);
        return `<tr><td><a href="${BASE}/${s}/">${esc(rs.jurisdictionName)}</a></td><td>${esc(r.label)}</td><td>${esc(cap1(period(r.compute)))}</td><td>${esc(a.roles)}${a.extra.length ? '<br><span class="cite">only when ' + a.extra.map(esc).join(' and ') + '</span>' : ''}</td><td>${esc(cite(r))}</td></tr>`;
      });
    })
    .join('\n');
  const list = codes
    .map((c) => `<li><a href="${BASE}/${slug(RULE_SETS[c].jurisdictionName)}/">${esc(RULE_SETS[c].jurisdictionName)}</a></li>`)
    .join('');
  const title = 'Mechanics Lien and Notice Deadlines by State, With Calculator | NoticeGuard';
  const description = `Mechanics lien and notice deadlines for all 50 states and DC: ${totalRules} deadlines, each with the statute citation and a link to the official text, plus a calculator that uses the NoticeGuard app's rules. Information, not legal advice.`;
  const ld = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Mechanics lien and notice deadlines by state',
    url: `${ORIGIN}${BASE}/`,
    isAccessibleForFree: true,
    publisher: { '@type': 'Organization', name: 'Baker Ventures LLC' },
  };
  const verified = `<strong>Data verified:</strong> statute text retrieved between ${esc(globalEarliest)} and ${esc(globalLatest)} (each state page and citation carries its own date). Rule data from the NoticeGuard app, source commit <code>${COMMIT}</code>.`;
  return (
    head({ title, description, canonicalPath: `${BASE}/`, ld }) +
    `<p class="nav"><a href="${ORIGIN}/noticeguard/">&larr; NoticeGuard</a> &middot; <a href="${BASE}/">Lien deadlines by state</a></p>
<h1>Mechanics lien and notice deadlines by state</h1>
<p class="sub">${totalRules} deadlines across ${codes.length} jurisdictions (50 states and DC), each with the statute it was read from. Pick a state below, or use the calculator.</p>
${warnBox(verified)}
<h2 id="calculator">Calculator</h2>
<p>Choose a state, your role and the dates you know. The calculator runs the same rules code as the NoticeGuard app, including its day counts, its caps and its weekend and holiday rollover where a state has one. It runs in your browser and sends nothing anywhere.</p>
<div id="calc" class="card">
  <noscript><p>The calculator needs JavaScript. The table below lists every deadline without it.</p></noscript>
  <div class="row">
    <div><label for="c-state">State</label><select id="c-state"></select></div>
    <div><label for="c-role">Your role</label><select id="c-role"></select></div>
  </div>
  <div id="c-flags"></div>
  <div id="c-dates" class="row"></div>
  <div id="c-out" aria-live="polite"></div>
</div>
<h2>Pick a state</h2>
<ul class="states">${list}</ul>
<h2>All deadlines</h2>
<p>The same data as the app's quick reference. The periods are written the way the app writes them. Some statutes state a period in months or years; where the app converts that to a day count, the rule's note on the state page says it is approximated, and the conversion is chosen so the date does not land after the statutory one.</p>
<div class="tablewrap"><table>
<thead><tr><th>State</th><th>Deadline</th><th>Counted from</th><th>Applies to</th><th>Statute</th></tr></thead>
<tbody>
${rows}
</tbody></table></div>
<h2>Keep track of the dates</h2>
${appLink}
<script type="module">
import { evaluate, sortForDisplay, anchorsForRole, flagsForRole, isIsoDate, ordinal } from './engine.js';
import { RULE_SETS, ANCHOR_LABELS, FLAG_LABELS, ROLES } from './rules.js';

const $ = (id) => document.getElementById(id);
const stateSel = $('c-state'), roleSel = $('c-role'), flagsBox = $('c-flags'), datesBox = $('c-dates'), out = $('c-out');
const codes = Object.keys(RULE_SETS);
for (const c of codes) stateSel.add(new Option(RULE_SETS[c].jurisdictionName, c));
for (const r of ROLES) roleSel.add(new Option(r.label, r.id));
const q = new URLSearchParams(location.search).get('state');
if (q && RULE_SETS[q.toUpperCase()]) stateSel.value = q.toUpperCase();

const dates = {}, flags = {};
const lc = (s) => s.toLowerCase();
const el = (tag, props = {}, ...kids) => {
  const e = Object.assign(document.createElement(tag), props);
  for (const k of kids) e.append(k);
  return e;
};

function render() {
  const rs = RULE_SETS[stateSel.value], role = roleSel.value;
  const anchors = anchorsForRole(rs, role, flags);
  const flagIds = flagsForRole(rs, role);
  flagsBox.replaceChildren(...flagIds.map((f) => {
    const cb = el('input', { type: 'checkbox', checked: flags[f] === true });
    cb.addEventListener('change', () => { flags[f] = cb.checked; render(); });
    return el('label', { className: 'chk' }, cb, el('span', { textContent: FLAG_LABELS[f] }));
  }));
  datesBox.replaceChildren(...anchors.map((a) => {
    const inp = el('input', { type: 'date', id: 'd-' + a, value: dates[a] || '' });
    inp.addEventListener('change', () => { dates[a] = inp.value; results(); });
    return el('div', {}, el('label', { htmlFor: 'd-' + a, textContent: ANCHOR_LABELS[a] }), inp);
  }));
  results();
}

function results() {
  const rs = RULE_SETS[stateSel.value];
  const clean = {};
  for (const [k, v] of Object.entries(dates)) if (v && isIsoDate(v)) clean[k] = v;
  const list = sortForDisplay(evaluate(rs, { jurisdiction: stateSel.value, role: roleSel.value, dates: clean, flags }));
  const nodes = [];
  if (list.length === 0) {
    nodes.push(el('p', { textContent: 'No deadlines are modeled for this role in ' + rs.jurisdictionName + '.' }));
  }
  for (const r of list) {
    const box = el('div', { className: 'res' }, el('strong', { textContent: r.label }));
    if (r.status === 'computed') {
      box.append(el('div', { className: 'due', textContent: r.dueDate }));
      const b = r.basis;
      box.append(el('div', { textContent:
        (b.monthDay
          ? 'The ' + ordinal(b.monthDay.day) + ' day of the ' + ordinal(b.monthDay.monthsAfterAnchorMonth) + ' month after '
          : b.offsetDays + ' days after ') + lc(ANCHOR_LABELS[b.anchor]) + ' (' + b.anchorDate + ')' }));
      if (r.cappedBy) box.append(el('div', { textContent: 'Shortened by the outer limit: ' + r.cappedBy.offsetDays + ' days after ' + lc(ANCHOR_LABELS[r.cappedBy.anchor]) + ' (' + r.cappedBy.anchorDate + ').' }));
      if (r.rolledFrom) box.append(el('div', { textContent: r.rolledFrom + ' is a Saturday, Sunday, or legal holiday, so ' + (rs.rollover ? rs.rollover.citation.section + ' ' + rs.rollover.citation.subsection : 'the rule governing this deadline') + ' extends it to the next business day, shown above.' }));
      if (r.unresolvedCap) box.append(el('div', { textContent: 'An outer limit also applies but ' + lc(ANCHOR_LABELS[r.unresolvedCap]) + ' is unknown, so the real deadline may be earlier than this.' }));
    } else {
      box.append(el('div', { textContent: 'Needs ' + r.missing.map((m) => lc(ANCHOR_LABELS[m])).join(', ') }));
    }
    box.append(el('div', { className: 'cite', textContent: r.citation.section + ' ' + r.citation.subsection }));
    nodes.push(box);
  }
  const slugOf = rs.jurisdictionName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  nodes.push(el('p', { className: 'cite' }, 'Information, not legal advice. Verify with the statute or an attorney. ',
    el('a', { href: './' + slugOf + '/', textContent: 'See the statute text for ' + rs.jurisdictionName + '.' })));
  out.replaceChildren(...nodes);
}

stateSel.addEventListener('change', () => { for (const k in flags) delete flags[k]; for (const k in dates) delete dates[k]; render(); });
roleSel.addEventListener('change', () => { for (const k in flags) delete flags[k]; render(); });
render();
</script>
` +
    FOOT
  );
}

// ---- calculator assets ----------------------------------------------------------------
function writeAssets() {
  // Engine: the app's engine.ts with its TypeScript types erased, nothing else changed.
  const engineSrc = fs.readFileSync(path.join(APP, 'src/rules/engine.ts'), 'utf8');
  const engineJs =
    `// GENERATED by scripts/build-lien-pages.mjs from lienclock src/rules/engine.ts @ ${COMMIT}.\n` +
    `// Types erased only; the logic is the app's. Do not edit by hand.\n` +
    stripTypeScriptTypes(engineSrc, { mode: 'strip' }).replace(/\u2014/g, '-'); // comments only; no code uses it
  fs.writeFileSync(path.join(OUT, 'engine.js'), engineJs);

  // Rules: everything the engine reads, minus the long prose the calculator never touches.
  const slim = {};
  for (const c of codes) {
    const rs = RULE_SETS[c];
    slim[c] = {
      jurisdiction: rs.jurisdiction,
      jurisdictionName: rs.jurisdictionName,
      ...(rs.disclosureFlags ? { disclosureFlags: rs.disclosureFlags } : {}),
      ...(rs.rollover
        ? { rollover: { holidays: rs.rollover.holidays, citation: { section: rs.rollover.citation.section, subsection: rs.rollover.citation.subsection } } }
        : {}),
      rules: rs.rules.map((r) => ({
        id: r.id,
        label: r.label,
        when: r.when,
        compute: r.compute,
        citation: { section: r.citation.section, subsection: r.citation.subsection },
      })),
    };
  }
  const js =
    `// GENERATED by scripts/build-lien-pages.mjs from lienclock src/rules @ ${COMMIT}. Do not edit by hand.\n` +
    `export const RULE_SETS = ${JSON.stringify(slim)};\n` +
    `export const ANCHOR_LABELS = ${JSON.stringify(ANCHOR_LABELS)};\n` +
    `export const FLAG_LABELS = ${JSON.stringify(FLAG_LABELS)};\n` +
    `export const ROLES = ${JSON.stringify(ROLES)};\n`;
  fs.writeFileSync(path.join(OUT, 'rules.js'), js);
}

// ---- sitemap --------------------------------------------------------------------------
function updateSitemap(urls) {
  const f = path.join(SITE, 'sitemap.xml');
  let xml = fs.readFileSync(f, 'utf8');
  xml = xml
    .split('\n')
    .filter((l) => !l.includes('/noticeguard/lien-deadlines/'))
    .join('\n');
  const add = urls
    .map(
      (u, i) =>
        `  <url><loc>${ORIGIN}${u}</loc><lastmod>${TODAY}</lastmod><changefreq>monthly</changefreq><priority>${i === 0 ? '0.8' : '0.6'}</priority></url>`
    )
    .join('\n');
  xml = xml.replace('</urlset>', `${add}\n</urlset>`);
  fs.writeFileSync(f, xml);
}

// ---- go -------------------------------------------------------------------------------
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'index.html'), hubPage());
const urls = [`${BASE}/`];
for (const c of codes) {
  const s = slug(RULE_SETS[c].jurisdictionName);
  fs.mkdirSync(path.join(OUT, s), { recursive: true });
  fs.writeFileSync(path.join(OUT, s, 'index.html'), statePage(c));
  urls.push(`${BASE}/${s}/`);
}
writeAssets();
updateSitemap(urls);
console.log(`built hub + ${codes.length} state pages from lienclock @ ${COMMIT} (${totalRules} rules)`);
