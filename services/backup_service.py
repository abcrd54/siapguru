from __future__ import annotations

import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from app.config import BACKUP_DIR
from app.database import DatabaseService


class BackupService:
    def __init__(self, database: DatabaseService, backup_dir: Path | None = None) -> None:
        self.database = database
        self.backup_dir = backup_dir or BACKUP_DIR

    def backup_database(self) -> str:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        target = self.backup_dir / f"backup_siapguru_{datetime.now():%Y%m%d_%H%M%S}.db"
        self.database.get_connection().commit()
        shutil.copy2(self.database.get_db_path(), target)
        self.database.execute(
            "INSERT INTO backups (backup_name, backup_path) VALUES (?, ?)",
            (target.name, str(target)),
        )
        return str(target)

    @staticmethod
    def validate_backup_file(file_path: str) -> None:
        path = Path(file_path)
        if path.suffix.lower() != ".db":
            raise ValueError("File backup tidak valid atau rusak.")
        try:
            conn = sqlite3.connect(path)
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            conn.close()
        except sqlite3.Error as exc:
            raise ValueError("File backup tidak valid atau rusak.") from exc
        tables = {row[0] for row in rows}
        required = {
            "settings",
            "classes",
            "students",
            "subjects",
            "assessment_components",
            "assessment_scores",
            "grades",
            "remedial_records",
            "report_descriptions",
            "backups",
        }
        if not required.issubset(tables):
            raise ValueError("File backup tidak valid atau rusak.")

    @staticmethod
    def read_backup_metadata(file_path: str) -> dict:
        BackupService.validate_backup_file(file_path)
        path = Path(file_path)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            settings = conn.execute("SELECT * FROM settings ORDER BY id ASC LIMIT 1").fetchone()
        finally:
            conn.close()
        settings_dict = dict(settings) if settings else {}
        academic_year = str(settings_dict.get("academic_year", "") or "").strip()
        semester = str(settings_dict.get("semester", "Ganjil") or "Ganjil")
        workspace_label = f"{academic_year} - {semester}" if academic_year else semester
        backup_date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "file_path": str(path),
            "file_name": path.name,
            "workspace_label": workspace_label,
            "academic_year": academic_year,
            "semester": semester,
            "school_name": str(settings_dict.get("school_name", "") or "").strip(),
            "teacher_name": str(settings_dict.get("teacher_name", "") or "").strip(),
            "backup_date": backup_date,
        }

    def restore_database(self, file_path: str) -> None:
        self.validate_backup_file(file_path)
        self.backup_database()
        self.database.replace_database(Path(file_path))
        self.database.init_database()

    def get_backup_history(self) -> list[dict]:
        return [dict(row) for row in self.database.fetch_all("SELECT * FROM backups ORDER BY backup_date DESC")]

    def open_backup_folder(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(self.backup_dir)])
