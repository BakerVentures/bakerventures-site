#!/usr/bin/env python3
"""Assert every FAQPage `acceptedAnswer` matches the visible answer it duplicates.

Why this exists: these pages state each FAQ answer twice — once in the visible
HTML, once inside an `application/ld+json` FAQPage block that search engines
serve directly. On 2026-10-01, six apps' support pages were found carrying false
claims, and in nearly every case the visible copy had been corrected at some
point while the structured-data copy kept the old, false sentence. A reader saw
the fix; a crawler was served the defect. This check makes that drift a failure.

It also enforces the other half of Google's own FAQPage requirement: the full
question and answer must actually be present on the page. A structured Q&A with
no visible counterpart is reported, not ignored.

Two visible markups are understood, because the site uses both:
    <dl class="faq"><dt>Question</dt><dd>Answer</dd></dl>
    <h2|h3|h4>Question</h2><p>Answer</p>   (one or more paragraphs)

Equality is on the text a human or a crawler reads: tags stripped, HTML entities
decoded, runs of whitespace collapsed. Any wording difference fails — `&#x27;`
vs `'` does not.

Two failure classes, deliberately not equal:
  DRIFT   — a structured answer whose wording differs from the visible answer on
            the same page. Never suppressible: this is the bug that shipped false
            copy to crawlers after the page itself was corrected.
  ORPHAN  — a structured question with no visible counterpart at all. Pages whose
            orphans are a known, undecided content question are listed in
            scripts/faq_jsonld_baseline.txt with a reason, so this check is usable
            as a gate today without hiding anything. New orphans still fail.

Usage:
    python3 scripts/check_faq_jsonld.py [path ...]    # default: repo root
    python3 scripts/check_faq_jsonld.py --no-baseline # ignore the baseline, show all
Exit 0 = no drift, and no orphan outside the baseline.
Exit 1 = otherwise.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
LDJSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
DL_RE = re.compile(r"<dl\b[^>]*>(.*?)</dl>", re.DOTALL | re.IGNORECASE)
DTDD_RE = re.compile(r"<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>", re.DOTALL | re.IGNORECASE)
HEADING_RE = re.compile(
    r"<(h[2-4])\b[^>]*>(.*?)</\1>(.*?)(?=<h[2-4]\b|</main>|</body>|\Z)", re.DOTALL | re.IGNORECASE
)
P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)


def norm(s: str) -> str:
    """The text a reader actually sees: tags gone, entities decoded, whitespace collapsed."""
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub("", s))).strip()


def find_faqpages(node) -> list[dict]:
    """FAQPage objects anywhere in a parsed ld+json blob (bare, in a list, or under @graph)."""
    out: list[dict] = []
    if isinstance(node, dict):
        t = node.get("@type")
        if "FAQPage" in (t if isinstance(t, list) else [t]):
            out.append(node)
        for v in node.values():
            out.extend(find_faqpages(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(find_faqpages(v))
    return out


def structured_qa(text: str, path: pathlib.Path, problems: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in LDJSON_RE.findall(text):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            problems.append(f"{path}: an ld+json block does not parse ({exc})")
            continue
        for faq in find_faqpages(data):
            entities = faq.get("mainEntity") or []
            if isinstance(entities, dict):
                entities = [entities]
            for q in entities:
                if not isinstance(q, dict):
                    continue
                ans = q.get("acceptedAnswer")
                ans_text = ans.get("text", "") if isinstance(ans, dict) else ""
                pairs.append((q.get("name", ""), ans_text))
    return pairs


def visible_qa(text: str) -> dict[str, list[str]]:
    """Map normalized visible question -> list of candidate normalized answers."""
    body = text[text.find("<body"):] or text
    found: dict[str, list[str]] = {}

    def add(question: str, answer: str) -> None:
        found.setdefault(norm(question), []).append(norm(answer))

    for block in DL_RE.findall(body):
        for dt, dd in DTDD_RE.findall(block):
            add(dt, dd)

    for _tag, heading, rest in HEADING_RE.findall(body):
        paragraphs = [norm(p) for p in P_RE.findall(rest) if norm(p)]
        if paragraphs:
            add(heading, " ".join(paragraphs))
            if len(paragraphs) > 1:  # a structured answer may quote only the lead paragraph
                found[norm(heading)].append(paragraphs[0])
    return found


BASELINE_PATH = pathlib.Path(__file__).resolve().parent / "faq_jsonld_baseline.txt"


def load_baseline(use_baseline: bool) -> set[str]:
    """Repo-relative page paths whose ORPHAN findings are known and awaiting a decision."""
    if not use_baseline or not BASELINE_PATH.exists():
        return set()
    out = set()
    for line in BASELINE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def repo_relative(path: pathlib.Path) -> str:
    root = pathlib.Path(__file__).resolve().parent.parent
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def check(path: pathlib.Path, problems: list[str], baseline: set[str], skipped: list[str]) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "FAQPage" not in text:
        return 0
    structured = structured_qa(text, path, problems)
    if not structured:
        return 0
    visible = visible_qa(text)
    checked = 0
    for question, answer in structured:
        q, a = norm(question), norm(answer)
        candidates = visible.get(q)
        if candidates is None:
            msg = (
                f"ORPHAN {path}: no visible question matches this structured one, so its "
                f"answer is served only to crawlers\n      question: {q}"
            )
            if repo_relative(path) in baseline:
                skipped.append(msg)
            else:
                problems.append(msg)
            continue
        if a not in candidates:
            problems.append(
                f"DRIFT  {path}: a crawler is served different copy than a reader\n"
                f"      question: {q}\n"
                f"       visible: {candidates[0]}\n"
                f"    structured: {a}"
            )
        checked += 1
    return checked


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--no-baseline"]
    baseline = load_baseline("--no-baseline" not in argv)
    targets = [pathlib.Path(a) for a in args] or [pathlib.Path(__file__).resolve().parent.parent]
    problems: list[str] = []
    skipped: list[str] = []
    files = pairs = 0
    for target in targets:
        candidates = [target] if target.is_file() else sorted(target.rglob("*.html"))
        for path in candidates:
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            n = check(path, problems, baseline, skipped)
            if n:
                files += 1
                pairs += n
    print(f"FAQ structured-data check: {pairs} Q&A pairs on {files} page(s) carrying a FAQPage block")
    if skipped:
        print(f"{len(skipped)} known orphan(s) on baselined pages (scripts/faq_jsonld_baseline.txt)")
    if problems:
        print(f"\n{len(problems)} problem(s):\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Every structured answer is identical to the visible answer it duplicates.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
