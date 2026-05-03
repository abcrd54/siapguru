from __future__ import annotations

import sqlite3

from app.database import DatabaseService


class SubjectService:
    def __init__(self, database: DatabaseService) -> None:
        self.database = database

    def _normalize_weight(self, value: int | str | None, default: int) -> int:
        if value in (None, ""):
            return default
        normalized = int(value)
        if normalized < 0 or normalized > 100:
            raise ValueError("Bobot penilaian mapel harus 0 - 100.")
        return normalized

    def _normalize_weights(
        self,
        weight_task: int | str | None,
        weight_mid: int | str | None,
        weight_final: int | str | None,
    ) -> tuple[int, int, int]:
        task = self._normalize_weight(weight_task, 30)
        mid = self._normalize_weight(weight_mid, 30)
        final = self._normalize_weight(weight_final, 40)
        if task + mid + final != 100:
            raise ValueError("Total bobot Harian, UTS, dan UAS untuk mapel harus 100.")
        return task, mid, final

    def _normalize_kkm(self, kkm: int | str | None) -> int | None:
        if kkm in (None, ""):
            return None
        value = int(kkm)
        if value < 0 or value > 100:
            raise ValueError("KKM mapel harus 0 - 100.")
        return value

    def add_subject(
        self,
        subject_name: str,
        teacher_name: str = "",
        kkm: int | str | None = None,
        weight_task: int | str | None = None,
        weight_mid: int | str | None = None,
        weight_final: int | str | None = None,
    ) -> None:
        if not subject_name.strip():
            raise ValueError("Nama mapel wajib diisi.")
        weights = self._normalize_weights(weight_task, weight_mid, weight_final)
        try:
            self.database.execute(
                """
                INSERT INTO subjects (subject_name, teacher_name, kkm, weight_task, weight_mid, weight_final)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (subject_name.strip(), teacher_name.strip(), self._normalize_kkm(kkm), *weights),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama mapel tidak boleh duplikat.") from exc

    def update_subject(
        self,
        subject_id: int,
        subject_name: str,
        teacher_name: str = "",
        kkm: int | str | None = None,
        weight_task: int | str | None = None,
        weight_mid: int | str | None = None,
        weight_final: int | str | None = None,
    ) -> None:
        if not subject_name.strip():
            raise ValueError("Nama mapel wajib diisi.")
        current = self.get_subject_by_id(subject_id) or {}
        weights = self._normalize_weights(
            weight_task if weight_task not in (None, "") else current.get("weight_task"),
            weight_mid if weight_mid not in (None, "") else current.get("weight_mid"),
            weight_final if weight_final not in (None, "") else current.get("weight_final"),
        )
        try:
            self.database.execute(
                """
                UPDATE subjects
                SET subject_name = ?, teacher_name = ?, kkm = ?,
                    weight_task = ?, weight_mid = ?, weight_final = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (subject_name.strip(), teacher_name.strip(), self._normalize_kkm(kkm), *weights, subject_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama mapel tidak boleh duplikat.") from exc

    def delete_subject(self, subject_id: int) -> None:
        self.database.execute("DELETE FROM remedial_records WHERE subject_id = ?", (subject_id,))
        self.database.execute("DELETE FROM report_descriptions WHERE subject_id = ?", (subject_id,))
        self.database.execute("DELETE FROM grades WHERE subject_id = ?", (subject_id,))
        self.database.execute("DELETE FROM assessment_components WHERE subject_id = ?", (subject_id,))
        self.database.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))

    def get_subject_usage_summary(self, subject_id: int) -> dict:
        grades = self.database.fetch_one("SELECT COUNT(*) AS total FROM grades WHERE subject_id = ?", (subject_id,))
        reports = self.database.fetch_one("SELECT COUNT(*) AS total FROM report_descriptions WHERE subject_id = ?", (subject_id,))
        remedials = self.database.fetch_one("SELECT COUNT(*) AS total FROM remedial_records WHERE subject_id = ?", (subject_id,))
        return {
            "grade_count": int(grades["total"]) if grades else 0,
            "report_count": int(reports["total"]) if reports else 0,
            "remedial_count": int(remedials["total"]) if remedials else 0,
        }

    def get_subjects(self, keyword: str = "") -> list[dict]:
        rows = self.database.fetch_all(
            "SELECT * FROM subjects WHERE subject_name LIKE ? ORDER BY subject_name",
            (f"%{keyword}%",),
        )
        return [dict(row) for row in rows]

    def get_subject_by_id(self, subject_id: int) -> dict | None:
        row = self.database.fetch_one("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        return dict(row) if row else None
