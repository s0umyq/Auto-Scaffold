@echo off
REM Auto-Scaffold GUI Launcher
echo Starting Auto-Scaffold GUI...
echo.
echo The GUI will be available at http://127.0.0.1:8765
echo Press Ctrl+C to stop
echo.
python -m auto_scaffold.gui.server
pause