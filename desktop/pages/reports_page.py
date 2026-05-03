from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader, fill_table, set_table_headers, table_item


class ReportsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []
        self.subject_headers: list[str] = []

        layout = QVBoxLayout(self)
        subtitle = "Pilih kelas yang Anda ampu, cek ringkasan nilai akhir tiap siswa, lalu buat file raport Excel."
        layout.addWidget(PageHeader("Buat Raport", subtitle))

        controls = QHBoxLayout()
        self.class_filter = QComboBox()
        self.class_filter.setMinimumWidth(260)
        self.class_filter.setMaximumWidth(340)
        generate_button = ActionButton("Generate Raport", primary=True)
        generate_button.setMaximumWidth(190)
        self.class_filter.currentIndexChanged.connect(self.refresh)
        generate_button.clicked.connect(self.export_report_book)
        controls.addWidget(self.class_filter)
        controls.addStretch()
        controls.addWidget(generate_button)
        layout.addLayout(controls)

        self.table = QTableWidget()
        set_table_headers(self.table, ["Nama Siswa", "Kelas", "Rata-rata Akhir"], default_row_height=64)
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        self.helper_label.setWordWrap(True)
        layout.addWidget(self.helper_label)

        self.refresh_filters()
        self.refresh()

    def refresh_filters(self) -> None:
        context = self.services["settings"].get_active_context()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("Pilih Kelas", None)
        for row in self.services["classes"].get_classes():
            self.class_filter.addItem(row["class_name"], row["id"])
        class_key = context.get("default_class_id")
        if class_key:
            index = self.class_filter.findData(class_key)
            if index >= 0:
                self.class_filter.setCurrentIndex(index)
        elif self.class_filter.count() > 1:
            self.class_filter.setCurrentIndex(1)
        self.class_filter.blockSignals(False)

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        self.table.setRowCount(0)
        self.subject_headers = []
        if not class_id:
            self.rows = []
            self.helper_label.setText("Pilih kelas untuk melihat kesiapan nilai akhir raport tiap siswa.")
            return
        self.services["settings"].update_active_context(
            default_class_id=class_id,
        )
        self.rows = self.services["reports"].get_report_book_data(class_id)
        if not self.rows:
            self.helper_label.setText("Belum ada siswa atau nilai akhir pada kelas ini.")
            return
        self.subject_headers = self._subject_headers(self.rows)
        set_table_headers(
            self.table,
            ["Nama Siswa", "Kelas", *self.subject_headers, "Rata-rata Akhir"],
            default_row_height=64,
        )
        fill_table(
            self.table,
            [
                [
                    row["full_name"],
                    row["class_name"],
                    *self._subject_scores(row["lessons"]),
                    self._average_score(row["lessons"]),
                ]
                for row in self.rows
            ],
        )
        for index, row in enumerate(self.rows):
            self.table.setItem(index, 0, table_item(row["full_name"], alignment=Qt.AlignLeft))
            self.table.setItem(index, 1, table_item(row["class_name"]))
            for offset, value in enumerate(self._subject_scores(row["lessons"]), start=2):
                self.table.setItem(index, offset, table_item(value))
            self.table.setItem(
                index,
                2 + len(self.subject_headers),
                table_item(self._average_score(row["lessons"]), foreground="#1D4ED8", background="#E8F1FF"),
            )
        self.table.resizeRowsToContents()
        self.helper_label.setText(
            f"{len(self.rows)} siswa siap dibuatkan raport. Nilai akhir tiap mapel ditampilkan per kolom agar mudah dicek sebelum file raport dibuat."
        )

    def _average_score(self, lessons: list[dict]) -> float:
        if not lessons:
            return 0.0
        return round(sum(float(lesson["final_result"]) for lesson in lessons) / len(lessons), 2)

    def _subject_headers(self, rows: list[dict]) -> list[str]:
        headers: list[str] = []
        for row in rows:
            for lesson in row["lessons"]:
                subject_name = str(lesson["subject_name"])
                if subject_name not in headers:
                    headers.append(subject_name)
        return headers

    def _subject_scores(self, lessons: list[dict]) -> list[object]:
        score_map = {str(lesson["subject_name"]): lesson["final_result"] for lesson in lessons}
        return [score_map.get(subject_name, "-") for subject_name in self.subject_headers]

    def export_report_book(self) -> None:
        class_id = self.class_filter.currentData()
        if not class_id:
            error(self, "Pilih kelas terlebih dahulu.")
            return
        try:
            path = self.services["excel"].export_reports_excel(class_id, None)
            info(self, f"File raport berhasil dibuat: {path}")
        except Exception as exc:
            error(self, str(exc))
