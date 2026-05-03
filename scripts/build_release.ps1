$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$distDir = Join-Path $root "dist_release"
$workDir = Join-Path $root "build_release"

python -m PyInstaller SiapGuru.spec --distpath $distDir --workpath $workDir --clean --noconfirm
