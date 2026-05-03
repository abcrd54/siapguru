from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QBrush, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemDelegate,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader, badge_item, set_table_headers


class GradeSheetTable(QTableWidget):
    def __init__(self) -> None:
        super().__init__()
        self._editor_filter_installed = False

    def mousePressEvent(self, event) -> None:
        if self.state() == QAbstractItemView.EditingState:
            self._finish_active_edit()
        super().mousePressEvent(event)
        item = self.itemAt(event.position().toPoint())
        if item and (item.flags() & Qt.ItemIsEditable):
            self._begin_edit(item)

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.Paste):
            self._paste_block()
            return
        if event.matches(QKeySequence.Copy):
            super().keyPressEvent(event)
            return
        if event.key() in {Qt.Key_Delete, Qt.Key_Backspace}:
            self._clear_selected_editable_cells()
            return
        if event.key() == Qt.Key_Tab:
            next_cell = self._adjacent_editable_cell(self.currentRow(), self.currentColumn(), forward=not bool(event.modifiers() & Qt.ShiftModifier))
            if next_cell:
                self.setCurrentCell(*next_cell)
                self._begin_edit(self.item(*next_cell))
            return
        if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
            current = self.currentItem()
            if current and (current.flags() & Qt.ItemIsEditable):
                next_cell = self._next_editable_cell(self.currentRow(), self.currentColumn())
                if next_cell:
                    self.setCurrentCell(*next_cell)
                    self._begin_edit(self.item(*next_cell))
                    return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.MouseButtonPress and self.state() == QAbstractItemView.EditingState:
            editor = self._active_editor()
            if editor is not None and watched is not editor and not editor.isAncestorOf(watched):
                self._finish_active_edit()
        return super().eventFilter(watched, event)

    def _begin_edit(self, item: QTableWidgetItem | None) -> None:
        if item is None:
            return
        self._ensure_editor_filter()
        self.editItem(item)

    def _ensure_editor_filter(self) -> None:
        if not self._editor_filter_installed:
            QApplication.instance().installEventFilter(self)
            self._editor_filter_installed = True

    def _active_editor(self):
        widget = QApplication.focusWidget()
        if widget and widget is not self and self.isAncestorOf(widget):
            return widget
        return None

    def _finish_active_edit(self) -> None:
        editor = self._active_editor()
        if editor is not None:
            self.closeEditor(editor, QAbstractItemDelegate.NoHint)
            self.setFocus()

    def _next_editable_cell(self, row: int, column: int) -> tuple[int, int] | None:
        for row_index in range(row, self.rowCount()):
            start_col = column + 1 if row_index == row else 0
            for col_index in range(start_col, self.columnCount()):
                item = self.item(row_index, col_index)
                if item and (item.flags() & Qt.ItemIsEditable):
                    return row_index, col_index
        return None

    def _paste_block(self) -> None:
        text = QApplication.clipboard().text().strip("\n")
        if not text:
            return
        start_row = self.currentRow()
        start_col = self.currentColumn()
        if start_row < 0 or start_col < 0:
            return
        rows = [line.split("\t") for line in text.splitlines()]
        for row_offset, values in enumerate(rows):
            target_row = start_row + row_offset
            if target_row >= self.rowCount():
                break
            for col_offset, value in enumerate(values):
                target_col = start_col + col_offset
                if target_col >= self.columnCount():
                    break
                item = self.item(target_row, target_col)
                if item and (item.flags() & Qt.ItemIsEditable):
                    item.setText(value.strip())

    def _clear_selected_editable_cells(self) -> None:
        for item in self.selectedItems():
            if item.flags() & Qt.ItemIsEditable:
                item.setText("")

    def _adjacent_editable_cell(self, row: int, column: int, *, forward: bool) -> tuple[int, int] | None:
        positions: list[tuple[int, int]] = []
        for row_index in range(self.rowCount()):
            for col_index in range(self.columnCount()):
                item = self.item(row_index, col_index)
                if item and (item.flags() & Qt.ItemIsEditable):
                    positions.append((row_index, col_index))
        if not positions:
            return None
        current = (row, column)
        if current not in positions:
            return positions[0] if forward else positions[-1]
        index = positions.index(current)
        next_index = index + 1 if forward else index - 1
        if 0 <= next_index < len(positions):
            return positions[next_index]
        return positions[-1] if not forward else positions[0]


class GradesPage(QWidget):
    BASE_COLUMNS = ["No", "NIS", "Nama Siswa"]
    SUMMARY_COLUMNS = ["Rata-rata Harian", "Nilai Akhir", "Predikat", "Status"]
    HEADER_ROWS = 2

    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []
        self.component_layout: list[dict] = []
        self.component_column_map: dict[str, int] = {}
        self.readonly_columns: set[int] = set()

        layout = QVBoxLayout(self)
        subtitle = "Pilih kelas dan mapel yang Anda ampu, lalu isi nilai seperti di lembar Excel. Komponen dan hasil akhir mengikuti pengaturan mapel."
        layout.addWidget(PageHeader("Nilai Siswa", subtitle))

        self.step_label = QLabel(
            "Pilih kelas dan mapel, lalu tabel siswa akan muncul otomatis. Isi komponen nilai, simpan, dan aplikasi akan menghitung nilai akhir raport sesuai bobot mapel."
        )
        self.step_label.setObjectName("DialogHint")
        self.step_label.setWordWrap(True)
        layout.addWidget(self.step_label)

        controls = QHBoxLayout()
        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.search_input = QLineEdit()
        self.class_filter.currentIndexChanged.connect(self.refresh)
        self.subject_filter.currentIndexChanged.connect(self.refresh)
        self.search_input.textChanged.connect(self._filter_visible_rows)
        self.class_filter.setMinimumWidth(220)
        self.class_filter.setMaximumWidth(300)
        self.subject_filter.setMinimumWidth(240)
        self.subject_filter.setMaximumWidth(340)
        self.search_input.setMinimumWidth(230)
        self.search_input.setMaximumWidth(280)
        self.search_input.setPlaceholderText("Cari siswa...")
        controls.addWidget(self.class_filter)
        controls.addWidget(self.subject_filter)
        controls.addWidget(self.search_input)
        controls.addStretch()

        layout.addLayout(controls)

        secondary_actions = QHBoxLayout()
        self.layout_tool_label = QLabel(
            "Atur komponen nilai aktif untuk mapel ini. Bobot Harian, UTS, dan UAS diatur dari menu Mata Pelajaran."
        )
        self.layout_tool_label.setObjectName("PageSubtitle")
        secondary_actions.addWidget(self.layout_tool_label)
        secondary_actions.addStretch()
        self.template_button = ActionButton("Template Isi Nilai")
        self.template_button.setMaximumWidth(160)
        self.template_button.clicked.connect(self.download_template)
        self.import_button = ActionButton("Import Excel")
        self.import_button.setMaximumWidth(160)
        self.import_button.clicked.connect(self.import_grades)
        secondary_actions.addWidget(self.template_button)
        secondary_actions.addWidget(self.import_button)
        layout.addLayout(secondary_actions)

        self.use_daily_components = QCheckBox("Aktifkan Harian")
        self.use_mid_component = QCheckBox("Aktifkan UTS")
        self.use_final_component = QCheckBox("Aktifkan UAS")
        self.daily_component_count = QComboBox()
        for value in range(0, 7):
            label = "Nonaktif" if value == 0 else str(value)
            self.daily_component_count.addItem(label, value)

        self.component_card = QWidget()
        self.component_card.setObjectName("DialogCard")
        component_layout = QVBoxLayout(self.component_card)
        component_layout.setContentsMargins(16, 16, 16, 16)
        component_layout.setSpacing(12)
        component_title = QLabel("Atur Kolom Nilai")
        component_title.setObjectName("CardTitle")
        component_help = QLabel(
            "Aktifkan komponen yang dipakai pada mapel ini, lalu tentukan berapa kolom Harian yang perlu dimunculkan."
        )
        component_help.setWordWrap(True)
        component_help.setObjectName("PageSubtitle")
        self.daily_component_count.setMaximumWidth(86)
        component_row = QHBoxLayout()
        component_row.setSpacing(18)
        component_row.addWidget(self.use_daily_components)
        component_row.addWidget(QLabel("Kolom"))
        component_row.addWidget(self.daily_component_count)
        component_row.addSpacing(10)
        component_row.addWidget(self.use_mid_component)
        component_row.addWidget(self.use_final_component)
        component_row.addStretch()
        component_buttons = QHBoxLayout()
        self.save_layout_button = ActionButton("Simpan Pengaturan Kolom")
        self.save_layout_button.clicked.connect(self.save_component_layout)
        component_buttons.addWidget(self.save_layout_button)
        component_buttons.addStretch()
        component_layout.addWidget(component_title)
        component_layout.addWidget(component_help)
        component_layout.addLayout(component_row)
        component_layout.addLayout(component_buttons)
        layout.addWidget(self.component_card)

        self.table_intro = QLabel(
            "Template Isi Nilai dan Import Excel dipakai untuk mulai input. Setelah selesai, klik Simpan Nilai agar aplikasi menghitung nilai akhir raport berdasarkan komponen aktif dan bobot mapel."
        )
        self.table_intro.setObjectName("DialogHint")
        self.table_intro.setWordWrap(True)
        layout.addWidget(self.table_intro)

        self.table = GradeSheetTable()
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        self.helper_label.setWordWrap(True)
        layout.addWidget(self.helper_label)

        bottom_actions = QHBoxLayout()
        bottom_actions.addStretch()
        self.export_button = ActionButton("Unduh Nilai")
        self.export_button.setMaximumWidth(160)
        self.export_button.clicked.connect(self.export_data)
        self.save_button = ActionButton("Simpan Nilai", primary=True)
        self.save_button.setMaximumWidth(160)
        self.save_button.clicked.connect(self.save_all)
        bottom_actions.addWidget(self.export_button)
        bottom_actions.addWidget(self.save_button)
        layout.addLayout(bottom_actions)

        self.refresh_filters()
        self.refresh()

        self.use_daily_components.toggled.connect(self._update_component_visibility)

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
        header.setVisible(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 110)
        self.component_column_map = {}
        self.readonly_columns = {0, 1, 2}
        component_start = len(self.BASE_COLUMNS)
        for index, component in enumerate(self.component_layout, start=component_start):
            self.component_column_map[component["component_code"]] = index
            header.setSectionResizeMode(index, QHeaderView.Fixed)
            self.table.setColumnWidth(index, 88 if component["component_type"] in {"uts", "uas"} else 78)
        summary_start = len(headers) - len(self.SUMMARY_COLUMNS)
        for index in range(summary_start, len(headers)):
            header.setSectionResizeMode(index, QHeaderView.Fixed)
        self.table.setColumnWidth(summary_start, 118)
        self.table.setColumnWidth(summary_start + 1, 104)
        self.table.setColumnWidth(summary_start + 2, 84)
        self.table.setColumnWidth(summary_start + 3, 132)
        self.readonly_columns.update({summary_start, summary_start + 1, summary_start + 2, summary_start + 3})
        self.table.setSpan(0, 0, 2, 1)
        self.table.setSpan(0, 1, 2, 1)
        self.table.setSpan(0, 2, 2, 1)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setRowHeight(0, 32)
        self.table.setRowHeight(1, 40)

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        self.table.setRowCount(0)
        if not self.services["classes"].get_classes():
            self._set_component_controls_enabled(False)
            self._set_action_buttons_enabled(False)
            self.helper_label.setText("Buat data kelas terlebih dahulu.")
            return
        if not self.services["subjects"].get_subjects():
            self._set_component_controls_enabled(False)
            self._set_action_buttons_enabled(False)
            self.helper_label.setText("Buat data mata pelajaran terlebih dahulu dan isi KKM per mapel.")
            return
        if not class_id or not subject_id:
            self._set_component_controls_enabled(False)
            self._set_action_buttons_enabled(False)
            self.helper_label.setText("Pilih kelas dan mapel untuk mulai input nilai.")
            return

        self._set_component_controls_enabled(True)
        self._set_action_buttons_enabled(True)
        self.services["settings"].update_active_context(default_class_id=class_id, default_subject_id=subject_id)
        self.rows = self.services["grades"].get_grade_rows(class_id, subject_id)
        self.component_layout = self.services["grades"].get_component_layout(subject_id)
        self._load_component_scheme(subject_id)
        self._setup_table()
        self.table.setRowCount(len(self.rows) + self.HEADER_ROWS)
        self._render_sheet_headers()
        if not self.rows:
            self.helper_label.setText("Belum ada siswa pada kelas ini. Tambahkan siswa terlebih dahulu.")
            return

        scheme = self.services["grades"].get_component_scheme(subject_id)
        has_existing_grades = any(row.get("has_grade_record") for row in self.rows)
        active_parts = []
        if scheme["use_daily_components"] and scheme["daily_component_count"] > 0:
            active_parts.append(f"H{scheme['daily_component_count']}")
        if scheme["use_mid_component"]:
            active_parts.append("UTS")
        if scheme["use_final_component"]:
            active_parts.append("UAS")
        kkm = self.rows[0].get("kkm", self.services["grades"].get_subject_kkm(subject_id))
        weights = self.services["grades"].get_subject_weights(subject_id)
        weight_text = f"Bobot mapel: Harian {weights[0]}% | UTS {weights[1]}% | UAS {weights[2]}%."
        if has_existing_grades:
            self.helper_label.setText(
                f"Nilai yang sudah tersimpan untuk kelas dan mapel ini langsung ditampilkan. Anda bisa edit sel nilainya, lalu proses dan simpan lagi. Header aktif: {', '.join(active_parts)}. KKM {kkm}. {weight_text}"
            )
        else:
            self.helper_label.setText(
                f"Belum ada nilai tersimpan untuk kelas dan mapel ini. Daftar siswa ditampilkan sebagai template kosong siap isi langsung di sel. Header aktif: {', '.join(active_parts)}. KKM {kkm}. {weight_text}"
            )

        for row_index, row in enumerate(self.rows):
            data_row = self._data_row(row_index)
            self.table.setItem(data_row, 0, self._readonly_item(row_index + 1, background="#F3F6FB"))
            self.table.setItem(data_row, 1, self._readonly_item(row["nis"], background="#F3F6FB"))
            self.table.setItem(data_row, 2, self._readonly_item(row["full_name"], alignment=Qt.AlignLeft, background="#F3F6FB"))
            for component in self.component_layout:
                column = self.component_column_map[component["component_code"]]
                value = row["component_scores"].get(component["component_code"])
                self.table.setItem(data_row, column, self._editable_numeric_item(value))

            summary_start = len(self.BASE_COLUMNS) + len(self.component_layout)
            has_grade_record = bool(row.get("has_grade_record"))
            self.table.setItem(
                data_row,
                summary_start,
                self._readonly_item(
                    self._display_score(row["daily_score"]) if has_grade_record else "",
                    foreground="#1D4ED8",
                    background="#E8F1FF",
                ),
            )
            self.table.setItem(
                data_row,
                summary_start + 1,
                self._readonly_item(
                    self._display_score(row["final_result"]) if has_grade_record else "",
                    foreground="#0F766E",
                    background="#DCFCE7",
                ),
            )
            self.table.setItem(data_row, summary_start + 2, badge_item(row["predicate"] if has_grade_record else ""))
            self.table.setItem(data_row, summary_start + 3, badge_item(row["status"] if has_grade_record else ""))
        self.table.resizeRowsToContents()
        self._filter_visible_rows()

    def _cell_text(self, row: int, column: int, default: str = "") -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item and item.text().strip() else default

    def _cell_float(self, row: int, column: int, *, allow_blank: bool = False) -> float | None:
        text = self._cell_text(row, column, "")
        return self.services["grades"].validate_score(text, allow_blank=allow_blank)

    def _readonly_item(
        self,
        value: object,
        *,
        foreground: str | None = None,
        background: str | None = None,
        alignment: Qt.AlignmentFlag | Qt.Alignment = Qt.AlignCenter,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem("" if value is None else str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(alignment | Qt.AlignVCenter)
        if foreground:
            item.setForeground(QBrush(QColor(foreground)))
        if background:
            item.setBackground(QBrush(QColor(background)))
        return item

    def _editable_numeric_item(self, value: object) -> QTableWidgetItem:
        item = QTableWidgetItem("" if value in (None, "") else str(self._display_score(value)))
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor("#FFFBEA")))
        item.setForeground(QBrush(QColor("#7A5612")))
        return item

    def _display_score(self, value: object) -> int | str:
        if value in (None, ""):
            return ""
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return str(value)

    def _summary_column(self, name: str) -> int:
        base = len(self.BASE_COLUMNS) + len(self.component_layout)
        return {
            "daily_avg": base,
            "final": base + 1,
            "predicate": base + 2,
            "status": base + 3,
        }[name]

    def _build_component_payload(self, row_index: int) -> dict[str, float | None]:
        data_row = self._data_row(row_index)
        return {
            component["component_code"]: self._cell_float(
                data_row,
                self.component_column_map[component["component_code"]],
                allow_blank=True,
            )
            for component in self.component_layout
        }

    def save_all(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        if not class_id or not subject_id:
            error(self, "Kelas dan mapel wajib dipilih.")
            return
        try:
            self.calculate_all(show_error=False)
            for row_index, row in enumerate(self.rows):
                self.services["grades"].save_grade(
                    {
                        "student_id": row["student_id"],
                        "subject_id": subject_id,
                        "component_scores": self._build_component_payload(row_index),
                        "extra_score": 0,
                    }
                )
            self.refresh()
            info(self, "Nilai berhasil disimpan.")
        except Exception as exc:
            error(self, str(exc))

    def calculate_all(self, *, show_error: bool = True) -> bool:
        subject_id = self.subject_filter.currentData()
        try:
            for row_index, _ in enumerate(self.rows):
                data_row = self._data_row(row_index)
                component_scores = self._build_component_payload(row_index)
                daily_scores = [
                    score
                    for code, score in component_scores.items()
                    if code.startswith("harian_")
                ]
                daily_average = self.services["grades"].calculate_daily_average(daily_scores)
                mid = float(component_scores.get("uts") or 0)
                final = float(component_scores.get("uas") or 0)
                result = self.services["grades"].calculate_final_score(
                    daily_average,
                    mid,
                    final,
                    0,
                    subject_id=subject_id,
                )
                predicate = self.services["grades"].get_predicate(result)
                status = self.services["grades"].get_status(result, subject_id=subject_id)
                self.table.setItem(
                    data_row,
                    self._summary_column("daily_avg"),
                    self._readonly_item(self._display_score(daily_average), foreground="#1D4ED8", background="#E8F1FF"),
                )
                self.table.setItem(
                    data_row,
                    self._summary_column("final"),
                    self._readonly_item(self._display_score(result), foreground="#0F766E", background="#DCFCE7"),
                )
                self.table.setItem(data_row, self._summary_column("predicate"), badge_item(predicate))
                self.table.setItem(data_row, self._summary_column("status"), badge_item(status))
            return True
        except Exception as exc:
            if show_error:
                error(self, str(exc))
            return False

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
            file_path = self.services["excel"].export_grades_excel(
                self.class_filter.currentData(),
                self.subject_filter.currentData(),
            )
            info(self, f"Data nilai berhasil diunduh: {file_path}")
        except Exception as exc:
            error(self, str(exc))

    def download_template(self) -> None:
        try:
            file_path = self.services["excel"].create_grade_template(
                self.subject_filter.currentData(),
                self.class_filter.currentData(),
            )
            info(self, f"Template isi nilai berhasil dibuat: {file_path}")
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
        self.use_mid_component.setChecked(bool(scheme["use_mid_component"]))
        self.use_final_component.setChecked(bool(scheme["use_final_component"]))
        daily_index = self.daily_component_count.findData(int(scheme["daily_component_count"]))
        self.daily_component_count.setCurrentIndex(daily_index if daily_index >= 0 else 0)
        self._update_component_visibility()

    def _set_component_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.use_daily_components,
            self.use_mid_component,
            self.use_final_component,
            self.daily_component_count,
            self.save_layout_button,
        ):
            widget.setEnabled(enabled)
        self._update_component_visibility()

    def _update_component_visibility(self) -> None:
        controls_enabled = self.save_layout_button.isEnabled()
        self.daily_component_count.setVisible(controls_enabled and self.use_daily_components.isChecked())
        self.daily_component_count.setEnabled(controls_enabled and self.use_daily_components.isChecked())

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        for widget in (
            self.template_button,
            self.import_button,
            self.export_button,
            self.save_button,
            self.search_input,
        ):
            widget.setEnabled(enabled)

    def _data_row(self, row_index: int) -> int:
        return row_index + self.HEADER_ROWS

    def _header_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QBrush(QColor("#223455")))
        item.setBackground(QBrush(QColor("#F7FAFF")))
        return item

    def _render_sheet_headers(self) -> None:
        self.table.clearSpans()
        headers = self._build_headers()
        for column, label in enumerate(self.BASE_COLUMNS):
            self.table.setSpan(0, column, self.HEADER_ROWS, 1)
            self.table.setItem(0, column, self._header_item(label))

        component_start = len(self.BASE_COLUMNS)
        component_groups: list[tuple[str, int, int]] = []
        for index, component in enumerate(self.component_layout, start=component_start):
            group_label = {
                "harian": "Nilai Harian",
                "uts": "Ujian",
                "uas": "Ujian",
            }.get(component["component_type"], "Nilai")
            if component_groups and component_groups[-1][0] == group_label:
                last_label, start, span = component_groups[-1]
                component_groups[-1] = (last_label, start, span + 1)
            else:
                component_groups.append((group_label, index, 1))
            self.table.setItem(1, index, self._header_item(component["component_name"]))

        for label, start, span in component_groups:
            self.table.setSpan(0, start, 1, span)
            self.table.setItem(0, start, self._header_item(label))

        summary_start = len(headers) - len(self.SUMMARY_COLUMNS)
        summary_groups = {
            "Rata-rata Harian": "Hasil",
            "Nilai Akhir": "Hasil",
            "Predikat": "Hasil",
            "Status": "Hasil",
        }
        current_group = None
        group_start = summary_start
        group_span = 0
        for index, label in enumerate(self.SUMMARY_COLUMNS, start=summary_start):
            group_label = summary_groups[label]
            self.table.setItem(1, index, self._header_item(label))
            if current_group is None:
                current_group = group_label
                group_start = index
                group_span = 1
            elif current_group == group_label:
                group_span += 1
            else:
                self.table.setSpan(0, group_start, 1, group_span)
                self.table.setItem(0, group_start, self._header_item(current_group))
                current_group = group_label
                group_start = index
                group_span = 1
        if current_group is not None:
            self.table.setSpan(0, group_start, 1, group_span)
            self.table.setItem(0, group_start, self._header_item(current_group))

    def _filter_visible_rows(self) -> None:
        keyword = self.search_input.text().strip().lower()
        for row_index, row in enumerate(self.rows):
            table_row = self._data_row(row_index)
            haystack = f"{row.get('full_name', '')} {row.get('nis', '')}".lower()
            self.table.setRowHidden(table_row, bool(keyword) and keyword not in haystack)
