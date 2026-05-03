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
        self.semester.addItem("Ganjil")
        self.semester.addItem("Genap")
        self.form.addRow("Nama Sekolah", self.school_name)
        self.form.addRow("Nama Guru", self.teacher_name)
        self.form.addRow("Tahun Ajaran", self.academic_year)
        self.form.addRow("Semester", self.semester)
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
        mode_label = "Guru Pengampu"
        workspace_label = current_workspace.get("label", "-")
        self.info_label.setText(
            f"Dashboard {mode_label} memakai workspace aktif {workspace_label}. "
            + "Nama sekolah dan nama guru menjadi profil utama aplikasi. "
            + "Tahun ajaran dan semester di bawah ini adalah identitas workspace aktif. "
            + "Lisensi aplikasi dikelola otomatis saat aktivasi dan tidak perlu diubah dari halaman ini. "
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
                }
            )
            self.services["current_workspace"] = updated_workspace
            info(self, "Profil dashboard guru berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))
