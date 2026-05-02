from __future__ import annotations

import sqlite3

from app.database import DatabaseService
from services.class_service import ClassService


class StudentService:
    def __init__(self, database: DatabaseService, class_service: ClassService) -> None:
        self.database = database
        self.class_service = class_service

    def add_student(self, payload: dict) -> None:
        self._validate(payload)
        try:
            self.database.execute(
                """
                INSERT INTO students (
                    nis, nisn, full_name, gender, class_id, address, parent_name, parent_phone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("nis", "").strip() or None,
                    payload.get("nisn", "").strip(),
                    payload["full_name"].strip(),
                    payload.get("gender", "").strip(),
                    payload["class_id"],
                    payload.get("address", "").strip(),
                    payload.get("parent_name", "").strip(),
                    payload.get("parent_phone", "").strip(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("NIS sudah digunakan oleh siswa lain.") from exc

    def update_student(self, student_id: int, payload: dict) -> None:
        self._validate(payload)
        try:
            self.database.execute(
                """
                UPDATE students
                SET nis = ?, nisn = ?, full_name = ?, gender = ?, class_id = ?, address = ?,
                    parent_name = ?, parent_phone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    payload.get("nis", "").strip() or None,
                    payload.get("nisn", "").strip(),
                    payload["full_name"].strip(),
                    payload.get("gender", "").strip(),
                    payload["class_id"],
                    payload.get("address", "").strip(),
                    payload.get("parent_name", "").strip(),
                    payload.get("parent_phone", "").strip(),
                    student_id,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("NIS sudah digunakan oleh siswa lain.") from exc

    def delete_student(self, student_id: int) -> None:
        self.database.execute("DELETE FROM report_descriptions WHERE student_id = ?", (student_id,))
        self.database.execute("DELETE FROM remedial_records WHERE student_id = ?", (student_id,))
        self.database.execute("DELETE FROM assessment_scores WHERE student_id = ?", (student_id,))
        self.database.execute("DELETE FROM grades WHERE student_id = ?", (student_id,))
        self.database.execute("DELETE FROM students WHERE id = ?", (student_id,))

    def search_students(self, keyword: str = "", class_id: int | None = None) -> list[dict]:
        query = """
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE (s.full_name LIKE ? OR COALESCE(s.nis, '') LIKE ? OR COALESCE(s.nisn, '') LIKE ?)
        """
        params: list[object] = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]
        if class_id:
            query += " AND s.class_id = ?"
            params.append(class_id)
        query += " ORDER BY s.full_name"
        rows = self.database.fetch_all(query, params)
        return [dict(row) for row in rows]

    def get_students_by_class(self, class_id: int) -> list[dict]:
        rows = self.database.fetch_all(
            "SELECT * FROM students WHERE class_id = ? ORDER BY full_name",
            (class_id,),
        )
        return [dict(row) for row in rows]

    def _validate(self, payload: dict) -> None:
        if not payload.get("full_name", "").strip() or not payload.get("class_id"):
            raise ValueError("Data wajib belum lengkap.")
