"""Наложение картинки/GIF/анимации на видео через ffmpeg."""
from __future__ import annotations

import os
import subprocess

_POSITIONS = {
    "top_left": ("{M}", "{M}"),
    "top_center": ("(main_w-overlay_w)/2", "{M}"),
    "top_right": ("main_w-overlay_w-{M}", "{M}"),
    "middle_left": ("{M}", "(main_h-overlay_h)/2"),
    "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
    "middle_right": ("main_w-overlay_w-{M}", "(main_h-overlay_h)/2"),
    "bottom_left": ("{M}", "main_h-overlay_h-{M}"),
    "bottom_center": ("(main_w-overlay_w)/2", "main_h-overlay_h-{M}"),
    "bottom_right": ("main_w-overlay_w-{M}", "main_h-overlay_h-{M}"),
}

_ANIMATED = {".gif", ".mp4", ".webm", ".mov", ".apng"}


def _video_width(path: str) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return int(out.stdout.strip().splitlines()[0])


def apply_overlay(
    video_path: str, overlay_path: str, position: str, scale_pct: int
) -> str:
    """Наложить overlay на видео. Вернуть путь к новому файлу (синхронно)."""
    width = _video_width(video_path)
    overlay_w = max(1, int(width * max(1, scale_pct) / 100))
    margin = max(2, int(width * 0.03))
    x_expr, y_expr = _POSITIONS.get(position, _POSITIONS["bottom_right"])
    x_expr = x_expr.format(M=margin)
    y_expr = y_expr.format(M=margin)

    ext = os.path.splitext(overlay_path)[1].lower()
    animated = ext in _ANIMATED
    shortest = ":shortest=1" if animated else ""
    filtergraph = (
        f"[1:v]scale={overlay_w}:-1[ovr];"
        f"[0:v][ovr]overlay={x_expr}:{y_expr}{shortest}[v]"
    )

    base, _ = os.path.splitext(video_path)
    out_path = f"{base}_ovr.mp4"

    cmd = ["ffmpeg", "-y", "-i", video_path]
    if ext == ".gif" or ext == ".apng":
        cmd += ["-ignore_loop", "0"]
    elif ext in (".mp4", ".webm", ".mov"):
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i", overlay_path,
        "-filter_complex", filtergraph,
        "-map", "[v]", "-map", "0:a?",
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path


_PHONE_FRAME = os.path.join(os.path.dirname(__file__), "..", "assets", "phone_frame.png")
_SCREEN_X, _SCREEN_Y, _SCREEN_W, _SCREEN_H = 24, 8, 805, 1825


def _screen_positions(sx: int, sy: int, sw: int, sh: int, m: int) -> dict:
    return {
        "top_left": (f"{sx}+{m}", f"{sy}+{m}"),
        "top_center": (f"{sx}+({sw}-overlay_w)/2", f"{sy}+{m}"),
        "top_right": (f"{sx}+{sw}-overlay_w-{m}", f"{sy}+{m}"),
        "middle_left": (f"{sx}+{m}", f"{sy}+({sh}-overlay_h)/2"),
        "center": (f"{sx}+({sw}-overlay_w)/2", f"{sy}+({sh}-overlay_h)/2"),
        "middle_right": (f"{sx}+{sw}-overlay_w-{m}", f"{sy}+({sh}-overlay_h)/2"),
        "bottom_left": (f"{sx}+{m}", f"{sy}+{sh}-overlay_h-{m}"),
        "bottom_center": (f"{sx}+({sw}-overlay_w)/2", f"{sy}+{sh}-overlay_h-{m}"),
        "bottom_right": (f"{sx}+{sw}-overlay_w-{m}", f"{sy}+{sh}-overlay_h-{m}"),
    }


def make_preview(
    overlay_path: str, position: str, scale_pct: int, out_path: str
) -> str:
    """JPG-превью: оверлей прямо на экране телефона, строго в пределах экрана."""
    sx, sy, sw, sh = _SCREEN_X, _SCREEN_Y, _SCREEN_W, _SCREEN_H
    overlay_w = max(1, int(sw * max(1, scale_pct) / 100))
    margin = max(2, int(sw * 0.03))
    positions = _screen_positions(sx, sy, sw, sh, margin)
    x_expr, y_expr = positions.get(position, positions["bottom_right"])
    filtergraph = (
        f"[1:v]scale={overlay_w}:-1[ovr];[0:v][ovr]overlay={x_expr}:{y_expr}[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", _PHONE_FRAME,
        "-i", overlay_path,
        "-filter_complex", filtergraph,
        "-map", "[v]", "-frames:v", "1", "-q:v", "3",
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path
