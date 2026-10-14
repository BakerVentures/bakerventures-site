# -*- coding: utf-8 -*-
import re, html as H, json
from html.parser import HTMLParser

PAGES = [
 ("index.html", "https://bakerventuresstudio.com/"),
 ("about/index.html", "https://bakerventuresstudio.com/about/"),
 ("apps/index.html", "https://bakerventuresstudio.com/apps/"),
 ("editorial-standards/index.html", "https://bakerventuresstudio.com/editorial-standards/"),
 ("questions-answered/index.html", "https://bakerventuresstudio.com/questions-answered/"),
]

def inline(frag):
    """HTML fragment -> markdown inline."""
    t = frag
    t = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: '[%s](%s)' % (m.group(2), m.group(1)), t, flags=re.S)
    t = re.sub(r'</?(strong|b)>', '**', t)
    t = re.sub(r'</?(em|i)>', '*', t)
    t = re.sub(r'<code>(.*?)</code>', r'`\1`', t, flags=re.S)
    t = re.sub(r'<br\s*/?>', ' ', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = H.unescape(t)
    t = re.sub(r'\*\*\s*\*\*', '', t)
    return re.sub(r'[ \t]+', ' ', t).strip()

def page_md(path):
    s = open(path, encoding='utf-8').read()
    title = inline(re.search(r'<title>(.*?)</title>', s, re.S).group(1))
    main = s[s.index('<main>'):s.index('</main>')]
    out = []
    # strip the cite + sources blocks: they are page furniture
    main = re.sub(r'<div class="cite">.*?</div>\s*', '', main, flags=re.S)
    stamp = re.search(r'<div class="stamp">(.*?)</div>', main, re.S)
    h1 = re.search(r'<h1>(.*?)</h1>', main, re.S)
    heading = inline(h1.group(1)) if h1 else title
    body = main
    # linear walk over the blocks we emit
    pat = re.compile(
        r'<h2[^>]*>(?P<h2>.*?)</h2>'
        r'|<h3[^>]*>(?P<h3>.*?)</h3>'
        r'|<div class="answer">(?P<answer>.*?)</div>'
        r'|<div class="restate">(?P<restate>.*?)</div>'
        r'|<div class="qa">(?P<qa>.*?)</div>'
        r'|<div class="cards">(?P<cards>.*?)</div>'
        r'|<div class="note">(?P<note>.*?)</div>'
        r'|<table>(?P<table>.*?)</table>'
        r'|<ul>(?P<ul>.*?)</ul>'
        r'|<ol>(?P<ol>.*?)</ol>'
        r'|<p>(?P<p>.*?)</p>'
        r'|<div class="srcs">(?P<srcs>.*?)</div>', re.S)
    seen_qa = False
    for m in pat.finditer(body):
        g = m.lastgroup
        v = m.group(g)
        if g == 'h2': out.append('\n## ' + inline(v))
        elif g == 'h3': out.append('\n### ' + inline(v))
        elif g == 'p': out.append(inline(v))
        elif g == 'answer':
            paras = [inline(x) for x in re.findall(r'<p>(.*?)</p>', v, re.S)]
            out.append(':::answer\n' + '\n\n'.join(paras) + '\n:::')
        elif g == 'restate':
            h = re.search(r'<h2[^>]*>(.*?)</h2>', v, re.S)
            if h: out.append('\n## ' + inline(h.group(1)))
            for x in re.findall(r'<p>(.*?)</p>', v, re.S): out.append(inline(x))
        elif g == 'qa':
            q = re.search(r'<h3[^>]*>(.*?)</h3>', v, re.S)
            a = [inline(x) for x in re.findall(r'<p>(.*?)</p>', v, re.S)]
            out.append('**%s** %s' % (inline(q.group(1)), ' '.join(a)))
        elif g == 'cards':
            for a in re.findall(r'<a class="card"[^>]*>(.*?)</a>', v, re.S):
                b = re.search(r'<b>(.*?)</b>', a, re.S); sp = re.search(r'<span>(.*?)</span>', a, re.S)
                out.append('- **%s** — %s' % (inline(b.group(1)) if b else '', inline(sp.group(1)) if sp else ''))
        elif g == 'note': 
            for x in re.findall(r'<p>(.*?)</p>', v, re.S): out.append('> ' + inline(x))
        elif g in ('ul','ol'):
            for li in re.findall(r'<li>(.*?)</li>', v, re.S): out.append('- ' + inline(li))
        elif g == 'table':
            head = [inline(x) for x in re.findall(r'<th[^>]*>(.*?)</th>', v, re.S)]
            rows = re.findall(r'<tr>(?:(?!</tr>).)*?<td.*?</tr>', v, re.S)
            if head:
                out.append('| ' + ' | '.join(head) + ' |')
                out.append('|' + '---|' * len(head))
            for r in rows:
                cells = [inline(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
                if cells: out.append('| ' + ' | '.join(cells) + ' |')
        elif g == 'srcs':
            items = [inline(x) for x in re.findall(r'<li>(.*?)</li>', v, re.S)]
            if items:
                out.append('\n### Sources')
                for it in items: out.append('- ' + it)
    md = ['## ' + heading, 'URL: ' + path_url(path), 'Updated: 2026-10-14', '']
    md += out
    return '\n'.join(x for x in md)

URLS = dict(PAGES)
def path_url(p): return URLS[p]

if __name__ == '__main__':
    parts = ['# Baker Ventures: full text', '',
      'Baker Ventures LLC is an independent software studio run by one person, building small, single-purpose iOS apps and developer tools. '
      'Published by Baker Ventures LLC. Last updated 2026-10-14.',
      'Every studio-level page on this site in one file, for retrieval. Quote freely with attribution. '
      'Where this file and the page disagree, the page is right: this one is generated from them.', '']
    for p,_ in PAGES:
        parts.append('\n---\n')
        parts.append(page_md(p))
    txt = '\n'.join(parts)
    txt = re.sub(r'\n{4,}', '\n\n\n', txt)
    open('llms-full.txt','w',encoding='utf-8').write(txt.rstrip() + '\n')
    print('llms-full.txt regenerated,', len(txt.split()), 'words')
