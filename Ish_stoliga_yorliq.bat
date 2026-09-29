@echo off
rem Ish stoliga "Eye Contact" yorlig'ini qo'yadi (logotip: assets\eyecontact.ico).
cd /d "%~dp0"
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Eye Contact.lnk')); $s.TargetPath = '%~dp0EyeContact.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Description = 'Eye Contact - nigohni kameraga qaratish'; $s.IconLocation = '%~dp0assets\eyecontact.ico,0'; $s.Save(); Write-Host 'Yorliq yaratildi.'"
pause
