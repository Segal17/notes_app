# Заметки

Настольное приложение для заметок на Python и Flet (Windows). Окно приложения
открывается с формы ввода, заметки отправляются по HTTP API в PostgreSQL,
который крутится в Docker на Raspberry Pi (см. `docker-compose.yml` и `manual`).

Стек: Python 3.11+, Flet (GUI), httpx (HTTP), pydantic (настройки в
`%APPDATA%\NotesApp\settings.json`). Сейчас в репозитории лежит минимальный
скелет: запуск окна, заготовка настроек и заготовка API-клиента.

Запуск на Windows: `run.bat` (создаст `.venv`, поставит зависимости из
`requirements.txt` и запустит `src/main.py`).

## Сборка в exe

Двойной клик по build_exe.bat. Скрипт:
- создаёт .venv, если нет;
- ставит зависимости и PyInstaller;
- собирает dist\NotesApp.exe (один файл, без консоли).

Готовый exe можно скопировать на любой Windows-ПК и запустить
без установки Python. Настройки хранятся в %APPDATA%\NotesApp\settings.json
и создаются при первом запуске.
