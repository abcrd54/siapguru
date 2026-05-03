param(
    [string]$Tag = "v1.1",
    [string]$Title = "SiapGuru v1.1",
    [string]$ExePath = ".\\dist_release\\SiapGuru.exe",
    [string]$NotesPath = ".\\RELEASE_NOTES_v1.1.md"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) belum terpasang."
}

if (-not (Test-Path $ExePath)) {
    throw "File EXE tidak ditemukan: $ExePath"
}

if (-not (Test-Path $NotesPath)) {
    throw "File release notes tidak ditemukan: $NotesPath"
}

$tagExists = $false
gh release view $Tag *> $null
if ($LASTEXITCODE -eq 0) {
    $tagExists = $true
}

if (-not $tagExists) {
    gh release create $Tag $ExePath --title $Title --notes-file $NotesPath
}
else {
    gh release upload $Tag $ExePath --clobber
    gh release edit $Tag --title $Title --notes-file $NotesPath
}

Write-Host "Release $Tag selesai diperbarui."
