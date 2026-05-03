from __future__ import annotations

from app.database import DatabaseService
from services.grade_service import GradeService
from services.remedial_service import RemedialService


PREDICATE_TEXT = {
    "A": "menunjukkan penguasaan materi yang sangat baik dan aktif dalam pembelajaran",
    "B": "memahami materi dengan baik dan menunjukkan perkembangan positif",
    "C": "cukup memahami materi, perlu peningkatan konsistensi belajar",
    "D": "perlu pendampingan lebih lanjut dalam memahami materi",
}


class ReportService:
    def __init__(self, database: DatabaseService, grade_service: GradeService, remedial_service: RemedialService) -> None:
        self.database = database
        self.grade_service = grade_service
        self.remedial_service = remedial_service

    def generate_description(self, student_name: str, subject_name: str, predicate: str, status: str) -> str:
        base = PREDICATE_TEXT.get(predicate, "menunjukkan perkembangan belajar")
        sentence = f"{student_name} {base} pada mata pelajaran {subject_name}."
        if status in {"Tuntas Setelah Remedial", "Tuntas Setelah Penyesuaian"}:
            sentence += " Setelah mengikuti program perbaikan dan penyesuaian, siswa menunjukkan peningkatan hasil belajar."
        elif status == "Belum Tuntas":
            sentence += " Perlu pendampingan dan latihan lanjutan agar pemahaman materi semakin baik."
        return sentence

    def _effective_grade_snapshot(self, row: dict) -> dict:
        remedial = self.remedial_service.get_record_by_grade(row["grade_id"]) if row.get("grade_id") else None
        effective_score = (
            float(remedial["adjusted_score"])
            if remedial and remedial.get("adjusted_score") is not None
            else float(row.get("final_result") or 0)
        )
        effective_status = (
            str(remedial["remedial_status"] or "").strip()
            if remedial and remedial.get("remedial_status")
            else str(row.get("status", "") or "").strip()
        )
        effective_predicate = self.grade_service.get_predicate(effective_score)
        return {
            "effective_score": round(effective_score, 2),
            "effective_status": effective_status,
            "effective_predicate": effective_predicate,
            "remedial": remedial,
        }

    def _should_regenerate_description(self, row: dict, snapshot: dict) -> bool:
        description = str(row.get("description", "") or "").strip()
        if not description:
            return True
        stored_score = round(float(row.get("final_result") or 0), 2)
        stored_predicate = str(row.get("predicate", "") or "").strip()
        stored_status = str(row.get("status", "") or "").strip()
        if stored_score != snapshot["effective_score"]:
            return True
        if stored_predicate != snapshot["effective_predicate"]:
            return True
        if stored_status != snapshot["effective_status"]:
            return True
        description_updated = str(row.get("description_updated_at", "") or "").strip()
        grade_updated = str(row.get("grade_updated_at", "") or "").strip()
        remedial_updated = str(row.get("remedial_updated_at", "") or "").strip()
        if not description_updated:
            return True
        if grade_updated and description_updated < grade_updated:
            return True
        if remedial_updated and description_updated < remedial_updated:
            return True
        return False

    def generate_all_descriptions(self, class_id: int, subject_id: int) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT g.id AS grade_id, s.id AS student_id, s.full_name, sub.subject_name,
                   g.final_result, g.predicate, g.status
            FROM grades g
            JOIN students s ON s.id = g.student_id
            JOIN subjects sub ON sub.id = g.subject_id
            WHERE s.class_id = ? AND g.subject_id = ?
            ORDER BY s.full_name
            """,
            (class_id, subject_id),
        )
        items = []
        for row in rows:
            snapshot = self._effective_grade_snapshot(dict(row))
            items.append(
                {
                    "grade_id": row["grade_id"],
                    "student_id": row["student_id"],
                    "full_name": row["full_name"],
                    "subject_name": row["subject_name"],
                    "final_result": snapshot["effective_score"],
                    "predicate": snapshot["effective_predicate"],
                    "status": snapshot["effective_status"],
                    "description": self.generate_description(
                        row["full_name"],
                        row["subject_name"],
                        snapshot["effective_predicate"],
                        snapshot["effective_status"],
                    ),
                }
            )
        return items

    def save_description(self, student_id: int, subject_id: int, grade_id: int, description: str) -> None:
        self.database.execute(
            """
            INSERT INTO report_descriptions (student_id, subject_id, grade_id, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, subject_id)
            DO UPDATE SET description = excluded.description, grade_id = excluded.grade_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (student_id, subject_id, grade_id, description.strip()),
        )

    def get_saved_descriptions(self, class_id: int | None = None, subject_id: int | None = None) -> list[dict]:
        query = """
            SELECT rd.*, s.full_name, c.class_name, sub.subject_name,
                   g.final_result, g.predicate, g.status
            FROM report_descriptions rd
            JOIN students s ON s.id = rd.student_id
            JOIN classes c ON c.id = s.class_id
            JOIN subjects sub ON sub.id = rd.subject_id
            LEFT JOIN grades g ON g.id = rd.grade_id
            WHERE 1 = 1
        """
        params: list[object] = []
        if class_id:
            query += " AND s.class_id = ?"
            params.append(class_id)
        if subject_id:
            query += " AND rd.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY c.class_name, s.full_name"
        rows = [dict(row) for row in self.database.fetch_all(query, params)]
        for row in rows:
            snapshot = self._effective_grade_snapshot(row)
            row["final_result"] = snapshot["effective_score"]
            row["status"] = snapshot["effective_status"]
            row["predicate"] = snapshot["effective_predicate"]
        return rows

    def get_report_book_data(self, class_id: int) -> list[dict]:
        students = self.database.fetch_all(
            """
            SELECT s.*, c.class_name
            FROM students s
            JOIN classes c ON c.id = s.class_id
            WHERE s.class_id = ?
            ORDER BY s.full_name
            """,
            (class_id,),
        )
        settings = self.database.fetch_one("SELECT * FROM settings ORDER BY id ASC LIMIT 1")
        items: list[dict] = []
        for student in students:
            subject_rows = self.database.fetch_all(
                """
                SELECT sub.subject_name,
                       COALESCE(rd.description, '') AS description,
                       rd.updated_at AS description_updated_at,
                       COALESCE(g.final_result, 0) AS final_result,
                       COALESCE(g.predicate, '') AS predicate,
                       COALESCE(g.status, '') AS status,
                       g.id AS grade_id,
                       g.updated_at AS grade_updated_at
                FROM grades g
                JOIN subjects sub ON sub.id = g.subject_id
                LEFT JOIN report_descriptions rd
                    ON rd.student_id = g.student_id
                   AND rd.subject_id = g.subject_id
                WHERE g.student_id = ?
                ORDER BY sub.subject_name
                """,
                (student["id"],),
            )
            lessons: list[dict] = []
            for row in subject_rows:
                row_data = dict(row)
                snapshot = self._effective_grade_snapshot(row_data)
                effective_score = snapshot["effective_score"]
                effective_predicate = snapshot["effective_predicate"]
                effective_status = snapshot["effective_status"]
                remedial = snapshot["remedial"]
                row_data["remedial_updated_at"] = str(remedial.get("updated_at", "") or "") if remedial else ""
                description = str(row_data["description"] or "").strip()
                if self._should_regenerate_description(row_data, snapshot):
                    description = self.generate_description(
                        str(student["full_name"]),
                        str(row_data["subject_name"]),
                        effective_predicate,
                        effective_status,
                    )
                lessons.append(
                    {
                        "subject_name": row_data["subject_name"],
                        "final_result": round(effective_score, 2),
                        "predicate": effective_predicate,
                        "status": effective_status,
                        "description": description,
                    }
                )
            items.append(
                {
                    "student_id": student["id"],
                    "full_name": student["full_name"],
                    "nis": student["nis"] or "",
                    "nisn": student["nisn"] or "",
                    "class_name": student["class_name"],
                    "gender": student["gender"] or "",
                    "parent_name": student["parent_name"] or "",
                    "class_id": class_id,
                    "school_name": settings["school_name"] if settings else "",
                    "teacher_name": settings["teacher_name"] if settings else "",
                    "academic_year": settings["academic_year"] if settings else "",
                    "semester": settings["semester"] if settings else "",
                    "lessons": lessons,
                }
            )
        return items
