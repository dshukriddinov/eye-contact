@echo off
rem Faqat dastur "Maxine SDK ishga tushmadi" desa kerak (RTX 40/30/20 seriya GPU). Internet va administrator ruxsati kerak.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SDK_ornatish.ps1"
echo.
pause
