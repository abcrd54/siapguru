# SiapGuru v1.1

SiapGuru v1.1 membawa perubahan besar pada alur kerja aplikasi agar lebih cocok dipakai guru lintas kelas dan mata pelajaran untuk penyusunan nilai akhir raport.

## Perubahan Utama

- Flow aplikasi sekarang berbasis `workspace` per `tahun ajaran` dan `semester`
- Startup disederhanakan menjadi:
  - aktivasi lisensi
  - profil guru
  - pilih atau buat workspace
- Backup sekarang per workspace aktif
- Restore dipindahkan ke wizard pemilihan workspace
- Mata pelajaran sekarang mendukung:
  - KKM per mapel
  - bobot nilai per mapel
- Perhitungan nilai akhir dan raport dibuat lebih konsisten
- Tampilan dashboard, nilai, export, dan workspace chooser dirapikan

## Perbaikan Teknis

- Hardening konfigurasi Firebase
- Build release tidak lagi membundel service account
- Update checker memakai cache release lokal
- Flow nilai akhir, katrol nilai, dan raport diselaraskan
- Perbaikan validasi lisensi Firebase
- Build script release dibuat lebih konsisten

## Catatan Build

Artifact Windows:
- `SiapGuru.exe`

## Catatan Upgrade

- Struktur workspace lama sudah disesuaikan ke model per periode akademik
- Build baru memakai konfigurasi Firebase melalui environment variable
