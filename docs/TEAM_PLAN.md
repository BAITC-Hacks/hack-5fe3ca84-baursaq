# План на ~3 часа: кто что делает (Career Quest)

Контекст задачи, ловушки данных, API-контракт и владение файлами — в `AGENTS.md` §0.
Codex читает `AGENTS.md` автоматически, поэтому в промптах ниже достаточно ссылаться на него.

## 0. Старт для каждого (5 минут)

```bash
git clone https://github.com/BAITC-Hacks/hack-5fe3ca84-baursaq.git
cd hack-5fe3ca84-baursaq
# коммиты засчитываются ТВОЕМУ аккаунту, только если email привязан к нему на GitHub
git config user.name  "<твой GitHub username>"
git config user.email "<email, привязанный к GitHub>"

cd backend && uv sync && cp .env.example .env     # ключ OPENAI_API_KEY вписать в .env
uv run uvicorn app.main:app --reload               # http://localhost:8000/docs
cd ../frontend && npm i && npm run dev             # http://localhost:5173
```

## 1. Git-процесс (без конфликтов и с коммитами у всех)

- Каждый работает в **своих папках** (см. «Владение файлами» в `AGENTS.md`). Работаем прямо в `main`,
  маленькими коммитами, пушим каждые 20–30 минут:
  ```bash
  git pull --rebase
  git add <свои файлы>
  git commit -m "feat(frontend): skill bars vs target grade [codex]"
  git pull --rebase && git push
  ```
- Формат: `feat|fix|docs|chore(backend|frontend|data|docs): что сделано`. Код от Codex — тег `[codex]`,
  скриншоты сессий Codex — в `docs/codex/` (это доказательство обязательного использования Codex).
- Если Codex работает в облаке и открывает PR — мёржим сразу после беглого просмотра, не копим.
- Конфликт в `package-lock.json` / `uv.lock` — не правим руками: берём версию из `main`
  и заново делаем `npm i` / `uv sync`.
- Перед дедлайном C ставит тег: `git tag submission && git push origin submission`.
  Правила о коммитах после дедлайна уточнить у организаторов; до ответа после тега — только README/документация.

## 2. Workstream A — Backend/AI (`backend/**`)

Фундамент (стор, движок, API, fallback-объяснения) закладывается первым коммитом. Дальше A делает:

- **A1. Агентный LLM-слой** (`backend/app/agents/recommender.py`) — главное «agentic»-место для жюри.
- **A2. Качество объяснений:** ≥3 фактора с цифрами, блок «почему не самый низкий навык», язык сотрудника (kk/ru/en).
- **A3. «Не сейчас»:** `POST /api/employees/{id}/feedback` → запись `declined` (self). Уважаем добровольность.
- **A4. Скорость:** кэш рекомендаций по (сотрудник, версия данных, язык), прогрев для демо-профилей на старте.

Промпт для Codex (A1):
```
Прочитай AGENTS.md §0 и backend/app/agents/recommender.py. Переделай LLM-часть в настоящего агента
на OpenAI Agents SDK (пакет openai-agents уже в pyproject): инструменты-обёртки над services/engine.py
(get_profile_summary, get_skill_gaps, get_history_signals, list_candidates, simulate_plan).
Агент обязан выбирать мероприятия ТОЛЬКО из list_candidates, возвращать структурированный вывод
(1–3 event_id по порядку, rationale на языке сотрудника с ≥3 факторами и цифрами, why_not для самого
низкого навыка), не больше 4 вызовов инструментов, общий таймаут settings.llm_timeout_s.
Каждый вызов инструмента добавляй в trace ответа. При любой ошибке/таймауте — текущий
детерминированный fallback. Сохрани сигнатуру recommend() и схему RecommendationResponse.
Добавь pytest: с USE_MOCKS=true ответ приходит и содержит ≥1 рекомендацию с ≥3 факторами.
```

## 3. Workstream B — Frontend/Demo (`frontend/**`)

- **B1. Каркас:** шапка с переключателем роли (Сотрудник: выбор из `/api/employees` | HR) и языка (kk/ru/en);
  `src/api/client.ts` сам подставляет заголовки `X-Role` / `X-Employee-Id`.
- **B2. Экран сотрудника:** карточка (имя, роль, грейд, стаж, цель); траектория Junior→…→Lead с готовностью %;
  навыки: эффективный vs требуемый для цели, критичные отмечены, бейдж «+1 после оценки»;
  история (пройдено / не пришёл / отказ); список доступных шагов.
- **B3. Рекомендации:** кнопка «Подобрать шаги» → анимация trace-шагов агента → 1–3 карточки
  (формат, ближайшая сессия, rationale, чипы факторов, «System Design 3→4», готовность после)
  + блок «Почему не …» + кнопки «Отметить пройденным» / «Не сейчас».
- **B4. Прогресс:** после «пройдено» — тост «до → после», полоски навыков и % готовности анимированно
  меняются, рекомендации перезапрашиваются.
- **B5. HR-экран:** бар-чарт отстающих навыков, таблица участия по активностям, «без шага» (с причиной),
  «выпадающие»; кнопка «Загрузить профили» (drag&drop файлов → результат → ссылки на загруженных) и «Сброс».
- **B6. Полировка:** состояния загрузки / ошибок / пусто; никаких рейтингов сотрудников.

Промпт для Codex (B2+B3):
```
Прочитай AGENTS.md §0 и frontend/src/api/types.ts. Сделай страницу сотрудника в
frontend/src/pages/EmployeePage.tsx на React + Tailwind + recharts + lucide-react: карточка профиля,
траектория грейдов с готовностью %, навыки (эффективный уровень против требуемого для цели, критичные
выделены, бейдж «+N после оценки» если effective > assessed), история участия, доступные шаги.
Панель рекомендаций: кнопка вызывает POST /api/employees/{id}/recommendations через src/api/client.ts,
пока ждём — показывай шаги из trace по одному; затем 1–3 карточки: rationale, чипы factors, gains
«навык before→after», readiness_after_pct, блок rejected «Почему не …», кнопка «Отметить пройденным»
(POST /complete) — после ответа анимируй изменения и перезапроси рекомендации. Чисто, светлая тема,
акцент — зелёный Halyk (#00805F). Без лидербордов.
```

## 4. Workstream C — Product/QA/Ops (`README.md`, `docs/**`, `data/test_profiles/**`, `scripts/**`, Docker)

- **C1. Тестовые «ловушки»** в `data/test_profiles/` (формат датасета: `employees.json` + `activity_history.csv`),
  3–5 профилей, для каждого — ожидаемый правильный ответ в `data/test_profiles/EXPECTED.md`:
  1) самый низкий навык Public Speaking, но 3 пропуска похожих; System Design критичен для Senior;
  2) обучение пройдено после `last_review_date` — наивный подход рекомендует уже пройденное;
  3) очевидное мероприятие закрыто пререквизитом — нужен путь через другое;
  4) remote-сотрудник, лучшие варианты офлайн; 5) Lead без цели / всё пройдено → «нет шага».
- **C2. `scripts/eval_profiles.py`:** грузит профили через `/api/dataset/upload`, запрашивает рекомендации,
  печатает таблицу и PASS/FAIL против ожиданий. Прогонять после каждого изменения движка.
- **C3. Запуск одной командой:** `Dockerfile` (multi-stage: сборка фронта → Python + uv; FastAPI раздаёт
  `frontend/dist`) + `docker-compose.yml` → `docker compose up --build` → http://localhost:8000.
- **C4. Деплой** (Render / Railway из Dockerfile) + keep-alive пинг `/api/health` каждые 5–10 минут.
- **C5. README.md — 25 баллов:** проблема → решение → скриншоты → архитектура (mermaid) → как считается
  рекомендация (факторы, веса, эффективные навыки) → agentic-поток → запуск одной командой → загрузка профилей
  → API → приватность/права/добровольность → ограничения и что дальше. Участников оставить.
- **C6. Питч:** 90 секунд + 1 слайд + бэкап-видео, скриншоты Codex в `docs/codex/`, раздел 8 `AGENTS.md`.

Промпт для Codex (C3):
```
Прочитай AGENTS.md. Создай в корне Dockerfile (stage 1: node:22-alpine, npm ci + npm run build в frontend/;
stage 2: python:3.12-slim + uv из ghcr.io/astral-sh/uv, uv sync --frozen --no-dev в backend/, копия data/
и frontend/dist; ENV DATA_DIR=/app/data/career_quest FRONTEND_DIST=/app/frontend/dist;
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000) и docker-compose.yml с одним сервисом app,
портом 8000:8000 и необязательным env_file backend/.env. Добавь .dockerignore (node_modules, .venv, dist).
Проверь `docker compose up --build` и что http://localhost:8000 открывает фронт, а /api/health отвечает.
```

## 5. Контрольные точки (подставьте реальное время)

| Когда | Что должно быть в `main` | Кто |
|---|---|---|
| T+0:15 | фундамент бэка, контракт, скелет фронта | A |
| T+0:45 | фронт рисует профиль с реального API; C1 — 3 ловушки готовы | B, C |
| T+1:30 | GATE-2: LLM-рекомендация на экране; eval-скрипт гоняется | A, B, C |
| T+2:00 | docker compose + деплой; README-черновик | C |
| T+2:30 | FREEZE: только багфиксы, демо-данные, прогон питча | все |
| T+3:00 | сабмит, тег `submission` | C |
