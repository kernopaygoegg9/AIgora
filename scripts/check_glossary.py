"""Fail when user-visible frontend text uses a word that GLOSSARY.md says to avoid.

Usage: python scripts/check_glossary.py [--root <repo root>]

Avoided words come from each `_Avoid_:` line of GLOSSARY.md (explanations in
parentheses are dropped). Scanned text: `.vue` <template> text and attribute
values, and string literals in `.ts` / `.vue` scripts, bound attributes, event
handlers, `{{ }}` and template-literal `${ }` expressions. Comments, regex
literals and identifiers are not scanned. Exits 2 when GLOSSARY.md yields no
avoided words (its format drifted). A hit that is part of a glossary term (「模式」 in
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


# After these keywords a `/` starts a regex literal, not a division.
REGEX_KEYWORDS = {
    "return",
    "typeof",
    "instanceof",
    "in",
    "of",
    "new",
    "delete",
    "void",
    "throw",
    "case",
    "do",
    "else",
    "yield",
    "await",
}


def _script_strings(code: str) -> str:
    """Mask of code that keeps only the contents of string literals.

    Template literals keep their text and recurse into `${...}`; regex literals are blanked.
    """
    out = [" "] * len(code)
    for k, c in enumerate(code):
        if c == "\n":
            out[k] = "\n"
    _scan_code(code, 0, out, in_interp=False)
    return "".join(out)


def _regex_end(code: str, i: int) -> int:
    """End (exclusive, flags included) of the regex literal at code[i] == "/", or -1."""
    j, in_class = i + 1, False
    while j < len(code) and code[j] != "\n":
        d = code[j]
        if d == "\\":
            j += 2
            continue
        if d == "[":
            in_class = True
        elif d == "]":
            in_class = False
        elif d == "/" and not in_class:
            j += 1
            while j < len(code) and (code[j].isalnum() or code[j] == "_"):
                j += 1
            return j
        j += 1
    return -1


def _scan_code(code: str, i: int, out: list[str], in_interp: bool) -> int:
    """Scan code from i, filling `out` with string contents; return where it stopped.

    With in_interp, stops at the `}` closing a template literal's `${`.
    """
    n = len(code)
    depth = 0
    regex_ok = True  # whether a `/` here would start a regex literal
    while i < n:
        c = code[i]
        if in_interp and c == "{":
            depth += 1
        elif in_interp and c == "}":
            if depth == 0:
                return i
            depth -= 1
        if code.startswith("//", i):
            end = code.find("\n", i)
            i = n if end == -1 else end
        elif code.startswith("/*", i):
            end = code.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif c in "'\"":
            i = _scan_string(code, i, out)
            regex_ok = False
        elif c == "`":
            i = _scan_template(code, i, out)
            regex_ok = False
        elif c == "/" and regex_ok and (end := _regex_end(code, i)) != -1:
            i = end
            regex_ok = False
        elif c.isalnum() or c in "_$":
            j = i
            while j < n and (code[j].isalnum() or code[j] in "_$"):
                j += 1
            regex_ok = code[i:j] in REGEX_KEYWORDS
            i = j
        else:
            if not c.isspace():
                regex_ok = c not in ")]"
            i += 1
    return n


def _scan_string(code: str, i: int, out: list[str]) -> int:
    quote, j, n = code[i], i + 1, len(code)
    while j < n and code[j] != quote:
        if code[j] == "\\":
            j += 2
            continue
        if code[j] != "\n":
            out[j] = code[j]
        j += 1
    return j + 1


def _scan_template(code: str, i: int, out: list[str]) -> int:
    j, n = i + 1, len(code)
    while j < n and code[j] != "`":
        if code[j] == "\\":
            j += 2
            continue
        if code.startswith("${", j):
            j = _scan_code(code, j + 2, out, in_interp=True) + 1
            continue
        if code[j] != "\n":
            out[j] = code[j]
        j += 1
    return j + 1


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
    mask = list(_blank(attrs))
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
            # A bound value (event handlers included) is a JS expression: only its string
            # literals show.
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


class GlossaryError(Exception):
    """GLOSSARY.md could not be read as expected."""


def find_violations(root: Path) -> list[str]:
    terms, avoid = parse_glossary((root / "GLOSSARY.md").read_text(encoding="utf-8"))
    if not avoid:
        raise GlossaryError(
            "GLOSSARY.md: no `_Avoid_:` words found under any `**Term**:` heading (format changed?)"
        )
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
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        violations = find_violations(args.root)
    except GlossaryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for line in violations:
        print(line)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
