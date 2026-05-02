from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QTableWidget, QVBoxLayout, QWidget

from ui.widgets import ActionButton, CardWidget, PageHeader, fill_table, set_table_headers


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, services: dict) -> None:
        super().__init__()
        self.services = services
        self.app_mode = self.services["app_mode"]
        layout = QVBoxLayout(self)
        subtitle = (
            "Ringkasan singkat untuk membantu wali kelas menyelesaikan pekerjaan utama lebih cepat."
            if self.app_mode == "wali_kelas"
            else "Ringkasan data akademik Anda"
        )
        layout.addWidget(PageHeader("Beranda", subtitle))

        self.card_grid = QGridLayout()
        layout.addLayout(self.card_grid)

        self.quick_actions = QHBoxLayout()
        layout.addLayout(self.quick_actions)

        self.empty_label = QLabel()
        layout.addWidget(self.empty_label)

        self.table = QTableWidget()
        set_table_headers(self.table, ["Nama", "Kelas", "Mapel", "Nilai", "KKM", "Status"])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        app_mode = self.app_mode
        context = self.services["settings"].get_active_context()
        active_class_id = context.get("default_class_id")
        active_subject_id = context.get("default_subject_id") if app_mode == "guru_mapel" else None
        while self.quick_actions.count():
            item = self.quick_actions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if app_mode == "wali_kelas":
            targets = {
                "Buka Data Siswa": "Data Siswa",
                "Data Kelas": "Data Kelas",
                "Buat Raport": "Buat Raport",
                "Unduh Laporan": "Unduh Laporan",
            }
            primary = {"Buka Data Siswa", "Unduh Laporan"}
        else:
            targets = {
                "Input Nilai": "Nilai",
                "Cek Ketuntasan": "Smart Ketuntasan",
                "Buat Raport": "Buat Raport",
                "Export Excel": "Unduh Laporan",
            }
            primary = {"Input Nilai", "Export Excel"}
        for label, target in targets.items():
            button = ActionButton(label, primary=label in primary)
            button.clicked.connect(lambda _, page=target: self.navigate_requested.emit(page))
            self.quick_actions.addWidget(button)
        self.quick_actions.addStretch()

        student_count = len(self.services["students"].search_students(class_id=active_class_id))
        class_count = len(self.services["classes"].get_classes())
        subject_count = len(self.services["subjects"].get_subjects())
        incomplete_query = """
            SELECT COUNT(*) AS total
            FROM students s
            LEFT JOIN grades g ON g.student_id = s.id
            WHERE g.id IS NULL
        """
        incomplete_params: list[object] = []
        if active_class_id:
            incomplete_query += " AND s.class_id = ?"
            incomplete_params.append(active_class_id)
        incomplete = self.services["database"].fetch_one(incomplete_query, incomplete_params)
        last_backup = self.services["backup"].get_backup_history()
        report_ready_count = 0
        if active_class_id:
            report_ready_count = len(self.services["reports"].get_report_book_data(active_class_id))
        below_query = """
            SELECT s.full_name, c.class_name, sub.subject_name, g.final_result, g.status, sub.kkm
            FROM grades g
            JOIN students s ON s.id = g.student_id
            JOIN classes c ON c.id = s.class_id
            JOIN subjects sub ON sub.id = g.subject_id
            WHERE g.status = 'Belum Tuntas'
        """
        below_params: list[object] = []
        if active_class_id:
            below_query += " AND s.class_id = ?"
            below_params.append(active_class_id)
        if active_subject_id:
            below_query += " AND g.subject_id = ?"
            below_params.append(active_subject_id)
        below_query += " ORDER BY g.final_result ASC LIMIT 10"
        below = self.services["database"].fetch_all(below_query, below_params)
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if app_mode == "wali_kelas":
            cards = [
                CardWidget("Total Siswa", str(student_count)),
                CardWidget("Total Kelas", str(class_count)),
                CardWidget("Siap Dibuat Raport", str(report_ready_count), "#2563EB"),
                CardWidget("Backup Terakhir", last_backup[0]["backup_date"] if last_backup else "-", "#16A34A"),
            ]
            self.empty_label.setText(
                "Fokus utama wali kelas: cek data siswa, lengkapi nilai, lalu buat file raport."
                if student_count == 0 else
                "Gunakan menu di atas untuk cek data kelas, pastikan nilai lengkap, lalu buat file raport."
            )
            self.table.setVisible(False)
        else:
            cards = [
                CardWidget("Total Siswa", str(student_count)),
                CardWidget("Total Kelas", str(class_count)),
                CardWidget("Backup Terakhir", last_backup[0]["backup_date"] if last_backup else "-", "#16A34A"),
                CardWidget("Total Mapel", str(subject_count)),
                CardWidget("Belum Tuntas", str(len(below)), "#DC2626"),
                CardWidget("Nilai Belum Lengkap", str(incomplete["total"] if incomplete else 0), "#F59E0B"),
            ]
            self.empty_label.setText(
                "Mode Guru Mapel: pilih kelas dan mapel aktif, lalu lanjut ke input nilai, ketuntasan, dan deskripsi."
                if student_count == 0 else
                "Mode Guru Mapel aktif. Dashboard ini mengikuti kelas dan mapel aktif yang sedang Anda kerjakan."
            )
            self.table.setVisible(True)
        for index, card in enumerate(cards):
            self.card_grid.addWidget(card, index // 3, index % 3)
        if self.table.isVisible():
            fill_table(
                self.table,
                [
                    [
                        row["full_name"],
                        row["class_name"],
                        row["subject_name"],
                        row["final_result"],
                        row["kkm"] if row["kkm"] is not None else self.services["settings"].get_kkm(),
                        row["status"],
                    ]
                    for row in below
                ],
            )
