from __future__ import annotations

import sqlite3

from app.database import DatabaseService


class SubjectService:
    def __init__(self, database: DatabaseService) -> None:
        self.database = database

    def _normalize_kkm(self, kkm: int | str | None) -> int | None:
        if kkm in (None, ""):
            return None
        value = int(kkm)
        if value < 0 or value > 100:
            raise ValueError("KKM mapel harus 0 - 100.")
        return value

    def add_subject(self, subject_name: str, teacher_name: str, kkm: int | str | None = None) -> None:
        if not subject_name.strip():
            raise ValueError("Nama mapel wajib diisi.")
        try:
            self.database.execute(
                "INSERT INTO subjects (subject_name, teacher_name, kkm) VALUES (?, ?, ?)",
                (subject_name.strip(), teacher_name.strip(), self._normalize_kkm(kkm)),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama mapel tidak boleh duplikat.") from exc

    def update_subject(self, subject_id: int, subject_name: str, teacher_name: str, kkm: int | str | None = None) -> None:
        if not subject_name.strip():
            raise ValueError("Nama mapel wajib diisi.")
        try:
            self.database.execute(
                """
                UPDATE subjects
                SET subject_name = ?, teacher_name = ?, kkm = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (subject_name.strip(), teacher_name.strip(), self._normalize_kkm(kkm), subject_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama mapel tidak boleh duplikat.") from exc

    def delete_subject(self, subject_id: int) -> None:
        row = self.database.fetch_one("SELECT COUNT(*) AS total FROM grades WHERE subject_id = ?", (subject_id,))
        if row and row["total"] > 0:
            raise ValueError("Mapel tidak boleh dihapus jika masih memiliki data nilai.")
        self.database.execute("DELETE FROM assessment_components WHERE subject_id = ?", (subject_id,))
        self.database.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))

    def get_subjects(self, keyword: str = "") -> list[dict]:
        rows = self.database.fetch_all(
            "SELECT * FROM subjects WHERE subject_name LIKE ? ORDER BY subject_name",
            (f"%{keyword}%",),
        )
        return [dict(row) for row in rows]

    def get_subject_by_id(self, subject_id: int) -> dict | None:
        row = self.database.fetch_one("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        return dict(row) if row else None
