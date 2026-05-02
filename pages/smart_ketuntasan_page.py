from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs import confirm, error, info
from ui.widgets import ActionButton, PageHeader, add_row_actions, badge_item, set_table_headers, table_item


class SmartKetuntasanPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []
        self.component_layout: list[dict] = []
        self.component_column_map: dict[str, int] = {}
        self.app_mode = self.services["app_mode"]

        layout = QVBoxLayout(self)
        subtitle = (
            "Ambil nilai akhir semua siswa pada mapel ini, lalu sesuaikan secara adil ke target rentang nilai raport yang Anda tentukan."
        )
        layout.addWidget(PageHeader("Smart Ketuntasan", subtitle))

        self.step_label = QLabel(
            "Pilih kelas dan mapel, lalu tentukan target nilai raport terendah dan tertinggi untuk hasil akhir semua siswa."
        )
        self.step_label.setWordWrap(True)
        layout.addWidget(self.step_label)

        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.target_min_score = QDoubleSpinBox()
        self.target_max_score = QDoubleSpinBox()
        for field, value, suffix, special in (
            (self.target_min_score, 75, " nilai", "Mulai 0"),
            (self.target_max_score, 96, " nilai", "Sampai 0"),
        ):
            field.setRange(0, 100)
            field.setDecimals(0)
            field.setValue(value)
            field.setSuffix(suffix)
            field.setSpecialValueText(special)

        apply_button = ActionButton("Proses Otomatis", primary=True)
        apply_button.setMaximumWidth(190)
        self.class_filter.currentIndexChanged.connect(self.refresh)
        self.subject_filter.currentIndexChanged.connect(self.refresh)
        self.target_min_score.valueChanged.connect(self.refresh)
        self.target_max_score.valueChanged.connect(self.refresh)
        apply_button.clicked.connect(self.apply_bulk)

        form_card = QWidget()
        form = QFormLayout(form_card)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.class_filter.setMinimumWidth(240)
        self.subject_filter.setMinimumWidth(240)
        self.target_min_score.setMinimumWidth(180)
        self.target_max_score.setMinimumWidth(180)
        form.addRow("1. Pilih Kelas", self.class_filter)
        form.addRow("2. Pilih Mapel", self.subject_filter)
        form.addRow("3. Target Nilai Terendah", self.target_min_score)
        form.addRow("4. Target Nilai Tertinggi", self.target_max_score)
        layout.addWidget(form_card)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(apply_button)
        layout.addLayout(actions)

        self.table = QTableWidget()
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        self.helper_label.setWordWrap(True)
        layout.addWidget(self.helper_label)

        self.refresh_filters()
        self.refresh()

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
            self.subject_filter.addItem(row["subject_name"], row["id"])
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
        component_headers = [component["component_name"] for component in self.component_layout]
        return [
            "Nama",
            "Kelas",
            *component_headers,
            "Tambahan",
            "Nilai Awal",
            "KKM",
            "Nilai Baru",
            "Status",
            "Aksi",
        ]

    def _setup_table(self) -> None:
        headers = self._build_headers()
        set_table_headers(self.table, headers, action_col_width=108, default_row_height=48)
        header = self.table.horizontalHeader()
        self.component_column_map = {}
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 110)
        start = 2
        for index, component in enumerate(self.component_layout, start=start):
            self.component_column_map[component["component_code"]] = index
            header.setSectionResizeMode(index, QHeaderView.Fixed)
            self.table.setColumnWidth(index, 78)
        self.table.setColumnWidth(start + len(self.component_layout), 84)
        self.table.setColumnWidth(start + len(self.component_layout) + 1, 94)
        self.table.setColumnWidth(start + len(self.component_layout) + 2, 70)
        self.table.setColumnWidth(start + len(self.component_layout) + 3, 94)
        status_col = start + len(self.component_layout) + 4
        header.setSectionResizeMode(status_col, QHeaderView.Stretch)

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        self.table.setRowCount(0)
        if not class_id or not subject_id:
            self.helper_label.setText("Pilih kelas dan mapel untuk melihat preview Smart Ketuntasan.")
            return
        self.services["settings"].update_active_context(
            default_class_id=class_id,
            default_subject_id=subject_id,
        )
        target_min = float(self.target_min_score.value())
        target_max = float(self.target_max_score.value())
        if target_min > target_max:
            self.helper_label.setText("Target nilai terendah tidak boleh lebih besar dari target nilai tertinggi.")
            return
        self.component_layout = self.services["grades"].get_component_layout(subject_id)
        self.rows = self.services["remedial"].get_adjustment_candidates(
            class_id,
            subject_id,
            target_min_score=target_min,
            target_max_score=target_max,
        )
        self._setup_table()
        self.table.setRowCount(len(self.rows))
        if not self.rows:
            self.helper_label.setText("Belum ada data siswa atau nilai pada kelas dan mapel ini.")
            return
        for row_index, row in enumerate(self.rows):
            self.table.setItem(row_index, 0, table_item(row["full_name"], alignment=Qt.AlignLeft))
            self.table.setItem(row_index, 1, table_item(row["class_name"]))
            for component in self.component_layout:
                column = self.component_column_map[component["component_code"]]
                score = row["component_scores"].get(component["component_code"], 0.0)
                self.table.setItem(row_index, column, table_item(round(float(score), 2)))
            summary_start = 2 + len(self.component_layout)
            self.table.setItem(row_index, summary_start, table_item(row["extra_score"]))
            self.table.setItem(
                row_index,
                summary_start + 1,
                table_item(row["original_score"], foreground="#9A3412", background="#FFF1E7"),
            )
            self.table.setItem(row_index, summary_start + 2, table_item(row["kkm"]))
            self.table.setItem(
                row_index,
                summary_start + 3,
                table_item(row["adjusted_score"], foreground="#1D4ED8", background="#E8F1FF"),
            )
            self.table.setItem(row_index, summary_start + 4, badge_item(row["remedial_status"]))
            add_row_actions(
                self.table,
                row_index,
                [("Terapkan", lambda _, data=row: self.apply_one(data)), ("Reset", lambda _, data=row: self.reset_one(data))],
            )
        self.table.resizeRowsToContents()
        self.helper_label.setText(
            (
                f"Data ini akan disesuaikan ke target rentang nilai {target_min:.0f}-{target_max:.0f}. "
                "Urutan nilai siswa tetap dipertahankan, lalu hasil akhirnya disebar secara adil ke rentang target itu."
            )
        )

    def apply_one(self, row: dict) -> None:
        try:
            self.services["remedial"].apply_recommendation(
                row["grade_id"],
                float(row["adjusted_score"]),
                f"Smart Ketuntasan rentang {row['target_min_score']:.0f}-{row['target_max_score']:.0f}",
                mode="minimal",
                category="Auto Ketuntasan",
                status_label=row["remedial_status"],
            )
            self.refresh()
            info(self, "Penyesuaian nilai berhasil diterapkan.")
        except Exception as exc:
            error(self, str(exc))

    def apply_bulk(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        if not class_id or not subject_id:
            error(self, "Kelas dan mapel wajib dipilih.")
            return
        target_min = float(self.target_min_score.value())
        target_max = float(self.target_max_score.value())
        if target_min > target_max:
            error(self, "Target nilai terendah tidak boleh lebih besar dari target nilai tertinggi.")
            return
        if not self.rows:
            error(self, "Belum ada data nilai yang bisa diproses.")
            return
        try:
            if not confirm(
                self,
                f"Proses otomatis semua siswa yang tampil ke target rentang nilai {target_min:.0f}-{target_max:.0f}?",
            ):
                return
            count = self.services["remedial"].apply_bulk_adjustments(
                class_id,
                subject_id,
                target_min_score=target_min,
                target_max_score=target_max,
            )
            self.refresh()
            info(self, f"{count} nilai berhasil disesuaikan.")
        except Exception as exc:
            error(self, str(exc))

    def reset_one(self, row: dict) -> None:
        self.services["remedial"].reset_remedial(row["grade_id"])
        self.refresh()
        info(self, "Nilai hasil Smart Ketuntasan direset.")
