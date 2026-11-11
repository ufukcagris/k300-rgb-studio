# K300 RGB Studio: testler -> exe -> kurulum dosyasi.   Kullanim:  .\scriptsuild.ps1
# Gerekenler: Python 3.10+, Inno Setup 6 (https://jrsoftware.org/isinfo.php  veya  winget install JRSoftware.InnoSetup)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
python scripts/make_icon.py
python scripts/sync_version.py
$version = (Select-String -Path k300fx\__init__.py -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value

python -m PyInstaller --noconfirm --clean K300RGBStudio.spec

# Paketlenmis exe'nin bagimliliklarini pencere acmadan sina
$out = Join-Path $env:TEMP "k300-selftest.json"
Start-Process -Wait -FilePath "dist\K300RGBStudio\K300RGBStudio.exe" -ArgumentList "--selftest", $out
Get-Content $out
$res = Get-Content $out -Raw | ConvertFrom-Json
if (-not ($res.qt.ok -and $res.hid.ok -and $res.paket.ok)) { throw "exe oz-testi basarisiz" }

# Inno Setup derleyicisini bul
$iscc = @(
  (Get-Command iscc -ErrorAction SilentlyContinue).Source,
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup bulunamadi. Kurmak icin: winget install JRSoftware.InnoSetup" }

& $iscc "/DAppVersion=$version" installer\setup.iss
Write-Host "Hazir: dist\K300RGBStudio-Setup-$version.exe"
