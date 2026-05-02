from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import confirm, error, info
from ui.widgets import ActionButton, PageHeader, fill_table, set_table_headers


class BackupPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services

        layout = QVBoxLayout(self)
        layout.addWidget(PageHeader("Backup Data", "Simpan cadangan data dan pulihkan bila diperlukan."))
        controls = QHBoxLayout()
        backup_button = ActionButton("Backup Sekarang", primary=True)
        restore_button = ActionButton("Pulihkan Data")
        folder_button = ActionButton("Buka Folder Backup")
        backup_button.clicked.connect(self.backup_now)
        restore_button.clicked.connect(self.restore_db)
        folder_button.clicked.connect(self.services["backup"].open_backup_folder)
        for widget in (backup_button, restore_button, folder_button):
            controls.addWidget(widget)
        layout.addLayout(controls)

        self.table = QTableWidget()
        set_table_headers(self.table, ["Tanggal", "Nama File", "Lokasi"])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        rows = self.services["backup"].get_backup_history()
        fill_table(self.table, [[row["backup_date"], row["backup_name"], row["backup_path"]] for row in rows])

    def backup_now(self) -> None:
        try:
            path = self.services["backup"].backup_database()
            self.refresh()
            info(self, f"Backup berhasil: {path}")
        except Exception as exc:
            error(self, str(exc))

    def restore_db(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Pulihkan Data", "", "Database Files (*.db)")
        if not file_path:
            return
        if not confirm(self, "Restore akan mengganti data saat ini. Lanjutkan?"):
            return
        try:
            self.services["backup"].restore_database(file_path)
            self.refresh()
            info(self, "Restore selesai. Silakan buka ulang aplikasi jika diperlukan.")
        except Exception as exc:
            error(self, str(exc))
