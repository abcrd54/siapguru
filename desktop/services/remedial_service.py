from __future__ import annotations

from app.database import DatabaseService
from services.grade_service import GradeService
from services.settings_service import SettingsService


class RemedialService:
    def __init__(self, database: DatabaseService, settings_service: SettingsService, grade_service: GradeService) -> None:
        self.database = database
        self.settings_service = settings_service
        self.grade_service = grade_service

    def get_below_kkm_students(self, class_id: int, subject_id: int) -> list[dict]:
        kkm = self.grade_service.get_subject_kkm(subject_id)
        rows = self.database.fetch_all(
            """
            SELECT g.id AS grade_id, g.student_id, g.subject_id, s.full_name, c.class_name,
                   sub.subject_name, g.final_result
            FROM grades g
            JOIN students s ON s.id = g.student_id
            JOIN classes c ON c.id = s.class_id
            JOIN subjects sub ON sub.id = g.subject_id
            WHERE s.class_id = ? AND g.subject_id = ? AND g.final_result < ?
            ORDER BY g.final_result DESC, s.full_name
            """,
            (class_id, subject_id, kkm),
        )
        result = []
        for row in rows:
            score = float(row["final_result"])
            recommendation = self.generate_recommendation(score, kkm, mode="minimal")
            data = dict(row)
            data["original_score"] = score
            data.update(recommendation)
            result.append(data)
        return result

    def get_adjustment_candidates(
        self,
        class_id: int,
        subject_id: int,
        *,
        target_min_score: float = 75,
        target_max_score: float = 100,
    ) -> list[dict]:
        if target_min_score > target_max_score:
            raise ValueError("Nilai minimal target tidak boleh lebih besar dari nilai maksimal target.")
        grade_rows = self.grade_service.get_grade_rows(class_id, subject_id)
        if not grade_rows:
            return []
        kkm = self.grade_service.get_subject_kkm(subject_id)
        scores = [self._base_final_score(row) for row in grade_rows]
        original_min = min(scores)
        original_max = max(scores)
        result = []
        for row in grade_rows:
            original_score = self._base_final_score(row)
            adjusted_score = self._scale_score(
                original_score,
                original_min,
                original_max,
                target_min_score,
                target_max_score,
            )
            data = dict(row)
            data["original_score"] = round(original_score, 2)
            data["target_min_score"] = round(target_min_score, 2)
            data["target_max_score"] = round(target_max_score, 2)
            data["adjusted_score"] = adjusted_score
            data["recommended_score"] = adjusted_score
            data["final_score"] = adjusted_score
            data["before_final_score"] = round(original_score, 2)
            data["after_final_score"] = adjusted_score
            data["kkm"] = kkm
            data["gap"] = round(max(0.0, float(kkm) - original_score), 2)
            data["difference"] = round(adjusted_score - original_score, 2)
            data["category"] = "Auto Ketuntasan"
            data["status"] = "Siap Diproses"
            data["remedial_status"] = "Tuntas Setelah Penyesuaian" if adjusted_score >= kkm else "Belum Tuntas"
            data["auto_applied"] = adjusted_score != round(original_score, 2)
            result.append(data)
        return result

    def _base_final_score(self, row: dict) -> float:
        if row.get("final_result") not in (None, ""):
            return round(float(row.get("final_result") or 0), 2)
        return self.grade_service.calculate_final_score(
            float(row.get("daily_score") or 0),
            float(row.get("mid_score") or 0),
            float(row.get("final_score") or 0),
            float(row.get("extra_score") or 0),
            subject_id=int(row["subject_id"]) if row.get("subject_id") else None,
        )

    def _scale_score(
        self,
        score: float,
        original_min: float,
        original_max: float,
        target_min: float,
        target_max: float,
    ) -> float:
        score = round(max(0.0, min(100.0, float(score))), 2)
        target_min = round(max(0.0, min(100.0, float(target_min))), 2)
        target_max = round(max(0.0, min(100.0, float(target_max))), 2)
        if original_max == original_min:
            adjusted = min(target_max, max(target_min, score))
        else:
            ratio = (score - original_min) / (original_max - original_min)
            adjusted = target_min + (ratio * (target_max - target_min))
        return round(max(0.0, min(100.0, adjusted)), 2)

    def generate_recommendation(self, score: float, kkm: int | None = None, *, mode: str = "minimal") -> dict:
        kkm = kkm if kkm is not None else self.settings_service.get_kkm()
        safe_score = round(max(0.0, min(100.0, float(score))), 2)
        gap = round(max(0.0, float(kkm) - safe_score), 2)
        mode = mode if mode in {"minimal", "natural"} else "minimal"
        if safe_score >= kkm:
            return {
                "kkm": kkm,
                "gap": 0.0,
                "difference": 0.0,
                "recommended_score": safe_score,
                "final_score": safe_score,
                "category": "Tuntas",
                "status": "Tidak Diubah",
                "remedial_status": "Tidak Diubah",
                "auto_applied": False,
                "mode": mode,
            }
        if 1 <= gap <= 5:
            category = "Remedial Ringan"
        else:
            category = "Auto Ketuntasan"
        if mode == "natural":
            final_score = min(100.0, float(kkm + 1 if gap <= 2 else kkm))
        else:
            final_score = min(100.0, float(kkm))
        return {
            "kkm": kkm,
            "gap": gap,
            "difference": round(safe_score - kkm, 2),
            "recommended_score": round(final_score, 2),
            "final_score": round(final_score, 2),
            "category": category,
            "status": "Auto Tuntas",
            "remedial_status": "Auto Tuntas",
            "auto_applied": True,
            "mode": mode,
        }

    def apply_recommendation(
        self,
        grade_id: int,
        remedial_score: float | None = None,
        notes: str = "",
        *,
        mode: str = "minimal",
        category: str | None = None,
        status_label: str | None = None,
    ) -> None:
        grade = self.database.fetch_one("SELECT * FROM grades WHERE id = ?", (grade_id,))
        if not grade:
            raise ValueError("Data nilai tidak ditemukan.")
        recommendation = self.generate_recommendation(
            float(grade["final_result"]),
            self.grade_service.get_subject_kkm(int(grade["subject_id"])),
            mode=mode,
        )
        adjusted_score = recommendation["final_score"] if remedial_score is None else float(remedial_score)
        adjusted_score = round(max(0.0, min(100.0, adjusted_score)), 2)
        category = category or recommendation["category"]
        internal_status = status_label or recommendation["status"]
        auto_applied = True if remedial_score is not None else bool(recommendation["auto_applied"])
        grade_status = self.grade_service.get_status(
            adjusted_score,
            subject_id=int(grade["subject_id"]),
            kkm=int(recommendation["kkm"]),
        )
        existing = self.database.fetch_one("SELECT id FROM remedial_records WHERE grade_id = ?", (grade_id,))
        if existing:
            self.database.execute(
                """
                UPDATE remedial_records
                SET original_score = ?, gap = ?, category = ?, recommended_score = ?, remedial_score = ?, adjusted_score = ?,
                    remedial_status = ?, auto_applied = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE grade_id = ?
                """,
                (
                    grade["final_result"],
                    recommendation["gap"],
                    category,
                    recommendation["final_score"],
                    adjusted_score,
                    adjusted_score,
                    internal_status,
                    1 if auto_applied else 0,
                    notes.strip(),
                    grade_id,
                ),
            )
        else:
            self.database.execute(
                """
                INSERT INTO remedial_records (
                    grade_id, student_id, subject_id, original_score, gap, category, recommended_score,
                    remedial_score, adjusted_score, remedial_status, auto_applied, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    grade["id"],
                    grade["student_id"],
                    grade["subject_id"],
                    grade["final_result"],
                    recommendation["gap"],
                    category,
                    recommendation["final_score"],
                    adjusted_score,
                    adjusted_score,
                    internal_status,
                    1 if auto_applied else 0,
                    notes.strip(),
                ),
            )
        self.database.execute(
            """
            UPDATE grades
            SET final_result = ?, predicate = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                adjusted_score,
                self.grade_service.get_predicate(adjusted_score),
                grade_status,
                grade["id"],
            ),
        )

    def apply_light_recommendations(self, class_id: int, subject_id: int) -> int:
        students = self.get_adjustment_candidates(class_id, subject_id, target_min_score=0, target_max_score=100)
        applied = 0
        for item in students:
            if item["category"] == "Remedial Ringan" and item["auto_applied"]:
                self.apply_recommendation(item["grade_id"], None, "Auto rekomendasi ringan", mode="minimal")
                applied += 1
        return applied

    def apply_bulk_adjustments(
        self,
        class_id: int,
        subject_id: int,
        *,
        target_min_score: float,
        target_max_score: float,
    ) -> int:
        rows = self.get_adjustment_candidates(class_id, subject_id, target_min_score=target_min_score, target_max_score=target_max_score)
        applied = 0
        for row in rows:
            current_score = float(row["original_score"])
            adjusted_score = float(row["adjusted_score"])
            if adjusted_score == current_score:
                continue
            self.apply_recommendation(
                row["grade_id"],
                adjusted_score,
                f"Smart Ketuntasan rentang {target_min_score:.0f}-{target_max_score:.0f}",
                mode="minimal",
                category="Auto Ketuntasan",
                status_label="Tuntas Setelah Penyesuaian" if adjusted_score >= float(row["kkm"]) else "Belum Tuntas",
            )
            applied += 1
        return applied

    def reset_remedial(self, grade_id: int) -> None:
        record = self.database.fetch_one("SELECT * FROM remedial_records WHERE grade_id = ?", (grade_id,))
        if record:
            original_score = float(record["original_score"])
            self.database.execute(
                """
                UPDATE grades
                SET final_result = ?, predicate = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    original_score,
                    self.grade_service.get_predicate(original_score),
                    self.grade_service.get_status(original_score, subject_id=int(record["subject_id"])),
                    grade_id,
                ),
            )
            self.database.execute("DELETE FROM remedial_records WHERE grade_id = ?", (grade_id,))

    def get_records(self, class_id: int | None = None, subject_id: int | None = None) -> list[dict]:
        query = """
            SELECT rr.*, s.full_name, c.class_name, sub.subject_name
            FROM remedial_records rr
            JOIN students s ON s.id = rr.student_id
            JOIN classes c ON c.id = s.class_id
            JOIN subjects sub ON sub.id = rr.subject_id
            WHERE 1 = 1
        """
        params: list[object] = []
        if class_id:
            query += " AND s.class_id = ?"
            params.append(class_id)
        if subject_id:
            query += " AND rr.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY rr.created_at DESC"
        return [dict(row) for row in self.database.fetch_all(query, params)]

    def get_record_by_grade(self, grade_id: int) -> dict | None:
        row = self.database.fetch_one(
            "SELECT * FROM remedial_records WHERE grade_id = ? ORDER BY updated_at DESC, id DESC LIMIT 1",
            (grade_id,),
        )
        return dict(row) if row else None
