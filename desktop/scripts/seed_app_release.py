from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


DEFAULT_RELEASE = {
    "app_id": "siapguru",
    "app_name": "SiapGuru",
    "channel": "production",
    "latest_version": "1.0.0",
    "minimum_version": "1.0.0",
    "force_update": False,
    "download_url": "https://siapdigital.web.id/download/siapguru-latest",
    "notes": [
        "Rilis awal SiapGuru untuk wali kelas dan guru mapel.",
        "Aktivasi lisensi memakai Firebase.",
        "File raport diexport ke Excel per siswa.",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed/update metadata rilis aplikasi ke Firestore.")
    parser.add_argument("--credentials", default="servicekey-py.json", help="Path service account Firebase.")
    parser.add_argument("--collection", default="app_releases", help="Nama collection Firestore.")
    parser.add_argument("--channel", default="production", help="Nama dokumen channel release.")
    parser.add_argument("--latest-version", default=DEFAULT_RELEASE["latest_version"])
    parser.add_argument("--minimum-version", default=DEFAULT_RELEASE["minimum_version"])
    parser.add_argument("--force-update", action="store_true", help="Paksa update untuk semua versi di bawah latest.")
    parser.add_argument("--download-url", default=DEFAULT_RELEASE["download_url"])
    parser.add_argument("--notes", nargs="*", default=DEFAULT_RELEASE["notes"])
    parser.add_argument("--dump-json", action="store_true", help="Cetak payload final setelah ditulis.")
    return parser.parse_args()


def get_firestore_client(credentials_path: str):
    app_name = "siapguru-release-seeder"
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        cred = credentials.Certificate(credentials_path)
        app = firebase_admin.initialize_app(
            cred,
            options={"projectId": cred.project_id},
            name=app_name,
        )
    return firestore.client(app=app)


def main() -> int:
    args = parse_args()
    credentials_path = Path(args.credentials)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Service account tidak ditemukan: {credentials_path}")

    client = get_firestore_client(str(credentials_path))
    now = datetime.now(UTC).isoformat()
    payload = {
        **DEFAULT_RELEASE,
        "channel": args.channel,
        "latest_version": args.latest_version,
        "minimum_version": args.minimum_version,
        "force_update": bool(args.force_update),
        "download_url": args.download_url,
        "notes": args.notes,
        "published_at": now,
        "updated_at": now,
    }
    client.collection(args.collection).document(args.channel).set(payload, merge=True)
    print(f"Updated Firestore: {args.collection}/{args.channel}")
    if args.dump_json:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
