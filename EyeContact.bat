@echo off
rem Eye Contact. Ikki marta bosing. Hech narsa o'rnatish shart emas: Python, ffmpeg va Maxine SDK paket ichida (runtime\).
cd /d "%~dp0"
if not exist "runtime\python\pythonw.exe" (
  echo runtime\python topilmadi. Paket to'liq nusxalanmagan.
  pause
  exit /b 1
)
start "" "runtime\python\pythonw.exe" -m eyecontact.gui
