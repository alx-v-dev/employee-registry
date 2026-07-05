# Employee Registry

Server-rendered реестр сотрудников на FastAPI, SQLAlchemy 2.0, Jinja2 и SQLite по умолчанию.

## Запуск

Команды ниже рассчитаны на PowerShell в Windows.

1. Создать виртуальное окружение:

```powershell
py -m venv .venv
```

2. Активировать окружение:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Проверить, что используется Python из `.venv`:

```powershell
py -c "import sys; print(sys.executable)"
```

Ожидаемый путь:

```text
...\employee-registry\.venv\Scripts\python.exe
```

4. Установить зависимости:

```powershell
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
```

5. Применить миграции:

```powershell
py -m alembic upgrade head
```

6. Запустить приложение:

```powershell
py -m uvicorn app.main:app --reload
```

После запуска приложение доступно по адресу http://127.0.0.1:8000.

Для PostgreSQL можно передать строку подключения через переменную окружения `DATABASE_URL`.
Для запуска вне локального прототипа задайте собственный `SECRET_KEY`, чтобы session-cookie и CSRF-токены подписывались не demo-ключом.

## Проверки

При активированном виртуальном окружении:

```powershell
py -m pytest
```

## Возможности

- реестр сотрудников с фото, возрастом, ФИО, полом, телефоном и действиями;
- поиск по ФИО и телефону;
- фильтр по полу и возрастному диапазону;
- создание и редактирование через одну форму;
- загрузка фото до 200 КБ с увеличением при наведении;
- удаление сотрудника с подтверждением.
