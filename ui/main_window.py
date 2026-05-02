from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
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
from ui.dialogs import WorkspaceSwitchDialog, confirm, info
from ui.widgets import ActionButton


class MainWindow(QMainWindow):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.setWindowTitle("SiapGuru")
        self.setMinimumSize(1280, 720)
        self.app_mode = self.services["app_mode"]
        self.enabled_modes = self.services["enabled_modes"]
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

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)

        topbar = QWidget()
        topbar_layout = QHBoxLayout(topbar)
        self.meta_label = QLabel(self._meta_text())
        self.meta_label.setObjectName("TopbarMeta")
        topbar_layout.addStretch()
        self.switch_button = ActionButton("Ganti Workspace")
        self.switch_button.clicked.connect(self.open_workspace_switcher)
        self.switch_button.setVisible(len(self.enabled_modes) > 1)
        topbar_layout.addWidget(self.switch_button)
        topbar_layout.addWidget(self.meta_label)

        self.stack = QStackedWidget()
        all_pages = {
            "Beranda": DashboardPage(services),
            "Data Siswa": StudentsPage(services),
            "Data Kelas": ClassesPage(services),
            "Mata Pelajaran": SubjectsPage(services),
            "Nilai": GradesPage(services),
            "Smart Ketuntasan": SmartKetuntasanPage(services),
            "Buat Raport": ReportsPage(services),
            "Unduh Laporan": ExportPage(services),
            "Backup": BackupPage(services),
            "Pengaturan": SettingsPage(services),
        }

        if self.app_mode == "wali_kelas":
            page_order = [
                "Beranda",
                "Data Siswa",
                "Data Kelas",
                "Mata Pelajaran",
                "Nilai",
                "Smart Ketuntasan",
                "Buat Raport",
                "Unduh Laporan",
                "Backup",
                "Pengaturan",
            ]
            self.default_page = "Beranda"
        else:
            page_order = [
                "Beranda",
                "Nilai",
                "Smart Ketuntasan",
                "Buat Raport",
                "Unduh Laporan",
                "Data Siswa",
                "Data Kelas",
                "Mata Pelajaran",
                "Backup",
                "Pengaturan",
            ]
            self.default_page = "Nilai"
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
        mode_label = "Guru Mapel" if self.app_mode == "guru_mapel" else "Wali Kelas"
        context = self.services["settings"].get_active_context()
        context_parts = []
        if self.app_mode == "guru_mapel":
            subject_id = context.get("default_subject_id")
            class_id = context.get("default_class_id")
            if subject_id:
                subject = self.services["subjects"].get_subject_by_id(int(subject_id))
                if subject:
                    context_parts.append(f"Mapel Aktif: {subject['subject_name']}")
            if class_id:
                kelas = self.services["classes"].get_class_by_id(int(class_id))
                if kelas:
                    context_parts.append(f"Kelas Aktif: {kelas['class_name']}")
        else:
            class_id = context.get("default_class_id")
            if class_id:
                kelas = self.services["classes"].get_class_by_id(int(class_id))
                if kelas:
                    context_parts.append(f"Kelas Aktif: {kelas['class_name']}")
        base = f"{mode_label} | {settings.get('academic_year', '-') or '-'} | Semester {settings.get('semester', 'Ganjil')}"
        return f"{base} | {' | '.join(context_parts)}" if context_parts else base

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

    def open_workspace_switcher(self) -> None:
        if len(self.enabled_modes) <= 1:
            info(self, "Workspace lain belum aktif.")
            return
        options = [
            (mode, f"{self.services['workspace'].get_mode_label(mode)}\n{self.services['workspace'].describe_workspace(mode)}")
            for mode in self.enabled_modes
        ]
        dialog = WorkspaceSwitchDialog(options, self.app_mode)
        if dialog.exec() and dialog.selected_mode and dialog.selected_mode != self.app_mode:
            if confirm(self, "Pindah workspace sekarang? Aplikasi akan membuka ulang dengan database mode yang dipilih."):
                self.services["workspace"].set_active_mode(dialog.selected_mode)
                self.restart_application()

    def restart_application(self) -> None:
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable])
        else:
            script = Path(sys.argv[0]).resolve()
            subprocess.Popen([sys.executable, str(script)])
        self.close()
