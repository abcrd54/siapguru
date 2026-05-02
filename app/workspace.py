from __future__ import annotations

import json
from pathlib import Path

from app.config import APP_STATE_PATH, BACKUP_DIR, EXPORT_DIR, WORKSPACES_DIR


MODE_LABELS = {
    "guru_mapel": "Guru Mapel",
    "wali_kelas": "Wali Kelas",
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
        cleaned = [mode for mode in modes if mode in MODE_LABELS]
        active = str(data.get("active_mode", "") or "")
        if active in MODE_LABELS and active not in cleaned:
            cleaned.insert(0, active)
        return cleaned

    def is_mode_enabled(self, mode: str) -> bool:
        return mode in self.get_enabled_modes()

    def set_enabled_modes(self, modes: list[str]) -> None:
        cleaned = []
        for mode in modes:
            if mode in MODE_LABELS and mode not in cleaned:
                cleaned.append(mode)
        if not cleaned:
            raise ValueError("Minimal satu workspace harus aktif.")
        self.ensure_storage()
        data = self._read_state()
        active = str(data.get("active_mode", "") or "")
        if active not in cleaned:
            active = cleaned[0]
        self._write_state({"active_mode": active, "enabled_modes": cleaned})

    def set_active_mode(self, mode: str) -> None:
        if mode not in MODE_LABELS:
            raise ValueError("Mode aplikasi tidak valid.")
        self.ensure_storage()
        data = self._read_state()
        enabled = data.get("enabled_modes", [])
        if mode not in enabled:
            enabled = [mode] if not enabled else [*enabled, mode]
        self._write_state({"active_mode": mode, "enabled_modes": enabled})

    def get_workspace_dir(self, mode: str) -> Path:
        if mode not in MODE_LABELS:
            raise ValueError("Mode aplikasi tidak valid.")
        return self.root_dir / mode

    def get_db_path(self, mode: str) -> Path:
        return self.get_workspace_dir(mode) / "siapguru.db"

    def get_export_dir(self, mode: str) -> Path:
        return EXPORT_DIR

    def get_backup_dir(self, mode: str) -> Path:
        return BACKUP_DIR

    def get_mode_label(self, mode: str) -> str:
        return MODE_LABELS.get(mode, "Belum Dipilih")

    def describe_workspace(self, mode: str) -> str:
        return f"Mode {self.get_mode_label(mode)} memakai database lokal terpisah di {self.get_workspace_dir(mode)}."

    def _read_state(self) -> dict:
        self.ensure_storage()
        if not self.state_path.exists():
            return {"active_mode": "", "enabled_modes": []}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"active_mode": "", "enabled_modes": []}
        return data if isinstance(data, dict) else {"active_mode": "", "enabled_modes": []}

    def _write_state(self, data: dict) -> None:
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
