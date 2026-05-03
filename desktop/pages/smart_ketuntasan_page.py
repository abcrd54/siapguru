from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs import confirm, error, info
from ui.widgets import ActionButton, CardWidget, PageHeader, add_row_actions, badge_item, set_table_headers, table_item


class SmartKetuntasanPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []
        self.component_layout: list[dict] = []
        self.component_column_map: dict[str, int] = {}

        layout = QVBoxLayout(self)
        subtitle = "Simulasikan dan terapkan penyesuaian nilai akhir raport pada kelas dan mapel yang Anda ampu tanpa mengubah urutan pencapaian siswa."
        layout.addWidget(PageHeader("Katrol Nilai", subtitle))

        self.step_label = QLabel(
            "1. Pilih kelas dan mapel. 2. Tentukan rentang nilai akhir yang diinginkan. 3. Periksa hasil simulasi, lalu proses jika sudah sesuai."
        )
        self.step_label.setObjectName("DialogHint")
        self.step_label.setWordWrap(True)
        layout.addWidget(self.step_label)

        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.target_min_score = QDoubleSpinBox()
        self.target_max_score = QDoubleSpinBox()
        for field, value in (
            (self.target_min_score, 75),
            (self.target_max_score, 96),
        ):
            field.setRange(0, 100)
            field.setDecimals(0)
            field.setValue(value)
            field.setButtonSymbols(QDoubleSpinBox.NoButtons)
            field.setAlignment(Qt.AlignCenter)
            field.setMinimumWidth(120)
            field.setMaximumWidth(140)

        self.class_filter.currentIndexChanged.connect(self.refresh)
        self.subject_filter.currentIndexChanged.connect(self.refresh)
        self.target_min_score.valueChanged.connect(self.refresh)
        self.target_max_score.valueChanged.connect(self.refresh)

        form_card = QWidget()
        form = QFormLayout(form_card)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.class_filter.setMinimumWidth(240)
        self.subject_filter.setMinimumWidth(240)
        form.addRow("1. Pilih Kelas", self.class_filter)
        form.addRow("2. Pilih Mapel", self.subject_filter)

        target_row = QWidget()
        target_layout = QHBoxLayout(target_row)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(14)

        min_wrap = QVBoxLayout()
        min_label = QLabel("Nilai Terendah")
        min_label.setObjectName("PageSubtitle")
        min_wrap.addWidget(min_label)
        min_wrap.addWidget(self.target_min_score)

        max_wrap = QVBoxLayout()
        max_label = QLabel("Nilai Tertinggi")
        max_label.setObjectName("PageSubtitle")
        max_wrap.addWidget(max_label)
        max_wrap.addWidget(self.target_max_score)

        dash_label = QLabel("sampai")
        dash_label.setObjectName("PageSubtitle")
        dash_label.setAlignment(Qt.AlignCenter)

        target_layout.addLayout(min_wrap)
        target_layout.addWidget(dash_label)
        target_layout.addLayout(max_wrap)
        target_layout.addStretch()

        form.addRow("3. Rentang Nilai Akhir", target_row)
        layout.addWidget(form_card)

        self.summary_grid = QGridLayout()
        layout.addLayout(self.summary_grid)

        actions = QHBoxLayout()
        actions.addStretch()
        self.apply_button = ActionButton("Proses Penyesuaian Nilai", primary=True)
        self.apply_button.setMaximumWidth(230)
        self.apply_button.clicked.connect(self.apply_bulk)
        actions.addWidget(self.apply_button)
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
            "Nilai Akhir Sebelum",
            "KKM",
            "Nilai Akhir Sesudah",
            "Status",
            "Aksi",
        ]

    def _setup_table(self) -> None:
        headers = self._build_headers()
        set_table_headers(self.table, headers, action_col_width=136, default_row_height=48)
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
        self.table.setColumnWidth(start + len(self.component_layout), 122)
        self.table.setColumnWidth(start + len(self.component_layout) + 1, 70)
        self.table.setColumnWidth(start + len(self.component_layout) + 2, 122)
        status_col = start + len(self.component_layout) + 3
        header.setSectionResizeMode(status_col, QHeaderView.Stretch)

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        self.table.setRowCount(0)
        if not class_id or not subject_id:
            self._render_summary([])
            self.apply_button.setEnabled(False)
            self.helper_label.setText("Pilih kelas dan mapel untuk melihat simulasi penyesuaian nilai akhir.")
            return
        self.services["settings"].update_active_context(default_class_id=class_id, default_subject_id=subject_id)
        target_min = float(self.target_min_score.value())
        target_max = float(self.target_max_score.value())
        if target_min > target_max:
            self._render_summary([])
            self.apply_button.setEnabled(False)
            self.helper_label.setText("Nilai akhir terendah tidak boleh lebih besar dari nilai akhir tertinggi.")
            return
        self.component_layout = self.services["grades"].get_component_layout(subject_id)
        self.rows = self.services["remedial"].get_adjustment_candidates(
            class_id,
            subject_id,
            target_min_score=target_min,
            target_max_score=target_max,
        )
        self._render_summary(self.rows)
        self._setup_table()
        self.table.setRowCount(len(self.rows))
        if not self.rows:
            self.apply_button.setEnabled(False)
            self.helper_label.setText("Belum ada data siswa atau nilai akhir pada kelas dan mapel ini.")
            return

        self.apply_button.setEnabled(True)
        for row_index, row in enumerate(self.rows):
            self.table.setItem(row_index, 0, table_item(row["full_name"], alignment=Qt.AlignLeft))
            self.table.setItem(row_index, 1, table_item(row["class_name"]))
            for component in self.component_layout:
                column = self.component_column_map[component["component_code"]]
                score = row["component_scores"].get(component["component_code"], 0.0)
                self.table.setItem(row_index, column, table_item(round(float(score), 0)))
            summary_start = 2 + len(self.component_layout)
            self.table.setItem(
                row_index,
                summary_start,
                table_item(row["before_final_score"], foreground="#9A3412", background="#FFF1E7"),
            )
            self.table.setItem(row_index, summary_start + 1, table_item(row["kkm"]))
            self.table.setItem(
                row_index,
                summary_start + 2,
                table_item(row["after_final_score"], foreground="#1D4ED8", background="#E8F1FF"),
            )
            self.table.setItem(row_index, summary_start + 3, badge_item(row["remedial_status"]))
            add_row_actions(
                self.table,
                row_index,
                [("Terapkan", lambda _, data=row: self.apply_one(data)), ("Reset", lambda _, data=row: self.reset_one(data))],
            )
        self.table.resizeRowsToContents()
        self.helper_label.setText(
            "Simulasi ini memakai nilai akhir raport yang sudah dihitung dari bobot mapel aktif. Nilai sebelum dan sesudah penyesuaian ditampilkan agar perubahan mudah dicek."
        )

    def apply_one(self, row: dict) -> None:
        try:
            self.services["remedial"].apply_recommendation(
                row["grade_id"],
                float(row["adjusted_score"]),
                f"Penyesuaian nilai akhir rentang {row['target_min_score']:.0f}-{row['target_max_score']:.0f}",
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
            error(self, "Nilai akhir terendah tidak boleh lebih besar dari nilai akhir tertinggi.")
            return
        if not self.rows:
            error(self, "Belum ada data nilai yang bisa diproses.")
            return
        try:
            if not confirm(
                self,
                f"Proses penyesuaian nilai akhir semua siswa ke rentang {target_min:.0f}-{target_max:.0f}?",
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
        info(self, "Nilai hasil penyesuaian berhasil direset.")

    def _render_summary(self, rows: list[dict]) -> None:
        while self.summary_grid.count():
            item = self.summary_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not rows:
            cards = [
                CardWidget("Jumlah Siswa", "0"),
                CardWidget("Nilai Terendah", "-"),
                CardWidget("Nilai Tertinggi", "-"),
                CardWidget("Target Baru", f"{self.target_min_score.value():.0f}-{self.target_max_score.value():.0f}", "#2563EB"),
            ]
        else:
            current_scores = [float(row["original_score"]) for row in rows]
            cards = [
                CardWidget("Jumlah Siswa", str(len(rows))),
                CardWidget("Nilai Awal Terendah", f"{min(current_scores):.0f}"),
                CardWidget("Nilai Awal Tertinggi", f"{max(current_scores):.0f}"),
                CardWidget("Target Baru", f"{self.target_min_score.value():.0f}-{self.target_max_score.value():.0f}", "#2563EB"),
            ]
        for index, card in enumerate(cards):
            self.summary_grid.addWidget(card, 0, index)
