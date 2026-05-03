import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.database import DatabaseService
from app.license import get_license_provider
from app.update_checker import FirebaseUpdateChecker
from app.workspace import WorkspaceManager
from app.workspace_runtime import choose_workspace, migrate_legacy_workspace_if_needed, seed_workspace_settings
from services.backup_service import BackupService
from services.admin_api_service import AdminApiService
from services.class_service import ClassService
from services.cloudinary_service import CloudinaryService
from services.excel_service import ExcelService
from services.grade_service import GradeService
from services.ai_service import AIService
from services.module_service import ModuleService
from services.question_service import QuestionService
from services.remote_storage_service import RemoteStorageService
from services.remedial_service import RemedialService
from services.report_service import ReportService
from services.settings_service import SettingsService
from services.student_service import StudentService
from services.subject_service import SubjectService
from ui.dialogs import InitialProfileDialog, LicenseActivationDialog, UpdateDialog, error
from ui.main_window import MainWindow


def resource_path(*parts: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path.joinpath(*parts)


def load_stylesheet() -> str:
    style_path = resource_path("ui", "styles.qss")
    return style_path.read_text(encoding="utf-8") if style_path.exists() else ""


def build_services(database: DatabaseService, workspace: WorkspaceManager, workspace_id: str, license_profile=None) -> dict:
    settings = SettingsService(database)
    if settings.get_app_mode() != "guru":
        settings.set_workspace_mode("guru")
    current_workspace = workspace.get_workspace(workspace_id)
    classes = ClassService(database)
    subjects = SubjectService(database)
    students = StudentService(database, classes)
    grades = GradeService(database, settings)
    admin_api = AdminApiService(settings)
    if license_profile:
        admin_api.set_active_license_key(getattr(license_profile, "active_key", "") or "")
    cloudinary = CloudinaryService()
    storage = RemoteStorageService(admin_api, cloudinary)
    ai_service = AIService(admin_api=admin_api)
    modules = ModuleService(database, workspace.get_workspace_dir(workspace_id), cloudinary=storage)
    questions = QuestionService(database, modules, ai_service=ai_service)
    remedial = RemedialService(database, settings, grades)
    reports = ReportService(database, grades, remedial)
    excel = ExcelService(
        classes,
        subjects,
        students,
        grades,
        remedial,
        reports,
        export_dir=workspace.get_export_dir(workspace_id),
    )
    backup = BackupService(database, backup_dir=workspace.get_backup_dir(workspace_id))

    return {
        "database": database,
        "workspace": workspace,
        "app_mode": "guru",
        "enabled_modes": workspace.get_enabled_modes(),
        "workspace_id": workspace_id,
        "current_workspace": current_workspace,
        "resource_path": resource_path,
        "settings": settings,
        "classes": classes,
        "subjects": subjects,
        "students": students,
        "grades": grades,
        "cloudinary": cloudinary,
        "admin_api": admin_api,
        "storage": storage,
        "ai": ai_service,
        "modules": modules,
        "questions": questions,
        "remedial": remedial,
        "reports": reports,
        "excel": excel,
        "backup": backup,
    }


def ensure_global_profile(workspace: WorkspaceManager) -> bool:
    if workspace.has_profile():
        return True
    profile = workspace.get_profile()
    dialog = InitialProfileDialog(
        school_name=profile["school_name"],
        teacher_name=profile["teacher_name"],
    )
    if not dialog.exec():
        return False
    payload = dialog.payload()
    if not all(payload.values()):
        error(None, "Nama sekolah dan nama guru wajib diisi.")
        return ensure_global_profile(workspace)
    workspace.save_profile(**payload)
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
        dialog = LicenseActivationDialog()
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
        workspace.set_active_mode(license_profile.enabled_modes[0])
    migrate_legacy_workspace_if_needed(workspace)
    if not ensure_global_profile(workspace):
        return 0
    selected_workspace = choose_workspace(workspace, None)
    if not selected_workspace:
        return 0
    workspace.set_active_workspace(selected_workspace["id"])
    database = DatabaseService(workspace.get_db_path(selected_workspace["id"]))
    database.init_database()
    seed_workspace_settings(database, selected_workspace, workspace.get_profile())
    services = build_services(database, workspace, selected_workspace["id"], license_profile=license_profile)
    services["license"] = license_profile
    try:
        update_info = FirebaseUpdateChecker().check()
    except Exception as exc:
        error(None, str(exc))
        return 0
    if update_info and (update_info.update_available or update_info.update_required):
        dialog = UpdateDialog(update_info)
        dialog.exec()
        if update_info.update_required:
            return 0

    window = MainWindow(services)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
