"""Tests for scripts/check_glossary.py, run as a CLI against a fake repo."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_glossary.py"

GLOSSARY = """\
# Fake

**討論模式 (Discussion Mode)**:
一場討論遵循的規則。
_Avoid_: 玩法

**發言 (Turn)**:
一個參與者在一輪中的一次回覆。
_Avoid_: 訊息、回答

**發言順序 (Speaking Order)**:
同時或依序。
_Avoid_: 模式（「模式」只指討論模式）

**參與者 (Participant)**:
一個 AI 設定。
_Avoid_: 成員、bot
"""


def run_check(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess:
    (tmp_path / "GLOSSARY.md").write_text(GLOSSARY, encoding="utf-8")
    for name, content in files.items():
        path = tmp_path / "frontend" / "src" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        encoding="utf-8",
    )


def test_template_text_hit_is_reported_with_location_and_preferred_term(tmp_path):
    result = run_check(
        tmp_path,
        {
            "components/Card.vue": "<template>\n  <p>\n    現有的回答當作第 1 輪\n  </p>\n</template>\n"
        },
    )

    assert result.returncode != 0
    assert (
        result.stdout.strip() == "frontend/src/components/Card.vue:3: 用詞「回答」，請改用「發言」"
    )


def test_string_literal_in_ts_and_vue_script_is_reported(tmp_path):
    result = run_check(
        tmp_path,
        {
            "labels.ts": "export const label = '玩法'\n",
            "Page.vue": '<script setup lang="ts">\nconst title = "新增成員"\n</script>\n'
            "<template><p>{{ title }}</p></template>\n",
        },
    )

    assert result.returncode != 0
    assert result.stdout.splitlines() == [
        "frontend/src/Page.vue:2: 用詞「成員」，請改用「參與者」",
        "frontend/src/labels.ts:1: 用詞「玩法」，請改用「討論模式」",
    ]


def test_comments_are_not_scanned(tmp_path):
    result = run_check(
        tmp_path,
        {
            "a.ts": "// 回答 here\n/* 訊息\n 玩法 */\nexport const x = 1\n",
            "B.vue": "<!-- 回答 -->\n<template>\n  <!-- 成員 -->\n  <p>ok</p>\n</template>\n",
        },
    )

    assert result.returncode == 0, result.stdout
    assert result.stdout == ""


def test_identifiers_are_not_scanned(tmp_path):
    result = run_check(
        tmp_path,
        {
            "a.ts": "const bot = 1\nexport const robot = bot + 1\n",
            "B.vue": '<template>\n  <div class="bot" :title="bot">{{ bot }}</div>\n</template>\n',
        },
    )

    assert result.returncode == 0, result.stdout


def test_ascii_word_matches_whole_words_only(tmp_path):
    result = run_check(
        tmp_path,
        {"a.ts": "export const a = 'bottom'\nexport const b = 'Add a Bot'\n"},
    )

    assert result.stdout.splitlines() == ["frontend/src/a.ts:2: 用詞「bot」，請改用「參與者」"]


def test_avoided_word_inside_a_glossary_term_is_fine(tmp_path):
    result = run_check(
        tmp_path,
        {"A.vue": "<template>\n  <legend>討論模式</legend>\n  <p>發言模式</p>\n</template>\n"},
    )

    assert result.stdout.splitlines() == ["frontend/src/A.vue:3: 用詞「模式」，請改用「發言順序」"]


def test_glossary_ignore_skips_the_line(tmp_path):
    result = run_check(
        tmp_path,
        {
            "a.ts": "export const a = '回答' // glossary-ignore\n",
            "B.vue": "<template>\n  <p>回答</p> <!-- glossary-ignore -->\n</template>\n",
        },
    )

    assert result.returncode == 0, result.stdout


def test_parenthetical_explanations_are_not_avoided_words(tmp_path):
    result = run_check(tmp_path, {"a.ts": "export const a = '只指討論模式'\n"})

    assert result.returncode == 0, result.stdout


def test_user_visible_attribute_values_are_scanned(tmp_path):
    result = run_check(
        tmp_path,
        {
            "A.vue": '<template>\n  <input placeholder="輸入訊息" />\n'
            "  <button :aria-label=\"busy ? '等待回答' : 'go'\">x</button>\n</template>\n",
        },
    )

    assert result.stdout.splitlines() == [
        "frontend/src/A.vue:2: 用詞「訊息」，請改用「發言」",
        "frontend/src/A.vue:3: 用詞「回答」，請改用「發言」",
    ]


def test_glossary_without_any_avoided_word_is_an_error(tmp_path):
    (tmp_path / "GLOSSARY.md").write_text(
        "# Fake\n\n**發言 (Turn)**:\n一次回覆。\n", encoding="utf-8"
    )
    (tmp_path / "frontend" / "src").mkdir(parents=True)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        capture_output=True,
        encoding="utf-8",
    )

    assert result.returncode == 2
    assert "_Avoid_" in result.stderr


def test_string_literals_in_event_handlers_are_scanned(tmp_path):
    result = run_check(
        tmp_path,
        {
            "A.vue": "<template>\n  <button @click=\"say('回答')\">x</button>\n"
            "  <button v-on:click=\"say('成員')\">y</button>\n</template>\n",
        },
    )

    assert result.stdout.splitlines() == [
        "frontend/src/A.vue:2: 用詞「回答」，請改用「發言」",
        "frontend/src/A.vue:3: 用詞「成員」，請改用「參與者」",
    ]


def test_string_literals_inside_template_literal_expressions_are_scanned(tmp_path):
    result = run_check(
        tmp_path,
        {"a.ts": "export const a = `第 ${n} 輪${busy ? '等待回答' : `${'成員'}`}`\n"},
    )

    assert result.stdout.splitlines() == [
        "frontend/src/a.ts:1: 用詞「回答」，請改用「發言」",
        "frontend/src/a.ts:1: 用詞「成員」，請改用「參與者」",
    ]


def test_regex_literals_are_not_strings(tmp_path):
    result = run_check(
        tmp_path,
        {
            "a.ts": "const r = /'/g\nconst bot = 1\nexport const s = '回答'\n"
            'export const t = /回答|[/"]/.test(s) ? bot / 2 : 0\n',
        },
    )

    assert result.stdout.splitlines() == ["frontend/src/a.ts:3: 用詞「回答」，請改用「發言」"]
