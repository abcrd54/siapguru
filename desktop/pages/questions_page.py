from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs import busy, error, info
from ui.widgets import ActionButton, PageHeader, add_row_actions, fill_table, set_table_headers


class QuestionsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.module_rows: list[dict] = []
        self.request_rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.addWidget(
            PageHeader(
                "Soal",
                "Pilih modul, tipe soal, lalu generate soal otomatis dari teks modul yang sudah diekstrak.",
            )
        )

        controls = QHBoxLayout()
        self.class_filter = QComboBox()
        self.subject_filter = QComboBox()
        self.module_filter = QComboBox()
        self.class_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.subject_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.module_filter.currentIndexChanged.connect(self._refresh_module_preview)
        self.class_filter.setMinimumWidth(180)
        self.subject_filter.setMinimumWidth(220)
        self.module_filter.setMinimumWidth(280)
        controls.addWidget(self.class_filter)
        controls.addWidget(self.subject_filter)
        controls.addWidget(self.module_filter)
        controls.addStretch()
        layout.addLayout(controls)

        form = QHBoxLayout()
        self.question_count = QLineEdit("10")
        self.question_count.setMaximumWidth(90)
        self.question_type = QComboBox()
        self.question_type.addItem("Pilihan Ganda", "pilihan_ganda")
        self.question_type.addItem("Essay", "essay")
        self.question_type.currentIndexChanged.connect(self._toggle_choice_count)
        self.choice_count = QComboBox()
        for value in range(2, 9):
            labels = "".join(chr(65 + index) for index in range(value))
            self.choice_count.addItem(f"{value} Pilihan ({labels})", value)
        self.choice_count.setMinimumWidth(170)
        form.addWidget(QLabel("Jumlah Soal"))
        form.addWidget(self.question_count)
        form.addWidget(QLabel("Tipe"))
        form.addWidget(self.question_type)
        form.addWidget(QLabel("Jumlah Opsi"))
        form.addWidget(self.choice_count)
        form.addStretch()
        self.generate_button = ActionButton("Generate Soal")
        self.generate_button.setMaximumWidth(160)
        self.generate_button.clicked.connect(self.generate_questions)
        self.save_button = ActionButton("Simpan Draft", primary=True)
        self.save_button.setMaximumWidth(160)
        self.save_button.clicked.connect(self.save_request)
        form.addWidget(self.save_button)
        form.addWidget(self.generate_button)
        layout.addLayout(form)

        preview_card = QVBoxLayout()
        preview_card.addWidget(QLabel("Pratinjau Teks Modul"))
        self.module_preview = QTextEdit()
        self.module_preview.setReadOnly(True)
        self.module_preview.setPlaceholderText("Pilih modul untuk melihat hasil ekstraksi teks PDF.")
        preview_card.addWidget(self.module_preview)
        layout.addLayout(preview_card)

        self.table = QTableWidget()
        set_table_headers(
            self.table,
            ["No", "Modul", "Kelas", "Mapel", "Tipe", "Jumlah", "Opsi", "Status", "Aksi"],
            action_col_width=92,
        )
        layout.addWidget(self.table)

        self.refresh_filters()
        self.refresh_requests()
        self._toggle_choice_count()

    def refresh(self) -> None:
        self.refresh_filters()
        self.refresh_requests()

    def refresh_filters(self) -> None:
        current_context = self.services["settings"].get_active_context()
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
        if current_context.get("default_class_id"):
            index = self.class_filter.findData(current_context["default_class_id"])
            if index >= 0:
                self.class_filter.setCurrentIndex(index)
        if current_context.get("default_subject_id"):
            index = self.subject_filter.findData(current_context["default_subject_id"])
            if index >= 0:
                self.subject_filter.setCurrentIndex(index)
        self.class_filter.blockSignals(False)
        self.subject_filter.blockSignals(False)
        self._reload_module_options()

    def refresh_requests(self) -> None:
        self.request_rows = self.services["questions"].get_requests()
        fill_table(
            self.table,
            [
                [
                    index + 1,
                    row.get("module_title", "-"),
                    row["class_name"],
                    row["subject_name"],
                    "Pilihan Ganda" if row["question_type"] == "pilihan_ganda" else "Essay",
                    row["question_count"],
                    row["choice_count"] if row["question_type"] == "pilihan_ganda" else "-",
                    self._display_status(row),
                    "",
                ]
                for index, row in enumerate(self.request_rows)
            ],
        )
        for index, row in enumerate(self.request_rows):
            actions = []
            if str(row.get("generated_output", "") or "").strip():
                actions.append(("Lihat", lambda _, data=row: self.view_generated_questions(data)))
            if actions:
                add_row_actions(self.table, index, actions)

    def _on_filter_changed(self) -> None:
        self.services["settings"].update_active_context(
            default_class_id=self.class_filter.currentData(),
            default_subject_id=self.subject_filter.currentData(),
        )
        self._reload_module_options()

    def _reload_module_options(self) -> None:
        class_id = self.class_filter.currentData()
        subject_id = self.subject_filter.currentData()
        self.module_filter.blockSignals(True)
        self.module_filter.clear()
        self.module_filter.addItem("Pilih Modul", None)
        self.module_rows = self.services["modules"].get_module_choices(class_id=class_id, subject_id=subject_id)
        for row in self.module_rows:
            self.module_filter.addItem(row["title"], row["id"])
        self.module_filter.blockSignals(False)
        self._refresh_module_preview()

    def _refresh_module_preview(self) -> None:
        module_id = self.module_filter.currentData()
        if not module_id:
            self.module_preview.clear()
            return
        try:
            excerpt = self.services["modules"].get_module_excerpt(module_id)
            self.module_preview.setPlainText(excerpt)
        except ValueError as exc:
            error(self, str(exc))

    def _toggle_choice_count(self) -> None:
        is_choice = self.question_type.currentData() == "pilihan_ganda"
        self.choice_count.setVisible(is_choice)

    def save_request(self) -> None:
        try:
            self.services["questions"].save_generation_request(
                module_id=self.module_filter.currentData(),
                class_id=self.class_filter.currentData(),
                subject_id=self.subject_filter.currentData(),
                question_count=int(self.question_count.text().strip() or "0"),
                question_type=self.question_type.currentData(),
                choice_count=int(self.choice_count.currentData() or 0),
            )
            self.refresh_requests()
            info(self, "Draft permintaan soal berhasil disimpan.")
        except ValueError as exc:
            error(self, str(exc))

    def generate_questions(self) -> None:
        try:
            with busy(self, "Sedang membuat soal dari modul...") as progress:
                progress.set_progress("Menyiapkan data modul...", 1, 4)
                progress.set_progress("Menyusun prompt soal...", 2, 4)
                progress.set_progress("Mengirim permintaan ke server...", 3, 4)
                result = self.services["questions"].generate_with_ai(
                    module_id=self.module_filter.currentData(),
                    class_id=self.class_filter.currentData(),
                    subject_id=self.subject_filter.currentData(),
                    question_count=int(self.question_count.text().strip() or "0"),
                    question_type=self.question_type.currentData(),
                    choice_count=int(self.choice_count.currentData() or 0),
                )
                progress.set_progress("Menyimpan hasil soal...", 4, 4)
            self.refresh_requests()
            info(self, "Soal berhasil dibuat.")
            row = self._find_request_row(result["request_id"])
            if row:
                self.view_generated_questions(row)
        except (ValueError, RuntimeError) as exc:
            error(self, str(exc))

    def _display_status(self, row: dict) -> str:
        remote_status = str(row.get("remote_sync_status", "") or "").strip()
        generation_status = str(row.get("generation_status", "") or row.get("status", "draft")).strip()
        if remote_status == "synced":
            return "Tersimpan"
        if generation_status == "success":
            return "Lokal"
        if generation_status:
            return generation_status
        return "draft"

    def _find_request_row(self, request_id: int) -> dict | None:
        for row in self.request_rows:
            if int(row["id"]) == int(request_id):
                return row
        refreshed = self.services["questions"].get_requests()
        for row in refreshed:
            if int(row["id"]) == int(request_id):
                return row
        return None

    def view_generated_questions(self, row: dict) -> None:
        payload = str(row.get("generated_output", "") or "").strip()
        if not payload:
            error(self, "Belum ada hasil generate untuk data ini.")
            return
        try:
            formatted = json.dumps(json.loads(payload), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            formatted = payload
        dialog = QuestionResultDialog(
            title=f"Hasil Soal - {row.get('module_title', 'Modul')}",
            content=formatted,
            parent=self,
        )
        dialog.exec()


class QuestionResultDialog(QDialog):
    def __init__(self, title: str, content: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setObjectName("DialogTitle")
        subtitle_label = QLabel("Hasil generate soal disimpan dalam format JSON.")
        subtitle_label.setObjectName("DialogSubtitle")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        content_box = QTextEdit()
        content_box.setReadOnly(True)
        content_box.setPlainText(content)
        layout.addWidget(content_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
