# План команды (с 16:15, три агента параллельно)

Схема: **Claude — лид/интегратор**, **три Codex — исполнители**, люди решают и пушат.
Задания: [Azamat](tasks/AZAMAT.md) · [Umar](tasks/UMAR.md) · [Aniyar](tasks/ANIYAR.md). Контекст кейса — `AGENTS.md` §0.

## Правила, чтобы работать одновременно без конфликтов
1. Каждый агент меняет **только свои файлы** (список — в его задании и в `AGENTS.md`).
2. Перед каждым push: `git pull --rebase`, тесты/сборка своей части зелёные.
3. Коммиты маленькие, от своего GitHub-аккаунта, код от Codex — с тегом `[codex]`.
4. После push — в общий чат: SHA + что сделано. Claude сверяет `main` (тесты, сборка, сценарий в браузере).
5. Нужна правка в чужой зоне или в контракте API → написать владельцу / Claude, не править самому.
6. Скриншоты сессий Codex → `docs/codex/<имя>-N.png` (доказательство обязательного использования Codex).

## Первый запуск у себя
```bash
git clone https://github.com/BAITC-Hacks/hack-5fe3ca84-baursaq.git && cd hack-5fe3ca84-baursaq
git config user.name "<GitHub username>" && git config user.email "<email, привязанный к GitHub>"
cd backend && uv sync && cp .env.example .env   # вписать свой OPENAI_API_KEY
uv run uvicorn app.main:app --reload            # http://localhost:8000/docs
cd ../frontend && npm ci && npm run dev         # http://localhost:5173
```

## Тайминг (подставьте реальный дедлайн)
| Когда | Что |
|---|---|
| +0:00 – +1:00 | три задания параллельно |
| +1:00 | интеграция: Claude проверяет `main` целиком |
| +1:15 | FREEZE: только багфиксы, README, прогон демо вслух (90 с) |
| +1:30 | `git tag submission` + «Сдать решение» на платформе |
