from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QLabel,
    QWidget,
)


class FormDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("FormDialog")
        self.setModal(True)
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
        self.save_button = self.buttons.button(QDialogButtonBox.Save)
        if self.save_button:
            self.save_button.setProperty("primary", True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.form.addRow(self.buttons)
        root.addWidget(card)

    def insert_field(self, label: str, widget) -> None:
        self.form.insertRow(self.form.rowCount() - 1, label, widget)

    def set_subtitle(self, text: str) -> None:
        self.findChild(QLabel, "DialogSubtitle")
        for child in self.findChildren(QLabel):
            if child.objectName() == "DialogSubtitle":
                child.setText(text)
                break

    def set_save_text(self, text: str) -> None:
        if self.save_button:
            self.save_button.setText(text)


class LicenseActivationDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Aktivasi SiapGuru")
        self.setMinimumWidth(520)
        self.entered_key = ""

        layout = QVBoxLayout(self)
        title = QLabel("Masukkan key untuk membuka SiapGuru")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Aplikasi akan dibuka setelah key aktivasi berhasil diperiksa.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Contoh: SG-GURU-XXXX-XXXX-XXXX-XXXX")
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


class InitialProfileDialog(QDialog):
    def __init__(self, school_name: str = "", teacher_name: str = "") -> None:
        super().__init__()
        self.setWindowTitle("Lengkapi Profil Guru")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        title = QLabel("Lengkapi profil guru sebelum memilih workspace")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Isi nama sekolah dan nama guru. Profil ini akan dipakai sebagai data awal saat membuat workspace baru."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.school_name = QLineEdit(school_name)
        self.teacher_name = QLineEdit(teacher_name)
        form.addRow("Nama Sekolah", self.school_name)
        form.addRow("Nama Guru", self.teacher_name)
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
        }


class WorkspaceSelectionDialog(QDialog):
    def __init__(self, workspaces: list[dict], active_workspace_id: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pilih Workspace")
        self.setMinimumWidth(620)
        self.selected_workspace_id = ""
        self.request_create = False
        self.request_restore = False

        layout = QVBoxLayout(self)
        title = QLabel("Pilih workspace tahun ajaran yang ingin dibuka")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Setiap workspace mewakili satu tahun ajaran dan semester.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("WorkspaceList")
        for row in workspaces:
            item = QListWidgetItem(f"{row['label']}  |  {row['academic_year']}  |  Semester {row['semester']}")
            item.setData(Qt.UserRole, row["id"])
            self.list_widget.addItem(item)
            if row["id"] == active_workspace_id:
                self.list_widget.setCurrentItem(item)
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        self.selection_meta = QLabel("")
        self.selection_meta.setObjectName("DialogHint")
        self.selection_meta.setWordWrap(True)
        layout.addWidget(self.selection_meta)

        buttons = QDialogButtonBox()
        self.open_button = buttons.addButton("Buka Workspace", QDialogButtonBox.AcceptRole)
        self.open_button.setProperty("primary", True)
        self.new_button = buttons.addButton("Buat Workspace Baru", QDialogButtonBox.ActionRole)
        self.restore_button = buttons.addButton("Pulihkan dari Backup", QDialogButtonBox.ActionRole)
        self.cancel_button = buttons.addButton(QDialogButtonBox.Cancel)
        self.open_button.clicked.connect(self.submit_open)
        self.new_button.clicked.connect(self.submit_create)
        self.restore_button.clicked.connect(self.submit_restore)
        self.cancel_button.clicked.connect(self.reject)
        self.open_button.setEnabled(self.list_widget.currentItem() is not None)
        self.list_widget.itemSelectionChanged.connect(self._update_selection_state)
        layout.addWidget(buttons)
        self._update_selection_state()

    def _update_selection_state(self) -> None:
        item = self.list_widget.currentItem()
        self.open_button.setEnabled(item is not None)
        if not item:
            self.selection_meta.setText("Pilih workspace yang ingin dibuka.")
            return
        self.selection_meta.setText("Workspace ini akan dibuka sesuai periode yang dipilih.")

    def submit_open(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        self.selected_workspace_id = str(item.data(Qt.UserRole) or "")
        self.request_create = False
        self.accept()

    def submit_create(self) -> None:
        self.selected_workspace_id = ""
        self.request_create = True
        self.request_restore = False
        self.accept()

    def submit_restore(self) -> None:
        self.selected_workspace_id = ""
        self.request_create = False
        self.request_restore = True
        self.accept()


class WorkspaceCreateDialog(QDialog):
    def __init__(self, workspaces: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buat Workspace Baru")
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)
        title = QLabel("Buat workspace baru untuk periode akademik berikutnya")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Tentukan periode akademik dan pilih data awal yang ingin dibawa.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.academic_year = QLineEdit()
        self.academic_year.setPlaceholderText("Contoh: 2026/2027")
        self.semester = QComboBox()
        self.semester.addItems(["Ganjil", "Genap"])
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Opsional. Kosongkan untuk pakai format otomatis.")
        self.source_workspace = QComboBox()
        self.source_workspace.addItem("Workspace Kosong", None)
        for row in workspaces:
            self.source_workspace.addItem(row["label"], row["id"])
        form.addRow("Tahun Ajaran", self.academic_year)
        form.addRow("Semester", self.semester)
        form.addRow("Nama Workspace", self.label_input)
        form.addRow("Buat Dari", self.source_workspace)
        layout.addLayout(form)

        self.copy_card = QWidget()
        self.copy_card.setObjectName("DialogCard")
        copy_layout = QVBoxLayout(self.copy_card)
        copy_layout.setContentsMargins(16, 16, 16, 16)
        copy_layout.setSpacing(10)
        copy_title = QLabel("Pilih data awal yang ingin disalin")
        copy_title.setObjectName("CardTitle")
        copy_hint = QLabel(
            "Nilai, deskripsi raport, dan riwayat penyesuaian tidak ikut disalin."
        )
        copy_hint.setObjectName("DialogHint")
        copy_hint.setWordWrap(True)
        copy_layout.addWidget(copy_title)
        copy_layout.addWidget(copy_hint)

        self.copy_classes = QCheckBox("Salin data kelas")
        self.copy_students = QCheckBox("Salin data siswa")
        self.copy_subjects = QCheckBox("Salin mata pelajaran")
        self.copy_subject_rules = QCheckBox("Salin KKM dan bobot nilai per mapel")
        self.copy_components = QCheckBox("Salin komponen nilai per mapel")
        for widget in (
            self.copy_classes,
            self.copy_students,
            self.copy_subjects,
            self.copy_subject_rules,
            self.copy_components,
        ):
            copy_layout.addWidget(widget)
        layout.addWidget(self.copy_card)

        self.source_hint = QLabel("")
        self.source_hint.setObjectName("DialogHint")
        self.source_hint.setWordWrap(True)
        layout.addWidget(self.source_hint)

        self.copy_students.toggled.connect(self._sync_copy_dependencies)
        self.copy_subjects.toggled.connect(self._sync_copy_dependencies)
        self.copy_subject_rules.toggled.connect(self._sync_copy_dependencies)
        self.copy_components.toggled.connect(self._sync_copy_dependencies)
        self.source_workspace.currentIndexChanged.connect(self._sync_copy_dependencies)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        if save_button:
            save_button.setProperty("primary", True)
            save_button.setText("Buat Workspace")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_copy_dependencies()

    def _sync_copy_dependencies(self) -> None:
        has_source = self.source_workspace.currentData() is not None
        for widget in (
            self.copy_classes,
            self.copy_students,
            self.copy_subjects,
            self.copy_subject_rules,
            self.copy_components,
        ):
            widget.setEnabled(has_source)
        if not has_source:
            for widget in (
                self.copy_classes,
                self.copy_students,
                self.copy_subjects,
                self.copy_subject_rules,
                self.copy_components,
            ):
                widget.setChecked(False)
            self.source_hint.setText("Workspace akan dibuat kosong.")
            return
        self.source_hint.setText("Pilih data awal yang ingin dibawa dari workspace sebelumnya.")
        if self.copy_students.isChecked():
            self.copy_classes.setChecked(True)
            self.copy_classes.setEnabled(False)
        else:
            self.copy_classes.setEnabled(True)
        if self.copy_subject_rules.isChecked() or self.copy_components.isChecked():
            self.copy_subjects.setChecked(True)
        if self.copy_subjects.isChecked():
            self.copy_subject_rules.setEnabled(True)
            self.copy_components.setEnabled(True)
        else:
            self.copy_subject_rules.setChecked(False)
            self.copy_components.setChecked(False)
            self.copy_subject_rules.setEnabled(False)
            self.copy_components.setEnabled(False)

    def payload(self) -> dict:
        return {
            "academic_year": self.academic_year.text().strip(),
            "semester": self.semester.currentText(),
            "label": self.label_input.text().strip(),
            "source_workspace_id": self.source_workspace.currentData(),
            "copy_options": {
                "classes": self.copy_classes.isChecked(),
                "students": self.copy_students.isChecked(),
                "subjects": self.copy_subjects.isChecked(),
                "subject_rules": self.copy_subject_rules.isChecked(),
                "assessment_components": self.copy_components.isChecked(),
            },
        }


class BackupRestoreDialog(QDialog):
    def __init__(self, metadata: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pulihkan dari Backup")
        self.setMinimumWidth(560)
        self.workspace_label = ""

        layout = QVBoxLayout(self)
        title = QLabel("Pulihkan workspace dari file backup")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Backup akan dipulihkan sebagai workspace baru agar data yang sudah ada tetap aman.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        card = QWidget()
        card.setObjectName("DialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        info_lines = [
            f"File backup: {metadata.get('file_name', '-')}",
            f"Periode: {metadata.get('academic_year', '-') or '-'} - {metadata.get('semester', 'Ganjil')}",
            f"Guru: {metadata.get('teacher_name', '-') or '-'}",
            f"Sekolah: {metadata.get('school_name', '-') or '-'}",
        ]
        if metadata.get("backup_date"):
            info_lines.append(f"Tanggal backup: {metadata.get('backup_date')}")
        info_label = QLabel("\n".join(info_lines))
        info_label.setWordWrap(True)
        card_layout.addWidget(info_label)
        layout.addWidget(card)

        form = QFormLayout()
        self.workspace_name = QLineEdit(metadata.get("workspace_label", ""))
        self.workspace_name.setPlaceholderText("Contoh: 2026/2027 - Ganjil")
        form.addRow("Nama Workspace Baru", self.workspace_name)
        layout.addLayout(form)

        note = QLabel("Nilai dan data backup akan dibuka sebagai workspace baru. Workspace lain tidak akan ditimpa.")
        note.setObjectName("DialogHint")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        if save_button:
            save_button.setProperty("primary", True)
            save_button.setText("Pulihkan Backup")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def submit(self) -> None:
        self.workspace_label = self.workspace_name.text().strip()
        self.accept()

    @staticmethod
    def choose_backup_file(parent: QWidget | None = None) -> str:
        file_path, _ = QFileDialog.getOpenFileName(parent, "Pilih File Backup", "", "Database Files (*.db)")
        return file_path


def info(parent, text: str) -> None:
    QMessageBox.information(parent, "SiapGuru", text)


def error(parent, text: str) -> None:
    QMessageBox.critical(parent, "SiapGuru", text)


def confirm(parent, text: str) -> bool:
    return QMessageBox.question(parent, "SiapGuru", text) == QMessageBox.Yes


class UpdateDialog(QDialog):
    def __init__(self, update_info) -> None:
        super().__init__()
        self.setWindowTitle("Update SiapGuru")
        self.setMinimumWidth(560)
        self.opened_download = False
        self.update_info = update_info

        layout = QVBoxLayout(self)
        title = QLabel("Update aplikasi tersedia")
        title.setObjectName("PageTitle")
        subtitle_text = (
            f"Versi saat ini {update_info.current_version}. "
            f"Versi terbaru {update_info.latest_version}."
        )
        if update_info.update_required:
            subtitle_text += f" Versi minimum yang diizinkan adalah {update_info.minimum_version}."
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        if update_info.notes:
            notes_title = QLabel("Perubahan:")
            notes_title.setProperty("muted", True)
            layout.addWidget(notes_title)
            notes = QLabel("\n".join(f"- {item}" for item in update_info.notes))
            notes.setWordWrap(True)
            layout.addWidget(notes)

        action_text = (
            "Aplikasi harus diperbarui sebelum bisa dipakai."
            if update_info.update_required
            else "Anda bisa memperbarui sekarang atau melanjutkan nanti."
        )
        action_label = QLabel(action_text)
        action_label.setWordWrap(True)
        layout.addWidget(action_label)

        buttons = QDialogButtonBox()
        self.download_button = buttons.addButton("Unduh Update", QDialogButtonBox.AcceptRole)
        self.download_button.setProperty("primary", True)
        if update_info.update_required:
            self.close_button = buttons.addButton("Tutup Aplikasi", QDialogButtonBox.RejectRole)
        else:
            self.close_button = buttons.addButton("Nanti Saja", QDialogButtonBox.RejectRole)
        self.download_button.clicked.connect(self.open_download)
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def open_download(self) -> None:
        webbrowser.open(self.update_info.download_url)
        self.opened_download = True
        self.accept()


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
