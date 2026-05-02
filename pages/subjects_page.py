from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import FormDialog, confirm, error, info, line_edit
from ui.widgets import ActionButton, PageHeader, add_row_actions, fill_table, set_table_headers


class SubjectsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.addWidget(PageHeader("Mata Pelajaran", "Kelola mapel, guru pengampu, dan KKM masing-masing mapel."))
        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari mata pelajaran...")
        self.search_input.textChanged.connect(self.refresh)
        add_button = ActionButton("Tambah Mapel", primary=True)
        add_button.clicked.connect(self.open_add_dialog)
        controls.addWidget(self.search_input)
        add_button.setMaximumWidth(180)
        controls.addWidget(add_button)
        layout.addLayout(controls)

        self.table = QTableWidget()
        set_table_headers(self.table, ["No", "Mata Pelajaran", "Nama Guru", "KKM", "Aksi"], action_col_width=92)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.services["subjects"].get_subjects(self.search_input.text().strip())
        fill_table(
            self.table,
            [
                [
                    index + 1,
                    row["subject_name"],
                    row.get("teacher_name") or "-",
                    row.get("kkm") if row.get("kkm") not in (None, "") else "-",
                    "",
                ]
                for index, row in enumerate(self.rows)
            ],
        )
        for index, row in enumerate(self.rows):
            add_row_actions(
                self.table,
                index,
                [("Edit", lambda _, data=row: self.open_edit_dialog(data)), ("Hapus", lambda _, data=row: self.delete_row(data))],
            )

    def open_add_dialog(self) -> None:
        dialog = FormDialog("Tambah Mapel")
        name = line_edit()
        teacher = line_edit()
        kkm = line_edit()
        dialog.insert_field("Nama Mata Pelajaran *", name)
        dialog.insert_field("Nama Guru Pengampu", teacher)
        dialog.insert_field("KKM Mapel", kkm)
        if dialog.exec():
            try:
                self.services["subjects"].add_subject(name.text().strip(), teacher.text().strip(), kkm.text().strip())
                self.refresh()
                info(self, "Mapel berhasil disimpan.")
            except ValueError as exc:
                error(self, str(exc))

    def open_edit_dialog(self, row: dict) -> None:
        dialog = FormDialog("Edit Mapel")
        name = line_edit(row["subject_name"])
        teacher = line_edit(row["teacher_name"] or "")
        kkm = line_edit("" if row.get("kkm") is None else str(row["kkm"]))
        dialog.insert_field("Nama Mata Pelajaran *", name)
        dialog.insert_field("Nama Guru Pengampu", teacher)
        dialog.insert_field("KKM Mapel", kkm)
        if dialog.exec():
            try:
                self.services["subjects"].update_subject(
                    row["id"],
                    name.text().strip(),
                    teacher.text().strip(),
                    kkm.text().strip(),
                )
                self.refresh()
                info(self, "Mapel berhasil diperbarui.")
            except ValueError as exc:
                error(self, str(exc))

    def delete_row(self, row: dict) -> None:
        if not confirm(self, f"Hapus mapel {row['subject_name']}?"):
            return
        try:
            self.services["subjects"].delete_subject(row["id"])
            self.refresh()
            info(self, "Mapel berhasil dihapus.")
        except ValueError as exc:
            error(self, str(exc))
