# PostiqBot

Telegram-бот для автоперепоста видео: следит за YouTube- и TikTok-каналами и публикует новые ролики на YouTube и TikTok клиентов по расписанию.

**Стек:** Python 3.12 · aiogram 3 · SQLAlchemy 2 (async) · asyncpg · Alembic · APScheduler · PostgreSQL · yt-dlp · ffmpeg · Docker

## Как работает

```
источник (RSS / TikTok) → job → скачивание (yt-dlp) → публикация (YouTube API / TikTok API) → уведомление в Telegram
```

- расписание: сразу, с интервалом или по слотам в таймзоне пользователя
- ретраи с нарастающей задержкой для сетевых ошибок
- пул Google OAuth-проектов для обхода квоты YouTube
- refresh-токены хранятся зашифрованными (Fernet)
- подписки и оплата, рефералы, промокоды, RU/EN

## Запуск

```bash
cp .env.example .env
touch cookies.txt
docker compose up -d --build
docker compose run --rm --no-deps -T bot alembic upgrade head
```

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```
