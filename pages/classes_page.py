from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import FormDialog, confirm, error, info, line_edit
from ui.widgets import ActionButton, PageHeader, add_row_actions, fill_table, set_table_headers


class ClassesPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []

        layout = QVBoxLayout(self)
        subtitle = "Kelola data kelas yang digunakan sebelum input siswa dan nilai."
        layout.addWidget(PageHeader("Data Kelas", subtitle))

        controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari nama kelas...")
        self.search_input.textChanged.connect(self.refresh)
        add_button = ActionButton("Tambah Kelas", primary=True)
        add_button.clicked.connect(self.open_add_dialog)
        controls.addWidget(self.search_input)
        add_button.setMaximumWidth(180)
        controls.addWidget(add_button)
        layout.addLayout(controls)

        self.table = QTableWidget()
        set_table_headers(self.table, ["No", "Nama Kelas", "Guru Kelas", "Jumlah Siswa", "Aksi"], action_col_width=128)
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        layout.addWidget(self.helper_label)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.services["classes"].get_classes(self.search_input.text().strip())
        fill_table(
            self.table,
            [[index + 1, row["class_name"], row["homeroom_teacher"], row["student_count"], ""] for index, row in enumerate(self.rows)],
        )
        self.helper_label.setText(
            "Belum ada kelas. Tambahkan kelas terlebih dahulu." if not self.rows
            else "Lengkapi guru kelas untuk kelas yang masih kosong agar data lebih rapi."
        )
        for index, row in enumerate(self.rows):
            add_row_actions(
                self.table,
                index,
                [("Edit", lambda _, data=row: self.open_edit_dialog(data)), ("Hapus", lambda _, data=row: self.delete_row(data))],
            )

    def open_add_dialog(self) -> None:
        dialog = FormDialog("Tambah Kelas")
        name = line_edit()
        teacher = line_edit()
        dialog.insert_field("Nama Kelas *", name)
        dialog.insert_field("Guru Kelas", teacher)
        if dialog.exec():
            try:
                self.services["classes"].add_class(name.text(), teacher.text())
                self.refresh()
                info(self, "Kelas berhasil disimpan.")
            except ValueError as exc:
                error(self, str(exc))

    def open_edit_dialog(self, row: dict) -> None:
        dialog = FormDialog("Edit Kelas")
        name = line_edit(row["class_name"])
        teacher = line_edit(row["homeroom_teacher"] or "")
        dialog.insert_field("Nama Kelas *", name)
        dialog.insert_field("Guru Kelas", teacher)
        if dialog.exec():
            try:
                self.services["classes"].update_class(row["id"], name.text(), teacher.text())
                self.refresh()
                info(self, "Kelas berhasil diperbarui.")
            except ValueError as exc:
                error(self, str(exc))

    def delete_row(self, row: dict) -> None:
        if not confirm(self, f"Hapus kelas {row['class_name']}?"):
            return
        try:
            self.services["classes"].delete_class(row["id"])
            self.refresh()
            info(self, "Kelas berhasil dihapus.")
        except ValueError as exc:
            error(self, str(exc))
