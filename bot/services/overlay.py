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


def make_preview(
    overlay_path: str,
    position: str,
    scale_pct: int,
    out_path: str,
    width: int = 1080,
    height: int = 1920,
) -> str:
    """Сгенерировать JPG-превью: оверлей поверх макета видео (по умолчанию 9:16)."""
    overlay_w = max(1, int(width * max(1, scale_pct) / 100))
    margin = max(2, int(width * 0.03))
    x_expr, y_expr = _POSITIONS.get(position, _POSITIONS["bottom_right"])
    x_expr = x_expr.format(M=margin)
    y_expr = y_expr.format(M=margin)
    filtergraph = (
        f"[1:v]scale={overlay_w}:-1[ovr];[0:v][ovr]overlay={x_expr}:{y_expr}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc2=s={width}x{height}:d=1",
        "-i", overlay_path,
        "-filter_complex", filtergraph,
        "-frames:v", "1",
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path
