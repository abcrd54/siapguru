from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.workspace_runtime import choose_workspace
from pages.backup_page import BackupPage
from pages.classes_page import ClassesPage
from pages.dashboard_page import DashboardPage
from pages.export_page import ExportPage
from pages.grades_page import GradesPage
from pages.reports_page import ReportsPage
from pages.settings_page import SettingsPage
from pages.smart_ketuntasan_page import SmartKetuntasanPage
from pages.students_page import StudentsPage
from pages.subjects_page import SubjectsPage
from ui.dialogs import confirm, info
from ui.widgets import ActionButton


class MainWindow(QMainWindow):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.setWindowTitle("SiapGuru")
        self.setMinimumSize(1280, 720)
        self.resource_path = self.services.get("resource_path")
        self._apply_window_icon()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar_shell = QWidget()
        sidebar_shell.setObjectName("Sidebar")
        sidebar_shell.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_shell)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(14)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SidebarMenu")
        self.sidebar.currentRowChanged.connect(self.change_page)
        sidebar_layout.addWidget(self.sidebar)
        sidebar_layout.addStretch()
        self.workspace_button = ActionButton("Ganti Workspace", compact=True)
        self.workspace_button.setMaximumWidth(180)
        self.workspace_button.clicked.connect(self.change_workspace)
        sidebar_layout.addWidget(self.workspace_button, alignment=Qt.AlignLeft | Qt.AlignBottom)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)

        topbar = QWidget()
        topbar_layout = QHBoxLayout(topbar)
        self.meta_label = QLabel(self._meta_text())
        self.meta_label.setObjectName("TopbarMeta")
        topbar_layout.addStretch()
        topbar_layout.addWidget(self.meta_label)

        self.stack = QStackedWidget()
        all_pages = {
            "Beranda": DashboardPage(services),
            "Data Siswa": StudentsPage(services),
            "Data Kelas": ClassesPage(services),
            "Mata Pelajaran": SubjectsPage(services),
            "Nilai": GradesPage(services),
            "Katrol Nilai": SmartKetuntasanPage(services),
            "Buat Raport": ReportsPage(services),
            "Unduh Laporan": ExportPage(services),
            "Backup": BackupPage(services),
            "Pengaturan": SettingsPage(services),
        }

        page_order = [
            "Beranda",
            "Data Siswa",
            "Data Kelas",
            "Mata Pelajaran",
            "Nilai",
            "Katrol Nilai",
            "Buat Raport",
            "Unduh Laporan",
            "Backup",
            "Pengaturan",
        ]
        self.default_page = "Beranda"
        self.pages = {name: all_pages[name] for name in page_order}

        for name, page in self.pages.items():
            self.sidebar.addItem(QListWidgetItem(name))
            self.stack.addWidget(page)
            if hasattr(page, "navigate_requested"):
                page.navigate_requested.connect(self.navigate_to)

        content_layout.addWidget(topbar)
        content_layout.addWidget(self.stack)
        root.addWidget(sidebar_shell)
        root.addWidget(content)
        self.navigate_to(self.default_page)

    def _resource(self, *parts: str) -> Path | None:
        if not self.resource_path:
            return None
        try:
            return Path(self.resource_path(*parts))
        except Exception:
            return None

    def _apply_window_icon(self) -> None:
        icon_path = self._resource("assets", "icon.ico")
        if icon_path and icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _meta_text(self) -> str:
        settings = self.services["settings"].get_settings()
        workspace = self.services.get("current_workspace") or {}
        teacher_name = str(settings.get("teacher_name", "") or "").strip() or "Guru Pengampu"
        workspace_label = workspace.get("label") or f"{settings.get('academic_year', '-') or '-'} - {settings.get('semester', 'Ganjil')}"
        return f"{teacher_name} | {workspace_label}"

    def change_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.meta_label.setText(self._meta_text())
        page = self.stack.currentWidget()
        if hasattr(page, "refresh_filters"):
            page.refresh_filters()
        if hasattr(page, "refresh"):
            page.refresh()

    def navigate_to(self, page_name: str) -> None:
        for index in range(self.sidebar.count()):
            if self.sidebar.item(index).text() == page_name:
                self.sidebar.setCurrentRow(index)
                return

    def change_workspace(self) -> None:
        workspace_manager = self.services["workspace"]
        current_workspace = self.services.get("current_workspace") or {}
        previous_workspace_id = current_workspace.get("id", "")
        selected = choose_workspace(workspace_manager, self)
        if not selected:
            return
        if selected["id"] == current_workspace.get("id"):
            self.meta_label.setText(self._meta_text())
            return
        if not confirm(
            self,
            f"Workspace aktif akan dipindahkan ke {selected['label']}. Aplikasi perlu dibuka ulang sekarang. Lanjutkan?",
        ):
            if previous_workspace_id:
                workspace_manager.set_active_workspace(previous_workspace_id)
            return
        workspace_manager.set_active_workspace(selected["id"])
        info(self, f"Workspace {selected['label']} dipilih. Aplikasi akan dibuka ulang.")
        QProcess.startDetached(sys.executable, sys.argv[1:])
        self.close()
