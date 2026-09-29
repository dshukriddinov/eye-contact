# Faqat paket ichidagi Maxine SDK sizning GPU ga mos kelmasa kerak (masalan RTX 40/30/20 seriya).
# GPU ga mos NVIDIA Maxine AR SDK v0.8.7 ni yuklab (~1.3 GB) o'rnatadi. Internet va administrator ruxsati kerak.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$gpu = (& nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>$null | Select-Object -First 1)
if (-not $gpu) { throw "nvidia-smi topilmadi. NVIDIA RTX GPU va drayver (>= 570) kerak." }
$name, $drv = $gpu.Split(",") | ForEach-Object { $_.Trim() }
Write-Host "GPU: $name, drayver $drv"
$arch = if ($name -match "RTX\s*(PRO\s*)?5\d{3}|Blackwell") { "blackwell" } elseif ($name -match "RTX\s*4\d{3}|Ada|L4\b|L40") { "ada" } `
        elseif ($name -match "RTX\s*3\d{3}|RTX A\d{4}|A10\b|A40") { "ampere" } elseif ($name -match "RTX\s*2\d{3}|GTX 16|Quadro RTX|T4\b") { "turing" } else { $null }
if (-not $arch) { throw "GPU arxitekturasi aniqlanmadi ($name). Qo'lda: https://www.nvidia.com/broadcast-sdk-resources" }
$bundled = Get-Content "runtime\maxine\ARCH.txt" -ErrorAction SilentlyContinue
if ($arch -eq $bundled) { Write-Host "Paket ichidagi SDK ($bundled) sizning GPU ga mos. O'rnatish shart emas."; exit 0 }
$sdk = "C:\Program Files\NVIDIA Corporation\NVIDIA AR SDK\nvARPose.dll"
if (Test-Path $sdk) { Write-Host "Tizimda SDK allaqachon bor: $sdk"; exit 0 }
New-Item -ItemType Directory -Force "runtime\download" | Out-Null
$exe = "runtime\download\nvidia_ar_sdk_installer_v0.8.7_$arch.exe"
if (-not (Test-Path $exe)) {
  Write-Host "Yuklanmoqda (~1.3 GB): $arch ..."
  curl.exe -L -o $exe "https://international.download.nvidia.com/Windows/broadcast/sdk/AR/nvidia_ar_sdk_installer_v0.8.7_$arch.exe"
}
Write-Host "O'rnatilmoqda (administrator ruxsati so'raladi)..."
$p = Start-Process -FilePath $exe -ArgumentList "/S" -Verb RunAs -PassThru -Wait
if (-not (Test-Path $sdk)) { throw "SDK o'rnatilmadi (kod $($p.ExitCode))." }
Write-Host "Tayyor. Endi EyeContact.bat ni ishga tushiring: dastur tizimdagi SDK ni o'zi topadi." -ForegroundColor Green
