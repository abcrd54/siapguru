from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QLabel,
)


class FormDialog(QDialog):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setObjectName("FormDialog")
        self.setMinimumWidth(460)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)
        title_label = QLabel(title)
        title_label.setObjectName("DialogTitle")
        subtitle_label = QLabel("Lengkapi form berikut lalu simpan perubahan.")
        subtitle_label.setObjectName("DialogSubtitle")
        root.addWidget(title_label)
        root.addWidget(subtitle_label)
        card = QWidget()
        card.setObjectName("DialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.form.setFormAlignment(Qt.AlignTop)
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(12)
        card_layout.addLayout(self.form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = self.buttons.button(QDialogButtonBox.Save)
        if save_button:
            save_button.setProperty("primary", True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.form.addRow(self.buttons)
        root.addWidget(card)

    def insert_field(self, label: str, widget) -> None:
        self.form.insertRow(self.form.rowCount() - 1, label, widget)


class ModeSelectionDialog(QDialog):
    def __init__(self, current_mode: str = "", enabled_modes: list[str] | None = None, source_label: str = "local") -> None:
        super().__init__()
        self.setWindowTitle("Pilih Mode SiapGuru")
        self.setMinimumWidth(520)
        self.selected_mode = current_mode
        self.enabled_modes = enabled_modes or ["guru_mapel", "wali_kelas"]

        layout = QVBoxLayout(self)
        title = QLabel("Pilih mode penggunaan SiapGuru")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            f"Setiap mode memakai database lokal terpisah agar data Guru Mapel dan Wali Kelas tidak tercampur. Sumber lisensi saat ini: {source_label}."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        button_row = QHBoxLayout()
        if "guru_mapel" in self.enabled_modes:
            guru_button = QPushButton("Guru Mapel")
            guru_button.setProperty("primary", True)
            guru_button.setMinimumHeight(56)
            guru_button.clicked.connect(lambda: self.pick_mode("guru_mapel"))
            button_row.addWidget(guru_button)
        if "wali_kelas" in self.enabled_modes:
            wali_button = QPushButton("Wali Kelas")
            wali_button.setProperty("primary", True)
            wali_button.setMinimumHeight(56)
            wali_button.clicked.connect(lambda: self.pick_mode("wali_kelas"))
            button_row.addWidget(wali_button)
        layout.addLayout(button_row)

    def pick_mode(self, mode: str) -> None:
        self.selected_mode = mode
        self.accept()


class LicenseActivationDialog(QDialog):
    def __init__(self, source_label: str = "local", helper_text: str = "") -> None:
        super().__init__()
        self.setWindowTitle("Aktivasi SiapGuru")
        self.setMinimumWidth(520)
        self.entered_key = ""

        layout = QVBoxLayout(self)
        title = QLabel("Masukkan key untuk membuka SiapGuru")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Aplikasi tidak akan membuka workspace sebelum key tervalidasi.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Contoh: SG-WK-XXXX-XXXX-XXXX-XXXX")
        self.key_input.returnPressed.connect(self.submit)
        form = QFormLayout()
        form.addRow("Key Aktivasi", self.key_input)
        layout.addLayout(form)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("DialogError")
        self.message_label.hide()
        layout.addWidget(self.message_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        ok_button.setText("Aktivasi")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_error(self, message: str) -> None:
        self.message_label.setText(message)
        self.message_label.setVisible(bool(message.strip()))

    def submit(self) -> None:
        self.entered_key = self.key_input.text().strip()
        self.accept()


class WorkspaceSwitchDialog(QDialog):
    def __init__(self, options: list[tuple[str, str]], current_mode: str) -> None:
        super().__init__()
        self.setWindowTitle("Ganti Workspace")
        self.setMinimumWidth(520)
        self.selected_mode = current_mode

        layout = QVBoxLayout(self)
        title = QLabel("Pilih workspace yang ingin dibuka")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Setiap workspace memakai database lokal terpisah. Pindah workspace akan membuka konteks data yang berbeda.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        button_row = QVBoxLayout()
        for mode, description in options:
            button = QPushButton(description)
            button.setProperty("primary", mode != current_mode)
            button.setMinimumHeight(48)
            button.setEnabled(mode != current_mode)
            button.clicked.connect(lambda _, m=mode: self.pick_mode(m))
            button_row.addWidget(button)
        layout.addLayout(button_row)

    def pick_mode(self, mode: str) -> None:
        self.selected_mode = mode
        self.accept()


class InitialProfileDialog(QDialog):
    def __init__(self, school_name: str = "", teacher_name: str = "", academic_year: str = "", semester: str = "Ganjil") -> None:
        super().__init__()
        self.setWindowTitle("Lengkapi Profil Awal")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        title = QLabel("Lengkapi data awal sebelum masuk aplikasi")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Isi nama sekolah, nama guru, tahun ajaran, dan semester. Data ini masih bisa diubah lagi di menu Pengaturan.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.school_name = QLineEdit(school_name)
        self.teacher_name = QLineEdit(teacher_name)
        self.academic_year = QLineEdit(academic_year)
        self.semester = QComboBox()
        self.semester.addItem("Ganjil")
        self.semester.addItem("Genap")
        self.semester.setCurrentText(semester or "Ganjil")
        form.addRow("Nama Sekolah", self.school_name)
        form.addRow("Nama Guru", self.teacher_name)
        form.addRow("Tahun Ajaran", self.academic_year)
        form.addRow("Semester", self.semester)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        if save_button:
            save_button.setProperty("primary", True)
            save_button.setText("Lanjutkan")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict:
        return {
            "school_name": self.school_name.text().strip(),
            "teacher_name": self.teacher_name.text().strip(),
            "academic_year": self.academic_year.text().strip(),
            "semester": self.semester.currentText(),
        }


def info(parent, text: str) -> None:
    QMessageBox.information(parent, "SiapGuru", text)


def error(parent, text: str) -> None:
    QMessageBox.critical(parent, "SiapGuru", text)


def confirm(parent, text: str) -> bool:
    return QMessageBox.question(parent, "SiapGuru", text) == QMessageBox.Yes


def line_edit(value: str = "") -> QLineEdit:
    widget = QLineEdit()
    widget.setText(value)
    return widget


def text_edit(value: str = "") -> QTextEdit:
    widget = QTextEdit()
    widget.setPlainText(value)
    widget.setFixedHeight(90)
    return widget


def combo_box(options: list[tuple[str, object]], current_value: object | None = None) -> QComboBox:
    widget = QComboBox()
    for label, value in options:
        widget.addItem(label, value)
    if current_value is not None:
        index = widget.findData(current_value)
        if index >= 0:
            widget.setCurrentIndex(index)
    return widget
