from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import (
    APP_VERSION,
    FIREBASE_COLLECTION,
    FIREBASE_CREDENTIALS_PATH,
    FIREBASE_LICENSE_CACHE_PATH,
    FIREBASE_PROJECT_ID,
    LICENSE_SOURCE,
    LOCAL_LICENSE_KEYS_PATH,
    LOCAL_LICENSE_PATH,
)
from app.workspace import MODE_LABELS


@dataclass
class LicenseProfile:
    source: str
    enabled_modes: list[str]
    customer_name: str = ""
    active_key: str = ""
    notes: str = ""
    is_activated: bool = False


class BaseLicenseProvider:
    source_name = "base"

    def get_profile(self) -> LicenseProfile:
        raise NotImplementedError

    def activate_key(self, key: str) -> LicenseProfile:
        raise NotImplementedError

    def get_activation_hint(self) -> str:
        return ""


class LocalLicenseProvider(BaseLicenseProvider):
    source_name = "local"

    def __init__(self, license_path: Path | None = None, keys_path: Path | None = None) -> None:
        self.license_path = license_path or LOCAL_LICENSE_PATH
        self.keys_path = keys_path or LOCAL_LICENSE_KEYS_PATH

    def get_profile(self) -> LicenseProfile:
        self._ensure_files()
        state = self._read_json(self.license_path, self._default_state())
        if state.get("is_activated") is not True:
            return LicenseProfile(
                source=self.source_name,
                enabled_modes=[],
                customer_name=str(state.get("customer_name", "") or ""),
                active_key="",
                notes="Aplikasi belum diaktivasi. Masukkan key untuk membuka dashboard guru.",
                is_activated=False,
            )
        enabled_modes = self._clean_modes(state.get("enabled_modes", []))
        if not enabled_modes:
            return LicenseProfile(
                source=self.source_name,
                enabled_modes=[],
                customer_name=str(state.get("customer_name", "") or ""),
                active_key="",
                notes="Key aktif tidak memiliki mode yang valid.",
                is_activated=False,
            )
        return LicenseProfile(
            source=self.source_name,
            enabled_modes=enabled_modes,
            customer_name=str(state.get("customer_name", "") or ""),
            active_key=str(state.get("active_key", "") or ""),
            notes=str(state.get("notes", "") or ""),
            is_activated=True,
        )

    def activate_key(self, key: str) -> LicenseProfile:
        self._ensure_files()
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Key wajib diisi.")
        catalog = self._read_json(self.keys_path, self._default_keys())
        if not isinstance(catalog, list):
            catalog = self._default_keys()
        match = next(
            (
                item
                for item in catalog
                if isinstance(item, dict) and str(item.get("key", "")).strip().lower() == normalized_key.lower()
            ),
            None,
        )
        if not match:
            raise ValueError("Key tidak valid.")
        enabled_modes = self._clean_modes(match.get("enabled_modes", []))
        if not enabled_modes:
            raise ValueError("Key valid, tetapi belum memiliki workspace aktif.")
        state = {
            "source": self.source_name,
            "customer_name": str(match.get("customer_name", "Testing User")),
            "active_key": str(match.get("key", normalized_key)),
            "enabled_modes": enabled_modes,
            "notes": str(match.get("notes", "Aktivasi lokal berhasil.")),
            "is_activated": True,
        }
        self.license_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return LicenseProfile(
            source=self.source_name,
            enabled_modes=enabled_modes,
            customer_name=state["customer_name"],
            active_key=state["active_key"],
            notes=state["notes"],
            is_activated=True,
        )

    def get_activation_hint(self) -> str:
        return (
            "Testing lokal aktif. Gunakan key dari file "
            f"{self.keys_path} lalu aktivasi sekali sebelum workspace bisa dibuka."
        )

    def _ensure_files(self) -> None:
        self.license_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.license_path.exists():
            self.license_path.write_text(json.dumps(self._default_state(), indent=2), encoding="utf-8")
        if not self.keys_path.exists():
            self.keys_path.write_text(json.dumps(self._default_keys(), indent=2), encoding="utf-8")

    def _read_json(self, path: Path, default):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = default
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return data

    def _clean_modes(self, modes: list[str] | tuple[str, ...] | object) -> list[str]:
        if not isinstance(modes, (list, tuple)):
            return []
        cleaned: list[str] = []
        for mode in modes:
            if mode in MODE_LABELS and mode not in cleaned:
                cleaned.append(mode)
        return cleaned

    def _default_state(self) -> dict:
        return {
            "source": self.source_name,
            "customer_name": "",
            "active_key": "",
            "enabled_modes": [],
            "notes": "Aplikasi belum diaktivasi.",
            "is_activated": False,
        }

    def _default_keys(self) -> list[dict]:
        return [
            {
                "key": "SG-GURU-001",
                "customer_name": "Testing Guru",
                "enabled_modes": ["guru"],
                "notes": "Key testing lokal untuk membuka dashboard guru.",
            },
        ]


class FirebaseLicenseProvider(BaseLicenseProvider):
    source_name = "firebase"

    def __init__(
        self,
        cache_path: Path | None = None,
        credentials_path: str | None = None,
        project_id: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.cache_path = cache_path or FIREBASE_LICENSE_CACHE_PATH
        self.credentials_path = str(credentials_path or FIREBASE_CREDENTIALS_PATH or "").strip()
        self.project_id = str(project_id or FIREBASE_PROJECT_ID or "").strip() or self._project_id_from_credentials()
        self.collection_name = str(collection_name or FIREBASE_COLLECTION or "licenses").strip()
        self._client = None

    def get_profile(self) -> LicenseProfile:
        cached = self._read_cache()
        if cached.get("is_activated") is not True:
            return LicenseProfile(
                source=self.source_name,
                enabled_modes=[],
                notes="Aplikasi belum diaktivasi. Masukkan key Firebase untuk membuka dashboard guru.",
                is_activated=False,
            )
        if self._is_cache_still_valid(cached):
            return self._profile_from_cache(cached, offline=True)
        active_key = str(cached.get("active_key", "") or "").strip()
        if not active_key:
            return LicenseProfile(
                source=self.source_name,
                enabled_modes=[],
                notes="Cache lisensi Firebase tidak lengkap. Aktivasi ulang diperlukan.",
                is_activated=False,
            )
        try:
            document = self._fetch_license_document(active_key)
            self._validate_license_document(document, active_key)
            self._ensure_device_allowed(document)
            cache = self._build_cache(document, active_key)
            self._write_cache(cache)
            return self._profile_from_cache(cache, offline=False)
        except Exception:
            if self._is_cache_still_valid(cached):
                return self._profile_from_cache(cached, offline=True)
            return LicenseProfile(
                source=self.source_name,
                enabled_modes=[],
                customer_name=str(cached.get("customer_name", "") or ""),
                active_key="",
                notes="Lisensi Firebase tidak dapat diverifikasi dan masa offline sudah habis.",
                is_activated=False,
            )

    def activate_key(self, key: str) -> LicenseProfile:
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Key wajib diisi.")
        document = self._fetch_license_document(normalized_key)
        self._validate_license_document(document, normalized_key)
        self._ensure_device_allowed(document)
        self._register_device(document)
        refreshed = self._fetch_license_document(normalized_key)
        cache = self._build_cache(refreshed, normalized_key)
        self._write_cache(cache)
        return self._profile_from_cache(cache, offline=False)

    def get_activation_hint(self) -> str:
        return (
            "Validasi key dilakukan ke Firebase Firestore. "
            "Aplikasi akan menyimpan cache lokal agar tetap bisa dibuka offline sesuai batas hari yang diizinkan."
        )

    def _client_instance(self):
        if self._client is not None:
            return self._client
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError as exc:
            raise RuntimeError("Library Firebase belum terpasang. Jalankan instalasi dependency terbaru.") from exc

        if self.credentials_path and not Path(self.credentials_path).exists():
            raise RuntimeError("File kredensial Firebase tidak ditemukan. Atur SIAPGURU_FIREBASE_CREDENTIALS dengan path yang valid.")
        if not self.credentials_path and not self.project_id:
            raise RuntimeError(
                "Konfigurasi Firebase belum lengkap. Atur SIAPGURU_FIREBASE_PROJECT_ID dan SIAPGURU_FIREBASE_CREDENTIALS."
            )

        app_name = "siapguru-license"
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

    def _fetch_license_document(self, key: str) -> dict:
        client = self._client_instance()
        document = client.collection(self.collection_name).document(key).get()
        if document.exists:
            payload = document.to_dict() or {}
            payload["docId"] = document.id
            return payload
        matches = list(
            client.collection(self.collection_name).where("license_key", "==", key).limit(1).stream()
        )
        if not matches:
            raise ValueError("Key tidak valid.")
        payload = matches[0].to_dict() or {}
        payload["docId"] = matches[0].id
        return payload

    def _validate_license_document(self, payload: dict, key: str) -> None:
        stored_key = str(payload.get("license_key", "") or "").strip()
        document_key = str(payload.get("docId", "") or "").strip()
        if stored_key and stored_key != key:
            raise ValueError("Key tidak cocok dengan data Firebase.")
        if not stored_key and document_key and document_key != key:
            raise ValueError("Key tidak cocok dengan data Firebase.")
        if str(payload.get("app_id", "") or "").strip().lower() != "siapguru":
            raise ValueError("Key ini bukan untuk aplikasi SiapGuru.")
        if str(payload.get("status", "") or "").strip().lower() != "active":
            raise ValueError("Status lisensi tidak aktif.")
        minimum_version = str(payload.get("minimum_app_version", "") or "").strip()
        if minimum_version and self._compare_version(APP_VERSION, minimum_version) < 0:
            raise ValueError(f"Aplikasi harus diperbarui minimal ke versi {minimum_version}.")
        expired_at = self._parse_datetime(payload.get("expired_at"))
        if expired_at and expired_at < datetime.now(UTC):
            raise ValueError("Lisensi sudah kedaluwarsa.")

    def _ensure_device_allowed(self, payload: dict) -> None:
        device_id = self._device_id()
        used_devices = payload.get("used_devices") or []
        if not isinstance(used_devices, list):
            used_devices = []
        max_devices = int(payload.get("max_devices", 1) or 1)
        registered_ids = [str(item.get("device_id", "") or "") for item in used_devices if isinstance(item, dict)]
        if device_id in registered_ids:
            return
        if len(registered_ids) >= max_devices:
            raise ValueError("Batas perangkat untuk key ini sudah tercapai.")

    def _register_device(self, payload: dict) -> None:
        client = self._client_instance()
        device_id = self._device_id()
        document_ref = client.collection(self.collection_name).document(str(payload["docId"]))
        snapshot = document_ref.get()
        current = snapshot.to_dict() or {}
        used_devices = current.get("used_devices") or []
        if not isinstance(used_devices, list):
            used_devices = []
        max_devices = int(current.get("max_devices", payload.get("max_devices", 1)) or 1)
        existing_device = any(
            str(item.get("device_id", "") or "") == device_id
            for item in used_devices
            if isinstance(item, dict)
        )
        if not existing_device and len(used_devices) >= max_devices:
            raise ValueError("Batas perangkat untuk key ini sudah tercapai.")
        if not existing_device:
            used_devices.append(
                {
                    "device_id": device_id,
                    "device_name": socket.gethostname(),
                    "activated_at": datetime.now(UTC).isoformat(),
                }
            )
        now_iso = datetime.now(UTC).isoformat()
        update_payload = {
            "used_devices": used_devices,
            "activated_at": current.get("activated_at") or now_iso,
            "last_check_at": now_iso,
            "updated_at": now_iso,
        }
        document_ref.update(update_payload)

    def _build_cache(self, payload: dict, active_key: str) -> dict:
        enabled_modes = self._extract_enabled_modes(payload)
        if not enabled_modes:
            raise ValueError("Key valid, tetapi tidak membuka workspace mana pun.")
        now = datetime.now(UTC)
        return {
            "source": self.source_name,
            "customer_name": str(payload.get("owner_name") or payload.get("institution_name") or ""),
            "active_key": active_key,
            "enabled_modes": enabled_modes,
            "notes": self._build_notes(payload, offline=False),
            "is_activated": True,
            "license_role": str(payload.get("license_role", "") or ""),
            "allow_offline_days": int(payload.get("allow_offline_days", 0) or 0),
            "last_validated_at": now.isoformat(),
            "cached_until": (now + timedelta(days=int(payload.get("allow_offline_days", 0) or 0))).isoformat(),
        }

    def _build_notes(self, payload: dict, *, offline: bool) -> str:
        role = str(payload.get("license_role", "") or "").replace("_", " ").strip()
        base = str(payload.get("notes", "") or "Lisensi Firebase aktif.").strip()
        if role:
            base = f"{base} Role: {role}."
        return f"{base} Mode offline aktif dari cache." if offline else base

    def _extract_enabled_modes(self, payload: dict) -> list[str]:
        features = payload.get("features") or {}
        if isinstance(features, dict):
            if bool(features.get("guru")):
                return ["guru"]
        role = str(payload.get("license_role", "") or "").strip().lower()
        role_map = {
            "guru": ["guru"],
        }
        return role_map.get(role, [])

    def _read_cache(self) -> dict:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_cache(self, payload: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _profile_from_cache(self, cache: dict, *, offline: bool) -> LicenseProfile:
        return LicenseProfile(
            source=self.source_name,
            enabled_modes=self._clean_modes(cache.get("enabled_modes", [])),
            customer_name=str(cache.get("customer_name", "") or ""),
            active_key=str(cache.get("active_key", "") or ""),
            notes=str(cache.get("notes", "") or "") + (" Cache offline digunakan." if offline else ""),
            is_activated=bool(cache.get("is_activated", False)),
        )

    def _is_cache_still_valid(self, cache: dict) -> bool:
        if cache.get("is_activated") is not True:
            return False
        cached_until = self._parse_datetime(cache.get("cached_until"))
        if not cached_until:
            return False
        return cached_until >= datetime.now(UTC)

    def _clean_modes(self, modes: list[str] | tuple[str, ...] | object) -> list[str]:
        if not isinstance(modes, (list, tuple)):
            return []
        return [mode for mode in modes if mode in MODE_LABELS]

    def _device_id(self) -> str:
        return f"{socket.gethostname()}-{uuid.getnode()}"

    def _parse_datetime(self, value) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        text = str(value).strip()
        if not text:
            return None
        for parser in (
            lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")),
            lambda item: datetime.strptime(item, "%Y-%m-%d").replace(tzinfo=UTC),
        ):
            try:
                parsed = parser(text)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
        return None

    def _compare_version(self, current: str, minimum: str) -> int:
        def normalize(value: str) -> list[int]:
            return [int(part) for part in value.split(".") if part.isdigit()]

        current_parts = normalize(current)
        minimum_parts = normalize(minimum)
        max_len = max(len(current_parts), len(minimum_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        minimum_parts.extend([0] * (max_len - len(minimum_parts)))
        if current_parts < minimum_parts:
            return -1
        if current_parts > minimum_parts:
            return 1
        return 0

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


def get_license_provider(source: str | None = None) -> BaseLicenseProvider:
    source = (source or LICENSE_SOURCE).strip().lower()
    if source and source != "firebase":
        raise RuntimeError("Aktivasi lokal sudah dinonaktifkan. SiapGuru hanya menerima lisensi Firebase.")
    return FirebaseLicenseProvider()
