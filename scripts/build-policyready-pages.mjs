#!/usr/bin/env node
// Builds the PolicyReady free tools from the app's own control registry.
//
//   node scripts/build-policyready-pages.mjs [path-to-cyberclose]      (default: ~/cyberclose)
//
// Reads (never writes) the cyberclose repo:
//   src/controls/registry.ts          the 50 controls
//   src/controls/types.ts             category labels
//   src/controls/cpgGoals.fixture.ts  the 34 pinned CISA CPG 2.0 goals with official titles
//   src/scoring/score.ts              computeReadiness (the app's scoring function)
// Writes: policyready/cyber-readiness-checklist/**, policyready/readiness-self-check/** and sitemap.xml entries.
// The browser self-check runs the app's own scoring code with its TypeScript types erased
// (only the relative import specifiers are repointed). Before finishing, the generated JS is run
// against the TypeScript original over thousands of generated answer sets; any mismatch aborts.
// The cyberclose commit hash is printed on every page. Needs Node 22.13+.

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { stripTypeScriptTypes } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.resolve(process.argv[2] || path.join(os.homedir(), 'cyberclose'));
const ORIGIN = 'https://bakerventuresstudio.com';
const HUB = '/policyready/cyber-readiness-checklist';
const CHECK = '/policyready/readiness-self-check';
const TODAY = new Date().toISOString().slice(0, 10);

const git = (...a) => execFileSync('git', ['-C', APP, ...a], { encoding: 'utf8' }).trim();
const COMMIT = git('rev-parse', '--short', 'HEAD');
if (git('status', '--porcelain', '--', 'src/controls', 'src/scoring') !== '') {
  console.error('cyberclose has uncommitted changes under src/controls or src/scoring; refusing to build from an unrecorded state.');
  process.exit(1);
}

const url = (p) => pathToFileURL(path.join(APP, p)).href;
const { CONTROLS } = await import(url('src/controls/registry.ts'));
const { CONTROL_CATEGORY_LABELS } = await import(url('src/controls/types.ts'));
const { CPG_2_0_GOALS, parseCpgCitations, normalizeGoalTitle } = await import(url('src/controls/cpgGoals.fixture.ts'));
const { computeReadiness } = await import(url('src/scoring/score.ts'));

const fixtureSrc = fs.readFileSync(path.join(APP, 'src/controls/cpgGoals.fixture.ts'), 'utf8');
const CPG_PDF = (fixtureSrc.match(/https:\/\/www\.cisa\.gov\/sites\/default\/files\/[^\s]+\.pdf/) || [])[0];
const CPG_PAGE = 'https://www.cisa.gov/cybersecurity-performance-goals-2-0-cpg-2-0';
const RETRIEVED = (fixtureSrc.match(/retrieved (\d{4}-\d{2}-\d{2})/) || [])[1];
assert(CPG_PDF && RETRIEVED, 'could not read CISA report URL / retrieval date from the fixture');
assert.equal(Object.keys(CPG_2_0_GOALS).length, 34, 'expected 34 pinned CPG goals');

// ---- helpers --------------------------------------------------------------------------
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// App-authored prose: site copy has no em-dashes, and the words this page must never use are softened.
const SOFTEN = [[/patch compliance/gi, 'patch status']];
const prose = (s) => {
  let t = s.replace(/\s*—\s*/g, ' - ');
  for (const [re, to] of SOFTEN) t = t.replace(re, to);
  return t;
};
const SMALL = new Set(['of', 'and', 'for', 'to', 'the', 'a', 'in', 'on', 'from', 'by', 'or', '&']);
function titleCase(upper) {
  return upper
    .toLowerCase()
    .split(' ')
    .map((w, i) => {
      if (w === 'mfa') return 'MFA';
      if (i > 0 && SMALL.has(w)) return w;
      return w.replace(/(^|[(/-])([a-z])/g, (m, p, c) => p + c.toUpperCase());
    })
    .join(' ');
}
const goalTitle = (code) => titleCase(CPG_2_0_GOALS[code]);

// Per control: CPG citations (validated against the pinned goals) and other framework references.
const CATEGORY_ORDER = Object.keys(CONTROL_CATEGORY_LABELS);
const info = new Map();
for (const c of CONTROLS) {
  const cpg = parseCpgCitations(c.sourceNote).map(({ code, title }) => {
    assert(CPG_2_0_GOALS[code], `${c.id}: cites unknown CPG goal ${code}`);
    if (title) assert.equal(normalizeGoalTitle(title), normalizeGoalTitle(CPG_2_0_GOALS[code]), `${c.id}: ${code} title mismatch`);
    return { code, title: title ? title : goalTitle(code) };
  });
  const others = c.sourceNote.split(';').map((s) => s.trim()).filter((s) => !/\bCPG\s+[1-6]\.[A-Z]/.test(s));
  info.set(c.id, { cpg, others });
}
const withCpg = CONTROLS.filter((c) => info.get(c.id).cpg.length > 0).length;
const goalsCited = new Map();
for (const c of CONTROLS) for (const g of info.get(c.id).cpg) goalsCited.set(g.code, (goalsCited.get(g.code) || 0) + 1);

const byCat = CATEGORY_ORDER.map((cat) => ({ cat, label: CONTROL_CATEGORY_LABELS[cat], controls: CONTROLS.filter((c) => c.category === cat) })).filter((g) => g.controls.length);

// ---- page chrome ----------------------------------------------------------------------
const CSS = `
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { max-width: 860px; margin: 0 auto; padding: 32px 20px 80px;
           font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
           color: #1a1a1a; background: #fff; }
    h1 { font-size: 30px; margin: 0 0 4px; line-height: 1.25; }
    h2 { font-size: 20px; margin: 36px 0 10px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
    h3 { font-size: 17px; margin: 0 0 6px; }
    p { margin: 12px 0; }
    ul, ol { margin: 12px 0; padding-left: 22px; }
    li { margin: 6px 0; }
    a { color: #5B4B9E; }
    code { background: #f5f5f5; padding: 1px 5px; border-radius: 4px; font-size: 0.92em; }
    .meta { color: #666; font-size: 14px; margin: 0 0 24px; }
    .sub { font-size: 18px; color: #444; margin: 10px 0 24px; }
    .warn { background: #f7f5fc; border-left: 3px solid #5B4B9E; padding: 12px 16px; margin: 20px 0; font-size: 15px; }
    .nav { font-size: 14px; margin: 0 0 20px; }
    .nav a { color: #666; }
    .cta { display: inline-block; background: #5B4B9E; color: #fff; text-decoration: none; padding: 11px 18px; border-radius: 8px; font-weight: 700; margin: 6px 0; }
    .card { border: 1px solid #e6e6e6; border-radius: 10px; padding: 14px 18px; margin: 14px 0; }
    .card h3 { margin-top: 0; }
    .cite { font-size: 13px; color: #666; }
    .tag { display: inline-block; font-size: 12px; font-weight: 700; background: #efeaf9; color: #3d3170; border-radius: 5px; padding: 1px 7px; margin-right: 4px; }
    .w { font-size: 12px; color: #555; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
    th { background: #fafafa; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; color: #555; }
    .tablewrap { overflow-x: auto; }
    details { margin: 8px 0; }
    summary { cursor: pointer; font-weight: 700; font-size: 14px; }
    fieldset { border: 0; padding: 0; margin: 10px 0 0; display: flex; gap: 6px; flex-wrap: wrap; }
    fieldset label { display: inline-flex; align-items: center; gap: 5px; font-size: 14px; border: 1px solid #ccc; border-radius: 7px; padding: 5px 10px; cursor: pointer; }
    button { font: inherit; cursor: pointer; }
    .btn { background: #5B4B9E; color: #fff; border: 0; padding: 10px 16px; border-radius: 8px; font-weight: 700; }
    .btn.alt { background: #fff; color: #5B4B9E; border: 1px solid #5B4B9E; }
    .score { font-size: 40px; font-weight: 700; margin: 4px 0; }
    .bar { background: #eee; border-radius: 6px; height: 10px; overflow: hidden; margin: 4px 0 10px; }
    .bar > span { display: block; height: 100%; background: #5B4B9E; }
    .goals { columns: 2 280px; list-style: none; padding: 0; }
    .goals li { break-inside: avoid; font-size: 14px; }
    footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #eee; color: #888; font-size: 13px; }
    footer a { color: #888; }
    @media print { .noprint { display: none !important; } }
`;

function head({ title, description, canonicalPath, ld }) {
  const u = `${ORIGIN}${canonicalPath}`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)}</title>
  <meta name="description" content="${esc(description)}">
  <link rel="canonical" href="${u}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="website">
  <meta property="og:title" content="${esc(title)}">
  <meta property="og:description" content="${esc(description)}">
  <meta property="og:url" content="${u}">
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
  <p>A free tool from <a href="${ORIGIN}/">Baker Ventures LLC</a>. A readiness self-check, not a security audit, certification or compliance determination.
  Generated from the control registry inside the PolicyReady app (source commit <code>${COMMIT}</code>), so the controls and the scoring here are the app's.</p>
  <p><a href="${ORIGIN}/policyready/">PolicyReady</a> &middot;
  <a href="${ORIGIN}/policyready/privacy/">Privacy</a> &middot;
  <a href="${ORIGIN}/policyready/terms/">Terms</a> &middot;
  <a href="${ORIGIN}/policyready/support/">Support</a></p>
</footer>
</body>
</html>
`;

const WARN = `<div class="warn"><strong>A readiness self-check, not an audit.</strong> This is a structured self-report against published guidance. It is not a security audit, a penetration test, a certification or a compliance determination, and nothing here promises a particular insurance outcome. Underwriting is each insurer's decision, made on that insurer's own application. For coverage questions talk to a licensed broker; for security work, to your IT or security lead.</div>`;

const SOURCES = `<h2>Sources</h2>
<ul>
  <li>CISA, <a href="${CPG_PAGE}" rel="noopener">Cross-Sector Cybersecurity Performance Goals (CPG 2.0)</a>, the official listing.</li>
  <li>CISA, <a href="${esc(CPG_PDF)}" rel="noopener">Cross-Sector Cybersecurity Performance Goals, Version 2.0 (PDF report)</a>. The goal codes and titles on these pages are the report's, 34 goals, retrieved ${RETRIEVED}. CISA's web listing words a few goals differently from the report; the report's wording is used here.</li>
  <li>Where a control also cites NIST Cybersecurity Framework 2.0, CIS Critical Security Controls v8 or an FBI IC3 report, that reference is shown on the control as the app records it.</li>
</ul>`;

const appLink = `<p class="noprint"><a class="cta" href="${ORIGIN}/policyready/">About the PolicyReady app</a></p>
<p>PolicyReady is an app that walks a small business through these same controls, ranks the gaps and exports a readiness summary. This page is a free, no-signup version of the idea; nothing here is sent anywhere.</p>
<p><strong>PolicyReady is not released.</strong> It is in App Store review as of ${TODAY}, so you cannot install it yet. This page works now and does not need it.</p>`;

// ---- hub: the checklist ---------------------------------------------------------------
function controlCard(c) {
  const i = info.get(c.id);
  const tags = i.cpg.map((g) => `<span class="tag">CPG ${esc(g.code)}</span>`).join('');
  const cpgLine = i.cpg.length
    ? `<p class="cite"><strong>CISA CPG 2.0:</strong> ${i.cpg.map((g) => `${esc(g.code)} ${esc(g.title)}`).join('; ')}. <a href="${CPG_PAGE}" rel="noopener">CISA's CPG page</a></p>`
    : `<p class="cite"><strong>CISA CPG 2.0:</strong> the app cites no CPG goal for this control. It is grounded in ${esc(prose(i.others.join('; ')))}.</p>`;
  const otherLine = i.cpg.length && i.others.length ? `<p class="cite">Also referenced: ${esc(prose(i.others.join('; ')))}.</p>` : '';
  return `<div class="card" id="${esc(c.id)}">
  <h3>${tags}${esc(c.title)} <span class="w">(weight ${c.weight} of 3)</span></h3>
  <p><strong>The question:</strong> ${esc(prose(c.question))}</p>
  <p>${esc(prose(c.explanation))}</p>
  ${cpgLine}${otherLine}
  <details><summary>Why insurers ask, and steps to close the gap</summary>
  <p><strong>Why it is asked.</strong> ${esc(prose(c.whyInsurersAsk))}</p>
  <ul>${c.howToSatisfy.map((s) => `<li>${esc(prose(s))}</li>`).join('')}</ul>
  </details>
</div>`;
}

function hubPage() {
  const title = 'Small Business Cybersecurity Checklist Mapped to CISA CPG 2.0 | PolicyReady';
  const description = `A free ${CONTROLS.length}-control cybersecurity readiness checklist for small businesses in ${byCat.length} categories, each tied to its CISA Cross-Sector Cybersecurity Performance Goals (CPG 2.0) code and official title. A self-check, not an audit.`;
  const ld = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Small business cybersecurity readiness checklist mapped to CISA CPG 2.0',
    url: `${ORIGIN}${HUB}/`,
    isAccessibleForFree: true,
    publisher: { '@type': 'Organization', name: 'Baker Ventures LLC' },
  };
  const toc = byCat.map((g) => `<li><a href="#${g.cat}">${esc(g.label)}</a> (${g.controls.length})</li>`).join('');
  const goalRows = [...goalsCited.keys()].sort().map((code) => `<tr><td>${esc(code)}</td><td>${esc(goalTitle(code))}</td><td>${goalsCited.get(code)}</td></tr>`).join('\n');
  return (
    head({ title, description, canonicalPath: `${HUB}/`, ld }) +
    `<p class="nav"><a href="${ORIGIN}/policyready/">&larr; PolicyReady</a> &middot; <a href="${CHECK}/">Take the self-check</a></p>
<h1>Small business cybersecurity checklist, mapped to CISA CPG 2.0</h1>
<p class="sub">${CONTROLS.length} controls insurers and security guidance commonly ask about, in ${byCat.length} groups. ${withCpg} of them cite a CISA Cross-Sector Cybersecurity Performance Goal by code and official title.</p>
${WARN}
<p class="noprint"><a class="cta" href="${CHECK}/">Score yourself against this checklist</a></p>
<h2>Groups</h2>
<ul>${toc}</ul>
<p>Each control shows the question as an insurance application would ask it, what it means in plain terms, the CISA goal it maps to (where the app cites one) and a weight from 1 to 3. The weight is how much the app counts the control when it scores readiness: heavier controls move the score more.</p>
${byCat.map((g) => `<h2 id="${g.cat}">${esc(g.label)}</h2>\n${g.controls.map(controlCard).join('\n')}`).join('\n')}
<h2>CISA goals these controls cite</h2>
<p>${goalsCited.size} of CISA's 34 CPG 2.0 goals are cited by at least one control above. CISA's full set has many more; this checklist is a small-business subset, not a replacement for the report.</p>
<div class="tablewrap"><table>
<thead><tr><th>Goal</th><th>Official title (CPG 2.0 report)</th><th>Controls citing it</th></tr></thead>
<tbody>
${goalRows}
</tbody></table></div>
${SOURCES}
<h2>Keep track of it</h2>
${appLink}
` +
    FOOT
  );
}

// ---- self-check page ------------------------------------------------------------------
function checkPage() {
  const title = 'Free Cybersecurity Readiness Self-Check for Small Business | PolicyReady';
  const description = `Answer ${CONTROLS.length} yes, partial or no questions and see a readiness score, a per-category breakdown and a ranked list of gaps, using the same scoring code as the PolicyReady app. Runs in your browser. A self-check, not an audit.`;
  const ld = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Cybersecurity readiness self-check for small business',
    url: `${ORIGIN}${CHECK}/`,
    isAccessibleForFree: true,
    publisher: { '@type': 'Organization', name: 'Baker Ventures LLC' },
  };
  return (
    head({ title, description, canonicalPath: `${CHECK}/`, ld }) +
    `<p class="nav"><a href="${ORIGIN}/policyready/">&larr; PolicyReady</a> &middot; <a href="${HUB}/">Full checklist with CISA goal codes</a></p>
<h1>Cybersecurity readiness self-check</h1>
<p class="sub">Answer for each control: Yes, Partial or No. The score and the ranked gap list update as you go.</p>
${WARN}
<p>How the score works, as the app computes it: each control has a weight of 1, 2 or 3. Yes earns the full weight, Partial earns half, No and unanswered earn nothing. The score is the weighted total as a percent, rounded. Gaps are listed heaviest first. It runs in your browser, stores nothing and sends nothing. The result is a self-reported estimate of where you stand; it says nothing about whether any insurer will offer coverage or at what terms.</p>
<div id="out" class="card" aria-live="polite">
  <noscript><p>The self-check needs JavaScript. The <a href="${HUB}/">full checklist</a> works without it.</p></noscript>
  <div class="score" id="score">0%</div>
  <div class="bar"><span id="bar" style="width:0%"></span></div>
  <p id="counts" class="cite"></p>
  <div id="cats"></div>
  <h3>Gaps to close next, heaviest first</h3>
  <ol id="gaps"></ol>
  <p class="noprint"><button class="btn alt" id="reset" type="button">Clear all answers</button></p>
</div>
<div id="qs"></div>
${SOURCES}
<h2>Keep track of it</h2>
${appLink}
<script type="module">
import { CONTROLS } from './controls.js';
import { CONTROL_CATEGORY_LABELS } from './types.js';
import { computeReadiness } from './score.js';

const $ = (id) => document.getElementById(id);
const answers = new Map();
const order = Object.keys(CONTROL_CATEGORY_LABELS);
const el = (tag, props = {}, ...kids) => {
  const e = Object.assign(document.createElement(tag), props);
  for (const k of kids) e.append(k);
  return e;
};

function build() {
  const root = $('qs');
  for (const cat of order) {
    const list = CONTROLS.filter((c) => c.category === cat);
    if (!list.length) continue;
    root.append(el('h2', { textContent: CONTROL_CATEGORY_LABELS[cat] }));
    for (const c of list) {
      const fs = el('fieldset');
      for (const [val, label] of [['yes', 'Yes'], ['partial', 'Partial'], ['no', 'No']]) {
        const r = el('input', { type: 'radio', name: 'q-' + c.id, value: val });
        r.addEventListener('change', () => { answers.set(c.id, val); update(); });
        fs.append(el('label', {}, r, document.createTextNode(label)));
      }
      const card = el('div', { className: 'card' },
        el('h3', { textContent: c.title }),
        el('p', { textContent: c.question }),
        el('details', {}, el('summary', { textContent: 'What this means' }), el('p', { textContent: c.explanation })),
        fs);
      root.append(card);
    }
  }
}

function update() {
  const list = [...answers].map(([controlId, status]) => ({ controlId, status, note: '', updatedAt: '' }));
  const r = computeReadiness(CONTROLS, list);
  $('score').textContent = r.scorePercent + '%';
  $('bar').style.width = r.scorePercent + '%';
  $('counts').textContent = r.inPlaceCount + ' yes, ' + r.partialCount + ' partial, ' + r.gapCount + ' no or unanswered, of ' + r.totalControls + ' controls.';
  $('cats').replaceChildren(...r.categories.map((c) => el('div', {},
    el('strong', { textContent: c.label + ': ' + c.scorePercent + '%' }),
    el('div', { className: 'bar' }, el('span', { style: 'width:' + c.scorePercent + '%' })))));
  $('gaps').replaceChildren(...r.gaps.map((g) => el('li', {},
    el('a', { href: '${HUB}/#' + g.control.id, textContent: g.control.title }),
    document.createTextNode(' (weight ' + g.control.weight + ', ' + (g.status === 'partial' ? 'partial' : g.status === 'no' ? 'no' : 'not answered') + ')'))));
}

$('reset').addEventListener('click', () => {
  answers.clear();
  for (const r of document.querySelectorAll('#qs input[type=radio]')) r.checked = false;
  update();
});
build();
update();
</script>
` +
    FOOT
  );
}

// ---- assets: the app's scoring code, types erased -------------------------------------
function strip(rel, repoint) {
  let src = stripTypeScriptTypes(fs.readFileSync(path.join(APP, rel), 'utf8'), { mode: 'strip' });
  for (const [from, to] of repoint) src = src.split(from).join(to);
  return `// GENERATED by scripts/build-policyready-pages.mjs from cyberclose ${rel} @ ${COMMIT}.\n// TypeScript types erased and import specifiers repointed only; the logic is the app's. Do not edit by hand.\n${src.replace(/—/g, '-')}`;
}
function writeAssets(dir) {
  fs.writeFileSync(path.join(dir, 'types.js'), strip('src/controls/types.ts', []));
  fs.writeFileSync(path.join(dir, 'controls.js'), strip('src/controls/registry.ts', [["'./types.ts'", "'./types.js'"]]));
  fs.writeFileSync(path.join(dir, 'score.js'), strip('src/scoring/score.ts', [["'../controls/types.ts'", "'./types.js'"]]));
}

// ---- parity: generated JS vs the TypeScript original ----------------------------------
async function parity(dir) {
  const js = await import(pathToFileURL(path.join(dir, 'score.js')).href + `?t=${Date.now()}`);
  const jsControls = (await import(pathToFileURL(path.join(dir, 'controls.js')).href + `?t=${Date.now()}`)).CONTROLS;
  // strip() makes exactly one declared cosmetic change to the app's strings: an em-dash
  // becomes a hyphen, because these strings are rendered onto the page and this site's copy
  // carries no em-dashes. So normalise the expected side by that same substitution before
  // comparing. The check stays meaningful - any other difference, structural or textual,
  // still fails. Without this it failed on the generator's own transform, which is why the
  // pages were written but the sitemap never was: the build exited before updateSitemap.
  const dashify = (v) =>
    typeof v === 'string' ? v.replace(/—/g, '-')
      : Array.isArray(v) ? v.map(dashify)
        : (v && typeof v === 'object')
          ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, dashify(x)]))
          : v;
  assert.deepEqual(JSON.parse(JSON.stringify(jsControls)), dashify(JSON.parse(JSON.stringify(CONTROLS))), 'generated controls.js differs from the registry');
  let seed = 20261013;
  const rnd = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const STATUSES = ['yes', 'no', 'partial', 'unanswered'];
  const ids = CONTROLS.map((c) => c.id);
  const sets = [];
  sets.push([CONTROLS, []]);
  for (const s of STATUSES) sets.push([CONTROLS, CONTROLS.map((c) => ({ controlId: c.id, status: s, note: '', updatedAt: '' }))]);
  sets.push([[], []]);
  while (sets.length < 20000) {
    const mode = rnd();
    const answers = [];
    const n = Math.floor(rnd() * (ids.length + 6));
    for (let k = 0; k < n; k++) {
      const status = mode < 0.1 && rnd() < 0.2 ? pick(['maybe', '', 'YES', null, 7]) : pick(STATUSES);
      const controlId = rnd() < 0.05 ? 'not-a-control' : pick(ids); // duplicates and unknown ids happen too
      answers.push({ controlId, status, note: rnd() < 0.3 ? 'n' + k : '', updatedAt: '' });
    }
    const controls = rnd() < 0.15 ? CONTROLS.filter(() => rnd() < 0.5) : CONTROLS;
    sets.push([controls, answers]);
  }
  let mismatches = 0;
  for (const [controls, answers] of sets) {
    const a = JSON.stringify(computeReadiness(controls, answers));
    const b = JSON.stringify(js.computeReadiness(controls, answers));
    if (a !== b) mismatches++;
  }
  return { cases: sets.length, mismatches };
}

// ---- sitemap --------------------------------------------------------------------------
function updateSitemap(urls) {
  const f = path.join(SITE, 'sitemap.xml');
  let xml = fs.readFileSync(f, 'utf8');
  xml = xml.split('\n').filter((l) => !urls.some((u) => l.includes(`<loc>${ORIGIN}${u}</loc>`))).join('\n');
  const add = urls.map((u, i) => `  <url><loc>${ORIGIN}${u}</loc><lastmod>${TODAY}</lastmod><changefreq>monthly</changefreq><priority>${i === 0 ? '0.7' : '0.6'}</priority></url>`).join('\n');
  fs.writeFileSync(f, xml.replace('</urlset>', `${add}\n</urlset>`));
}

// ---- go -------------------------------------------------------------------------------
const hubDir = path.join(SITE, 'policyready', 'cyber-readiness-checklist');
const checkDir = path.join(SITE, 'policyready', 'readiness-self-check');
for (const d of [hubDir, checkDir]) { fs.rmSync(d, { recursive: true, force: true }); fs.mkdirSync(d, { recursive: true }); }
fs.writeFileSync(path.join(hubDir, 'index.html'), hubPage());
fs.writeFileSync(path.join(checkDir, 'index.html'), checkPage());
writeAssets(checkDir);
const p = await parity(checkDir);
console.log(`parity: ${p.cases} answer sets, ${p.mismatches} mismatches`);
if (p.mismatches !== 0) { console.error('PARITY FAILED; not updating the sitemap.'); process.exit(1); }
updateSitemap([`${HUB}/`, `${CHECK}/`]);
console.log(`built checklist + self-check from cyberclose @ ${COMMIT} (${CONTROLS.length} controls, ${withCpg} with a CPG goal, ${goalsCited.size} goals cited)`);
