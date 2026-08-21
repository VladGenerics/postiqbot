"""Английская локаль — без русских остатков."""
from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bot.handlers import menu
from bot.i18n import COMMANDS, LABELS, LANGS, T, command_descriptions, t
from bot.services.subscription import status_text
from bot.ui import ICONS, _ASSETS
from bot.web import oauth_callback, pages, tiktok_callback
from bot.db.models import User

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
FIELD = re.compile(r"{(\w+)")
BOT_DIR = Path(menu.__file__).resolve().parent.parent

RU_ON_PURPOSE = {"lang"}


def _sources() -> list[Path]:
    return sorted(BOT_DIR.rglob("*.py"))


def test_every_message_exists_in_both_languages():
    for key, langs in T.items():
        assert set(langs) == set(LANGS), key


def test_english_messages_have_no_russian_left():
    for key, langs in T.items():
        assert not CYRILLIC.search(langs["en"]), f"T[{key}][en] = {langs['en']!r}"


def test_english_labels_have_no_russian_left():
    for key, langs in LABELS.items():
        assert set(langs) == set(LANGS), key
        if key in RU_ON_PURPOSE:
            continue
        assert not CYRILLIC.search(langs["en"]), f"LABELS[{key}][en]"


def test_placeholders_are_the_same_in_both_languages():
    """{date} потерянный в переводе — это либо KeyError, либо пропавшая дата."""
    for key, langs in T.items():
        fields = {lang: set(FIELD.findall(text)) for lang, text in langs.items()}
        assert len(set(map(frozenset, fields.values()))) == 1, (key, fields)


def test_every_key_used_in_code_exists():
    """t("опечатка") молча вернёт саму строку ключа — это видно только в чате."""
    used: set[tuple[str, str]] = set()
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            arg = node.args[0]
            if name == "t" and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                used.add((arg.value, f"{path.name}:{node.lineno}"))
    assert used, "вызовов t() не нашлось — тест перестал что-либо проверять"
    missing = sorted(f"{key} ({where})" for key, where in used if key not in T)
    assert not missing, missing


def test_menu_buttons_have_an_english_half():
    """Подписи экранов зашиты в _btn("ru", "en", …): второй аргумент — английский."""
    tree = ast.parse(Path(menu.__file__).read_text(encoding="utf-8"))
    pairs = [
        node.args[:2]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_btn"
        and len(node.args) >= 2
    ]
    assert len(pairs) >= 15
    for ru, en in pairs:
        assert isinstance(en, ast.Constant) and isinstance(en.value, str)
        assert CYRILLIC.search(ru.value), f"первый аргумент — русский: {ru.value!r}"
        assert not CYRILLIC.search(en.value), f"английская подпись: {en.value!r}"


def test_command_menu_is_translated():
    for cmd, langs in COMMANDS:
        assert set(langs) == set(LANGS), cmd
        assert not CYRILLIC.search(langs["en"]), cmd
    assert len(command_descriptions("en")) == len(COMMANDS)


def test_commands_in_menu_are_handled():
    """Команда в меню без хендлера = кнопка, которая ничего не делает."""
    registered: set[str] = set()
    for path in _sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            if name == "CommandStart":
                registered.add("start")
            elif name == "Command":
                registered |= {
                    a.value for a in node.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)
                }
    for cmd, _ in COMMANDS:
        assert cmd in registered, f"/{cmd} есть в меню, но не обрабатывается"


@pytest.mark.parametrize("until", [None, timedelta(days=5), timedelta(days=-1)])
def test_status_text_english_has_no_russian(until):
    now = datetime.now(timezone.utc)
    user = User(
        telegram_id=1, tier_plan="starter", tier_accounts=4, tier_videos=4,
        subscription_until=None if until is None else now + until,
    )
    text = status_text(user, "en")
    assert text and not CYRILLIC.search(text), text


@pytest.mark.parametrize(
    "table", [oauth_callback._TXT, tiktok_callback._TXT, pages._RESULT_TXT]
)
def test_result_pages_are_fully_bilingual(table):
    assert set(table) == set(LANGS)
    assert set(table["ru"]) == set(table["en"])
    for key, value in table["en"].items():
        text = " ".join(value) if isinstance(value, tuple) else value
        assert not CYRILLIC.search(text), f"{key}: {text!r}"


def test_every_banner_exists_in_every_language():
    for icon, fname in ICONS.items():
        for lang in LANGS:
            path = Path(_ASSETS) / lang / fname
            assert path.exists(), f"нет баннера {lang}/{fname} (раздел {icon})"


def test_referral_texts_render_in_both_languages():
    for lang in LANGS:
        body = t("referral", lang, bonus=14, plan="🟢 Starter", link="https://t.me/x",
                 invited=3, paid=1)
        reward = t("ref_reward", lang, days=14, plan="🟢 Starter", date="01.09.2026")
        assert "14" in body and "Starter" in body
        assert "14" in reward and "Starter" in reward
