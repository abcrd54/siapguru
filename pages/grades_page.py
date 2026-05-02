from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader, badge_item, set_table_headers


class GradesPage(QWidget):
    BASE_COLUMNS = ["Nama", "Kelas"]
    SUMMARY_COLUMNS = ["Rata-rata Harian", "Tambahan", "Nilai Akhir", "Predikat", "Status", "Ranking"]

    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []
        self.component_layout: list[dict] = []
        self.app_mode = self.services["app_mode"]
        self.component_column_map: dict[str, int] = {}
        self.readonly_columns: set[int] = set()

        layout = QVBoxLayout(self)
        subtitle = (
            "Kelola komponen nilai yang aktif untuk kelas-mapel yang Anda ajar."
            if self.app_mode == "guru_mapel"
            else "Atur komponen nilai per mapel, lalu input atau import nilainya di halaman yang sama."
        )
        layout.addWidget(PageHeader("Nilai Siswa", subtitle))

        controls = QHBoxLayout()
        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.class_filter.currentIndexChanged.connect(self.refresh)
        self.subject_filter.currentIndexChanged.connect(self.refresh)
        template_button = ActionButton("Download Template")
        template_button.clicked.connect(self.download_template)
        import_button = ActionButton("Import Nilai")
        import_button.clicked.connect(self.import_grades)
        calculate_button = ActionButton("Hitung Semua")
        calculate_button.clicked.connect(self.calculate_all)
        save_button = ActionButton("Simpan", primary=True)
        save_button.clicked.connect(self.save_all)
        export_button = ActionButton("Export")
        export_button.clicked.connect(self.export_data)
        self.class_filter.setMinimumWidth(220)
        self.class_filter.setMaximumWidth(300)
        self.subject_filter.setMinimumWidth(240)
        self.subject_filter.setMaximumWidth(340)
        template_button.setMaximumWidth(180)
        import_button.setMaximumWidth(160)
        calculate_button.setMaximumWidth(160)
        save_button.setMaximumWidth(140)
        export_button.setMaximumWidth(140)
        controls.addWidget(self.class_filter)
        controls.addWidget(self.subject_filter)
        controls.addStretch()
        for widget in (template_button, import_button, calculate_button, save_button, export_button):
            controls.addWidget(widget)
        layout.addLayout(controls)

        self.use_daily_components = QCheckBox("Aktifkan Harian")
        self.use_homework_components = QCheckBox("Aktifkan PR")
        self.use_practice_component = QCheckBox("Aktifkan Praktek")
        self.use_mid_component = QCheckBox("Aktifkan UTS")
        self.use_final_component = QCheckBox("Aktifkan UAS")
        self.daily_component_count = QComboBox()
        self.homework_component_count = QComboBox()
        for value in range(0, 7):
            label = "Nonaktif" if value == 0 else str(value)
            self.daily_component_count.addItem(label, value)
            self.homework_component_count.addItem(label, value)
        component_card = QWidget()
        component_form = QFormLayout(component_card)
        component_form.setContentsMargins(0, 0, 0, 0)
        component_form.setHorizontalSpacing(18)
        component_form.setVerticalSpacing(10)
        component_form.addRow("Komponen Harian", self.use_daily_components)
        component_form.addRow("Jumlah Kolom Harian", self.daily_component_count)
        component_form.addRow("Komponen PR", self.use_homework_components)
        component_form.addRow("Jumlah Kolom PR", self.homework_component_count)
        component_form.addRow("Komponen Praktek", self.use_practice_component)
        component_form.addRow("Komponen UTS", self.use_mid_component)
        component_form.addRow("Komponen UAS", self.use_final_component)
        component_buttons = QHBoxLayout()
        self.save_layout_button = ActionButton("Simpan Komponen Nilai")
        self.save_layout_button.clicked.connect(self.save_component_layout)
        component_buttons.addWidget(self.save_layout_button)
        component_buttons.addStretch()
        component_form.addRow("", component_buttons)
        layout.addWidget(component_card)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        self.helper_label.setWordWrap(True)
        layout.addWidget(self.helper_label)

        self.refresh_filters()
        self.refresh()

        self.use_daily_components.toggled.connect(self._update_component_visibility)
        self.use_homework_components.toggled.connect(self._update_component_visibility)

    def refresh_filters(self) -> None:
        context = self.services["settings"].get_active_context()
        self.class_filter.blockSignals(True)
        self.subject_filter.blockSignals(True)
        self.class_filter.clear()
        self.subject_filter.clear()
        self.class_filter.addItem("Pilih Kelas", None)
        self.subject_filter.addItem("Pilih Mapel", None)
        for row in self.services["classes"].get_classes():
            self.class_filter.addItem(row["class_name"], row["id"])
        for row in self.services["subjects"].get_subjects():
            label = row["subject_name"]
            if row.get("kkm") is not None:
                label = f"{label} (KKM {row['kkm']})"
            self.subject_filter.addItem(label, row["id"])
        class_key = context.get("default_class_id")
        if class_key:
            index = self.class_filter.findData(class_key)
            if index >= 0:
                self.class_filter.setCurrentIndex(index)
        elif self.class_filter.count() > 1:
            self.class_filter.setCurrentIndex(1)
        subject_key = context.get("default_subject_id")
        if subject_key:
            index = self.subject_filter.findData(subject_key)
            if index >= 0:
                self.subject_filter.setCurrentIndex(index)
        elif self.subject_filter.count() > 1:
            self.subject_filter.setCurrentIndex(1)
        self.class_filter.blockSignals(False)
        self.subject_filter.blockSignals(False)

    def _build_headers(self) -> list[str]:
        return self.BASE_COLUMNS + [component["component_name"] for component in self.component_layout] + self.SUMMARY_COLUMNS

    def _setup_table(self) -> None:
        headers = self._build_headers()
        set_table_headers(self.table, headers, default_row_height=42)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 120)
        self.component_column_map = {}
        self.readonly_columns = {0, 1}
        component_start = len(self.BASE_COLUMNS)
        for index, component in enumerate(self.component_layout, start=component_start):
            self.component_column_map[component["component_code"]] = index
            header.setSectionResizeMode(index, QHeaderView.Fixed)
            self.table.setColumnWidth(index, 88 if component["component_type"] in {"uts", "uas"} else 78)
        summary_start = len(headers) - len(self.SUMMARY_COLUMNS)
        for index in range(summary_start, len(headers)):
            header.setSectionResizeMode(index, QHeaderView.Fixed)
        self.table.setColumnWidth(summary_start, 118)
        self.table.setColumnWidth(summary_start + 1, 88)
        self.table.setColumnWidth(summary_start + 2, 100)
        self.table.setColumnWidth(summary_start + 3, 84)
        self.table.setColumnWidth(summary_start + 4, 132)
        self.table.setColumnWidth(summary_start + 5, 78)
        self.readonly_columns.update({summary_start, summary_start + 2, summary_start + 3, summary_start + 4, summary_start + 5})

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        self.table.setRowCount(0)
        if not self.services["classes"].get_classes():
            self.helper_label.setText("Buat data kelas terlebih dahulu.")
            return
        if not self.services["subjects"].get_subjects():
            self.helper_label.setText("Buat data mata pelajaran terlebih dahulu dan isi KKM per mapel.")
            return
        if not class_id or not subject_id:
            self.helper_label.setText("Pilih kelas dan mapel untuk mulai input nilai.")
            self._set_component_controls_enabled(False)
            return
        self._set_component_controls_enabled(True)
        if self.app_mode == "guru_mapel":
            self.services["settings"].update_active_context(default_class_id=class_id, default_subject_id=subject_id)
        self.rows = self.services["grades"].get_grade_rows(class_id, subject_id)
        self.component_layout = self.services["grades"].get_component_layout(subject_id)
        self._load_component_scheme(subject_id)
        self._setup_table()
        self.table.setRowCount(len(self.rows))
        if not self.rows:
            self.helper_label.setText("Belum ada siswa pada kelas ini. Tambahkan siswa terlebih dahulu.")
            return
        kkm = self.rows[0].get("kkm", self.services["grades"].get_subject_kkm(subject_id))
        active_parts = []
        scheme = self.services["grades"].get_component_scheme(subject_id)
        if scheme["use_daily_components"] and scheme["daily_component_count"] > 0:
            active_parts.append(f"Harian {scheme['daily_component_count']} kolom")
        if scheme["use_homework_components"] and scheme["homework_component_count"] > 0:
            active_parts.append(f"PR {scheme['homework_component_count']} kolom")
        if scheme["use_practice_component"]:
            active_parts.append("Praktek")
        if scheme["use_mid_component"]:
            active_parts.append("UTS")
        if scheme["use_final_component"]:
            active_parts.append("UAS")
        self.helper_label.setText(
            f"Komponen aktif: {', '.join(active_parts)}. KKM mapel ini {kkm}."
        )
        for row_index, row in enumerate(self.rows):
            self.table.setItem(row_index, 0, self._readonly_item(row["full_name"]))
            self.table.setItem(row_index, 1, self._readonly_item(row["class_name"]))
            for component in self.component_layout:
                column = self.component_column_map[component["component_code"]]
                value = row["component_scores"].get(component["component_code"], 0.0)
                self.table.setItem(row_index, column, self._editable_numeric_item(value))
            summary_start = len(self.BASE_COLUMNS) + len(self.component_layout)
            values = [
                row["daily_score"],
                row["extra_score"],
                row["final_result"],
                row["predicate"],
                row["status"],
                row["rank_number"],
            ]
            for offset, value in enumerate(values):
                column = summary_start + offset
                if column == summary_start + 3 or column == summary_start + 4:
                    item = badge_item(value)
                else:
                    item = self._readonly_item(value) if column in self.readonly_columns else QTableWidgetItem(str(value))
                self.table.setItem(row_index, column, item)

    def _cell_text(self, row: int, column: int, default: str = "") -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item and item.text().strip() else default

    def _cell_float(self, row: int, column: int, *, allow_blank: bool = False) -> float | None:
        text = self._cell_text(row, column, "")
        return self.services["grades"].validate_score(text, allow_blank=allow_blank)

    def _readonly_item(self, value: object) -> QTableWidgetItem:
        item = QTableWidgetItem("" if value is None else str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _editable_numeric_item(self, value: object) -> QTableWidgetItem:
        item = QTableWidgetItem("" if value is None else str(value))
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _summary_column(self, name: str) -> int:
        base = len(self.BASE_COLUMNS) + len(self.component_layout)
        return {
            "daily_avg": base,
            "extra": base + 1,
            "final": base + 2,
            "predicate": base + 3,
            "status": base + 4,
            "rank": base + 5,
        }[name]

    def _build_component_payload(self, row_index: int) -> dict[str, float | None]:
        return {
            component["component_code"]: self._cell_float(row_index, self.component_column_map[component["component_code"]], allow_blank=True)
            for component in self.component_layout
        }

    def save_all(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        if not class_id or not subject_id:
            error(self, "Kelas dan mapel wajib dipilih.")
            return
        try:
            extra_column = self._summary_column("extra")
            for row_index, row in enumerate(self.rows):
                self.services["grades"].save_grade(
                    {
                        "student_id": row["student_id"],
                        "subject_id": subject_id,
                        "component_scores": self._build_component_payload(row_index),
                        "extra_score": self._cell_float(row_index, extra_column) or 0,
                    }
                )
            self.services["grades"].calculate_ranking(class_id, subject_id)
            self.refresh()
            info(self, "Nilai berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))

    def calculate_all(self) -> None:
        subject_id = self.subject_filter.currentData()
        try:
            for row_index, _ in enumerate(self.rows):
                component_scores = self._build_component_payload(row_index)
                daily_scores = [
                    score
                    for code, score in component_scores.items()
                    if code.startswith("harian_") or code.startswith("pr_") or code == "praktek"
                ]
                daily_average = self.services["grades"].calculate_daily_average(daily_scores)
                mid = float(component_scores.get("uts") or 0)
                final = float(component_scores.get("uas") or 0)
                extra = self._cell_float(row_index, self._summary_column("extra")) or 0
                result = self.services["grades"].calculate_final_score(daily_average, mid, final, extra)
                predicate = self.services["grades"].get_predicate(result)
                status = self.services["grades"].get_status(result, subject_id=subject_id)
                self.table.setItem(row_index, self._summary_column("daily_avg"), self._readonly_item(daily_average))
                self.table.setItem(row_index, self._summary_column("final"), self._readonly_item(result))
                self.table.setItem(row_index, self._summary_column("predicate"), badge_item(predicate))
                self.table.setItem(row_index, self._summary_column("status"), badge_item(status))
        except Exception as exc:
            error(self, str(exc))

    def import_grades(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Nilai", "", "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return
        try:
            count = self.services["excel"].import_grades_excel(file_path)
            self.refresh_filters()
            self.refresh()
            info(self, f"{count} nilai berhasil diimport.")
        except Exception as exc:
            error(self, str(exc))

    def export_data(self) -> None:
        try:
            file_path = self.services["excel"].export_grades_excel(self.class_filter.currentData(), self.subject_filter.currentData())
            info(self, f"Export berhasil: {file_path}")
        except Exception as exc:
            error(self, str(exc))

    def download_template(self) -> None:
        try:
            file_path = self.services["excel"].create_grade_template(self.subject_filter.currentData())
            info(self, f"Template berhasil dibuat: {file_path}")
        except Exception as exc:
            error(self, str(exc))

    def save_component_layout(self) -> None:
        subject_id = self.subject_filter.currentData()
        if not subject_id:
            error(self, "Pilih mapel terlebih dahulu.")
            return
        try:
            self.services["grades"].update_component_layout(
                subject_id,
                {
                    "use_daily_components": 1 if self.use_daily_components.isChecked() else 0,
                    "daily_component_count": self.daily_component_count.currentData(),
                    "use_homework_components": 1 if self.use_homework_components.isChecked() else 0,
                    "homework_component_count": self.homework_component_count.currentData(),
                    "use_practice_component": 1 if self.use_practice_component.isChecked() else 0,
                    "use_mid_component": 1 if self.use_mid_component.isChecked() else 0,
                    "use_final_component": 1 if self.use_final_component.isChecked() else 0,
                },
            )
            self.refresh()
            info(self, "Komponen nilai mapel berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))

    def _load_component_scheme(self, subject_id: int) -> None:
        scheme = self.services["grades"].get_component_scheme(subject_id)
        self.use_daily_components.setChecked(bool(scheme["use_daily_components"]))
        self.use_homework_components.setChecked(bool(scheme["use_homework_components"]))
        self.use_practice_component.setChecked(bool(scheme["use_practice_component"]))
        self.use_mid_component.setChecked(bool(scheme["use_mid_component"]))
        self.use_final_component.setChecked(bool(scheme["use_final_component"]))
        daily_index = self.daily_component_count.findData(int(scheme["daily_component_count"]))
        homework_index = self.homework_component_count.findData(int(scheme["homework_component_count"]))
        self.daily_component_count.setCurrentIndex(daily_index if daily_index >= 0 else 0)
        self.homework_component_count.setCurrentIndex(homework_index if homework_index >= 0 else 0)
        self._update_component_visibility()

    def _set_component_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.use_daily_components,
            self.use_homework_components,
            self.use_practice_component,
            self.use_mid_component,
            self.use_final_component,
            self.daily_component_count,
            self.homework_component_count,
            self.save_layout_button,
        ):
            widget.setEnabled(enabled)
        self._update_component_visibility()

    def _update_component_visibility(self) -> None:
        controls_enabled = self.save_layout_button.isEnabled()
        self._set_field_visible(
            self.daily_component_count,
            controls_enabled and self.use_daily_components.isChecked(),
        )
        self._set_field_visible(
            self.homework_component_count,
            controls_enabled and self.use_homework_components.isChecked(),
        )
        self.daily_component_count.setEnabled(controls_enabled and self.use_daily_components.isChecked())
        self.homework_component_count.setEnabled(controls_enabled and self.use_homework_components.isChecked())

    def _set_field_visible(self, widget: QWidget, visible: bool) -> None:
        parent = widget.parentWidget()
        if parent:
            label = parent.layout().labelForField(widget) if isinstance(parent.layout(), QFormLayout) else None
            if label:
                label.setVisible(visible)
        widget.setVisible(visible)
