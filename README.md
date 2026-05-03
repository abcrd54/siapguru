# SiapGuru

SiapGuru adalah aplikasi desktop Windows untuk membantu guru mengelola nilai akhir raport lintas kelas dan mata pelajaran.

## Fitur Utama

- Aktivasi lisensi berbasis Firebase
- Profil guru global yang tetap
- Workspace per tahun ajaran dan semester
- Import siswa dan nilai
- Pengelolaan mapel, KKM, dan bobot per mapel
- Perhitungan nilai akhir raport
- Katrol nilai / penyesuaian ketuntasan
- Generate deskripsi raport
- Export laporan dan backup per workspace

## Alur Aplikasi

1. Aktivasi lisensi
2. Lengkapi profil guru
3. Pilih atau buat workspace
4. Kelola kelas, siswa, mapel, dan nilai
5. Buat raport dan unduh laporan

Setiap workspace mewakili satu periode akademik:
- `Tahun Ajaran`
- `Semester`

## Struktur Workspace

- Profil guru disimpan global untuk aplikasi
- Data akademik disimpan per workspace
- Backup dan export dipisah per workspace
- Restore dilakukan dari wizard pemilihan workspace

## Menjalankan Dari Source

Prasyarat:
- Python 3.12+
- Windows

Install dependency:

```powershell
pip install -r requirements.txt
```

Jalankan aplikasi:

```powershell
python main.py
```

## Konfigurasi Firebase

Production build tidak lagi membundel service account.

Set environment variable berikut di mesin build/admin:

```powershell
setx SIAPGURU_FIREBASE_CREDENTIALS "C:\secure\siapguru-firebase-admin.json"
setx SIAPGURU_FIREBASE_PROJECT_ID "siapguru-81acc"
```

Tutup lalu buka ulang terminal setelah menjalankan `setx`.

## Build EXE

Gunakan script release:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

Output build:
- `dist_release/SiapGuru.exe`

## Testing

Jalankan test:

```powershell
python -m unittest tests.test_app -v
```

Validasi sintaks:

```powershell
python -m compileall main.py app services pages ui tests
```

## Catatan Rilis v1.1

- Flow baru berbasis workspace per periode akademik
- Backup dan restore disesuaikan ke level workspace
- Perhitungan nilai dan raport dibuat lebih konsisten
- Pengamanan konfigurasi Firebase diperketat
- Build release dipisah ke `dist_release`
