@echo off
setlocal

cd /d "%~dp0"

echo === Проверка venv ===
if not exist .venv (
    echo Создаю venv...
    python -m venv .venv
    if errorlevel 1 goto :error
)

echo === Активация venv ===
call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

echo === Установка зависимостей ===
pip install -r requirements.txt
if errorlevel 1 goto :error

echo === Установка PyInstaller ===
pip install pyinstaller
if errorlevel 1 goto :error

echo === Очистка старых сборок ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist NotesApp.spec del /q NotesApp.spec

echo === Сборка exe ===
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name NotesApp ^
    --version-file version_info.txt ^
    --collect-all flet ^
    --collect-all flet_runtime ^
    --collect-all flet_core ^
    --collect-all speech_recognition ^
    --collect-all pyaudio ^
    --hidden-import src.config ^
    --hidden-import src.db_client ^
    --hidden-import src.speech ^
    --hidden-import src.ui.note_form ^
    --hidden-import src.ui.settings ^
    src\main.py

if errorlevel 1 goto :error

echo.
echo === ГОТОВО ===
echo Файл: dist\NotesApp.exe
goto :end

:error
echo.
echo === ОШИБКА СБОРКИ ===
echo Смотри сообщения выше.

:end
endlocal
pause
