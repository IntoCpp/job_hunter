@echo off
REM Start a dedicated Microsoft Edge instance for Job-Hunter browser-session retrieval.
REM See README.md section "Start the debug browser" for why this is required.
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\EdgeDebugProfile"
