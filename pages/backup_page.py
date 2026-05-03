from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QTableWidget, QVBoxLayout, QWidget

from ui.dialogs import error, info
from ui.widgets import ActionButton, PageHeader, fill_table, set_table_headers


class BackupPage(QWidget):
    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services

        layout = QVBoxLayout(self)
        layout.addWidget(
            PageHeader(
                "Backup Data",
                "Simpan cadangan workspace aktif. Pemulihan backup dilakukan dari layar awal saat memilih workspace.",
            )
        )
        controls = QHBoxLayout()
        backup_button = ActionButton("Backup Sekarang", primary=True)
        folder_button = ActionButton("Buka Folder Backup")
        backup_button.clicked.connect(self.backup_now)
        folder_button.clicked.connect(self.services["backup"].open_backup_folder)
        for widget in (backup_button, folder_button):
            controls.addWidget(widget)
        controls.addStretch()
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
