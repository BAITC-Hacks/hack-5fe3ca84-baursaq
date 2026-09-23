# Задание: Aniyar — запуск одной командой, README, проверка, сдача

Ты — Codex-исполнитель Анияра. Лид и интегратор — Claude (ревьюит и проверяет `main`).
Сначала: `git pull origin main`, прочитай `AGENTS.md` и `README.md` (заготовка Умара с `[TODO]`).
База — `main`. Из ветки `codex/career-quest-foundation` можно брать идеи, но не копировать её структуру.

## Твои файлы (только они)
`README.md`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `run.py`, `data/test_profiles/**`,
`scripts/**`, `docs/**` (кроме `docs/tasks/*` других участников).
НЕ трогать: `backend/app/**`, `frontend/src/**` — нашёл баг → напиши в чат (бэк — Азамату/Claude, фронт — Умару).

## Задача по приоритету (≈60 мин)
1. **Запуск одной командой (обязательное требование ТЗ).**
   - `Dockerfile`: stage 1 `node:22-alpine` → `npm ci && npm run build` в `frontend/`;
     stage 2 `python:3.12-slim` + uv (`COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/`),
     `uv sync --frozen --no-dev` в `/app/backend`, копии `backend/`, `data/`, `frontend/dist`;
     `ENV DATA_DIR=/app/data/career_quest FRONTEND_DIST=/app/frontend/dist`;
     `CMD ["uv","run","--no-sync","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]` (workdir `/app/backend`).
   - `docker-compose.yml`: сервис `app`, порт `8000:8000`, `env_file: [{path: backend/.env, required: false}]`.
   - `run.py` для запуска без Docker: `uv sync` в backend → `npm ci && npm run build` → uvicorn :8000.
   - Проверить С ЧИСТОГО КЛОНА: `docker compose up --build` → http://localhost:8000 (UI) и `/api/health`.
2. **Тестовые профили как у жюри** → `data/test_profiles/employees.json` + `activity_history.csv` (формат
   датасета, id `T001…`), и `EXPECTED.md` с ожидаемыми СВОЙСТВАМИ (не один захардкоженный event_id):
   1) самый низкий навык Public Speaking + 3 неявки на похожее, System Design критичен для Senior;
   2) обучение пройдено после `last_review_date` → повторять его нельзя;
   3) очевидное мероприятие закрыто пререквизитом;
   4) remote-сотрудник, лучшие варианты офлайн;
   5) всё закрыто / нет подходящих активностей → «нет шага» с причиной.
3. **`scripts/eval_profiles.py`**: грузит профили через `POST /api/dataset/upload` (заголовок `X-Role: hr`),
   запрашивает рекомендации, печатает таблицу и PASS/FAIL по свойствам из EXPECTED.md. Работает против :8000.
4. **README (25 баллов из 100)** — закрыть все `[TODO]`: запуск одной командой (docker + `run.py`); ключ
   (`backend/.env`, `USE_MOCKS`); демо-сценарий (E0072 ru; E0052 kk; E0028 как пример ловушки «пройдено
   после оценки»); таблица факторов и весов (константы в начале `backend/app/services/engine.py`); агент
   (режим и инструменты — после отчёта Азамата); тестовые профили + команда eval; API включая
   `POST /employees/{id}/feedback`; приватность и права (демо-заголовки → в проде SSO); ограничения;
   команда и вклад каждого; раздел «Как мы использовали Codex» (скриншоты `docs/codex/`).
5. **Финал** (за 20–30 мин до дедлайна): pytest + build + docker с чистого клона + ручной сценарий →
   `git tag submission && git push origin submission` → на платформе нажать **«Сдать решение»**.

Коммиты `feat|docs(...): ... [codex]`, `git pull --rebase && git push`. В чат: SHA + что проверено.
