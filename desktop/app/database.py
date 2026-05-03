from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.config import DB_PATH, DEFAULT_SETTINGS


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_mode TEXT DEFAULT '',
        default_class_id INTEGER,
        default_subject_id INTEGER,
        primary_class_id INTEGER,
        school_name TEXT,
        teacher_name TEXT,
        academic_year TEXT,
        semester TEXT,
        kkm INTEGER DEFAULT 75,
        weight_task INTEGER DEFAULT 30,
        weight_mid INTEGER DEFAULT 30,
        weight_final INTEGER DEFAULT 40,
        daily_component_count INTEGER DEFAULT 3,
        homework_component_count INTEGER DEFAULT 0,
        use_daily_components INTEGER DEFAULT 1,
        use_homework_components INTEGER DEFAULT 0,
        use_practice_component INTEGER DEFAULT 0,
        use_mid_component INTEGER DEFAULT 1,
        use_final_component INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL UNIQUE,
        homeroom_teacher TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nis TEXT UNIQUE,
        nisn TEXT,
        full_name TEXT NOT NULL,
        gender TEXT,
        class_id INTEGER,
        address TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL UNIQUE,
        teacher_name TEXT,
        kkm INTEGER,
        weight_task INTEGER DEFAULT 30,
        weight_mid INTEGER DEFAULT 30,
        weight_final INTEGER DEFAULT 40,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assessment_components (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        component_code TEXT NOT NULL,
        component_name TEXT NOT NULL,
        component_type TEXT NOT NULL,
        weight REAL DEFAULT 0,
        order_no INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        UNIQUE(subject_id, component_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS assessment_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        component_id INTEGER NOT NULL,
        score REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (component_id) REFERENCES assessment_components(id) ON DELETE CASCADE,
        UNIQUE(student_id, subject_id, component_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        task_score REAL DEFAULT 0,
        mid_score REAL DEFAULT 0,
        final_score REAL DEFAULT 0,
        extra_score REAL DEFAULT 0,
        final_result REAL DEFAULT 0,
        predicate TEXT,
        status TEXT,
        rank_number INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        UNIQUE(student_id, subject_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS remedial_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grade_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        original_score REAL NOT NULL,
        gap REAL,
        category TEXT,
        recommended_score REAL,
        remedial_score REAL,
        adjusted_score REAL,
        remedial_status TEXT,
        auto_applied INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (grade_id) REFERENCES grades(id),
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS report_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        grade_id INTEGER,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        FOREIGN KEY (grade_id) REFERENCES grades(id),
        UNIQUE(student_id, subject_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        backup_name TEXT,
        backup_path TEXT,
        backup_date TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT,
        message TEXT,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        description TEXT,
        pdf_file_name TEXT NOT NULL,
        pdf_path TEXT NOT NULL,
        extracted_text TEXT DEFAULT '',
        page_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS question_generation_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id INTEGER,
        class_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        question_type TEXT NOT NULL,
        question_count INTEGER NOT NULL,
        choice_count INTEGER DEFAULT 0,
        prompt_text TEXT NOT NULL,
        generated_output TEXT DEFAULT '',
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (module_id) REFERENCES learning_modules(id) ON DELETE SET NULL,
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )
    """,
]


class DatabaseService:
    def __init__(self, db_path: Path | None = None) -> None:
        self._conn: sqlite3.Connection | None = None
        self._db_path = db_path or DB_PATH

    def get_db_path(self) -> Path:
        return self._db_path

    def ensure_storage(self) -> None:
        self.get_db_path().parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self.ensure_storage()
            self._conn = sqlite3.connect(self.get_db_path())
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def init_database(self) -> None:
        conn = self.get_connection()
        for statement in SCHEMA:
            conn.execute(statement)
        conn.commit()
        self.ensure_settings_columns()
        self.ensure_subjects_columns()
        self.ensure_remedial_columns()
        self.ensure_learning_module_columns()
        self.ensure_question_request_columns()
        exists = self.fetch_one("SELECT id FROM settings LIMIT 1")
        if not exists:
            columns = ", ".join(DEFAULT_SETTINGS.keys())
            placeholders = ", ".join(["?"] * len(DEFAULT_SETTINGS))
            self.execute(
                f"INSERT INTO settings ({columns}) VALUES ({placeholders})",
                tuple(DEFAULT_SETTINGS.values()),
            )

    def ensure_settings_columns(self) -> None:
        rows = self.fetch_all("PRAGMA table_info(settings)")
        existing = {row["name"] for row in rows}
        required_columns = {
            "app_mode": "TEXT DEFAULT ''",
            "default_class_id": "INTEGER",
            "default_subject_id": "INTEGER",
            "primary_class_id": "INTEGER",
            "school_name": "TEXT",
            "teacher_name": "TEXT",
            "academic_year": "TEXT",
            "semester": "TEXT",
            "admin_api_base_url": "TEXT DEFAULT ''",
            "admin_api_token": "TEXT DEFAULT ''",
            "kkm": "INTEGER DEFAULT 75",
            "weight_task": "INTEGER DEFAULT 30",
            "weight_mid": "INTEGER DEFAULT 30",
            "weight_final": "INTEGER DEFAULT 40",
            "daily_component_count": "INTEGER DEFAULT 3",
            "homework_component_count": "INTEGER DEFAULT 0",
            "use_daily_components": "INTEGER DEFAULT 1",
            "use_homework_components": "INTEGER DEFAULT 0",
            "use_practice_component": "INTEGER DEFAULT 0",
            "use_mid_component": "INTEGER DEFAULT 1",
            "use_final_component": "INTEGER DEFAULT 1",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        }
        for name, definition in required_columns.items():
            if name not in existing:
                self.get_connection().execute(f"ALTER TABLE settings ADD COLUMN {name} {definition}")
        self.get_connection().commit()

    def ensure_subjects_columns(self) -> None:
        rows = self.fetch_all("PRAGMA table_info(subjects)")
        existing = {row["name"] for row in rows}
        required_columns = {
            "teacher_name": "TEXT",
            "kkm": "INTEGER",
            "weight_task": "INTEGER DEFAULT 30",
            "weight_mid": "INTEGER DEFAULT 30",
            "weight_final": "INTEGER DEFAULT 40",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        }
        for name, definition in required_columns.items():
            if name not in existing:
                self.get_connection().execute(f"ALTER TABLE subjects ADD COLUMN {name} {definition}")
        self.get_connection().commit()

    def ensure_remedial_columns(self) -> None:
        rows = self.fetch_all("PRAGMA table_info(remedial_records)")
        existing = {row["name"] for row in rows}
        required_columns = {
            "gap": "REAL",
            "category": "TEXT",
            "auto_applied": "INTEGER DEFAULT 0",
        }
        for name, definition in required_columns.items():
            if name not in existing:
                self.get_connection().execute(f"ALTER TABLE remedial_records ADD COLUMN {name} {definition}")
        self.get_connection().commit()

    def ensure_learning_module_columns(self) -> None:
        rows = self.fetch_all("PRAGMA table_info(learning_modules)")
        existing = {row["name"] for row in rows}
        required_columns = {
            "cloudinary_public_id": "TEXT",
            "cloudinary_url": "TEXT",
            "cloudinary_resource_type": "TEXT",
            "upload_status": "TEXT DEFAULT 'local_only'",
            "upload_error": "TEXT",
        }
        for name, definition in required_columns.items():
            if name not in existing:
                self.get_connection().execute(f"ALTER TABLE learning_modules ADD COLUMN {name} {definition}")
        self.get_connection().commit()

    def ensure_question_request_columns(self) -> None:
        rows = self.fetch_all("PRAGMA table_info(question_generation_requests)")
        existing = {row["name"] for row in rows}
        required_columns = {
            "provider": "TEXT DEFAULT 'openrouter'",
            "model_name": "TEXT DEFAULT ''",
            "response_text": "TEXT DEFAULT ''",
            "generation_status": "TEXT DEFAULT 'draft'",
            "error_message": "TEXT DEFAULT ''",
            "remote_result_id": "TEXT DEFAULT ''",
            "remote_sync_status": "TEXT DEFAULT 'local_only'",
            "remote_sync_error": "TEXT DEFAULT ''",
        }
        for name, definition in required_columns.items():
            if name not in existing:
                self.get_connection().execute(f"ALTER TABLE question_generation_requests ADD COLUMN {name} {definition}")
        self.get_connection().commit()

    def run_query(self, query: str, params: Iterable[Any] | None = None) -> sqlite3.Cursor:
        return self.get_connection().execute(query, tuple(params or ()))

    def fetch_all(self, query: str, params: Iterable[Any] | None = None) -> list[sqlite3.Row]:
        return list(self.run_query(query, params).fetchall())

    def fetch_one(self, query: str, params: Iterable[Any] | None = None) -> sqlite3.Row | None:
        return self.run_query(query, params).fetchone()

    def execute(self, query: str, params: Iterable[Any] | None = None) -> int:
        cur = self.get_connection().execute(query, tuple(params or ()))
        self.get_connection().commit()
        return cur.lastrowid

    def executemany(self, query: str, rows: list[tuple[Any, ...]]) -> None:
        self.get_connection().executemany(query, rows)
        self.get_connection().commit()

    def replace_database(self, source_path: Path) -> None:
        self.close_connection()
        shutil.copy2(source_path, self.get_db_path())

    def close_connection(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
