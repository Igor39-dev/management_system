# Management System

Веб-приложение для управления командой внутри компании: пользователи, команды, задачи, оценки работы, встречи и календарь событий.

## Стек

- **Backend:** FastAPI, SQLAlchemy (async), Alembic, Pydantic v2
- **БД:** PostgreSQL 15
- **Авторизация:** JWT
- **Админ-панель:** SQLAdmin
- **Контейнеризация:** Docker, Docker Compose

## Быстрый старт (Docker)
1. Склонировать репозиторий:

```sh 
git clone https://github.com/Igor39-dev/management_system
```

2. Скопируйте файл окружения и заполните переменные:

```bash
cp .env.example .env
```

3. Сгенерируйте `JWT_SECRET_KEY` и вставьте значение в `.env` (Windows, Linux, macOS):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

4. Запустите проект:

```bash
docker compose up -d --build
```

При старте контейнера приложения автоматически применяются миграции Alembic.

| Сервис | URL |
|--------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Админ-панель | http://localhost:8000/admin |
| Healthcheck | http://localhost:8000/health |

Остановка:

```bash
docker compose down
```

Удаление данных БД (volume):

```bash
docker compose down -v
```

## Локальный запуск

**Требования:** Python 3.12+, PostgreSQL 15.

1. Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Настройте `.env` (скопируйте из `.env.example`). Для локальной БД укажите `DB_HOST=localhost`.

4. Примените миграции:

```bash
alembic -c backend/alembic.ini upgrade head
```

5. Запустите сервер:

```bash
uvicorn backend.src.main:app --reload
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `DB_HOST` | Хост PostgreSQL (`localhost` локально, `db` в Docker) |
| `DB_PORT` | Порт PostgreSQL |
| `DB_USER` | Пользователь БД |
| `DB_PASS` | Пароль БД |
| `DB_NAME` | Имя базы данных |
| `JWT_SECRET_KEY` | Секретный ключ для JWT-токенов |
| `JWT_ALGORITHM` | Алгоритм подписи (по умолчанию `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access-токена в минутах |



## Проверка функционала

через Swagger: http://localhost:8000/docs

Авторизация работает через **cookie** `access_token` — после `register` или `login` браузер сохраняет сессию автоматически, повторный вход не нужен.


### 1. Регистрация администратора

`POST /auth/register`

```json
{
  "email": "admin@example.com",
  "password": "password123",
  "first_name": "Admin",
  "last_name": "User"
}
```

Новый пользователь получает роль `user`. Для создания команды нужна роль `admin` — назначьте её один раз в БД:

```bash
docker compose exec db psql -U postgres -d management_db -c "UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';"
```

> Локально без Docker: выполните тот же `UPDATE` через любой клиент PostgreSQL.

Затем выполните `POST /auth/login` с теми же email и паролем (или зарегистрируйтесь заново после смены роли).

### 2. Создание команды

`POST /teams`

```json
{
  "name": "Моя компания"
}
```

Сохраните из ответа поля `id` и `code` — код понадобится для приглашения сотрудников.

### 3. Вступление администратора в команду

Даже у admin для создания задач нужен `team_id`. Присоединитесь к своей команде:

`POST /teams/join`

```json
{
  "code": "КОД_ИЗ_ШАГА_2"
}
```

Проверка: `GET /auth/me` → в ответе должно быть `"team_id": 1`.

### 4. Регистрация и добавление сотрудника

1. Выйдите (`POST /auth/logout`) или откройте Swagger в режиме инкогнито.
2. `POST /auth/register` — зарегистрируйте сотрудника:

```json
{
  "email": "employee@example.com",
  "password": "password123",
  "first_name": "Ivan",
  "last_name": "Petrov"
}
```

3. `POST /teams/join` — тот же код команды.

4. Войдите снова как admin и назначьте сотруднику роль менеджера (нужна для создания задач):

`PATCH /teams/{team_id}/members/{user_id}/role`

```json
{
  "role": "manager"
}
```

`user_id` — id сотрудника из `GET /teams/{team_id}`.

### 5. Задачи

Войдите как менеджер (`POST /auth/login`).

**Создание задачи** — `POST /tasks`:

```json
{
  "title": "Подготовить отчёт",
  "description": "Отчёт за неделю",
  "assignee_id": 2,
  "deadline": "2026-06-20T18:00:00"
}
```

**Список задач** — `GET /tasks`

**Смена статуса** (исполнителем) — `PATCH /tasks/{task_id}`:

```json
{
  "status": "in_progress"
}
```

Допустимые статусы: `open`, `in_progress`, `done`.

**Комментарий** — `POST /tasks/{task_id}/comments`:

```json
{
  "text": "Начал работу над задачей"
}
```

**Оценка** (менеджером, после выполнения) — `POST /tasks/{task_id}/evaluation`:

```json
{
  "score": 5
}
```

**Свои оценки** (сотрудник) — `GET /evaluations/me` и `GET /evaluations/me/average`.

### 6. Встречи

`POST /meetings` (любой участник команды):

```json
{
  "title": "Планёрка",
  "description": "Еженедельная встреча",
  "start_at": "2026-06-15T10:00:00",
  "end_at": "2026-06-15T11:00:00",
  "participant_ids": [2]
}
```

**Список встреч** — `GET /meetings`

**Отмена** — `POST /meetings/{meeting_id}/cancel`

### 7. Календарь

`GET /calendar/month?year=2026&month=6` — задачи и встречи за месяц.

`GET /calendar/day?day=2026-06-15` — события за день.

### 8. Админ-панель

http://localhost:8000/admin — вход под пользователем с ролью `admin`.

## Тесты

```bash
pytest
```
