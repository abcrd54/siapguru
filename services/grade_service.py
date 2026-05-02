from __future__ import annotations

import math
import sqlite3

from app.database import DatabaseService
from services.settings_service import SettingsService


class GradeService:
    def __init__(self, database: DatabaseService, settings_service: SettingsService) -> None:
        self.database = database
        self.settings_service = settings_service

    def get_subject_kkm(self, subject_id: int | None) -> int:
        if subject_id:
            row = self.database.fetch_one("SELECT kkm FROM subjects WHERE id = ?", (subject_id,))
            if row and row["kkm"] is not None:
                return int(row["kkm"])
        return self.settings_service.get_kkm()

    def get_component_blueprint(self, scheme: dict | None = None) -> list[dict]:
        scheme = scheme or self.settings_service.get_assessment_scheme()
        blueprints: list[dict] = []
        order_no = 1
        component_groups = (
            ("harian", "Harian", int(scheme["daily_component_count"]), bool(scheme["use_daily_components"])),
            ("pr", "PR", int(scheme["homework_component_count"]), bool(scheme["use_homework_components"])),
        )
        for prefix, label, count, enabled in component_groups:
            for index in range(1, 7):
                blueprints.append(
                    {
                        "component_code": f"{prefix}_{index}",
                        "component_name": f"{label} {index}",
                        "component_type": prefix,
                        "order_no": order_no,
                        "is_active": 1 if enabled and index <= count else 0,
                    }
                )
                order_no += 1
        if bool(scheme["use_practice_component"]):
            blueprints.append(
                {
                    "component_code": "praktek",
                    "component_name": "Praktek",
                    "component_type": "praktek",
                    "order_no": order_no,
                    "is_active": 1,
                }
            )
            order_no += 1
        for code, name, component_type, enabled in (
            ("uts", "UTS", "uts", bool(scheme["use_mid_component"])),
            ("uas", "UAS", "uas", bool(scheme["use_final_component"])),
        ):
            blueprints.append(
                {
                    "component_code": code,
                    "component_name": name,
                    "component_type": component_type,
                    "order_no": order_no,
                    "is_active": 1 if enabled else 0,
                }
            )
            order_no += 1
        return blueprints

    def _get_default_component_scheme(self) -> dict:
        scheme = self.settings_service.get_assessment_scheme()
        if not any(
            [
                scheme["use_daily_components"] and scheme["daily_component_count"] > 0,
                scheme["use_homework_components"] and scheme["homework_component_count"] > 0,
                scheme["use_practice_component"],
                scheme["use_mid_component"],
                scheme["use_final_component"],
            ]
        ):
            return {
                "daily_component_count": 3,
                "homework_component_count": 0,
                "use_daily_components": True,
                "use_homework_components": False,
                "use_practice_component": False,
                "use_mid_component": True,
                "use_final_component": True,
            }
        return scheme

    def calculate_daily_average(self, component_scores: list[float | None]) -> float:
        values = [float(score) for score in component_scores if score is not None]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def calculate_final_score(self, daily: float, mid: float, final: float, extra: float = 0) -> float:
        settings = self.settings_service.get_settings()
        scheme = self.settings_service.get_assessment_scheme()
        active_weights: list[tuple[float, int]] = []
        if any(
            [
                bool(scheme["use_daily_components"]) and int(scheme["daily_component_count"]) > 0,
                bool(scheme["use_homework_components"]) and int(scheme["homework_component_count"]) > 0,
                bool(scheme["use_practice_component"]),
            ]
        ):
            active_weights.append((daily, int(settings["weight_task"])))
        if bool(scheme["use_mid_component"]):
            active_weights.append((mid, int(settings["weight_mid"])))
        if bool(scheme["use_final_component"]):
            active_weights.append((final, int(settings["weight_final"])))
        total_weight = sum(weight for _, weight in active_weights)
        weighted_score = 0.0 if total_weight == 0 else sum(score * weight for score, weight in active_weights) / total_weight
        result = weighted_score + extra
        return round(max(0, min(100, result)), 2)

    def get_predicate(self, score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        return "D"

    def get_status(self, score: float, subject_id: int | None = None, kkm: int | None = None) -> str:
        target = int(kkm) if kkm is not None else self.get_subject_kkm(subject_id)
        return "Tuntas" if score >= target else "Belum Tuntas"

    def validate_score(self, value: float | int | str | None, *, allow_blank: bool = False) -> float | None:
        if value in (None, ""):
            if allow_blank:
                return None
            return 0.0
        numeric = float(value)
        if numeric < 0 or numeric > 100:
            raise ValueError("Nilai harus berada di antara 0 sampai 100.")
        return numeric

    def ensure_subject_components(self, subject_id: int) -> list[dict]:
        existing_rows = self.database.fetch_all(
            """
            SELECT * FROM assessment_components
            WHERE subject_id = ?
            ORDER BY order_no ASC, id ASC
            """,
            (subject_id,),
        )
        existing = {row["component_code"]: dict(row) for row in existing_rows}
        blueprints = self.get_component_blueprint(self._get_default_component_scheme())
        preserve_subject_layout = bool(existing_rows)
        for blueprint in blueprints:
            current = existing.get(blueprint["component_code"])
            if current:
                self.database.execute(
                    """
                    UPDATE assessment_components
                    SET component_name = ?, component_type = ?, order_no = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        blueprint["component_name"],
                        blueprint["component_type"],
                        blueprint["order_no"],
                        current["is_active"] if preserve_subject_layout else blueprint["is_active"],
                        current["id"],
                    ),
                )
            else:
                self.database.execute(
                    """
                    INSERT INTO assessment_components (
                        subject_id, component_code, component_name, component_type, weight, order_no, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        subject_id,
                        blueprint["component_code"],
                        blueprint["component_name"],
                        blueprint["component_type"],
                        0,
                        blueprint["order_no"],
                        blueprint["is_active"],
                    ),
                )
        rows = self.database.fetch_all(
            """
            SELECT * FROM assessment_components
            WHERE subject_id = ?
            ORDER BY order_no ASC, id ASC
            """,
            (subject_id,),
        )
        return [dict(row) for row in rows]

    def get_component_scheme(self, subject_id: int) -> dict:
        rows = self.ensure_subject_components(subject_id)
        return {
            "daily_component_count": sum(
                1 for row in rows if row["component_type"] == "harian" and int(row["is_active"]) == 1
            ),
            "homework_component_count": sum(
                1 for row in rows if row["component_type"] == "pr" and int(row["is_active"]) == 1
            ),
            "use_daily_components": any(
                row["component_type"] == "harian" and int(row["is_active"]) == 1 for row in rows
            ),
            "use_homework_components": any(
                row["component_type"] == "pr" and int(row["is_active"]) == 1 for row in rows
            ),
            "use_practice_component": any(
                row["component_code"] == "praktek" and int(row["is_active"]) == 1 for row in rows
            ),
            "use_mid_component": any(
                row["component_code"] == "uts" and int(row["is_active"]) == 1 for row in rows
            ),
            "use_final_component": any(
                row["component_code"] == "uas" and int(row["is_active"]) == 1 for row in rows
            ),
        }

    def update_component_layout(self, subject_id: int, payload: dict) -> None:
        daily_count = int(payload.get("daily_component_count", 0) or 0)
        homework_count = int(payload.get("homework_component_count", 0) or 0)
        use_daily_components = bool(int(payload.get("use_daily_components", 0) or 0))
        use_homework_components = bool(int(payload.get("use_homework_components", 0) or 0))
        use_practice_component = bool(int(payload.get("use_practice_component", 0) or 0))
        use_mid_component = bool(int(payload.get("use_mid_component", 0) or 0))
        use_final_component = bool(int(payload.get("use_final_component", 0) or 0))
        if not use_daily_components:
            daily_count = 0
        if not use_homework_components:
            homework_count = 0
        self.settings_service.validate_component_counts(
            daily_count,
            homework_count,
            use_daily_components=use_daily_components,
            use_homework_components=use_homework_components,
            use_practice_component=use_practice_component,
            use_mid_component=use_mid_component,
            use_final_component=use_final_component,
        )
        components = {row["component_code"]: row for row in self.ensure_subject_components(subject_id)}
        for blueprint in self.get_component_blueprint(
            {
                "daily_component_count": daily_count,
                "homework_component_count": homework_count,
                "use_daily_components": use_daily_components,
                "use_homework_components": use_homework_components,
                "use_practice_component": use_practice_component,
                "use_mid_component": use_mid_component,
                "use_final_component": use_final_component,
            }
        ):
            component = components[blueprint["component_code"]]
            self.database.execute(
                """
                UPDATE assessment_components
                SET component_name = ?, component_type = ?, order_no = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    blueprint["component_name"],
                    blueprint["component_type"],
                    blueprint["order_no"],
                    blueprint["is_active"],
                    component["id"],
                ),
            )

    def get_component_layout(self, subject_id: int) -> list[dict]:
        return [row for row in self.ensure_subject_components(subject_id) if int(row["is_active"]) == 1]

    def get_student_component_scores(self, student_id: int, subject_id: int) -> dict[str, float]:
        self.ensure_subject_components(subject_id)
        rows = self.database.fetch_all(
            """
            SELECT ac.component_code, ac.is_active, ass.score
            FROM assessment_components ac
            LEFT JOIN assessment_scores ass
                ON ass.component_id = ac.id
               AND ass.student_id = ?
               AND ass.subject_id = ?
            WHERE ac.subject_id = ?
            ORDER BY ac.order_no ASC, ac.id ASC
            """,
            (student_id, subject_id, subject_id),
        )
        result: dict[str, float] = {}
        for row in rows:
            result[row["component_code"]] = float(row["score"]) if row["score"] is not None else 0.0
        return result

    def save_grade(self, payload: dict) -> None:
        subject_id = int(payload["subject_id"])
        student_id = int(payload["student_id"])
        components = {row["component_code"]: row for row in self.ensure_subject_components(subject_id)}
        component_scores = payload.get("component_scores", {})
        if not component_scores:
            daily_scores = payload.get("daily_scores", [])
            homework_scores = payload.get("homework_scores", [])
            component_scores = {
                **{f"harian_{index}": value for index, value in enumerate(daily_scores, start=1)},
                **{f"pr_{index}": value for index, value in enumerate(homework_scores, start=1)},
                "uts": payload.get("mid_score", 0),
                "uas": payload.get("final_score", 0),
                "praktek": payload.get("practice_score", 0),
            }
        extra_score = self.validate_score(payload.get("extra_score", 0)) or 0.0

        for code, component in components.items():
            score = self.validate_score(component_scores.get(code, ""), allow_blank=True)
            self.database.execute(
                """
                INSERT INTO assessment_scores (student_id, subject_id, component_id, score, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id, component_id)
                DO UPDATE SET score = excluded.score, notes = excluded.notes, updated_at = CURRENT_TIMESTAMP
                """,
                (student_id, subject_id, component["id"], float(score or 0), ""),
            )

        active_layout = self.get_component_layout(subject_id)
        persisted_scores = self.get_student_component_scores(student_id, subject_id)
        daily_bucket = [
            persisted_scores.get(component["component_code"])
            for component in active_layout
            if component["component_type"] in {"harian", "pr", "praktek"}
        ]
        mid_score = persisted_scores.get("uts", 0.0)
        final_score = persisted_scores.get("uas", 0.0)
        daily_average = self.calculate_daily_average(daily_bucket)
        final_result = self.calculate_final_score(daily_average, mid_score, final_score, extra_score)
        predicate = self.get_predicate(final_result)
        kkm = self.get_subject_kkm(subject_id)
        status = self.get_status(final_result, subject_id=subject_id, kkm=kkm)
        try:
            self.database.execute(
                """
                INSERT INTO grades (
                    student_id, subject_id, task_score, mid_score, final_score,
                    extra_score, final_result, predicate, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id)
                DO UPDATE SET
                    task_score = excluded.task_score,
                    mid_score = excluded.mid_score,
                    final_score = excluded.final_score,
                    extra_score = excluded.extra_score,
                    final_result = excluded.final_result,
                    predicate = excluded.predicate,
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    student_id,
                    subject_id,
                    daily_average,
                    mid_score,
                    final_score,
                    extra_score,
                    final_result,
                    predicate,
                    status,
                    payload.get("notes", "").strip(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Terjadi masalah pada database. Silakan lakukan backup atau hubungi support.") from exc

    def get_grade_rows(self, class_id: int, subject_id: int) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT s.id AS student_id, s.full_name, c.class_name, g.id AS grade_id,
                   COALESCE(g.task_score, 0) AS daily_score,
                   COALESCE(g.mid_score, 0) AS mid_score,
                   COALESCE(g.final_score, 0) AS final_score,
                   COALESCE(g.extra_score, 0) AS extra_score,
                   COALESCE(g.final_result, 0) AS final_result,
                   COALESCE(g.predicate, '') AS predicate,
                   COALESCE(g.status, '') AS status,
                   COALESCE(g.rank_number, 0) AS rank_number,
                   COALESCE(g.notes, '') AS notes
            FROM students s
            JOIN classes c ON c.id = s.class_id
            LEFT JOIN grades g ON g.student_id = s.id AND g.subject_id = ?
            WHERE s.class_id = ?
            ORDER BY s.full_name
            """,
            (subject_id, class_id),
        )
        data: list[dict] = []
        layout = self.get_component_layout(subject_id)
        kkm = self.get_subject_kkm(subject_id)
        for row in rows:
            item = dict(row)
            scores = self.get_student_component_scores(item["student_id"], subject_id)
            item["component_layout"] = layout
            item["component_scores"] = {component["component_code"]: scores.get(component["component_code"], 0.0) for component in layout}
            item["kkm"] = kkm
            data.append(item)
        return data

    def calculate_ranking(self, class_id: int, subject_id: int) -> None:
        rows = self.database.fetch_all(
            """
            SELECT g.id, g.final_result
            FROM grades g
            JOIN students s ON s.id = g.student_id
            WHERE s.class_id = ? AND g.subject_id = ?
            ORDER BY g.final_result DESC, s.full_name ASC
            """,
            (class_id, subject_id),
        )
        current_rank = 0
        last_score = None
        for index, row in enumerate(rows, start=1):
            if last_score is None or not math.isclose(row["final_result"], last_score):
                current_rank = index
                last_score = row["final_result"]
            self.database.execute(
                "UPDATE grades SET rank_number = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (current_rank, row["id"]),
            )

    def get_all_grades(self, class_id: int | None = None, subject_id: int | None = None) -> list[dict]:
        query = """
            SELECT g.*, s.full_name, s.nis, c.class_name, sub.subject_name, sub.kkm AS subject_kkm
            FROM grades g
            JOIN students s ON s.id = g.student_id
            JOIN classes c ON c.id = s.class_id
            JOIN subjects sub ON sub.id = g.subject_id
            WHERE 1 = 1
        """
        params: list[object] = []
        if class_id:
            query += " AND s.class_id = ?"
            params.append(class_id)
        if subject_id:
            query += " AND g.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY c.class_name, sub.subject_name, s.full_name"
        rows = [dict(row) for row in self.database.fetch_all(query, params)]
        for row in rows:
            row["kkm"] = int(row["subject_kkm"]) if row.get("subject_kkm") is not None else self.settings_service.get_kkm()
        return rows
