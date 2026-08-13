"""Привести пул Google-проектов (oauth_projects) к заданному списку client_id."""
from __future__ import annotations

import asyncio
import os
import re
import sys

from sqlalchemy import func, select

from bot.config import get_settings
from bot.db.models import OAuthProject, PublishAccount
from bot.db.session import get_session
from bot.services.crypto import encrypt

_CLIENT_RE = re.compile(r"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", re.I)
_SECRET_RE = re.compile(r"GOCSPX-[\w-]+")


def parse(raw: str) -> list[tuple[str, str]]:
    """Список (client_id, secret) из произвольно отформатированного текста."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for num, line in enumerate(raw.splitlines(), 1):
        cid, sec = _CLIENT_RE.search(line), _SECRET_RE.search(line)
        if cid is None and sec is None:
            continue
        if cid is None or sec is None:
            raise SystemExit(f"строка {num}: нашёл только одно из двух значений")
        if cid.group(0) in seen:
            raise SystemExit(f"строка {num}: client_id повторяется")
        seen.add(cid.group(0))
        pairs.append((cid.group(0), sec.group(0)))
    if not pairs:
        raise SystemExit("Список пуст: ни одной пары client_id + GOCSPX-секрет")
    return pairs


async def read_state() -> tuple[list[tuple[int, str, str, bool]], dict[int, int]]:
    """Снимок пула: (id, name, client_id, is_active) + число аккаунтов на проект."""
    async with get_session() as session:
        rows = [
            (p.id, p.name, p.client_id, p.is_active)
            for p in await session.scalars(
                select(OAuthProject).order_by(OAuthProject.id)
            )
        ]
        counts = dict(
            (
                await session.execute(
                    select(PublishAccount.project_id, func.count(PublishAccount.id))
                    .where(PublishAccount.project_id.isnot(None))
                    .group_by(PublishAccount.project_id)
                )
            ).all()
        )
    return rows, counts


def build_plan(pairs, rows, counts) -> list[tuple[str, int, str, str]]:
    """Список действий (action, project_id, name, client_id). Ничего не меняет."""
    names = {cid: f"pool-{i:02d}" for i, (cid, _) in enumerate(pairs, 1)}
    wanted = set(names)
    plan: list[tuple[str, int, str, str]] = []
    for pid, name, cid, _active in rows:
        if cid in wanted:
            plan.append(("update", pid, names[cid], cid))
        elif counts.get(pid, 0):
            plan.append(("disable", pid, f"{name} ({counts[pid]} акк.)", cid))
        else:
            plan.append(("delete", pid, name, cid))
    have = {cid for _pid, _n, cid, _a in rows}
    plan += [("insert", 0, names[cid], cid) for cid, _s in pairs if cid not in have]
    return plan


async def apply_plan(plan, pairs) -> None:
    secrets = dict(pairs)
    quota = get_settings().daily_upload_quota
    async with get_session() as session:
        for action, pid, name, cid in plan:
            if action == "insert":
                session.add(
                    OAuthProject(
                        name=name,
                        client_id=cid,
                        client_secret_enc=encrypt(secrets[cid]),
                        owner_telegram_id=None,
                        daily_quota=quota,
                        is_active=True,
                    )
                )
                continue
            row = await session.get(OAuthProject, pid)
            if row is None:
                continue
            if action == "update":
                row.client_secret_enc = encrypt(secrets[cid])
                row.name = name
                row.is_active = True
            elif action == "disable":
                row.is_active = False
            elif action == "delete":
                await session.delete(row)


async def main() -> None:
    apply = "--apply" in sys.argv[1:]
    raw = os.environ.get("PROJECTS", "")
    if not raw.strip():
        raise SystemExit("Передай список в переменной PROJECTS")
    pairs = parse(raw)
    rows, counts = await read_state()
    plan = build_plan(pairs, rows, counts)

    order = {"update": 0, "insert": 1, "disable": 2, "delete": 3}
    for action, pid, name, cid in sorted(plan, key=lambda x: (order[x[0]], x[1])):
        where = f"#{pid}" if pid else "новый"
        print(f"{action:<8} {where:<6} {name:<22} {cid[:24]}…")
    stats = {a: sum(1 for p in plan if p[0] == a) for a in order}
    print(f"\nВ списке: {len(pairs)}. План: " + ", ".join(
        f"{a}={n}" for a, n in stats.items()))

    if not apply:
        print("\nЭто только план. Повтори с --apply, чтобы записать.")
        return
    await apply_plan(plan, pairs)
    rows, _ = await read_state()
    active = sum(1 for _p, _n, _c, a in rows if a)
    print(f"\nГотово. В пуле {len(rows)} проектов, активных {active}.")


if __name__ == "__main__":
    asyncio.run(main())
