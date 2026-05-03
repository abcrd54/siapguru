# Release Update Flow

## Firestore

Gunakan collection `app_releases`.

Dokumen minimal:

- `production`
- opsional `beta`

Contoh payload:

```json
{
  "app_id": "siapguru",
  "app_name": "SiapGuru",
  "channel": "production",
  "latest_version": "1.0.0",
  "minimum_version": "1.0.0",
  "force_update": false,
  "download_url": "https://siapdigital.web.id/download/siapguru-latest",
  "notes": [
    "Rilis awal SiapGuru untuk wali kelas dan guru mapel.",
    "Aktivasi lisensi memakai Firebase.",
    "File raport diexport ke Excel per siswa."
  ],
  "published_at": "2026-05-02T00:00:00+00:00",
  "updated_at": "2026-05-02T00:00:00+00:00"
}
```

Seed/update dokumen dari repo ini:

```powershell
python scripts/seed_app_release.py --channel production --latest-version 1.0.0 --minimum-version 1.0.0 --download-url https://siapdigital.web.id/download/siapguru-latest --dump-json
```

Jika update wajib:

```powershell
python scripts/seed_app_release.py --channel production --latest-version 1.0.1 --minimum-version 1.0.1 --force-update --download-url https://siapdigital.web.id/download/siapguru-1.0.1
```

## GitHub Release

Urutan rilis:

1. Commit source final.
2. Buat tag versi.
3. Push tag ke GitHub.
4. Buat release.
5. Upload `SiapGuru.exe`.
6. Salin URL download asset.
7. Update Firestore `download_url`.

Contoh git:

```powershell
git add .
git commit -m "release: v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

Di GitHub:

1. Buka repository.
2. Buka `Releases`.
3. Klik `Draft a new release`.
4. Pilih tag `v1.0.0`.
5. Isi judul `SiapGuru v1.0.0`.
6. Upload `dist/SiapGuru.exe`.
7. Publish release.

Dokumentasi resmi:

- GitHub Releases: https://docs.github.com/en/repositories/releasing-projects-on-github

## Domain Redirect

Pola yang disarankan:

- `https://siapdigital.web.id/download/siapguru-latest`
- `https://siapdigital.web.id/download/siapguru-1.0.0`

Target redirect:

- URL asset GitHub Releases

Jika project web Anda di Vercel, bisa pakai `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "redirects": [
    {
      "source": "/download/siapguru-latest",
      "destination": "https://github.com/USERNAME/REPO/releases/download/v1.0.0/SiapGuru.exe",
      "statusCode": 308
    },
    {
      "source": "/download/siapguru-1.0.0",
      "destination": "https://github.com/USERNAME/REPO/releases/download/v1.0.0/SiapGuru.exe",
      "statusCode": 308
    }
  ]
}
```

Atau pakai Vercel CLI:

```powershell
vercel redirects add /download/siapguru-latest https://github.com/USERNAME/REPO/releases/download/v1.0.0/SiapGuru.exe --status 308 --yes
vercel redirects add /download/siapguru-1.0.0 https://github.com/USERNAME/REPO/releases/download/v1.0.0/SiapGuru.exe --status 308 --yes
```

Dokumentasi resmi:

- Vercel Redirects: https://vercel.com/docs/routing/redirects
- Vercel CLI Redirects: https://vercel.com/docs/cli/redirects
