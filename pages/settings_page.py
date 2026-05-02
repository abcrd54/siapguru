from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QFormLayout, QLineEdit, QVBoxLayout, QWidget

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader


class SettingsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.app_mode_value = self.services["app_mode"]
        layout = QVBoxLayout(self)
        subtitle = (
            "Lengkapi data sekolah untuk workspace wali kelas."
            if self.app_mode_value == "wali_kelas"
            else "Atur profil, bobot nilai, dan konteks default untuk workspace ini."
        )
        layout.addWidget(PageHeader("Pengaturan", subtitle))
        self.form = QFormLayout()
        self.school_name = QLineEdit()
        self.teacher_name = QLineEdit()
        self.academic_year = QLineEdit()
        self.app_mode = QComboBox()
        self.app_mode.addItem("Guru Mapel", "guru_mapel")
        self.app_mode.addItem("Wali Kelas", "wali_kelas")
        self.app_mode.setEnabled(False)
        self.semester = QComboBox()
        self.semester.addItem("Ganjil")
        self.semester.addItem("Genap")
        self.weight_task = QLineEdit()
        self.weight_mid = QLineEdit()
        self.weight_final = QLineEdit()
        self.default_class = QComboBox()
        self.default_subject = QComboBox()
        self.form.addRow("Mode Aplikasi", self.app_mode)
        self.form.addRow("Kelas Aktif Guru", self.default_class)
        self.form.addRow("Mapel Aktif Guru", self.default_subject)
        self.form.addRow("Nama Sekolah", self.school_name)
        self.form.addRow("Nama Guru", self.teacher_name)
        self.form.addRow("Tahun Ajaran", self.academic_year)
        self.form.addRow("Semester", self.semester)
        self.form.addRow("Bobot Harian", self.weight_task)
        self.form.addRow("Bobot UTS", self.weight_mid)
        self.form.addRow("Bobot UAS", self.weight_final)
        layout.addLayout(self.form)
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        save_button = ActionButton("Simpan Pengaturan", primary=True)
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        settings = self.services["settings"].get_settings()
        context = self.services["settings"].get_active_context()
        index = self.app_mode.findData(settings.get("app_mode", "guru_mapel") or "guru_mapel")
        self.app_mode.setCurrentIndex(index if index >= 0 else 0)
        self.default_class.clear()
        self.default_subject.clear()
        self.default_class.addItem("Belum Dipilih", None)
        self.default_subject.addItem("Belum Dipilih", None)
        for row in self.services["classes"].get_classes():
            self.default_class.addItem(row["class_name"], row["id"])
        for row in self.services["subjects"].get_subjects():
            self.default_subject.addItem(row["subject_name"], row["id"])
        if context.get("default_class_id"):
            idx = self.default_class.findData(context["default_class_id"])
            if idx >= 0:
                self.default_class.setCurrentIndex(idx)
        if context.get("default_subject_id"):
            idx = self.default_subject.findData(context["default_subject_id"])
            if idx >= 0:
                self.default_subject.setCurrentIndex(idx)
        self.school_name.setText(settings.get("school_name", ""))
        self.teacher_name.setText(settings.get("teacher_name", ""))
        self.academic_year.setText(settings.get("academic_year", ""))
        self.semester.setCurrentText(settings.get("semester", "Ganjil"))
        self.weight_task.setText(str(settings.get("weight_task", 30)))
        self.weight_mid.setText(str(settings.get("weight_mid", 30)))
        self.weight_final.setText(str(settings.get("weight_final", 40)))
        mode_label = "Guru Mapel" if self.app_mode_value == "guru_mapel" else "Wali Kelas"
        enabled_modes = self.services["enabled_modes"]
        license_info = self.services.get("license")
        license_source = license_info.source if license_info else "local"
        self.info_label.setText(
            (
                f"Workspace {mode_label} memakai database lokal terpisah. "
                "Pilih kelas langsung dari halaman kerja sesuai data yang sedang Anda tangani."
            )
            if self.app_mode_value == "wali_kelas"
            else
            (
                f"Workspace {mode_label} memakai database lokal terpisah. Data mode ini tidak otomatis tercampur dengan mode lain. "
                f"Sumber lisensi saat ini: {license_source}. "
                + (
                    "Menu Ganti Workspace akan muncul jika lebih dari satu workspace aktif."
                    if len(enabled_modes) > 1
                    else "Menu Ganti Workspace belum muncul karena hanya satu workspace yang aktif saat ini."
                )
                + " Komponen nilai tiap mapel sekarang diatur langsung dari halaman Nilai."
            )
        )
        self._set_field_visible(self.default_class, self.app_mode_value == "guru_mapel")
        self._set_field_visible(self.default_subject, self.app_mode_value == "guru_mapel")
        self._set_field_visible(self.app_mode, self.app_mode_value != "wali_kelas")

    def save(self) -> None:
        try:
            self.services["settings"].update_settings(
                {
                    "app_mode": self.app_mode_value,
                    "default_class_id": self.default_class.currentData(),
                    "default_subject_id": self.default_subject.currentData(),
                    "school_name": self.school_name.text(),
                    "teacher_name": self.teacher_name.text(),
                    "academic_year": self.academic_year.text(),
                    "semester": self.semester.currentText(),
                    "weight_task": self.weight_task.text(),
                    "weight_mid": self.weight_mid.text(),
                    "weight_final": self.weight_final.text(),
                }
            )
            info(self, "Pengaturan workspace berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))

    def _set_field_visible(self, widget, visible: bool) -> None:
        label = self.form.labelForField(widget)
        if label:
            label.setVisible(visible)
        widget.setVisible(visible)
