# Publish Checklist v1.0.0

## File yang diupload

- `installer_output/Setup-SiapGuru-1.0.0.exe`
- opsional `dist/SiapGuru.exe`
- isi release notes dari `release/RELEASE_NOTES_v1.0.0.md`

## GitHub Release

1. Buat repository atau buka repository release Anda.
2. Buat tag `v1.0.0`.
3. Buat release baru dengan judul `SiapGuru v1.0.0`.
4. Upload `Setup-SiapGuru-1.0.0.exe`.
5. Jika ingin build portable, upload juga `SiapGuru.exe`.
6. Tempel isi `release/RELEASE_NOTES_v1.0.0.md`.
7. Publish release.

## Redirect domain

Set redirect:

- `/download/siapguru-latest`
- `/download/siapguru-1.0.0`

arah ke asset GitHub Release `Setup-SiapGuru-1.0.0.exe`.

## Update Firestore

Update dokumen `app_releases/production`:

- `latest_version = 1.0.0`
- `minimum_version = 1.0.0`
- `force_update = false`
- `download_url = https://siapdigital.web.id/download/siapguru-latest`
