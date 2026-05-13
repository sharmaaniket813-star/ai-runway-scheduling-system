@echo off
title Runway Assistant ATC — Birmingham Airport

echo.
echo  > RUNWAY ASSISTANT ATC ^| Birmingham Airport (EGBB/BHX)
echo  -------------------------------------------------------
echo.

if "%ANTHROPIC_API_KEY%"=="" (
    set /p ANTHROPIC_API_KEY="Enter your Anthropic API key (or press Enter to skip): "
)

echo.
echo  Starting server on http://localhost:8000
echo  Open that URL in your browser.
echo  Press Ctrl+C to stop.
echo.

cd /d "%~dp0backend"
python server.py
pause
