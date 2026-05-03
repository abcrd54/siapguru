# Inno Setup

## Sumber Build

- Script installer: `installer/SiapGuru.iss`
- Source aplikasi: `dist_release/SiapGuru.exe`

## Compile

Gunakan script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

Atau langsung:

```powershell
iscc installer\SiapGuru.iss
```

## Output

Installer akan dibuat di:

```text
installer_output\Setup-SiapGuru-v1.1.exe
```
