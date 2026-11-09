#!/usr/bin/env python3
"""MK-2 static acceptance check. Optional local HTTP check: --server http://127.0.0.1:8322"""
from pathlib import Path
import argparse, json, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parent.parent
NEW = ['hatchwindow/rivers/', 'hatchwindow/rivers/san-juan-nm/', 'hatchwindow/rivers/animas-durango-co/', 'hatchwindow/rivers/gunnison-black-canyon-co/', 'hatchwindow/rivers/roaring-fork-glenwood-co/', 'hatchwindow/rivers/snake-moran-wy/', 'rigsheet/deposit-policy-templates/', 'hormonelog/visit-packet/', 'ioltalign/three-way-reconciliation/']
p = argparse.ArgumentParser();p.add_argument('--server');args=p.parse_args()
errors=[];titles=set();descs=set();site=ET.parse(ROOT/'sitemap.xml');urls={e.text for e in site.iter() if e.tag.endswith('}loc')}
files=set(ROOT/route/'index.html' for route in NEW)
files.update((ROOT/'noticeguard/lien-deadlines').glob('*/index.html'))
files.update(ROOT/route for route in ['hatchwindow/index.html','noticeguard/index.html','noticeguard/lien-deadlines/index.html','rigsheet/index.html','rigsheet/tools/index.html','rigsheet/job-price-calculator/index.html','hormonelog/index.html','ioltalign/index.html','policyready/index.html','policyready/cyber-readiness-checklist/index.html','policyready/readiness-self-check/index.html'])
for f in sorted(files):
 s=f.read_text();route='/'+str(f.parent.relative_to(ROOT))+'/'
 if args.server:
  try:
   with urllib.request.urlopen(args.server.rstrip('/')+route,timeout=10) as response:
    if response.status!=200 or response.read().decode()!=s:errors.append(f'{route}: HTTP/body mismatch')
  except Exception as e:errors.append(f'{route}: {e}')
 for target in re.findall(r'href=["\']([^"\']+)',s):
  u=urllib.parse.urlparse(target)
  if u.scheme or target.startswith('#'):continue
  dest=ROOT/urllib.parse.unquote(u.path.lstrip('/')) if target.startswith('/') else f.parent/urllib.parse.unquote(u.path)
  if dest.is_dir():dest=dest/'index.html'
  if not dest.exists():errors.append(f'{route}: missing {target}')
 for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',s,re.S):
  try:json.loads(block)
  except ValueError:errors.append(f'{route}: invalid JSON-LD')
 if route.lstrip('/') in NEW:
  title=re.search(r'<title>(.*?)</title>',s);desc=re.search(r'<meta name="description" content="([^"]+)"',s)
  if not title or title[1] in titles:errors.append(f'{route}: missing/duplicate title')
  if not desc or desc[1] in descs:errors.append(f'{route}: missing/duplicate description')
  if title:titles.add(title[1])
  if desc:descs.add(desc[1])
  if 'SoftwareApplication' not in s:errors.append(f'{route}: missing SoftwareApplication')
  if 'https://bakerventuresstudio.com'+route not in urls:errors.append(f'{route}: missing sitemap entry')
 if 'hatchwindow' not in route and ('apps.apple.com' in s or re.search(r'download now|download on the app store',s,re.I)):errors.append(f'{route}: unreleased App Store CTA')
 if '/noticeguard/lien-deadlines/' in route and route!='/noticeguard/lien-deadlines/':
  if not all(x in s for x in ['Coming soon','not legal advice','retrieved','Official source','/noticeguard/lien-deadlines/']):errors.append(f'{route}: missing state-page context')
print(json.dumps({'checked_pages':len(files),'new_pages':len(NEW),'errors':errors},indent=2))
raise SystemExit(bool(errors))
