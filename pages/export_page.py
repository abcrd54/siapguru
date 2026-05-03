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
        subtitle = "Unduh rekap siswa, nilai, dan file raport dari kelas yang Anda ampu."
        layout.addWidget(PageHeader("Unduh Laporan", subtitle))

        filters = QHBoxLayout()
        self.class_filter = QComboBox()
        filters.addWidget(self.class_filter)
        layout.addLayout(filters)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        actions = [
            ("Unduh Data Siswa", self.export_students),
            ("Unduh Rekap Nilai", self.export_grades),
            ("Unduh File Raport", self.export_reports),
            ("Unduh Semua Laporan", self.export_all),
        ]
        for label, callback in actions:
            button = ActionButton(label, primary=label == "Unduh Semua Laporan")
            button.setMinimumWidth(180)
            button.setMaximumWidth(220)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.helper_label = QLabel()
        self.helper_label.setText(
            "Pilih kelas untuk memusatkan export pada rombel tertentu, lalu gunakan tombol di atas dari kiri ke kanan sesuai file yang ingin diunduh."
        )
        layout.addWidget(self.helper_label)
        layout.addStretch()
        self.refresh_filters()

    def refresh_filters(self) -> None:
        context = self.services["settings"].get_active_context()
        self.class_filter.clear()
        self.class_filter.addItem("Semua Kelas", None)
        for row in self.services["classes"].get_classes():
            self.class_filter.addItem(row["class_name"], row["id"])
        class_key = context.get("default_class_id")
        if class_key:
            index = self.class_filter.findData(class_key)
            if index >= 0:
                self.class_filter.setCurrentIndex(index)

    def _as_csv(self) -> bool:
        return False

    def export_students(self) -> None:
        try:
            path = self.services["excel"].export_students_excel(self.class_filter.currentData(), self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_grades(self) -> None:
        try:
            path = self.services["excel"].export_grades_excel(self.class_filter.currentData(), None, self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_reports(self) -> None:
        try:
            path = self.services["excel"].export_reports_excel(self.class_filter.currentData(), None, self._as_csv())
            info(self, f"Export berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def export_all(self) -> None:
        exporters = [
            ("Data Siswa", lambda: self.services["excel"].export_students_excel(self.class_filter.currentData(), self._as_csv())),
            ("Nilai", lambda: self.services["excel"].export_grades_excel(self.class_filter.currentData(), None, self._as_csv())),
            ("File Raport", lambda: self.services["excel"].export_reports_excel(self.class_filter.currentData(), None, self._as_csv())),
        ]
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
