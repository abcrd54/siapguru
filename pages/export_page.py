from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader


class ExportPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services

        layout = QVBoxLayout(self)
        app_mode = self.services["app_mode"]
        subtitle = (
            "Export nilai dan deskripsi per mapel ke Excel atau CSV."
            if app_mode == "guru_mapel"
            else "Unduh file yang dibutuhkan wali kelas tanpa langkah yang rumit."
        )
        layout.addWidget(PageHeader("Unduh Laporan", subtitle))

        filters = QHBoxLayout()
        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.format_filter = QComboBox()
        self.format_filter.addItem("XLSX", False)
        self.format_filter.addItem("CSV", True)
        filters.addWidget(self.class_filter)
        if app_mode != "wali_kelas":
            filters.addWidget(self.subject_filter)
        if app_mode != "wali_kelas":
            filters.addWidget(self.format_filter)
        layout.addLayout(filters)

        buttons = QVBoxLayout()
        if app_mode == "wali_kelas":
            actions = [
                ("Unduh Data Siswa", self.export_students),
                ("Unduh Rekap Nilai", self.export_grades),
                ("Unduh File Raport", self.export_reports),
                ("Unduh Semua Laporan", self.export_all),
            ]
        else:
            actions = [
                ("Export Data Siswa", self.export_students),
                ("Export Nilai", self.export_grades),
                ("Export File Raport", self.export_reports),
                ("Export Smart Ketuntasan", self.export_remedial),
                ("Export Semua Data", self.export_all),
            ]
        for label, callback in actions:
            button = ActionButton(label, primary=label in {"Unduh Semua Laporan", "Export Semua Data"})
            button.setMaximumWidth(260)
            button.clicked.connect(callback)
            buttons.addWidget(button)
            buttons.setAlignment(button, Qt.AlignRight)
        layout.addLayout(buttons)
        self.helper_label = QLabel()
        self.helper_label.setText(
            "Pilih kelas, lalu unduh file yang dibutuhkan. File raport akan dibuat per kelas dengan satu sheet per siswa."
            if app_mode == "wali_kelas"
            else "Pilih filter seperlunya, lalu export file ke format yang dibutuhkan."
        )
        layout.addWidget(self.helper_label)
        layout.addStretch()
        self.refresh_filters()

    def refresh_filters(self) -> None:
        context = self.services["settings"].get_active_context()
        self.class_filter.clear()
        self.subject_filter.clear()
        self.class_filter.addItem("Semua Kelas", None)
        if self.services["app_mode"] != "wali_kelas":
            self.subject_filter.addItem("Semua Mapel", None)
        for row in self.services["classes"].get_classes():
            self.class_filter.addItem(row["class_name"], row["id"])
        if self.services["app_mode"] != "wali_kelas":
            for row in self.services["subjects"].get_subjects():
                self.subject_filter.addItem(row["subject_name"], row["id"])
        class_key = context.get("default_class_id")
        if class_key:
            index = self.class_filter.findData(class_key)
            if index >= 0:
                self.class_filter.setCurrentIndex(index)
        if self.services["app_mode"] != "wali_kelas":
            subject_key = context.get("default_subject_id")
            if subject_key:
                index = self.subject_filter.findData(subject_key)
                if index >= 0:
                    self.subject_filter.setCurrentIndex(index)

    def _as_csv(self) -> bool:
        if self.services["app_mode"] == "wali_kelas":
            return False
        return bool(self.format_filter.currentData())

    def export_students(self) -> None:
        try:
            path = self.services["excel"].export_students_excel(self.class_filter.currentData(), self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_grades(self) -> None:
        try:
            subject_id = None if self.services["app_mode"] == "wali_kelas" else self.subject_filter.currentData()
            path = self.services["excel"].export_grades_excel(self.class_filter.currentData(), subject_id, self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_reports(self) -> None:
        try:
            path = self.services["excel"].export_reports_excel(self.class_filter.currentData(), None, self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_remedial(self) -> None:
        try:
            path = self.services["excel"].export_remedial_excel(self.class_filter.currentData(), self.subject_filter.currentData(), self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_all(self) -> None:
        exporters = [
            ("Data Siswa", lambda: self.services["excel"].export_students_excel(self.class_filter.currentData(), self._as_csv())),
            (
                "Nilai",
                lambda: self.services["excel"].export_grades_excel(
                    self.class_filter.currentData(),
                    None if self.services["app_mode"] == "wali_kelas" else self.subject_filter.currentData(),
                    self._as_csv(),
                ),
            ),
            ("File Raport", lambda: self.services["excel"].export_reports_excel(self.class_filter.currentData(), None, self._as_csv())),
        ]
        if self.services["app_mode"] != "wali_kelas":
            exporters.append(
                ("Smart Ketuntasan", lambda: self.services["excel"].export_remedial_excel(self.class_filter.currentData(), self.subject_filter.currentData(), self._as_csv()))
            )
        created: list[str] = []
        skipped: list[str] = []
        try:
            for label, exporter in exporters:
                try:
                    created.append(exporter())
                except ValueError:
                    skipped.append(label)
            if not created:
                raise ValueError("Data kosong.")
            message = "Export berhasil:\n" + "\n".join(created)
            if skipped:
                message += "\n\nTidak diexport karena data kosong:\n" + "\n".join(skipped)
            info(self, message)
        except Exception as exc:
            error(self, str(exc))
