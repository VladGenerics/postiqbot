"""Рабочая копия cookies-файла для yt-dlp."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile

logger = logging.getLogger("postiqbot.ytdlp_cookies")

_WORK_SUBDIR = ".cookies"


def working_copy(master: str, work_dir: str) -> str | None:
    """Путь к рабочей копии `master`; None — если мастера нет (тогда без cookies)."""
    if not master or not os.path.exists(master):
        return None
    try:
        work_dir = os.path.join(work_dir, _WORK_SUBDIR)
        os.makedirs(work_dir, exist_ok=True)
        work = os.path.join(work_dir, os.path.basename(master))
        if not os.path.exists(work) or os.path.getmtime(master) > os.path.getmtime(work):
            fd, tmp = tempfile.mkstemp(dir=work_dir, prefix=".tmp-cookies-")
            os.close(fd)
            try:
                shutil.copy2(master, tmp)
                os.replace(tmp, work)
            except OSError:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        return work
    except OSError:
        logger.warning("Не смог создать рабочую копию cookies %s — работаю с мастером", master)
        return master
