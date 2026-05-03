from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader


class SettingsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        layout = QVBoxLayout(self)
        subtitle = "Atur profil sekolah dan identitas guru yang dipakai di seluruh dashboard penilaian."
        layout.addWidget(PageHeader("Pengaturan", subtitle))
        self.form = QFormLayout()
        self.school_name = QLineEdit()
        self.teacher_name = QLineEdit()
        self.academic_year = QLineEdit()
        self.semester = QComboBox()
        self.admin_api_base_url = QLineEdit()
        self.admin_api_token = QLineEdit()
        self.semester.addItem("Ganjil")
        self.semester.addItem("Genap")
        self.form.addRow("Nama Sekolah", self.school_name)
        self.form.addRow("Nama Guru", self.teacher_name)
        self.form.addRow("Tahun Ajaran", self.academic_year)
        self.form.addRow("Semester", self.semester)
        self.form.addRow("Admin API Base URL", self.admin_api_base_url)
        self.form.addRow("Admin API Token", self.admin_api_token)
        layout.addLayout(self.form)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        save_button = ActionButton("Simpan Pengaturan", primary=True)
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        settings = self.services["settings"].get_settings()
        current_workspace = self.services.get("current_workspace") or {}
        self.school_name.setText(settings.get("school_name", ""))
        self.teacher_name.setText(settings.get("teacher_name", ""))
        self.academic_year.setText(current_workspace.get("academic_year", settings.get("academic_year", "")))
        self.semester.setCurrentText(current_workspace.get("semester", settings.get("semester", "Ganjil")))
        self.admin_api_base_url.setText(settings.get("admin_api_base_url", ""))
        self.admin_api_token.setText(settings.get("admin_api_token", ""))
        mode_label = "Guru Pengampu"
        workspace_label = current_workspace.get("label", "-")
        self.info_label.setText(
            f"Dashboard {mode_label} memakai workspace aktif {workspace_label}. "
            + "Nama sekolah dan nama guru menjadi profil utama aplikasi. "
            + "Tahun ajaran dan semester di bawah ini adalah identitas workspace aktif. "
            + "Jika backend admin sudah siap, isi base URL dan token agar desktop bisa memakai layanan lisensi, AI, dan upload cloud lewat backend tersebut. "
            + "Gunakan menu Mata Pelajaran untuk mengatur KKM dan bobot nilai akhir per mapel. "
            + "Gunakan menu Nilai untuk mengatur komponen penilaian aktif pada mapel yang sedang diampu."
        )

    def save(self) -> None:
        try:
            if not self.academic_year.text().strip():
                raise ValueError("Tahun ajaran workspace wajib diisi.")
            if not self.school_name.text().strip() or not self.teacher_name.text().strip():
                raise ValueError("Nama sekolah dan nama guru wajib diisi.")
            workspace = self.services["workspace"]
            workspace_id = self.services["workspace_id"]
            workspace.save_profile(
                school_name=self.school_name.text(),
                teacher_name=self.teacher_name.text(),
            )
            updated_workspace = workspace.update_workspace(
                workspace_id,
                academic_year=self.academic_year.text(),
                semester=self.semester.currentText(),
                label=f"{self.academic_year.text().strip()} - {self.semester.currentText()}",
            )
            self.services["settings"].update_settings(
                {
                    "app_mode": "guru",
                    "school_name": self.school_name.text(),
                    "teacher_name": self.teacher_name.text(),
                    "academic_year": self.academic_year.text(),
                    "semester": self.semester.currentText(),
                    "admin_api_base_url": self.admin_api_base_url.text(),
                    "admin_api_token": self.admin_api_token.text(),
                }
            )
            self.services["current_workspace"] = updated_workspace
            info(self, "Profil dashboard guru berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))
