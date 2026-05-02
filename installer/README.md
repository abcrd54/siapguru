# Inno Setup

## Prasyarat

Install Inno Setup 6.

Download resmi:

- https://jrsoftware.org/isinfo.php

## File

- Script installer: `installer/SiapGuru.iss`
- Source aplikasi: `dist/SiapGuru.exe`

## Compile

Jika `iscc.exe` sudah ada di PATH:

```powershell
iscc installer\SiapGuru.iss
```

Jika belum ada di PATH:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\SiapGuru.iss
```

## Output

Installer akan dibuat di:

```text
installer_output\Setup-SiapGuru-1.0.0.exe
```
