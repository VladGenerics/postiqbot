"""Наложение картинки/GIF/анимации на видео через ffmpeg."""
from __future__ import annotations

import glob
import os
import subprocess
import tempfile

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

_PROBE_TIMEOUT = 30
_FRAMES_TIMEOUT = 180
_ENCODE_TIMEOUT = 900


def _trim_transparent(path: str) -> str | None:
    """Обрезать прозрачные поля статичной картинки до видимого содержимого."""
    ext = os.path.splitext(path)[1].lower()
    if ext in _ANIMATED:
        return None
    try:
        from PIL import Image

        img = Image.open(path)
        if img.mode not in ("RGBA", "LA") and "transparency" not in img.info:
            return None
        img = img.convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if not bbox or bbox == (0, 0, img.width, img.height):
            return None
        out = f"{os.path.splitext(path)[0]}_trim.png"
        img.crop(bbox).save(out)
        return out
    except Exception:
        return None


def _representative_frame(path: str) -> str | None:
    """Для анимированного оверлея выбрать «наполненный» кадр (PNG) для превью."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in _ANIMATED:
        return None
    tmp_dir = tempfile.mkdtemp(prefix="ovlframes_")
    try:
        from PIL import Image

        pattern = os.path.join(tmp_dir, "f_%04d.png")
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-frames:v", "60", "-vsync", "0", pattern],
            capture_output=True, text=True, check=True, timeout=_FRAMES_TIMEOUT,
        )
        frames = sorted(glob.glob(os.path.join(tmp_dir, "f_*.png")))
        best_path, best_score = None, -1
        for fp in frames:
            img = Image.open(fp).convert("RGBA")
            alpha_hist = img.getchannel("A").histogram()
            visible = sum(alpha_hist[33:])
            if visible > best_score:
                best_path, best_score = fp, visible
        if best_path is None:
            return None
        out = f"{os.path.splitext(path)[0]}_frame.png"
        Image.open(best_path).convert("RGBA").save(out)
        return out
    except Exception:
        return None
    finally:
        for fp in glob.glob(os.path.join(tmp_dir, "*")):
            try:
                os.remove(fp)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass


def video_duration(path: str) -> float:
    """Длительность видео в секундах (0.0, если определить не удалось)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True, timeout=_PROBE_TIMEOUT,
        )
        return float(out.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001 — битый файл/нет ffprobe: считаем «неизвестно»
        return 0.0


def _video_width(path: str) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True, timeout=_PROBE_TIMEOUT,
    )
    return int(out.stdout.strip().splitlines()[0])


def apply_overlay(
    video_path: str, overlay_path: str, position: str, scale_pct: int
) -> str:
    """Наложить overlay на видео. Вернуть путь к новому файлу (синхронно)."""
    trimmed = _trim_transparent(overlay_path)
    overlay_path = trimmed or overlay_path
    width = _video_width(video_path)
    overlay_w = max(2, int(width * max(1, scale_pct) / 100))
    overlay_w -= overlay_w % 2
    margin = max(2, int(width * 0.03))
    x_expr, y_expr = _POSITIONS.get(position, _POSITIONS["bottom_right"])
    x_expr = x_expr.format(M=margin)
    y_expr = y_expr.format(M=margin)

    ext = os.path.splitext(overlay_path)[1].lower()
    animated = ext in _ANIMATED
    shortest = ":shortest=1" if animated else ""
    filtergraph = (
        f"[1:v]scale={overlay_w}:-2[ovr];"
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
    subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=_ENCODE_TIMEOUT
    )
    if trimmed:
        try:
            os.remove(trimmed)
        except OSError:
            pass
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
    frame = _representative_frame(overlay_path)
    overlay_path = frame or overlay_path
    trimmed = _trim_transparent(overlay_path)
    overlay_path = trimmed or overlay_path
    sx, sy, sw, sh = _SCREEN_X, _SCREEN_Y, _SCREEN_W, _SCREEN_H
    overlay_w = max(1, int(sw * max(1, scale_pct) / 100))
    margin = max(2, int(sw * 0.03))
    positions = _screen_positions(sx, sy, sw, sh, margin)
    x_expr, y_expr = positions.get(position, positions["bottom_right"])
    filtergraph = (
        f"color=c=black:s=852x1846[bg];[bg][0:v]overlay=0:0[frame];"
        f"[1:v]scale={overlay_w}:-1[ovr];"
        f"[frame][ovr]overlay={x_expr}:{y_expr},scale=426:-1[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", _PHONE_FRAME,
        "-i", overlay_path,
        "-filter_complex", filtergraph,
        "-map", "[v]", "-frames:v", "1", "-q:v", "3",
        out_path,
    ]
    subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=_FRAMES_TIMEOUT
    )
    if trimmed:
        try:
            os.remove(trimmed)
        except OSError:
            pass
    if frame:
        try:
            os.remove(frame)
        except OSError:
            pass
    return out_path
