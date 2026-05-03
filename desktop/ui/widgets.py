from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


BADGE_STYLES = {
    "Tuntas": ("#0F766E", "#D1FAE5"),
    "Belum Tuntas": ("#B91C1C", "#FEE2E2"),
    "Tidak Diubah": ("#475569", "#E2E8F0"),
    "Auto Tuntas": ("#1D4ED8", "#DBEAFE"),
    "Auto Ketuntasan": ("#7C3AED", "#EDE9FE"),
    "Perlu Review": ("#9A3412", "#FED7AA"),
    "Tuntas Setelah Penyesuaian": ("#1D4ED8", "#DBEAFE"),
    "Tuntas Setelah Remedial": ("#1D4ED8", "#DBEAFE"),
    "Remedial Ringan": ("#92400E", "#FEF3C7"),
    "Review Manual": ("#9A3412", "#FED7AA"),
    "Perlu Remedial": ("#9A3412", "#FED7AA"),
    "Perlu Evaluasi": ("#7C2D12", "#FFEDD5"),
    "A": ("#166534", "#DCFCE7"),
    "B": ("#1D4ED8", "#DBEAFE"),
    "C": ("#92400E", "#FEF3C7"),
    "D": ("#B91C1C", "#FEE2E2"),
}


class CardWidget(QFrame):
    def __init__(self, title: str, value: str, accent: str = "#2563EB") -> None:
        super().__init__()
        self.setObjectName("CardWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("CardValue")
        value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(title_label)
        layout.addWidget(value_label)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        layout.addWidget(title_label)
        if subtitle:
            layout.addWidget(subtitle_label)


class ActionButton(QPushButton):
    def __init__(self, label: str, primary: bool = False, compact: bool = False) -> None:
        super().__init__(label)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("primary", primary)
        self.setProperty("compact", compact)
        self.setFixedHeight(36 if compact else 46)


def table_item(
    value: object,
    *,
    editable: bool = False,
    alignment: Qt.AlignmentFlag | Qt.Alignment = Qt.AlignCenter,
    foreground: str | None = None,
    background: str | None = None,
) -> QTableWidgetItem:
    item = QTableWidgetItem("" if value is None else str(value))
    item.setTextAlignment(alignment | Qt.AlignVCenter)
    if foreground:
        item.setForeground(QBrush(QColor(foreground)))
    if background:
        item.setBackground(QBrush(QColor(background)))
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    return item


def _wrap_header_label(label: str) -> str:
    if len(label) <= 12 or " " not in label:
        return label
    parts = label.split()
    midpoint = max(1, len(parts) // 2)
    return " ".join(parts[:midpoint]) + "\n" + " ".join(parts[midpoint:])


def set_table_headers(
    table: QTableWidget,
    headers: list[str],
    *,
    action_col_width: int | None = None,
    default_row_height: int = 44,
) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([_wrap_header_label(label) for label in headers])
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setWordWrap(True)
    table.setShowGrid(False)
    table.verticalHeader().setDefaultSectionSize(default_row_height)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.setFocusPolicy(Qt.NoFocus)
    table.setFrameShape(QFrame.NoFrame)
    table.setTextElideMode(Qt.ElideNone)

    header = table.horizontalHeader()
    header.setStretchLastSection(action_col_width is None)
    header.setMinimumSectionSize(42)
    header.setDefaultAlignment(Qt.AlignCenter)
    for index, label in enumerate(headers):
        if index == 0 and label == "No":
            header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
        elif action_col_width is not None and index == len(headers) - 1:
            header.setSectionResizeMode(index, QHeaderView.Fixed)
            table.setColumnWidth(index, action_col_width)
        else:
            header.setSectionResizeMode(index, QHeaderView.Stretch)


def fill_table(table: QTableWidget, rows: list[list[str]]) -> None:
    table.setRowCount(len(rows))
    for row_index, row_data in enumerate(rows):
        for col_index, value in enumerate(row_data):
            item = table_item(value)
            table.setItem(row_index, col_index, item)
    table.resizeRowsToContents()


def badge_item(value: object, *, editable: bool = False) -> QTableWidgetItem:
    text = "" if value is None else str(value)
    item = table_item(text, editable=editable)
    fg_bg = BADGE_STYLES.get(text)
    if fg_bg:
        foreground, background = fg_bg
        item.setForeground(QBrush(QColor(foreground)))
        item.setBackground(QBrush(QColor(background)))
    return item


def add_row_actions(
    table: QTableWidget,
    row: int,
    actions: list[tuple[str, callable]],
    *,
    show_text: bool = False,
) -> None:
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(10)
    for label, callback in actions:
        button = ActionButton(label if show_text else "", compact=True)
        button.setToolTip(label)
        button.setProperty("actionRole", _action_role(label))
        if show_text:
            button.setMinimumWidth(64)
        else:
            button.setFixedWidth(46)
            button.setProperty("iconOnly", True)
        icon = _action_icon(wrapper, label)
        if icon is not None:
            button.setIcon(icon)
        button.clicked.connect(callback)
        layout.addWidget(button)
    if not show_text:
        layout.addStretch()
        wrapper.setMinimumWidth((len(actions) * 46) + (max(0, len(actions) - 1) * 10) + 20)
    table.setCellWidget(row, table.columnCount() - 1, wrapper)


def _action_icon(widget: QWidget, label: str):
    icon_map = {
        "Edit": QStyle.SP_FileDialogDetailedView,
        "Hapus": QStyle.SP_TrashIcon,
        "Simpan": QStyle.SP_DialogSaveButton,
        "Terapkan": QStyle.SP_DialogApplyButton,
        "Reset": QStyle.SP_BrowserReload,
        "Buka": QStyle.SP_DialogOpenButton,
        "Lihat": QStyle.SP_FileDialogContentsView,
        "Salin": QStyle.SP_FileDialogContentsView,
    }
    icon_type = icon_map.get(label)
    if icon_type is None:
        return None
    return widget.style().standardIcon(icon_type)


def _action_role(label: str) -> str:
    role_map = {
        "Edit": "edit",
        "Hapus": "delete",
        "Simpan": "save",
        "Terapkan": "apply",
        "Reset": "reset",
        "Buka": "open",
        "Lihat": "open",
        "Salin": "copy",
    }
    return role_map.get(label, "default")
