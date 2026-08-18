"""Подписи кнопок — с эмодзи, и только с эмодзи."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from bot.handlers import menu
from bot.i18n import LABELS, LANGS, T

_ALWAYS_EMOJI = [
    (0x231A, 0x231B), (0x23E9, 0x23F3), (0x23F8, 0x23FA), (0x25FD, 0x25FE),
    (0x2614, 0x2615), (0x2648, 0x2653), (0x267F, 0x267F), (0x2693, 0x2693),
    (0x26A1, 0x26A1), (0x26AA, 0x26AB), (0x26BD, 0x26BE), (0x26C4, 0x26C5),
    (0x26CE, 0x26CE), (0x26D4, 0x26D4), (0x26EA, 0x26EA), (0x26F2, 0x26F3),
    (0x26F5, 0x26F5), (0x26FA, 0x26FA), (0x26FD, 0x26FD), (0x2705, 0x2705),
    (0x270A, 0x270B), (0x2728, 0x2728), (0x274C, 0x274C), (0x274E, 0x274E),
    (0x2753, 0x2755), (0x2757, 0x2757), (0x2795, 0x2797), (0x27B0, 0x27B0),
    (0x27BF, 0x27BF), (0x2B1B, 0x2B1C), (0x2B50, 0x2B50), (0x2B55, 0x2B55),
    (0x1F000, 0x1FAFF),
]

_REJECTED = frozenset("◉○▣□⊘⊕⊗☰◈※✦§⋯⇄▷♪◷▭▩↯↻▤‖▸◎★∞✓✕✎●→↓")

_BUTTON_KEY = re.compile(r"btn|^mv_no_folder$|^c_active$|^c_paused$|^c_priv_|^c_sched_(now|interval|times)$")

_NOT_A_BUTTON = {"choose_platform"}


def _emoji(value: str) -> list[str]:
    """Настоящие эмодзи в строке: цветная картинка, а не глиф шрифтом."""
    found = []
    for i, ch in enumerate(value):
        cp = ord(ch)
        if ch == "️":
            found.append(f"U+FE0F после {value[i - 1] if i else '?'}")
        elif any(lo <= cp <= hi for lo, hi in _ALWAYS_EMOJI):
            found.append(f"U+{cp:04X} {ch}")
    return found


def _rejected(value: str) -> list[str]:
    return [f"U+{ord(ch):04X} {ch}" for ch in value if ch in _REJECTED]


def _button_labels() -> list[tuple[str, str, str]]:
    out = [
        (f"LABELS.{key}", lang, value)
        for key, langs in LABELS.items()
        if key not in _NOT_A_BUTTON
        for lang, value in langs.items()
    ]
    out += [
        (key, lang, value)
        for key, langs in T.items()
        if _BUTTON_KEY.search(key)
        for lang, value in langs.items()
    ]
    return out


_CASES = [pytest.param(k, lang, v, id=f"{k}-{lang}") for k, lang, v in _button_labels()]


@pytest.mark.parametrize("key,lang,value", _CASES)
def test_button_label_has_emoji(key, lang, value):
    assert _emoji(value), f"{key}[{lang}] = {value!r} — кнопка без иконки"


@pytest.mark.parametrize("key,lang,value", _CASES)
def test_button_label_has_no_rejected_glyph(key, lang, value):
    assert not _rejected(value), f"{key}[{lang}] = {value!r}: {_rejected(value)}"


def test_the_checks_actually_work():
    """Страховка от «тест зелёный, потому что ничего не проверяет»."""
    assert _emoji("📋 Мои подключения")
    assert _emoji("✏️ Переименовать")
    assert _emoji("⭐ Моя подписка")
    assert not _emoji("☰ Мои подключения")
    assert not _emoji("« Назад")
    assert _rejected("★ Моя подписка")
    assert not _rejected("⭐ Моя подписка")


def test_every_button_label_exists_in_both_languages():
    """Пропущенный перевод показывает пользователю чужой язык на кнопке."""
    for key, langs in LABELS.items():
        assert set(langs) == set(LANGS), key
    for key, langs in T.items():
        if _BUTTON_KEY.search(key):
            assert set(langs) == set(LANGS), key


def test_menu_screens_use_emoji_in_buttons():
    """Экраны меню зашивают подписи прямо в вызовы `_btn("ru", "en", …)` — правило для них то же."""
    tree = ast.parse(Path(menu.__file__).read_text(encoding="utf-8"))
    labels = [
        arg.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_btn"
        for arg in node.args[:2]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]
    assert len(labels) >= 20
    for text in labels:
        assert _emoji(text), f"{text!r} — кнопка меню без иконки"
        assert not _rejected(text), f"{text!r}: {_rejected(text)}"
