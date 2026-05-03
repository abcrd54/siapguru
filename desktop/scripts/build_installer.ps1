param(
    [string]$InnoScript = ".\\installer\\SiapGuru.iss"
)

$ErrorActionPreference = "Stop"

$machinePath = [System.Environment]::GetEnvironmentVariable('Path','Machine')
$userPath = [System.Environment]::GetEnvironmentVariable('Path','User')
$env:Path = "$machinePath;$userPath"

if (-not (Get-Command iscc -ErrorAction SilentlyContinue)) {
    throw "Inno Setup Compiler (iscc) belum tersedia di PATH."
}

if (-not (Test-Path $InnoScript)) {
    throw "Script installer tidak ditemukan: $InnoScript"
}

iscc $InnoScript
