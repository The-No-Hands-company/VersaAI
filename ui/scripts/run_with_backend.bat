@echo off
REM VersaAI Full Stack Launcher (Windows)
REM Starts VersaAI backend + Flutter UI together

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║              VersaAI Full Stack Launcher                      ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Get project root (2 levels up from scripts directory)
cd /d "%~dp0"
cd ..\..
set PROJECT_ROOT=%CD%

echo 📁 Project root: %PROJECT_ROOT%
echo.

REM Start backend in background
echo 📡 Starting VersaAI WebSocket backend...
cd "%PROJECT_ROOT%"

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo    Using virtual environment...
    call .venv\Scripts\activate.bat
)

REM Start backend server in background
start /B python start_editor_bridge.py
set BACKEND_PID=%ERRORLEVEL%

echo    Backend URL: ws://localhost:8765
echo.

REM Wait for backend to start
echo ⏳ Waiting for backend to initialize (3 seconds)...
timeout /t 3 /nobreak >nul

echo ✅ Backend should be running
echo.

echo 🎨 Starting Flutter UI...
cd "%PROJECT_ROOT%\ui"

REM Install dependencies if needed
if not exist ".dart_tool" (
    echo    Installing Flutter dependencies...
    flutter pub get
)

echo    Platform: windows
echo.

REM Start Flutter app
flutter run -d windows

echo.
echo ✅ VersaAI Full Stack launcher exited
pause
