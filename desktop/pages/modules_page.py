from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import FormDialog, busy, combo_box, confirm, error, info, line_edit, text_edit
from ui.widgets import ActionButton, PageHeader, add_row_actions, fill_table, set_table_headers


class ModulesPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.addWidget(
            PageHeader(
                "Modul",
                "Upload modul pembelajaran PDF per kelas dan mapel. Aplikasi akan menyalin file ke workspace aktif lalu mengekstrak seluruh teksnya.",
            )
        )
        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari judul modul...")
        self.search_input.textChanged.connect(self.refresh)
        add_button = ActionButton("Upload Modul", primary=True)
        add_button.setMaximumWidth(180)
        add_button.clicked.connect(self.open_add_dialog)
        controls.addWidget(self.search_input)
        controls.addWidget(add_button)
        layout.addLayout(controls)

        self.table = QTableWidget()
        set_table_headers(self.table, ["No", "Judul Modul", "Kelas", "Mapel", "PDF", "Halaman", "Cloud", "Aksi"], action_col_width=240)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.services["modules"].get_modules(self.search_input.text().strip())
        fill_table(
            self.table,
            [
                [
                    index + 1,
                    row["title"],
                    row["class_name"],
                    row["subject_name"],
                    row["pdf_file_name"],
                    row.get("page_count", 0),
                    row.get("upload_status", "local_only"),
                    "",
                ]
                for index, row in enumerate(self.rows)
            ],
        )
        for index, row in enumerate(self.rows):
            add_row_actions(
                self.table,
                index,
                [
                    ("Edit", lambda _, data=row: self.open_edit_dialog(data)),
                    ("Buka", lambda _, data=row: self.open_pdf(data)),
                    ("Hapus", lambda _, data=row: self.delete_row(data)),
                ],
                show_text=True,
            )

    def open_add_dialog(self) -> None:
        dialog = ModuleFormDialog(self.services, parent=self.window())
        if dialog.exec():
            try:
                payload = dialog.payload()
                with busy(self, "Sedang mengupload dan memproses modul PDF...") as dialog_progress:
                    def progress(message: str, current: int | None = None, total: int | None = None) -> None:
                        dialog_progress.set_progress(message, current, total)

                    self.services["modules"].add_module(**payload, progress_callback=progress)
                self.refresh()
                message = "Modul berhasil disimpan dan teks PDF berhasil diekstrak."
                if payload.get("source_pdf_path"):
                    latest = self.services["modules"].get_modules(payload["title"])
                    if latest:
                        status = latest[0].get("upload_status", "local_only")
                        if status == "uploaded":
                            message += " Upload Cloudinary berhasil."
                        elif status == "upload_failed":
                            message += " Upload Cloudinary gagal, modul tetap tersimpan lokal."
                info(self, message)
            except ValueError as exc:
                error(self, str(exc))

    def open_edit_dialog(self, row: dict) -> None:
        dialog = ModuleFormDialog(self.services, parent=self.window(), row=row)
        if dialog.exec():
            try:
                payload = dialog.payload()
                with busy(self, "Sedang memperbarui modul PDF...") as dialog_progress:
                    def progress(message: str, current: int | None = None, total: int | None = None) -> None:
                        dialog_progress.set_progress(message, current, total)

                    self.services["modules"].update_module(row["id"], **payload, progress_callback=progress)
                self.refresh()
                info(self, "Modul berhasil diperbarui.")
            except ValueError as exc:
                error(self, str(exc))

    def open_pdf(self, row: dict) -> None:
        pdf_path = Path(str(row.get("pdf_path", "") or ""))
        if not pdf_path.exists():
            error(self, "File PDF modul tidak ditemukan di workspace.")
            return
        try:
            import os

            os.startfile(str(pdf_path))
        except Exception as exc:
            error(self, f"PDF tidak dapat dibuka: {exc}")

    def delete_row(self, row: dict) -> None:
        if not confirm(self, f"Hapus modul {row['title']}? Riwayat draft soal terkait juga akan ikut dihapus."):
            return
        try:
            with busy(self, "Sedang menghapus modul dan file cloud..."):
                self.services["modules"].delete_module(row["id"])
            self.refresh()
            info(self, "Modul berhasil dihapus.")
        except ValueError as exc:
            error(self, str(exc))


class ModuleFormDialog(FormDialog):
    def __init__(self, services: dict, parent=None, row: dict | None = None) -> None:
        super().__init__("Upload Modul" if row is None else "Edit Modul", parent)
        self.services = services
        self.row = row
        self.setMinimumWidth(620)
        self.set_subtitle("Tentukan kelas, mapel, judul modul, lalu pilih file PDF pembelajaran.")
        self.set_save_text("Simpan Modul" if row is None else "Simpan Perubahan")

        self.class_input = combo_box(self._class_options(), row.get("class_id") if row else None)
        self.subject_input = combo_box(self._subject_options(), row.get("subject_id") if row else None)
        self.title_input = line_edit(row["title"] if row else "")
        self.description_input = text_edit(row.get("description", "") if row else "")
        self.pdf_input = line_edit(row.get("pdf_path", "") if row else "")
        self.pdf_input.setReadOnly(True)
        self.pdf_button = ActionButton("Pilih PDF")
        self.pdf_button.setMaximumWidth(120)
        self.pdf_button.clicked.connect(self.choose_pdf)
        pdf_row = QWidget()
        pdf_layout = QHBoxLayout(pdf_row)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        pdf_layout.setSpacing(10)
        pdf_layout.addWidget(self.pdf_input)
        pdf_layout.addWidget(self.pdf_button)

        self.title_input.setPlaceholderText("Contoh: Sistem Pencernaan Manusia")
        self.description_input.setPlaceholderText("Ringkasan materi atau catatan guru.")
        if row is not None:
            self.pdf_button.setText("Ganti PDF")

        self.insert_field("Kelas *", self.class_input)
        self.insert_field("Mapel *", self.subject_input)
        self.insert_field("Judul Modul *", self.title_input)
        self.insert_field("Deskripsi", self.description_input)
        self.insert_field("File PDF *", pdf_row)

    def _class_options(self) -> list[tuple[str, object]]:
        return [("Pilih Kelas", None)] + [
            (row["class_name"], row["id"]) for row in self.services["classes"].get_classes()
        ]

    def _subject_options(self) -> list[tuple[str, object]]:
        return [("Pilih Mapel", None)] + [
            (row["subject_name"], row["id"]) for row in self.services["subjects"].get_subjects()
        ]

    def choose_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Modul PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.pdf_input.setText(file_path)

    def payload(self) -> dict:
        description = self.description_input.toPlainText().strip()
        pdf_path = self.pdf_input.text().strip()
        if self.row is not None and pdf_path == str(self.row.get("pdf_path", "")):
            pdf_path = ""
        return {
            "title": self.title_input.text().strip(),
            "class_id": self.class_input.currentData(),
            "subject_id": self.subject_input.currentData(),
            "description": description,
            "source_pdf_path": pdf_path,
        }
