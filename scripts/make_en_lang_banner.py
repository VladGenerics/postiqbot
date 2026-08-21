"""Собрать EN-версию баннера «Сменить язык» из русской."""
from __future__ import annotations

import os
import sys

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

SRC = "bot/assets/ru/banner_lang.png"
DST = "bot/assets/en/banner_lang.png"
WEB_FONT = "bot/assets/web/geist.woff2"
TTF = "/tmp/geist-banner.ttf"

CAPTION = "Language"
LEFT, BASELINE, CAP_PX, WEIGHT = 107, 875, 108, 700

BOX = (60, 690, 880, 890)


def _font() -> ImageFont.FreeTypeFont:
    """Geist нужного веса: woff2 сайта → ttf, вес выставляем по оси wght."""
    if not os.path.exists(TTF):
        web = TTFont(WEB_FONT)
        web.flavor = None
        web.save(TTF)
    upem = TTFont(TTF)["head"].unitsPerEm
    cap = TTFont(TTF)["OS/2"].sCapHeight
    size = round(CAP_PX * upem / cap)
    font = ImageFont.truetype(TTF, size)
    try:
        font.set_variation_by_axes([WEIGHT])
    except Exception as exc:  # noqa: BLE001 — статический шрифт без осей
        print(f"вес не выставлен ({exc}) — рисую как есть", file=sys.stderr)
    return font


def _text_mask(a: np.ndarray) -> np.ndarray:
    """Маска старой подписи: белёсые пиксели зоны, кроме пурпурного подчёркивания."""
    x0, y0, x1, y1 = BOX
    mx, mn = a.max(axis=2), a.min(axis=2)
    white = (mn > 90) & ((mx - mn) < 60)
    purple = (a[:, :, 0] > 90) & (a[:, :, 2] > 120) & (a[:, :, 1] < 90)
    mask = np.zeros(a.shape[:2], bool)
    mask[y0:y1, x0:x1] = white[y0:y1, x0:x1]
    for _ in range(5):
        mask[1:, :] |= mask[:-1, :]
        mask[:-1, :] |= mask[1:, :]
        mask[:, 1:] |= mask[:, :-1]
        mask[:, :-1] |= mask[:, 1:]
    mask[:y0, :] = mask[y1:, :] = False
    mask[:, :x0] = mask[:, x1:] = False
    return mask & ~purple


def _inpaint(a: np.ndarray, mask: np.ndarray, rounds: int = 600) -> np.ndarray:
    """Затереть маску фоном: усреднение соседей, пока пятно не разойдётся."""
    out = a.astype(np.float64).copy()
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min() - 2, ys.max() + 3
    x0, x1 = xs.min() - 2, xs.max() + 3
    tile, m = out[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    tile[m] = np.nan
    known = ~m
    filled = np.where(np.isnan(tile), np.nanmedian(tile[known]), tile)
    for _ in range(rounds):
        nb = np.zeros_like(filled)
        nb[1:] += filled[:-1]
        nb[:-1] += filled[1:]
        nb[:, 1:] += filled[:, :-1]
        nb[:, :-1] += filled[:, 1:]
        cnt = np.full(filled.shape, 4.0)
        cnt[0] -= 1
        cnt[-1] -= 1
        cnt[:, 0] -= 1
        cnt[:, -1] -= 1
        avg = nb / cnt
        filled = np.where(m[:, :, None], avg, filled)
    out[y0:y1, x0:x1] = filled
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> int:
    if not os.path.exists(SRC):
        print(f"нет исходника {SRC}", file=sys.stderr)
        return 1
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(int)
    mask = _text_mask(a)
    if not mask.any():
        print("подпись не найдена — проверь BOX", file=sys.stderr)
        return 1
    print(f"затираю {mask.sum()} px подписи")
    img = Image.fromarray(_inpaint(a, mask))
    draw = ImageDraw.Draw(img)
    draw.text((LEFT, BASELINE), CAPTION, font=_font(), fill=(255, 255, 255), anchor="ls")
    img.save(DST)
    print(f"готово: {DST} ({img.size[0]}×{img.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
