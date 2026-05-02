import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.database import DatabaseService
from app.license import get_license_provider
from app.workspace import WorkspaceManager
from services.backup_service import BackupService
from services.class_service import ClassService
from services.excel_service import ExcelService
from services.grade_service import GradeService
from services.remedial_service import RemedialService
from services.report_service import ReportService
from services.settings_service import SettingsService
from services.student_service import StudentService
from services.subject_service import SubjectService
from ui.dialogs import InitialProfileDialog, LicenseActivationDialog, ModeSelectionDialog, error
from ui.main_window import MainWindow


def resource_path(*parts: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path.joinpath(*parts)


def load_stylesheet() -> str:
    style_path = resource_path("ui", "styles.qss")
    return style_path.read_text(encoding="utf-8") if style_path.exists() else ""


def build_services(database: DatabaseService, workspace: WorkspaceManager, active_mode: str) -> dict:
    settings = SettingsService(database)
    if settings.get_app_mode() != active_mode:
        settings.set_workspace_mode(active_mode)
    classes = ClassService(database)
    subjects = SubjectService(database)
    students = StudentService(database, classes)
    grades = GradeService(database, settings)
    remedial = RemedialService(database, settings, grades)
    reports = ReportService(database, grades, remedial)
    excel = ExcelService(
        classes,
        subjects,
        students,
        grades,
        remedial,
        reports,
        export_dir=workspace.get_export_dir(active_mode),
    )
    backup = BackupService(database, backup_dir=workspace.get_backup_dir(active_mode))

    return {
        "database": database,
        "workspace": workspace,
        "app_mode": active_mode,
        "enabled_modes": workspace.get_enabled_modes(),
        "resource_path": resource_path,
        "settings": settings,
        "classes": classes,
        "subjects": subjects,
        "students": students,
        "grades": grades,
        "remedial": remedial,
        "reports": reports,
        "excel": excel,
        "backup": backup,
    }


def ensure_initial_profile(services: dict) -> bool:
    settings_service = services["settings"]
    if settings_service.is_profile_complete():
        return True
    settings = settings_service.get_settings()
    dialog = InitialProfileDialog(
        school_name=str(settings.get("school_name", "") or ""),
        teacher_name=str(settings.get("teacher_name", "") or ""),
        academic_year=str(settings.get("academic_year", "") or ""),
        semester=str(settings.get("semester", "Ganjil") or "Ganjil"),
    )
    if not dialog.exec():
        return False
    payload = dialog.payload()
    if not all(payload.values()):
        error(None, "Nama sekolah, nama guru, tahun ajaran, dan semester wajib diisi.")
        return ensure_initial_profile(services)
    try:
        settings_service.update_settings(
            {
                **payload,
                "app_mode": services["app_mode"],
                "default_class_id": settings.get("default_class_id"),
                "default_subject_id": settings.get("default_subject_id"),
            }
        )
    except Exception as exc:
        error(None, str(exc))
        return ensure_initial_profile(services)
    return True


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SiapGuru")
    icon_path = resource_path("assets", "icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(load_stylesheet())

    workspace = WorkspaceManager()
    license_provider = get_license_provider()
    license_profile = license_provider.get_profile()
    while not license_profile.is_activated:
        dialog = LicenseActivationDialog(
            source_label=license_profile.source,
            helper_text=license_provider.get_activation_hint(),
        )
        if not dialog.exec():
            return 0
        try:
            license_profile = license_provider.activate_key(dialog.entered_key)
        except Exception as exc:
            error(None, str(exc))
            license_profile = license_provider.get_profile()
            continue

    workspace.set_enabled_modes(license_profile.enabled_modes)
    active_mode = workspace.get_active_mode()
    if not active_mode or active_mode not in license_profile.enabled_modes:
        if len(license_profile.enabled_modes) == 1:
            active_mode = license_profile.enabled_modes[0]
            workspace.set_active_mode(active_mode)
        else:
            dialog = ModeSelectionDialog(
                current_mode=active_mode,
                enabled_modes=license_profile.enabled_modes,
                source_label=license_profile.source,
            )
            if dialog.exec() and dialog.selected_mode:
                active_mode = dialog.selected_mode
                workspace.set_active_mode(active_mode)
            else:
                return 0
    database = DatabaseService(workspace.get_db_path(active_mode))
    database.init_database()
    services = build_services(database, workspace, active_mode)
    services["license"] = license_profile
    if not ensure_initial_profile(services):
        return 0

    window = MainWindow(services)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
