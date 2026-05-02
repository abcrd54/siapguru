from __future__ import annotations

import sqlite3

from app.database import DatabaseService


class ClassService:
    def __init__(self, database: DatabaseService) -> None:
        self.database = database

    def add_class(self, class_name: str, homeroom_teacher: str) -> None:
        if not class_name.strip():
            raise ValueError("Nama kelas wajib diisi.")
        try:
            self.database.execute(
                """
                INSERT INTO classes (class_name, homeroom_teacher)
                VALUES (?, ?)
                """,
                (class_name.strip(), homeroom_teacher.strip()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama kelas tidak boleh duplikat.") from exc

    def update_class(self, class_id: int, class_name: str, homeroom_teacher: str) -> None:
        if not class_name.strip():
            raise ValueError("Nama kelas wajib diisi.")
        try:
            self.database.execute(
                """
                UPDATE classes
                SET class_name = ?, homeroom_teacher = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (class_name.strip(), homeroom_teacher.strip(), class_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Nama kelas tidak boleh duplikat.") from exc

    def delete_class(self, class_id: int) -> None:
        row = self.database.fetch_one("SELECT COUNT(*) AS total FROM students WHERE class_id = ?", (class_id,))
        if row and row["total"] > 0:
            raise ValueError("Kelas tidak boleh dihapus jika masih memiliki siswa.")
        self.database.execute("DELETE FROM classes WHERE id = ?", (class_id,))

    def get_classes(self, keyword: str = "") -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT c.*, COUNT(s.id) AS student_count
            FROM classes c
            LEFT JOIN students s ON s.class_id = c.id
            WHERE c.class_name LIKE ?
            GROUP BY c.id
            ORDER BY c.class_name
            """,
            (f"%{keyword}%",),
        )
        return [dict(row) for row in rows]

    def get_class_by_id(self, class_id: int) -> dict | None:
        row = self.database.fetch_one("SELECT * FROM classes WHERE id = ?", (class_id,))
        return dict(row) if row else None
