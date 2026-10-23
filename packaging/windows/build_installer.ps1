# Build the Windows installer locally (PowerShell, from the repo root):
#   pip install pyinstaller pillow
#   powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1
# Needs Inno Setup 6 (https://jrsoftware.org/isdl.php) — iscc.exe on PATH or in the default folder.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")

$version = python packaging\make_version_info.py
python -m PyInstaller --noconfirm --clean packaging\vectra.spec

$thai = "packaging\windows\Thai.isl"
$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not $iscc -or -not (Test-Path $iscc)) { $iscc = "$env:ProgramFiles\Inno Setup 7\ISCC.exe" }
$bundled = Join-Path (Split-Path $iscc) "Languages\Thai.isl"
if (-not (Test-Path $bundled) -and -not (Test-Path $thai)) {
  try {
    Invoke-WebRequest -UseBasicParsing -OutFile $thai `
      "https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Thai.isl"
  } catch { Write-Warning "Thai wizard language not downloaded; installer will be English only." }
}

& $iscc "/DAppVersion=$version" packaging\windows\vectra.iss
if ($LASTEXITCODE -ne 0 -and (Test-Path $thai)) {
  Write-Warning "Retrying without the downloaded Thai.isl (version mismatch?)"
  Remove-Item $thai
  & $iscc "/DAppVersion=$version" packaging\windows\vectra.iss
}
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
Get-ChildItem dist\installer
