from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.widgets import ActionButton, CardWidget, PageHeader


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        layout = QVBoxLayout(self)
        subtitle = "Pantau workspace aktif, cek progres kelas dan mapel, lalu lanjutkan ke input nilai atau pembuatan raport."
        layout.addWidget(PageHeader("Beranda", subtitle))

        self.context_label = QLabel()
        self.context_label.setObjectName("DialogHint")
        self.context_label.setWordWrap(True)
        layout.addWidget(self.context_label)

        self.card_grid = QGridLayout()
        self.card_grid.setHorizontalSpacing(14)
        self.card_grid.setVerticalSpacing(14)
        layout.addLayout(self.card_grid)

        self.quick_title = QLabel("Aksi Cepat")
        self.quick_title.setObjectName("CardTitle")
        layout.addWidget(self.quick_title)

        self.quick_actions = QHBoxLayout()
        self.quick_actions.setSpacing(12)
        layout.addLayout(self.quick_actions)

        self.empty_label = QLabel()
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)
        self.refresh()

    def refresh(self) -> None:
        context = self.services["settings"].get_active_context()
        active_class_id = context.get("default_class_id")
        current_workspace = self.services.get("current_workspace") or {}
        workspace_label = current_workspace.get("label", "Workspace belum dipilih")
        active_class_name = "-"
        if active_class_id:
            active_class = next(
                (row for row in self.services["classes"].get_classes() if row["id"] == active_class_id),
                None,
            )
            if active_class:
                active_class_name = active_class["class_name"]
        while self.quick_actions.count():
            item = self.quick_actions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        targets = {
            "Input Nilai": "Nilai",
            "Atur Mapel": "Mata Pelajaran",
            "Data Kelas": "Data Kelas",
            "Buat Raport": "Buat Raport",
            "Unduh Laporan": "Unduh Laporan",
        }
        primary = {"Input Nilai", "Unduh Laporan"}
        for label, target in targets.items():
            button = ActionButton(label, primary=label in primary)
            button.setMaximumWidth(168)
            button.clicked.connect(lambda _, page=target: self.navigate_requested.emit(page))
            self.quick_actions.addWidget(button)
        self.quick_actions.addStretch()

        student_count = len(self.services["students"].search_students(class_id=active_class_id))
        total_students = len(self.services["students"].search_students())
        class_count = len(self.services["classes"].get_classes())
        subject_count = len(self.services["subjects"].get_subjects())
        last_backup = self.services["backup"].get_backup_history()
        report_ready_count = 0
        if active_class_id:
            report_ready_count = len(self.services["reports"].get_report_book_data(active_class_id))
        self.context_label.setText(
            f"Workspace aktif: {workspace_label}. "
            f"Kelas fokus saat ini: {active_class_name}. "
            "Gunakan workspace ini untuk mengelola nilai akhir raport pada periode akademik yang sedang berjalan."
        )
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cards = [
            CardWidget("Siswa Kelas Fokus", str(student_count)),
            CardWidget("Total Siswa Workspace", str(total_students)),
            CardWidget("Total Kelas", str(class_count)),
            CardWidget("Total Mapel", str(subject_count)),
            CardWidget("Siap Dibuat Raport", str(report_ready_count), "#2563EB"),
            CardWidget("Backup Terakhir", last_backup[0]["backup_date"] if last_backup else "-", "#16A34A"),
        ]
        self.empty_label.setText(
            "Mulai dari menyiapkan kelas, mapel, dan siswa pada workspace ini, lalu lanjutkan ke input nilai akhir raport."
            if total_students == 0 else
            "Beranda ini dipakai untuk memantau workspace aktif dan mempercepat perpindahan ke langkah kerja utama guru."
        )
        for index, card in enumerate(cards):
            self.card_grid.addWidget(card, index // 3, index % 3)
