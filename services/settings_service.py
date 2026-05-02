from __future__ import annotations

from app.database import DatabaseService


class SettingsService:
    def __init__(self, database: DatabaseService) -> None:
        self.database = database

    def get_settings(self) -> dict:
        row = self.database.fetch_one("SELECT * FROM settings ORDER BY id ASC LIMIT 1")
        return dict(row) if row else {}

    def validate_weights(self, task: int, mid: int, final: int) -> None:
        if task + mid + final != 100:
            raise ValueError("Total bobot nilai harus 100.")

    def validate_component_counts(
        self,
        daily_count: int,
        homework_count: int,
        *,
        use_daily_components: bool,
        use_homework_components: bool,
        use_practice_component: bool,
        use_mid_component: bool,
        use_final_component: bool,
    ) -> None:
        if use_daily_components and (daily_count < 1 or daily_count > 6):
            raise ValueError("Jumlah kolom Harian aktif harus 1 - 6.")
        if use_homework_components and (homework_count < 1 or homework_count > 6):
            raise ValueError("Jumlah kolom PR aktif harus 1 - 6.")
        if not use_daily_components:
            daily_count = 0
        if not use_homework_components:
            homework_count = 0
        if daily_count < 0 or daily_count > 6:
            raise ValueError("Jumlah kolom Harian harus 0 - 6.")
        if homework_count < 0 or homework_count > 6:
            raise ValueError("Jumlah kolom PR harus 0 - 6.")
        if not any(
            [
                use_daily_components and daily_count > 0,
                use_homework_components and homework_count > 0,
                use_practice_component,
                use_mid_component,
                use_final_component,
            ]
        ):
            raise ValueError("Minimal satu komponen nilai harus aktif.")

    def update_settings(self, payload: dict) -> None:
        current_settings = self.get_settings()
        kkm = int(payload.get("kkm", current_settings.get("kkm", 75)))
        if not 0 <= kkm <= 100:
            raise ValueError("KKM harus 0 - 100.")
        self.validate_weights(
            int(payload.get("weight_task", current_settings.get("weight_task", 30))),
            int(payload.get("weight_mid", current_settings.get("weight_mid", 30))),
            int(payload.get("weight_final", current_settings.get("weight_final", 40))),
        )
        settings = current_settings
        daily_count = int(payload.get("daily_component_count", settings.get("daily_component_count", 3)))
        homework_count = int(payload.get("homework_component_count", settings.get("homework_component_count", 0)))
        use_daily_components = bool(
            int(
                payload.get(
                    "use_daily_components",
                    1 if daily_count > 0 else settings.get("use_daily_components", 1) or 0,
                )
            )
        )
        use_homework_components = bool(
            int(
                payload.get(
                    "use_homework_components",
                    1 if homework_count > 0 else settings.get("use_homework_components", 0) or 0,
                )
            )
        )
        use_practice_component = bool(
            int(payload.get("use_practice_component", settings.get("use_practice_component", 0) or 0))
        )
        use_mid_component = bool(int(payload.get("use_mid_component", settings.get("use_mid_component", 1) or 0)))
        use_final_component = bool(int(payload.get("use_final_component", settings.get("use_final_component", 1) or 0)))
        if not use_daily_components:
            daily_count = 0
        if not use_homework_components:
            homework_count = 0
        self.validate_component_counts(
            daily_count,
            homework_count,
            use_daily_components=use_daily_components,
            use_homework_components=use_homework_components,
            use_practice_component=use_practice_component,
            use_mid_component=use_mid_component,
            use_final_component=use_final_component,
        )
        self.database.execute(
            """
            UPDATE settings
            SET app_mode = ?, default_class_id = ?, default_subject_id = ?, primary_class_id = ?,
                school_name = ?, teacher_name = ?, academic_year = ?, semester = ?,
                kkm = ?, weight_task = ?, weight_mid = ?, weight_final = ?,
                daily_component_count = ?, homework_component_count = ?,
                use_daily_components = ?, use_homework_components = ?, use_practice_component = ?,
                use_mid_component = ?, use_final_component = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM settings ORDER BY id ASC LIMIT 1)
            """,
            (
                payload.get("app_mode", self.get_app_mode()),
                payload.get("default_class_id"),
                payload.get("default_subject_id"),
                payload.get("primary_class_id"),
                payload["school_name"],
                payload["teacher_name"],
                payload["academic_year"],
                payload["semester"],
                kkm,
                int(payload.get("weight_task", settings.get("weight_task", 30))),
                int(payload.get("weight_mid", settings.get("weight_mid", 30))),
                int(payload.get("weight_final", settings.get("weight_final", 40))),
                daily_count,
                homework_count,
                1 if use_daily_components else 0,
                1 if use_homework_components else 0,
                1 if use_practice_component else 0,
                1 if use_mid_component else 0,
                1 if use_final_component else 0,
            ),
        )

    def get_kkm(self) -> int:
        return int(self.get_settings().get("kkm", 75))

    def is_profile_complete(self) -> bool:
        settings = self.get_settings()
        return all(
            [
                str(settings.get("school_name", "")).strip(),
                str(settings.get("teacher_name", "")).strip(),
                str(settings.get("academic_year", "")).strip(),
                str(settings.get("semester", "")).strip(),
            ]
        )

    def get_app_mode(self) -> str:
        return str(self.get_settings().get("app_mode", "") or "")

    def get_assessment_scheme(self) -> dict:
        settings = self.get_settings()
        return {
            "daily_component_count": int(settings.get("daily_component_count", 3) or 0),
            "homework_component_count": int(settings.get("homework_component_count", 0) or 0),
            "use_daily_components": bool(int(settings.get("use_daily_components", 1) or 0)),
            "use_homework_components": bool(int(settings.get("use_homework_components", 0) or 0)),
            "use_practice_component": bool(int(settings.get("use_practice_component", 0) or 0)),
            "use_mid_component": bool(int(settings.get("use_mid_component", 1) or 0)),
            "use_final_component": bool(int(settings.get("use_final_component", 1) or 0)),
        }

    def set_workspace_mode(self, app_mode: str) -> None:
        if app_mode not in {"guru_mapel", "wali_kelas"}:
            raise ValueError("Mode aplikasi tidak valid.")
        self.database.execute(
            """
            UPDATE settings
            SET app_mode = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM settings ORDER BY id ASC LIMIT 1)
            """,
            (app_mode,),
        )

    def set_app_mode(self, app_mode: str) -> None:
        self.set_workspace_mode(app_mode)

    def get_active_context(self) -> dict:
        settings = self.get_settings()
        return {
            "default_class_id": settings.get("default_class_id"),
            "default_subject_id": settings.get("default_subject_id"),
            "primary_class_id": settings.get("primary_class_id"),
        }

    def update_active_context(
        self,
        *,
        default_class_id: int | None = None,
        default_subject_id: int | None = None,
        primary_class_id: int | None = None,
    ) -> None:
        current = self.get_active_context()
        self.database.execute(
            """
            UPDATE settings
            SET default_class_id = ?, default_subject_id = ?, primary_class_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM settings ORDER BY id ASC LIMIT 1)
            """,
            (
                current["default_class_id"] if default_class_id is None else default_class_id,
                current["default_subject_id"] if default_subject_id is None else default_subject_id,
                current["primary_class_id"] if primary_class_id is None else primary_class_id,
            ),
        )
