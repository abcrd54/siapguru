from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import (
    APP_VERSION,
    FIREBASE_CREDENTIALS_PATH,
    FIREBASE_PROJECT_ID,
    FIREBASE_RELEASES_COLLECTION,
    FIREBASE_RELEASE_CHANNEL,
    FIREBASE_UPDATE_CACHE_PATH,
)


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    minimum_version: str
    force_update: bool
    download_url: str
    notes: list[str]
    update_available: bool
    update_required: bool


class FirebaseUpdateChecker:
    def __init__(
        self,
        cache_path: Path | None = None,
        credentials_path: str | None = None,
        project_id: str | None = None,
        collection_name: str | None = None,
        channel: str | None = None,
    ) -> None:
        self.cache_path = cache_path or FIREBASE_UPDATE_CACHE_PATH
        self.credentials_path = str(credentials_path or FIREBASE_CREDENTIALS_PATH or "").strip()
        self.project_id = str(project_id or FIREBASE_PROJECT_ID or "").strip() or self._project_id_from_credentials()
        self.collection_name = str(collection_name or FIREBASE_RELEASES_COLLECTION or "app_releases").strip()
        self.channel = str(channel or FIREBASE_RELEASE_CHANNEL or "production").strip()
        self._client = None

    def check(self, current_version: str = APP_VERSION) -> UpdateInfo | None:
        try:
            payload = self._fetch_release_document()
            self._write_cache(payload)
        except Exception as exc:
            payload = self._read_cache()
            if not payload:
                raise RuntimeError(
                    "Pemeriksaan update tidak dapat dilakukan. Hubungkan internet dan periksa konfigurasi Firebase."
                ) from exc
        latest_version = str(payload.get("latest_version", "") or "").strip()
        minimum_version = str(payload.get("minimum_version", "") or "").strip() or latest_version
        download_url = str(payload.get("download_url", "") or "").strip()
        notes = payload.get("notes") or []
        if not latest_version or not download_url:
            return None
        if not isinstance(notes, list):
            notes = [str(notes)]
        force_update = bool(payload.get("force_update", False))
        update_available = self._compare_version(current_version, latest_version) < 0
        update_required = force_update or self._compare_version(current_version, minimum_version) < 0
        return UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            minimum_version=minimum_version,
            force_update=force_update,
            download_url=download_url,
            notes=[str(item).strip() for item in notes if str(item).strip()],
            update_available=update_available,
            update_required=update_required,
        )

    def _client_instance(self):
        if self._client is not None:
            return self._client
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError as exc:
            raise RuntimeError("Library Firebase belum terpasang.") from exc

        if self.credentials_path and not Path(self.credentials_path).exists():
            raise RuntimeError("File kredensial Firebase tidak ditemukan. Atur SIAPGURU_FIREBASE_CREDENTIALS dengan path yang valid.")
        if not self.credentials_path and not self.project_id:
            raise RuntimeError(
                "Konfigurasi Firebase belum lengkap. Atur SIAPGURU_FIREBASE_PROJECT_ID dan SIAPGURU_FIREBASE_CREDENTIALS."
            )

        app_name = "siapguru-update-checker"
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            if self.credentials_path:
                cred = credentials.Certificate(self.credentials_path)
                options = {"projectId": self.project_id} if self.project_id else None
                app = firebase_admin.initialize_app(cred, options=options, name=app_name)
            else:
                app = firebase_admin.initialize_app(options={"projectId": self.project_id} if self.project_id else None, name=app_name)
        self._client = firestore.client(app=app)
        return self._client

    def _fetch_release_document(self) -> dict:
        client = self._client_instance()
        document = client.collection(self.collection_name).document(self.channel).get()
        if not document.exists:
            raise ValueError("Dokumen update aplikasi tidak ditemukan.")
        payload = document.to_dict() or {}
        return payload

    def _read_cache(self) -> dict:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_cache(self, payload: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _project_id_from_credentials(self) -> str:
        if not self.credentials_path:
            return ""
        path = Path(self.credentials_path)
        if not path.exists():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return ""
        return str(data.get("project_id", "") or "").strip()

    def _compare_version(self, current: str, target: str) -> int:
        def normalize(value: str) -> list[int]:
            return [int(part) for part in value.split(".") if part.isdigit()]

        current_parts = normalize(current)
        target_parts = normalize(target)
        max_len = max(len(current_parts), len(target_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        target_parts.extend([0] * (max_len - len(target_parts)))
        if current_parts < target_parts:
            return -1
        if current_parts > target_parts:
            return 1
        return 0
