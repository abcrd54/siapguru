from __future__ import annotations

import shutil

from app.database import DatabaseService
from app.workspace import WorkspaceManager
from services.backup_service import BackupService
from services.settings_service import SettingsService
from ui.dialogs import BackupRestoreDialog, WorkspaceCreateDialog, WorkspaceSelectionDialog, error


def seed_workspace_settings(database: DatabaseService, workspace: dict, profile: dict) -> None:
    settings = SettingsService(database)
    current = settings.get_settings()
    settings.update_settings(
        {
            "app_mode": "guru",
            "default_class_id": current.get("default_class_id"),
            "default_subject_id": current.get("default_subject_id"),
            "primary_class_id": current.get("primary_class_id"),
            "school_name": current.get("school_name") or profile["school_name"],
            "teacher_name": current.get("teacher_name") or profile["teacher_name"],
            "academic_year": workspace["academic_year"],
            "semester": workspace["semester"],
        }
    )


def copy_workspace_seed(source_db: DatabaseService, target_db: DatabaseService, options: dict) -> None:
    class_id_map: dict[int, int] = {}
    subject_id_map: dict[int, int] = {}

    if options.get("classes"):
        for row in source_db.fetch_all("SELECT class_name, homeroom_teacher FROM classes ORDER BY id ASC"):
            new_id = target_db.execute(
                """
                INSERT INTO classes (class_name, homeroom_teacher)
                VALUES (?, ?)
                """,
                (row["class_name"], row["homeroom_teacher"]),
            )
            old_row = source_db.fetch_one("SELECT id FROM classes WHERE class_name = ?", (row["class_name"],))
            if old_row:
                class_id_map[int(old_row["id"])] = int(new_id)

    if options.get("students"):
        for row in source_db.fetch_all(
            """
            SELECT nis, nisn, full_name, gender, class_id, address, parent_name, parent_phone
            FROM students
            ORDER BY id ASC
            """
        ):
            class_id = class_id_map.get(int(row["class_id"])) if row["class_id"] is not None else None
            target_db.execute(
                """
                INSERT INTO students (nis, nisn, full_name, gender, class_id, address, parent_name, parent_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["nis"],
                    row["nisn"],
                    row["full_name"],
                    row["gender"],
                    class_id,
                    row["address"],
                    row["parent_name"],
                    row["parent_phone"],
                ),
            )

    if options.get("subjects"):
        copy_rules = bool(options.get("subject_rules"))
        for row in source_db.fetch_all(
            """
            SELECT id, subject_name, teacher_name, kkm, weight_task, weight_mid, weight_final
            FROM subjects
            ORDER BY id ASC
            """
        ):
            new_id = target_db.execute(
                """
                INSERT INTO subjects (subject_name, teacher_name, kkm, weight_task, weight_mid, weight_final)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["subject_name"],
                    row["teacher_name"],
                    row["kkm"] if copy_rules else None,
                    row["weight_task"] if copy_rules else 30,
                    row["weight_mid"] if copy_rules else 30,
                    row["weight_final"] if copy_rules else 40,
                ),
            )
            subject_id_map[int(row["id"])] = int(new_id)

    if options.get("assessment_components") and subject_id_map:
        for row in source_db.fetch_all(
            """
            SELECT subject_id, component_code, component_name, component_type, weight, order_no, is_active
            FROM assessment_components
            ORDER BY subject_id ASC, order_no ASC, id ASC
            """
        ):
            mapped_subject_id = subject_id_map.get(int(row["subject_id"]))
            if not mapped_subject_id:
                continue
            target_db.execute(
                """
                INSERT INTO assessment_components (
                    subject_id, component_code, component_name, component_type, weight, order_no, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mapped_subject_id,
                    row["component_code"],
                    row["component_name"],
                    row["component_type"],
                    row["weight"],
                    row["order_no"],
                    row["is_active"],
                ),
            )


def create_workspace_with_seed(workspace_manager: WorkspaceManager, payload: dict) -> dict:
    workspace = workspace_manager.create_workspace(
        academic_year=payload["academic_year"],
        semester=payload["semester"],
        label=payload.get("label", ""),
    )
    profile = workspace_manager.get_profile()
    target_db = DatabaseService(workspace_manager.get_db_path(workspace["id"]))
    target_db.init_database()
    seed_workspace_settings(target_db, workspace, profile)
    source_workspace_id = payload.get("source_workspace_id")
    if source_workspace_id:
        source_db = DatabaseService(workspace_manager.get_db_path(source_workspace_id))
        source_db.init_database()
        copy_workspace_seed(source_db, target_db, payload.get("copy_options", {}))
        source_db.close_connection()
    target_db.close_connection()
    return workspace


def restore_workspace_from_backup(
    workspace_manager: WorkspaceManager,
    file_path: str,
    *,
    workspace_label: str = "",
) -> dict:
    metadata = BackupService.read_backup_metadata(file_path)
    academic_year = str(metadata.get("academic_year", "") or "").strip()
    semester = str(metadata.get("semester", "Ganjil") or "Ganjil")
    if not academic_year:
        raise ValueError("Backup tidak memiliki tahun ajaran yang valid.")
    workspace = workspace_manager.create_workspace(
        academic_year=academic_year,
        semester=semester,
        label=workspace_label.strip() or str(metadata.get("workspace_label", "") or f"{academic_year} - {semester}"),
    )
    target_db_path = workspace_manager.get_db_path(workspace["id"])
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, target_db_path)
    target_db = DatabaseService(target_db_path)
    target_db.init_database()
    target_db.close_connection()
    profile = workspace_manager.get_profile()
    if not profile["teacher_name"] and metadata.get("teacher_name"):
        workspace_manager.save_profile(
            school_name=str(metadata.get("school_name", "") or ""),
            teacher_name=str(metadata.get("teacher_name", "") or ""),
        )
    return workspace


def choose_workspace(workspace: WorkspaceManager, parent=None) -> dict | None:
    while True:
        rows = workspace.list_workspaces()
        dialog = WorkspaceSelectionDialog(rows, workspace.get_active_workspace_id(), parent)
        if not dialog.exec():
            return None
        if dialog.request_create:
            create_dialog = WorkspaceCreateDialog(rows, parent)
            if not create_dialog.exec():
                continue
            payload = create_dialog.payload()
            if not payload["academic_year"]:
                error(parent, "Tahun ajaran wajib diisi.")
                continue
            try:
                return create_workspace_with_seed(workspace, payload)
            except Exception as exc:
                error(parent, str(exc))
                continue
        if dialog.request_restore:
            file_path = BackupRestoreDialog.choose_backup_file(parent)
            if not file_path:
                continue
            try:
                metadata = BackupService.read_backup_metadata(file_path)
                restore_dialog = BackupRestoreDialog(metadata, parent)
                if not restore_dialog.exec():
                    continue
                return restore_workspace_from_backup(
                    workspace,
                    file_path,
                    workspace_label=restore_dialog.workspace_label,
                )
            except Exception as exc:
                error(parent, str(exc))
                continue
        selected = workspace.get_workspace(dialog.selected_workspace_id)
        if selected:
            workspace.set_active_workspace(selected["id"])
            return selected
        error(parent, "Workspace yang dipilih tidak ditemukan.")


def migrate_legacy_workspace_if_needed(workspace: WorkspaceManager) -> None:
    if workspace.list_workspaces(include_archived=True):
        return
    legacy_db_path = workspace.root_dir / "guru" / "siapguru.db"
    if not legacy_db_path.exists():
        return
    legacy_db = DatabaseService(legacy_db_path)
    settings = {}
    try:
        row = legacy_db.fetch_one("SELECT * FROM settings ORDER BY id ASC LIMIT 1")
        settings = dict(row) if row else {}
    except Exception:
        settings = {}
    academic_year = str(settings.get("academic_year", "") or "").strip() or "Migrasi Lama"
    semester = str(settings.get("semester", "Ganjil") or "Ganjil")
    created = workspace.create_workspace(
        academic_year=academic_year,
        semester=semester,
        label=f"{academic_year} - {semester}",
    )
    target_db_path = workspace.get_db_path(created["id"])
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    if target_db_path != legacy_db_path:
        shutil.copy2(legacy_db_path, target_db_path)
    profile = workspace.get_profile()
    if not profile["teacher_name"] and settings.get("teacher_name"):
        workspace.save_profile(
            school_name=str(settings.get("school_name", "") or ""),
            teacher_name=str(settings.get("teacher_name", "") or ""),
        )
    legacy_db.close_connection()
