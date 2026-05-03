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
        layout.addWidget(
            PageHeader(
                "Mata Pelajaran",
                "Kelola mapel yang Anda ampu, KKM, dan bobot nilai akhir raport untuk tiap mapel.",
            )
        )
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
        set_table_headers(self.table, ["No", "Mata Pelajaran", "KKM", "Bobot Nilai Akhir", "Aksi"], action_col_width=128)
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
                    row.get("kkm") if row.get("kkm") not in (None, "") else "-",
                    f"H {row.get('weight_task', 30)}% | UTS {row.get('weight_mid', 30)}% | UAS {row.get('weight_final', 40)}%",
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
        dialog = FormDialog("Tambah Mapel", self.window())
        dialog.set_subtitle("Isi mapel, KKM, dan bobot nilai akhir raport untuk mapel ini.")
        dialog.set_save_text("Simpan Mapel")
        name = line_edit()
        kkm = line_edit()
        weight_task = line_edit("30")
        weight_mid = line_edit("30")
        weight_final = line_edit("40")
        name.setPlaceholderText("Contoh: Matematika")
        kkm.setPlaceholderText("Contoh: 75")
        weight_task.setPlaceholderText("30")
        weight_mid.setPlaceholderText("30")
        weight_final.setPlaceholderText("40")
        dialog.insert_field("Nama Mata Pelajaran *", name)
        dialog.insert_field("KKM Mapel", kkm)
        dialog.insert_field("Bobot Harian (%)", weight_task)
        dialog.insert_field("Bobot UTS (%)", weight_mid)
        dialog.insert_field("Bobot UAS (%)", weight_final)
        dialog.raise_()
        dialog.activateWindow()
        if dialog.exec():
            try:
                self.services["subjects"].add_subject(
                    name.text().strip(),
                    "",
                    kkm.text().strip(),
                    weight_task.text().strip(),
                    weight_mid.text().strip(),
                    weight_final.text().strip(),
                )
                self.refresh()
                info(self, "Mapel berhasil disimpan.")
            except ValueError as exc:
                error(self, str(exc))

    def open_edit_dialog(self, row: dict) -> None:
        dialog = FormDialog("Edit Mapel", self.window())
        dialog.set_subtitle("Perbarui mapel, KKM, dan bobot nilai akhir raport lalu simpan perubahan.")
        dialog.set_save_text("Simpan Perubahan")
        name = line_edit(row["subject_name"])
        kkm = line_edit("" if row.get("kkm") is None else str(row["kkm"]))
        weight_task = line_edit(str(row.get("weight_task", 30)))
        weight_mid = line_edit(str(row.get("weight_mid", 30)))
        weight_final = line_edit(str(row.get("weight_final", 40)))
        name.setPlaceholderText("Contoh: Matematika")
        kkm.setPlaceholderText("Contoh: 75")
        weight_task.setPlaceholderText("30")
        weight_mid.setPlaceholderText("30")
        weight_final.setPlaceholderText("40")
        dialog.insert_field("Nama Mata Pelajaran *", name)
        dialog.insert_field("KKM Mapel", kkm)
        dialog.insert_field("Bobot Harian (%)", weight_task)
        dialog.insert_field("Bobot UTS (%)", weight_mid)
        dialog.insert_field("Bobot UAS (%)", weight_final)
        dialog.raise_()
        dialog.activateWindow()
        if dialog.exec():
            try:
                self.services["subjects"].update_subject(
                    row["id"],
                    name.text().strip(),
                    "",
                    kkm.text().strip(),
                    weight_task.text().strip(),
                    weight_mid.text().strip(),
                    weight_final.text().strip(),
                )
                self.refresh()
                info(self, "Mapel berhasil diperbarui.")
            except ValueError as exc:
                error(self, str(exc))

    def delete_row(self, row: dict) -> None:
        usage = self.services["subjects"].get_subject_usage_summary(row["id"])
        if usage["grade_count"] > 0:
            message = (
                f"Mapel {row['subject_name']} sudah memiliki {usage['grade_count']} data nilai"
                f"{', ' + str(usage['report_count']) + ' deskripsi raport' if usage['report_count'] else ''}"
                f"{', dan ' + str(usage['remedial_count']) + ' data ketuntasan' if usage['remedial_count'] else ''}.\n\n"
                "Jika dihapus, semua data terkait mapel ini ikut terhapus. Yakin lanjut?"
            )
        else:
            message = f"Hapus mapel {row['subject_name']}?"
        if not confirm(self, message):
            return
        try:
            self.services["subjects"].delete_subject(row["id"])
            self.refresh()
            info(self, "Mapel berhasil dihapus.")
        except ValueError as exc:
            error(self, str(exc))
