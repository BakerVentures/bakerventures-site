#!/usr/bin/env python3
"""Write a page's FAQPage `mainEntity` from the Q&A that is visible on that same page.

`scripts/check_faq_jsonld.py` fails when a structured answer differs by one character from
the visible answer it duplicates, because that is how false copy stayed in front of crawlers
after the page itself had been corrected. Rather than keep two copies of every answer in step
by hand -- which is the thing that failed -- this generates the structured block from the
visible copy, using the gate's own parser, so the two cannot drift apart in the first place.

Workflow: write the page with its real Q&A and an empty `"mainEntity": []`, then run this.

    python3 scripts/fill-faq-jsonld.py nearvo/support/index.html
    python3 scripts/check_faq_jsonld.py nearvo/support/index.html

Each page must carry exactly one `application/ld+json` block containing exactly one FAQPage.
Both markups the gate understands are supported: `<dl><dt>Q</dt><dd>A</dd></dl>`, and an
`<h2>`/`<h3>`/`<h4>` question followed by paragraphs (headings are only treated as questions
when they end in a question mark, so ordinary section headings are left alone). Questions are
emitted in the order they appear on the page.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "faq_gate", ROOT / "scripts" / "check_faq_jsonld.py"
)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

LD = re.compile(
    r'(<script[^>]+type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.DOTALL
)


def visible_in_order(text: str) -> list[tuple[str, str]]:
    """Visible questions in document order, each with the answer the gate will compare."""
    body = text[text.find("<body"):] or text
    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    for block in gate.DL_RE.findall(body):
        for dt, dd in gate.DTDD_RE.findall(block):
            q, a = gate.norm(dt), gate.norm(dd)
            if q and a and q not in seen:
                seen.add(q)
                out.append((q, a))

    for _tag, heading, rest in gate.HEADING_RE.findall(body):
        q = gate.norm(heading)
        paragraphs = [gate.norm(p) for p in gate.P_RE.findall(rest) if gate.norm(p)]
        if paragraphs and q.endswith("?") and q not in seen:
            seen.add(q)
            out.append((q, " ".join(paragraphs)))

    return out


def fill(path: pathlib.Path) -> int:
    text = path.read_text(encoding="utf-8")
    qa = visible_in_order(text)
    if not qa:
        print(f"  !! {path}: no visible Q&A found")
        return 1

    blocks = LD.findall(text)
    if len(blocks) != 1:
        print(f"  !! {path}: expected 1 ld+json block, found {len(blocks)}")
        return 1
    open_tag, raw, close_tag = blocks[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  !! {path}: ld+json does not parse ({exc})")
        return 1

    faqs = gate.find_faqpages(data)
    if len(faqs) != 1:
        print(f"  !! {path}: expected 1 FAQPage node, found {len(faqs)}")
        return 1

    faqs[0]["mainEntity"] = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in qa
    ]

    rendered = open_tag + "\n" + json.dumps(data, indent=1, ensure_ascii=False) + "\n" + close_tag
    start = text.index(open_tag)
    end = text.index(close_tag) + len(close_tag)
    path.write_text(text[:start] + rendered + text[end:], encoding="utf-8")
    print(f"  ok {path}: {len(qa)} Q&A pairs")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    return max(fill(pathlib.Path(a)) for a in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
