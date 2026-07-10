"""AI-генерация заголовка и описания для YouTube (OpenAI-совместимый API, freemodel)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from bot.config import get_settings

logger = logging.getLogger("postiqbot.ai")

_SYSTEM = (
    "You are a YouTube SEO assistant. Given a video's original title, produce a "
    "clean, catchy YouTube title and a short description with relevant hashtags. "
    "Match the language of the original title. Do not invent facts about the video "
    "content. Return STRICT JSON only: "
    '{"title": "...", "description": "..."}. '
    "Title max 90 chars. Description max 400 chars, may include 3-6 hashtags."
)


@dataclass
class GeneratedMeta:
    title: str
    description: str


def is_configured() -> bool:
    return bool(get_settings().ai_api_key)


async def generate_meta(source_title: str, platform_hint: str = "") -> GeneratedMeta | None:
    """Сгенерировать (title, description). None — если выключено/ошибка."""
    s = get_settings()
    if not s.ai_api_key:
        return None
    prompt = (
        f"Original title: {source_title!r}\n"
        f"{('Source platform: ' + platform_hint) if platform_hint else ''}\n"
        "Rewrite for YouTube."
    )
    body = {
        "model": s.ai_model,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {s.ai_api_key}",
        "content-type": "application/json",
    }
    url = s.ai_base_url.rstrip("/") + "/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(url, json=body, headers=headers)
        data = resp.json()
        choices = data.get("choices") or []
        text = ""
        if choices:
            text = (choices[0].get("message") or {}).get("content", "").strip()
        if not text:
            logger.warning("AI: пустой ответ (%s): %s", resp.status_code, str(data)[:300])
            return None
        obj = _extract_json(text)
        title = (obj.get("title") or "").strip()[:100]
        desc = (obj.get("description") or "").strip()[:5000]
        if not title:
            return None
        return GeneratedMeta(title=title, description=desc)
    except Exception:  # noqa: BLE001 — не роняем публикацию
        logger.exception("AI generate_meta failed")
        return None


def _extract_json(text: str) -> dict:
    """Достать JSON-объект из ответа (иногда модель добавляет ```json ... ```)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {}
