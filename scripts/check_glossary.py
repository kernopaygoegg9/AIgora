"""Fail when user-visible frontend text uses a word that GLOSSARY.md says to avoid.

Usage: python scripts/check_glossary.py [--root <repo root>]

Avoided words come from each `_Avoid_:` line of GLOSSARY.md (explanations in
parentheses are dropped). Scanned text: `.vue` <template> text and attribute
values, and string literals in `.ts` / `.vue` scripts. Comments and
identifiers are not scanned. A hit that is part of a glossary term (「模式」 in
「討論模式」) is fine. Lines containing `glossary-ignore` are skipped.
"""

import argparse
import re
import sys
from pathlib import Path

TERM_RE = re.compile(r"^\*\*(.+?)\*\*:\s*$")
AVOID_RE = re.compile(r"^_Avoid_:\s*(.*)$")
PAREN_RE = re.compile(r"[（(][^）)]*[）)]")
IGNORE_MARK = "glossary-ignore"


def parse_glossary(text: str) -> tuple[list[str], dict[str, str]]:
    """Return (glossary terms, avoided word -> preferred term)."""
    terms: list[str] = []
    avoid: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        term = TERM_RE.match(line)
        if term:
            name = term.group(1)
            current = PAREN_RE.sub("", name).strip()
            terms.append(current)
            english = re.search(r"\(([^)]*)\)", name)
            if english:
                terms.append(english.group(1).strip())
            continue
        found = AVOID_RE.match(line)
        if found and current:
            for word in re.split(r"[、,，]", PAREN_RE.sub("", found.group(1))):
                word = word.strip()
                if word:
                    avoid.setdefault(word, current)
    return terms, avoid


def _blank(text: str) -> str:
    """Same length as text, with everything but newlines turned into spaces."""
    return re.sub(r"[^\n]", " ", text)


def _script_strings(code: str) -> str:
    """Mask of code that keeps only the contents of string literals."""
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if code.startswith("//", i):
            end = code.find("\n", i)
            end = n if end == -1 else end
            out.append(_blank(code[i:end]))
            i = end
        elif code.startswith("/*", i):
            end = code.find("*/", i + 2)
            end = n if end == -1 else end + 2
            out.append(_blank(code[i:end]))
            i = end
        elif c in "'\"`":
            j = i + 1
            content = []
            depth = 0
            while j < n:
                d = code[j]
                if depth == 0 and d == "\\" and j + 1 < n:
                    content.append("  " if code[j + 1] != "\n" else " \n")
                    j += 2
                    continue
                if depth == 0 and d == c:
                    break
                if c == "`" and depth == 0 and code.startswith("${", j):
                    depth = 1
                    content.append("  ")
                    j += 2
                    continue
                if depth:
                    depth += {"{": 1, "}": -1}.get(d, 0)
                    content.append("\n" if d == "\n" else " ")
                else:
                    content.append(d)
                j += 1
            out.append(" " + "".join(content))
            if j < n:
                out.append(" ")
            i = j + 1
        else:
            out.append("\n" if c == "\n" else " ")
            i += 1
    return "".join(out)[:n]


# Attributes whose values are not shown to users.
HIDDEN_ATTRS = {
    "class",
    "style",
    "id",
    "ref",
    "key",
    "name",
    "type",
    "for",
    "href",
    "src",
    "to",
    "role",
    "lang",
    "is",
    "slot",
}
ATTR_RE = re.compile(r"""([^\s=/>"']+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]+))?""")
TAG_RE = re.compile(r"<(/?)([A-Za-z][\w.:-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*)>|<!--.*?-->", re.S)
INTERP_RE = re.compile(r"\{\{(.*?)\}\}", re.S)


def _attr_mask(attrs: str) -> str:
    out = [_blank(attrs)]
    mask = list(out[0])
    for m in ATTR_RE.finditer(attrs):
        name, value = m.group(1), m.group(2)
        if value is None:
            continue
        start = m.start(2)
        inner, offset = value, 0
        if value[0] in "\"'":
            inner, offset = value[1:-1], 1
        bound = name.startswith((":", "@", "#", "v-"))
        base = re.sub(r"^(v-bind:|:)", "", name).lower()
        if base in HIDDEN_ATTRS or base.startswith("data-"):
            continue
        if bound:
            # A bound value is a JS expression: only its string literals show.
            if name.startswith("@") or name.startswith("v-on:"):
                continue
            visible = _script_strings(inner)
        else:
            visible = inner
        for k, ch in enumerate(visible):
            mask[start + offset + k] = ch
    return "".join(mask)


def _template_mask(template: str) -> str:
    out = []
    pos = 0
    for m in TAG_RE.finditer(template):
        out.append(_text_mask(template[pos : m.start()]))
        if m.group(0).startswith("<!--"):
            out.append(_blank(m.group(0)))
        else:
            head = m.start(3) - m.start()
            out.append(_blank(m.group(0)[:head]))
            out.append(_attr_mask(m.group(3)))
            out.append(" ")
        pos = m.end()
    out.append(_text_mask(template[pos:]))
    return "".join(out)


def _text_mask(text: str) -> str:
    def code(m: re.Match) -> str:
        return "  " + _script_strings(m.group(1)) + "  "

    return INTERP_RE.sub(code, text)


BLOCK_RE = re.compile(r"(<(script|style)\b[^>]*>)(.*?)(</\2\s*>)", re.S | re.I)


def visible_text(path: Path, source: str) -> str:
    """Same-length mask of source keeping only user-visible characters."""
    if path.suffix == ".ts":
        return _script_strings(source)
    out = []
    pos = 0
    for m in BLOCK_RE.finditer(source):
        out.append(_template_mask(source[pos : m.start()]))
        out.append(_blank(m.group(1)))
        body = m.group(3)
        out.append(_script_strings(body) if m.group(2).lower() == "script" else _blank(body))
        out.append(_blank(m.group(4)))
        pos = m.end()
    out.append(_template_mask(source[pos:]))
    return "".join(out)


def _word_pattern(word: str) -> re.Pattern:
    escaped = re.escape(word)
    if word.isascii():
        return re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", re.I)
    return re.compile(escaped)


def find_violations(root: Path) -> list[str]:
    terms, avoid = parse_glossary((root / "GLOSSARY.md").read_text(encoding="utf-8"))
    patterns = {word: _word_pattern(word) for word in avoid}
    src = root / "frontend" / "src"
    found = []
    for path in sorted(
        (p for p in src.rglob("*") if p.suffix in (".ts", ".vue")), key=lambda p: p.as_posix()
    ):
        source = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        lines = source.split("\n")
        mask_lines = visible_text(path, source).split("\n")
        rel = path.relative_to(root).as_posix()
        for number, (line, mask) in enumerate(zip(lines, mask_lines), start=1):
            if IGNORE_MARK in line:
                continue
            for word, pattern in patterns.items():
                for m in pattern.finditer(mask):
                    if not _inside_term(mask, m.start(), word, terms):
                        found.append(f"{rel}:{number}: 用詞「{word}」，請改用「{avoid[word]}」")
                        break
    return found


def _inside_term(text: str, start: int, word: str, terms: list[str]) -> bool:
    """Whether the hit at text[start:] is part of a glossary term."""
    for term in terms:
        k = term.find(word)
        while k != -1:
            if start >= k and text[start - k : start - k + len(term)] == term:
                return True
            k = term.find(word, k + 1)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    violations = find_violations(args.root)
    for line in violations:
        print(line)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
