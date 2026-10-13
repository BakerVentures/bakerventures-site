// Generates the Hatch Window hatch-chart and river pages from the app's own data.
// Usage: node scripts/gen-hatchwindow-pages.mjs /path/to/flyfish
// Reads src/data/hatches.ts and src/data/spots.ts (read-only) and records the source commit on each page.
import { writeFileSync, mkdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const src = resolve(process.argv[2] || process.env.HOME + '/flyfish');
const { HATCH_DB, REGION_NAMES } = await import(pathToFileURL(join(src, 'src/data/hatches.ts')));
const { CURATED_SPOTS } = await import(pathToFileURL(join(src, 'src/data/spots.ts')));
const sh = (c) => execSync(c, { cwd: src }).toString().trim();
const commit = sh('git log -1 --format=%h -- src/data/hatches.ts src/data/spots.ts');
const out = resolve(new URL('..', import.meta.url).pathname);

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const WT = { tailwater: 'Tailwater', freestone: 'Freestone', 'spring-creek': 'Spring creek' };
const WT_ORDER = ['tailwater', 'freestone', 'spring-creek'];
const BASE = 'https://bakerventuresstudio.com';
const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const clean = (s) => String(s).replace(/\s*—\s*/g, ', ').replace(/\s*–\s*/g, '-');
const slug = (m) => MONTHS[m - 1].toLowerCase();
const regionList = (r) => r.map((x) => REGION_NAMES[x]).join('; ');

const CSS = `
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { max-width: 760px; margin: 0 auto; padding: 32px 20px 80px;
           font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
           color: #1a1a1a; background: #fff; }
    h1 { font-size: 30px; margin: 0 0 4px; line-height: 1.25; }
    h2 { font-size: 20px; margin: 36px 0 10px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
    h3 { font-size: 17px; margin: 24px 0 4px; }
    p { margin: 12px 0; }
    ul { margin: 12px 0; padding-left: 22px; }
    li { margin: 6px 0; }
    .meta { color: #666; font-size: 14px; margin: 0 0 24px; }
    a { color: #1F6F5C; }
    .note { background: #fafafa; border-left: 3px solid #1F6F5C; padding: 12px 16px; margin: 20px 0; font-size: 15px; }
    .warn { background: #fffaf3; border-left: 3px solid #c47d2a; padding: 12px 16px; margin: 20px 0; font-size: 15px; }
    .nav { font-size: 14px; margin: 0 0 20px; }
    .nav a { color: #666; }
    .sub { font-size: 18px; color: #444; margin: 10px 0 24px; }
    .cite { font-size: 13px; color: #666; }
    .latin { font-style: italic; color: #666; font-size: 14px; }
    .tags { font-size: 14px; color: #555; margin: 2px 0; }
    .grid { display: flex; flex-wrap: wrap; gap: 6px 14px; padding: 0; list-style: none; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 15px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }
    th { background: #fafafa; font-size: 13px; text-transform: uppercase; letter-spacing: .03em; color: #555; }
    footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #eee; color: #888; font-size: 13px; }
    footer a { color: #888; }
    @media (max-width: 560px) { th, td { padding: 6px 6px; font-size: 14px; } }`;

function page({ path, title, desc, nav, body, ld }) {
  const url = BASE + path;
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)}</title>
  <meta name="description" content="${esc(desc)}">
  <link rel="canonical" href="${url}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Hatch Window">
  <meta property="og:title" content="${esc(title)}">
  <meta property="og:description" content="${esc(desc)}">
  <meta property="og:url" content="${url}">
  <meta name="twitter:card" content="summary">
  <style>${CSS}
  </style>${ld ? `\n  <script type="application/ld+json">\n${JSON.stringify(ld, null, 1)}\n</script>` : ''}
</head>
<body>
  <div class="nav">${nav}</div>
${body}
  <div class="warn"><strong>Check local regulations.</strong> Seasons, gear rules, closures and access vary by water and change often. Check current regulations and conditions for the water you plan to fish, and carry a valid license.</div>
  <div class="note"><strong>About this page.</strong> Hatch timing varies by year, elevation and water temperature. Months here are typical ranges from the Hatch Window curated chart, a starting point and not a live report of what is hatching today. <a href="/hatchwindow/">Hatch Window</a> is a free fly-fishing companion app from Baker Ventures LLC with a built-in version of this chart, plus streamflow from USGS and weather from Open-Meteo. Data source: Hatch Window source files <code>src/data/hatches.ts</code> and <code>src/data/spots.ts</code>, commit <code>${commit}</code>.</p></div>
  <footer>&copy; Baker Ventures LLC &middot; <a href="/hatchwindow/">Hatch Window</a> &middot; <a href="/hatchwindow/hatch-chart/">Hatch chart</a> &middot; <a href="/hatchwindow/privacy/">Privacy Policy</a> &middot; <a href="/hatchwindow/terms/">Terms</a> &middot; <a href="/">Baker Ventures Studio</a></footer>
</body>
</html>
`.replace('</code>.</p></div>', '</code>.</div>');
  const dir = join(out, path);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, 'index.html'), html);
  return path;
}

const created = [];
const inMonth = (m) => HATCH_DB.filter((h) => h.months.includes(m));
const rangeText = (months) => {
  const runs = []; let s = months[0], p = months[0];
  for (const m of months.slice(1).concat([null])) {
    if (m !== p + 1) { runs.push(s === p ? MONTHS[s-1] : `${MONTHS[s-1]} to ${MONTHS[p-1]}`); s = m; }
    p = m;
  }
  return runs.join(', ');
};
const patt = (p) => `${esc(p.name)} (${esc(p.type)}, size ${esc(p.sizeRange)})`;

function hatchCard(h) {
  return `  <h3>${esc(h.insect)}</h3>
  ${h.latinName ? `<div class="latin">${esc(h.latinName)}</div>` : ''}
  <div class="tags">Typical months: ${rangeText(h.months)}. Water types: ${h.waterTypes.map((w) => WT[w]).join(', ')}. Regions: ${regionList(h.regions)}.</div>
  <ul>
${h.patterns.map((p) => `    <li>${patt(p)}</li>`).join('\n')}
  </ul>
  <p>${esc(clean(h.notes))}</p>`;
}

// Month pages
for (let m = 1; m <= 12; m++) {
  const list = inMonth(m);
  const name = MONTHS[m - 1];
  const prev = m === 1 ? 12 : m - 1, next = m === 12 ? 1 : m + 1;
  const byWT = WT_ORDER.map((w) => {
    const l = list.filter((h) => h.waterTypes.includes(w));
    return `    <li><strong>${WT[w]}:</strong> ${l.length ? l.map((h) => esc(h.insect)).join(', ') : 'no entries in the chart'}</li>`;
  }).join('\n');
  const body = `  <h1>What hatches in ${name}: flies and patterns</h1>
  <p class="sub">${list.length} entries in the Hatch Window curated chart are typically active in ${name}, with the fly patterns that match each.</p>
  <h2>By water type</h2>
  <ul>
${byWT}
  </ul>
  <h2>Hatches and matching patterns</h2>
${list.map(hatchCard).join('\n')}
  <p>Browse the neighbouring months: <a href="../${slug(prev)}/">${MONTHS[prev-1]}</a> &middot; <a href="../${slug(next)}/">${MONTHS[next-1]}</a> &middot; <a href="../">all months</a>.</p>`;
  created.push(page({
    path: `/hatchwindow/hatch-chart/${slug(m)}/`,
    title: `${name} Fly Fishing Hatch Chart: What's Hatching and What to Tie On | Hatch Window`,
    desc: `Typical ${name} hatches by water type (tailwater, freestone, spring creek) with matching dry, nymph and emerger patterns, from the Hatch Window curated chart.`,
    nav: `<a href="/hatchwindow/">Hatch Window</a> &rsaquo; <a href="../">Hatch chart</a> &rsaquo; ${name}`,
    body,
  }));
}

// Hub
{
  const rows = MONTHS.map((n, i) => {
    const l = inMonth(i + 1);
    return `    <tr><td><a href="${slug(i+1)}/">${n}</a></td><td>${l.map((h) => esc(h.insect)).join(', ')}</td></tr>`;
  }).join('\n');
  const wtSections = WT_ORDER.map((w) => {
    const r = MONTHS.map((n, i) => {
      const l = inMonth(i + 1).filter((h) => h.waterTypes.includes(w));
      return `    <tr><td>${n}</td><td>${l.map((h) => esc(h.insect)).join(', ')}</td></tr>`;
    }).join('\n');
    return `  <h3>${WT[w]}</h3>\n  <table>\n    <tr><th>Month</th><th>Hatches</th></tr>\n${r}\n  </table>`;
  }).join('\n');
  const west = CURATED_SPOTS;
  const body = `  <h1>Fly Fishing Hatch Chart by Month and Water Type</h1>
  <p class="sub">What is typically hatching, and which fly patterns match it. Generated from the curated chart inside the Hatch Window app: ${HATCH_DB.length} hatch entries covering ${Object.values(REGION_NAMES).join(', ')}.</p>
  <h2>Pick a month</h2>
  <table>
    <tr><th>Month</th><th>Typically active</th></tr>
${rows}
  </table>
  <h2>By water type</h2>
  <p>The chart tags each entry with the water types where it is commonly fished: tailwater, freestone or spring creek.</p>
${wtSections}
  <h2>Starter rivers</h2>
  <p>Hatch Window ships a starter list of well-known Western waters, each with a USGS gauge. Each page shows the gauge number, a link to the official USGS page, and the chart entries for that water type in the Mountain West.</p>
  <ul>
${west.map((s) => `    <li><a href="/hatchwindow/rivers/${s.id}/">${esc(s.name)}</a>, ${esc(s.state)}</li>`).join('\n')}
  </ul>
  <p>Want this chart on your phone? <a href="/hatchwindow/">See Hatch Window</a>.</p>`;
  created.push(page({
    path: '/hatchwindow/hatch-chart/',
    title: 'Fly Fishing Hatch Chart by Month and Water Type | Hatch Window',
    desc: 'A free hatch chart: what is typically hatching each month on tailwaters, freestone rivers and spring creeks, with matching fly patterns and sizes.',
    nav: `<a href="/hatchwindow/">Hatch Window</a> &rsaquo; Hatch chart`,
    body,
  }));
}

// River pages
for (const s of CURATED_SPOTS) {
  const list = HATCH_DB.filter((h) => h.regions.includes(s.region) && h.waterTypes.includes(s.waterType));
  const usgs = `https://waterdata.usgs.gov/monitoring-location/${s.usgsSiteNo}/`;
  const gaugeNote = /gauge/i.test(s.note) ? `\n  <p>${esc(clean(s.note))}</p>` : '';
  const body = `  <h1>${esc(s.name)}: USGS Gauge and Hatch Chart</h1>
  <p class="sub">${esc(s.state)} &middot; ${WT[s.waterType]} &middot; USGS site ${esc(s.usgsSiteNo)}</p>
  <h2>Gauge</h2>
  <p>Hatch Window's starter list uses USGS site <strong>${esc(s.usgsSiteNo)}</strong> for this water. Gauge coordinates: ${s.lat}, ${s.lng}. This page does not show live conditions. For current streamflow and gauge height, see the <a href="${usgs}" rel="noopener">official USGS page for site ${esc(s.usgsSiteNo)}</a>. USGS water data is provisional and may be revised.</p>${gaugeNote}
  <h2>Hatch chart entries tagged ${WT[s.waterType].toLowerCase()} in the Mountain West</h2>
  <p>These are the curated chart entries tagged for Mountain West waters and the ${WT[s.waterType].toLowerCase()} water type. They are general entries, not a report specific to this river.</p>
  <table>
    <tr><th>Hatch</th><th>Typical months</th><th>Patterns</th></tr>
${list.map((h) => `    <tr><td>${esc(h.insect)}</td><td>${rangeText(h.months)}</td><td>${h.patterns.map(patt).join('; ')}</td></tr>`).join('\n')}
  </table>
  <p>See also the <a href="/hatchwindow/hatch-chart/">full hatch chart</a>.</p>`;
  created.push(page({
    path: `/hatchwindow/rivers/${s.id}/`,
    title: `${s.name.replace(/ \(.*\)/, '')} USGS Gauge and Hatch Chart | Hatch Window`.replace(/\s+/g,' '),
    desc: `USGS gauge site ${s.usgsSiteNo} for the ${s.name} in ${s.state}, with a link to the official USGS page and typical ${WT[s.waterType].toLowerCase()} hatches and fly patterns.`,
    nav: `<a href="/hatchwindow/">Hatch Window</a> &rsaquo; <a href="/hatchwindow/hatch-chart/">Hatch chart</a> &rsaquo; ${esc(s.name.replace(/ \(.*\)/, ''))}`,
    body,
  }));
}
console.log(created.length, 'pages, source commit', commit);
