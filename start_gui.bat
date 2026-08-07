@echo off
REM Auto-Scaffold GUI Launcher
REM Opens the GUI server in a new terminal window
echo.
echo ============================================================
echo   Auto-Scaffold CLI - GUI Launcher
echo ============================================================
echo.
echo Starting Auto-Scaffold GUI in a new window...
echo.
echo The GUI will be available at: http://127.0.0.1:8080
echo.
echo Features available in the GUI:
echo   - Project scanning ^& language detection
echo   - Test generation for your codebase
echo   - Test execution with live results
echo   - AI-powered fix proposals
echo   - Interactive review ^& approval of fixes
echo.
echo Press Ctrl+C in the NEW window to stop the server
echo The server logs will appear in the new terminal window
echo ============================================================
echo.

REM Launch in a new terminal window - works from both cmd and PowerShell
cmd /c start "Auto-Scaffold GUI" cmd /d "c:\Users\HP\OneDrive\Desktop\Hackathon\Auto-Scaffold" /k python -m uvicorn auto_scaffold.gui.server:app --host 127.0.0.1 --port 8080 --log-level info