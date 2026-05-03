from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from app.config import APP_STATE_PATH, BACKUP_DIR, EXPORT_DIR, WORKSPACES_DIR


MODE_LABELS = {
    "guru": "Guru",
}


class WorkspaceManager:
    def __init__(self, root_dir: Path | None = None, state_path: Path | None = None) -> None:
        self.root_dir = root_dir or WORKSPACES_DIR
        self.state_path = state_path or APP_STATE_PATH

    def ensure_storage(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def get_active_mode(self) -> str:
        data = self._read_state()
        return str(data.get("active_mode", "") or "")

    def get_enabled_modes(self) -> list[str]:
        data = self._read_state()
        modes = data.get("enabled_modes", [])
        if not isinstance(modes, list):
            modes = []
        cleaned = [str(mode) for mode in modes if mode in MODE_LABELS]
        active = str(data.get("active_mode", "") or "")
        if active in MODE_LABELS and active not in cleaned:
            cleaned.insert(0, active)
        return cleaned

    def is_mode_enabled(self, mode: str) -> bool:
        return mode in self.get_enabled_modes()

    def set_enabled_modes(self, modes: list[str]) -> None:
        cleaned: list[str] = []
        for mode in modes:
            if mode in MODE_LABELS and mode not in cleaned:
                cleaned.append(mode)
        if not cleaned:
            raise ValueError("Minimal satu mode lisensi harus aktif.")
        self.ensure_storage()
        data = self._read_state()
        active = str(data.get("active_mode", "") or "")
        if active not in cleaned:
            active = cleaned[0]
        data["active_mode"] = active
        data["enabled_modes"] = cleaned
        self._write_state(data)

    def set_active_mode(self, mode: str) -> None:
        if mode not in MODE_LABELS:
            raise ValueError("Mode aplikasi tidak valid.")
        self.ensure_storage()
        data = self._read_state()
        enabled = self.get_enabled_modes()
        if mode not in enabled:
            enabled = [mode] if not enabled else [*enabled, mode]
        data["active_mode"] = mode
        data["enabled_modes"] = enabled
        self._write_state(data)

    def get_profile(self) -> dict:
        profile = self._read_state().get("profile", {})
        if not isinstance(profile, dict):
            return {"school_name": "", "teacher_name": ""}
        return {
            "school_name": str(profile.get("school_name", "") or ""),
            "teacher_name": str(profile.get("teacher_name", "") or ""),
        }

    def save_profile(self, *, school_name: str, teacher_name: str) -> None:
        data = self._read_state()
        data["profile"] = {
            "school_name": school_name.strip(),
            "teacher_name": teacher_name.strip(),
        }
        self._write_state(data)

    def has_profile(self) -> bool:
        profile = self.get_profile()
        return bool(profile["school_name"] and profile["teacher_name"])

    def list_workspaces(self, *, include_archived: bool = False) -> list[dict]:
        rows = self._read_state().get("workspaces", [])
        if not isinstance(rows, list):
            return []
        workspaces = [self._normalize_workspace(item) for item in rows if isinstance(item, dict)]
        if not include_archived:
            workspaces = [row for row in workspaces if not row["archived"]]
        return sorted(workspaces, key=lambda row: (row["academic_year"], row["semester"], row["label"]))

    def get_workspace(self, workspace_id: str) -> dict | None:
        workspace_id = workspace_id.strip()
        for row in self.list_workspaces(include_archived=True):
            if row["id"] == workspace_id:
                return row
        return None

    def get_active_workspace_id(self) -> str:
        return str(self._read_state().get("active_workspace_id", "") or "")

    def get_active_workspace(self) -> dict | None:
        workspace_id = self.get_active_workspace_id()
        return self.get_workspace(workspace_id) if workspace_id else None

    def set_active_workspace(self, workspace_id: str) -> None:
        workspace = self.get_workspace(workspace_id)
        if not workspace or workspace["archived"]:
            raise ValueError("Workspace tidak ditemukan.")
        data = self._read_state()
        data["active_workspace_id"] = workspace["id"]
        self._write_state(data)

    def create_workspace(self, *, academic_year: str, semester: str, label: str = "") -> dict:
        academic_year = academic_year.strip()
        semester = semester.strip() or "Ganjil"
        if not academic_year:
            raise ValueError("Tahun ajaran wajib diisi.")
        if semester not in {"Ganjil", "Genap"}:
            raise ValueError("Semester tidak valid.")
        workspace_label = label.strip() or f"{academic_year} - {semester}"
        workspace_id = self._unique_workspace_id(academic_year, semester)
        now = datetime.now().isoformat(timespec="seconds")
        workspace = {
            "id": workspace_id,
            "label": workspace_label,
            "academic_year": academic_year,
            "semester": semester,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        self.ensure_storage()
        data = self._read_state()
        workspaces = data.get("workspaces", [])
        if not isinstance(workspaces, list):
            workspaces = []
        workspaces.append(workspace)
        data["workspaces"] = workspaces
        data["active_workspace_id"] = workspace_id
        self._write_state(data)
        self.get_workspace_dir(workspace_id).mkdir(parents=True, exist_ok=True)
        return workspace

    def update_workspace(
        self,
        workspace_id: str,
        *,
        academic_year: str | None = None,
        semester: str | None = None,
        label: str | None = None,
        archived: bool | None = None,
    ) -> dict:
        data = self._read_state()
        rows = data.get("workspaces", [])
        if not isinstance(rows, list):
            rows = []
        updated: dict | None = None
        for index, row in enumerate(rows):
            normalized = self._normalize_workspace(row)
            if normalized["id"] != workspace_id:
                continue
            if academic_year is not None:
                normalized["academic_year"] = academic_year.strip()
            if semester is not None:
                normalized["semester"] = semester.strip() or normalized["semester"]
            if label is not None:
                normalized["label"] = label.strip() or f"{normalized['academic_year']} - {normalized['semester']}"
            if archived is not None:
                normalized["archived"] = bool(archived)
            normalized["updated_at"] = datetime.now().isoformat(timespec="seconds")
            rows[index] = normalized
            updated = normalized
            break
        if not updated:
            raise ValueError("Workspace tidak ditemukan.")
        data["workspaces"] = rows
        self._write_state(data)
        return updated

    def get_workspace_dir(self, workspace_id: str) -> Path:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace tidak ditemukan.")
        return self.root_dir / workspace["id"]

    def get_db_path(self, workspace_id: str) -> Path:
        return self.get_workspace_dir(workspace_id) / "siapguru.db"

    def get_export_dir(self, workspace_id: str) -> Path:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace tidak ditemukan.")
        return EXPORT_DIR / self._slugify(workspace["label"])

    def get_backup_dir(self, workspace_id: str) -> Path:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace tidak ditemukan.")
        return BACKUP_DIR / self._slugify(workspace["label"])

    def get_mode_label(self, mode: str) -> str:
        return MODE_LABELS.get(mode, "Belum Dipilih")

    def describe_workspace(self, workspace_id: str) -> str:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return "Workspace belum dipilih."
        return (
            f"Workspace {workspace['label']} memakai database lokal di "
            f"{self.get_workspace_dir(workspace_id)}."
        )

    def _unique_workspace_id(self, academic_year: str, semester: str) -> str:
        base = f"ws_{self._slugify(academic_year)}_{self._slugify(semester)}"
        existing = {row["id"] for row in self.list_workspaces(include_archived=True)}
        if base not in existing:
            return base
        index = 2
        while f"{base}_{index}" in existing:
            index += 1
        return f"{base}_{index}"

    def _slugify(self, value: str) -> str:
        text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
        return text or "workspace"

    def _normalize_workspace(self, row: dict) -> dict:
        return {
            "id": str(row.get("id", "") or ""),
            "label": str(row.get("label", "") or ""),
            "academic_year": str(row.get("academic_year", "") or ""),
            "semester": str(row.get("semester", "Ganjil") or "Ganjil"),
            "archived": bool(row.get("archived", False)),
            "created_at": str(row.get("created_at", "") or ""),
            "updated_at": str(row.get("updated_at", "") or ""),
        }

    def _read_state(self) -> dict:
        self.ensure_storage()
        default = {
            "active_mode": "",
            "enabled_modes": [],
            "active_workspace_id": "",
            "profile": {"school_name": "", "teacher_name": ""},
            "workspaces": [],
        }
        if not self.state_path.exists():
            return default
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
        if not isinstance(data, dict):
            return default
        raw_modes = data.get("enabled_modes", [])
        if not isinstance(raw_modes, list):
            raw_modes = []
        profile = data.get("profile", {})
        if not isinstance(profile, dict):
            profile = {"school_name": "", "teacher_name": ""}
        workspaces = data.get("workspaces", [])
        if not isinstance(workspaces, list):
            workspaces = []
        return {
            "active_mode": str(data.get("active_mode", "") or ""),
            "enabled_modes": [str(mode) for mode in raw_modes if mode in MODE_LABELS],
            "active_workspace_id": str(data.get("active_workspace_id", "") or ""),
            "profile": {
                "school_name": str(profile.get("school_name", "") or ""),
                "teacher_name": str(profile.get("teacher_name", "") or ""),
            },
            "workspaces": workspaces,
        }

    def _write_state(self, data: dict) -> None:
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
