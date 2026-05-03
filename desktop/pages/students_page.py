from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import FormDialog, combo_box, confirm, error, info, line_edit, text_edit
from ui.widgets import ActionButton, PageHeader, add_row_actions, fill_table, set_table_headers


class StudentsPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.rows: list[dict] = []

        layout = QVBoxLayout(self)
        subtitle = "Tambahkan siswa satu per satu atau impor dari template Excel."
        layout.addWidget(PageHeader("Data Siswa", subtitle))

        top_controls = QGridLayout()
        top_controls.setHorizontalSpacing(16)
        top_controls.setVerticalSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cari nama siswa...")
        self.search_input.textChanged.connect(self.refresh)
        self.class_filter = QComboBox()
        self.class_filter.currentIndexChanged.connect(self.refresh)
        template_button = ActionButton("Ambil Template")
        template_button.clicked.connect(self.download_template)
        import_button = ActionButton("Import Data Siswa", primary=True)
        import_button.clicked.connect(self.import_excel)
        export_button = ActionButton("Unduh Data Siswa")
        export_button.clicked.connect(self.export_excel)
        add_button = ActionButton("Tambah Siswa")
        add_button.clicked.connect(self.open_add_dialog)
        self.class_filter.setMinimumWidth(280)
        self.class_filter.setMaximumWidth(360)
        self.search_input.setMinimumWidth(360)
        self.search_input.setMaximumWidth(520)
        import_button.setMaximumWidth(220)
        add_button.setMaximumWidth(180)
        template_button.setMaximumWidth(180)
        export_button.setMaximumWidth(180)

        right_row_one = QHBoxLayout()
        right_row_one.setSpacing(10)
        right_row_one.addStretch()
        right_row_one.addWidget(import_button)
        right_row_one.addWidget(add_button)

        right_row_two = QHBoxLayout()
        right_row_two.setSpacing(10)
        right_row_two.addStretch()
        right_row_two.addWidget(template_button)
        right_row_two.addWidget(export_button)

        top_controls.addWidget(self.class_filter, 0, 0)
        top_controls.addLayout(right_row_one, 0, 1)
        top_controls.addWidget(self.search_input, 1, 0)
        top_controls.addLayout(right_row_two, 1, 1)
        top_controls.setColumnStretch(0, 1)
        top_controls.setColumnStretch(1, 0)
        layout.addLayout(top_controls)

        self.table = QTableWidget()
        set_table_headers(
            self.table,
            ["No", "Nama Siswa", "NIS", "NISN", "Kelas", "Gender", "No. WA Ortu", "Aksi"],
            action_col_width=138,
        )
        layout.addWidget(self.table)
        self.helper_label = QLabel()
        layout.addWidget(self.helper_label)
        self.refresh_filters()
        self.refresh()

    def refresh_filters(self) -> None:
        context = self.services["settings"].get_active_context()
        target_class = context.get("default_class_id")
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("Semua Kelas", None)
        for row in self.services["classes"].get_classes():
            self.class_filter.addItem(row["class_name"], row["id"])
        if target_class:
            index = self.class_filter.findData(target_class)
            if index >= 0:
                self.class_filter.setCurrentIndex(index)
        self.class_filter.blockSignals(False)

    def refresh(self) -> None:
        class_id = self.class_filter.currentData()
        if class_id:
            self.services["settings"].update_active_context(default_class_id=class_id)
        self.rows = self.services["students"].search_students(self.search_input.text().strip(), class_id)
        fill_table(
            self.table,
            [
                [index + 1, row["full_name"], row["nis"] or "", row["nisn"] or "", row["class_name"] or "", row["gender"] or "", row["parent_phone"] or "", ""]
                for index, row in enumerate(self.rows)
            ],
        )
        if not self.services["classes"].get_classes():
            self.helper_label.setText("Tambahkan kelas terlebih dahulu sebelum menambah atau mengimpor siswa.")
        elif not self.rows:
            self.helper_label.setText("Belum ada siswa. Gunakan Import Data Siswa atau Tambah Siswa.")
        else:
            self.helper_label.setText("Periksa kembali kelas dan nomor WA orang tua setelah data masuk.")
        for index, row in enumerate(self.rows):
            add_row_actions(
                self.table,
                index,
                [("Edit", lambda _, data=row: self.open_edit_dialog(data)), ("Hapus", lambda _, data=row: self.delete_row(data))],
            )

    def open_student_dialog(self, title: str, data: dict | None = None) -> dict | None:
        class_rows = self.services["classes"].get_classes()
        if not class_rows:
            error(self, "Belum ada data kelas. Tambahkan kelas terlebih dahulu.")
            return None
        dialog = FormDialog(title)
        classes = [(row["class_name"], row["id"]) for row in class_rows]
        name = line_edit(data["full_name"] if data else "")
        nis = line_edit(data["nis"] or "" if data else "")
        nisn = line_edit(data["nisn"] or "" if data else "")
        gender = combo_box([("Laki-laki", "L"), ("Perempuan", "P"), ("-", "")], data["gender"] if data else "")
        class_select = combo_box(classes, data["class_id"] if data else None)
        address = text_edit(data["address"] or "" if data else "")
        parent_name = line_edit(data["parent_name"] or "" if data else "")
        parent_phone = line_edit(data["parent_phone"] or "" if data else "")
        dialog.insert_field("Nama Lengkap *", name)
        dialog.insert_field("NIS", nis)
        dialog.insert_field("NISN", nisn)
        dialog.insert_field("Jenis Kelamin", gender)
        dialog.insert_field("Kelas *", class_select)
        dialog.insert_field("Alamat", address)
        dialog.insert_field("Nama Orang Tua", parent_name)
        dialog.insert_field("Nomor WA Orang Tua", parent_phone)
        if dialog.exec():
            return {
                "full_name": name.text(),
                "nis": nis.text(),
                "nisn": nisn.text(),
                "gender": gender.currentData(),
                "class_id": class_select.currentData(),
                "address": address.toPlainText(),
                "parent_name": parent_name.text(),
                "parent_phone": parent_phone.text(),
            }
        return None

    def open_add_dialog(self) -> None:
        payload = self.open_student_dialog("Tambah Siswa")
        if payload is None:
            return
        try:
            self.services["students"].add_student(payload)
            self.refresh_filters()
            self.refresh()
            info(self, "Siswa berhasil disimpan.")
        except ValueError as exc:
            error(self, str(exc))

    def open_edit_dialog(self, row: dict) -> None:
        payload = self.open_student_dialog("Edit Siswa", row)
        if payload is None:
            return
        try:
            self.services["students"].update_student(row["id"], payload)
            self.refresh()
            info(self, "Siswa berhasil diperbarui.")
        except ValueError as exc:
            error(self, str(exc))

    def delete_row(self, row: dict) -> None:
        if not confirm(self, f"Hapus siswa {row['full_name']}?"):
            return
        self.services["students"].delete_student(row["id"])
        self.refresh()
        info(self, "Siswa berhasil dihapus.")

    def import_excel(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Siswa", "", "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return
        try:
            count = self.services["excel"].import_students_excel(file_path)
            self.refresh_filters()
            self.refresh()
            info(self, f"{count} siswa berhasil diimport.")
        except Exception as exc:
            error(self, str(exc))

    def export_excel(self) -> None:
        try:
            file_path = self.services["excel"].export_students_excel(self.class_filter.currentData())
            info(self, f"Export berhasil: {file_path}")
        except Exception as exc:
            error(self, str(exc))

    def download_template(self) -> None:
        try:
            file_path = self.services["excel"].create_student_template()
            info(self, f"Template berhasil dibuat: {file_path}")
        except Exception as exc:
            error(self, str(exc))
