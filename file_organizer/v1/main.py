# file_organizer\v1\main.py

"""
main.py (simplified v1)
PyQt5 UI implementing only:
- drag & drop folder
- browse button for folder selection
- preview table (file -> category -> planned destination)
- Organize (executes moves safely)
- Undo Last
- Config editor (basic JSON editor)
"""

import sys
import json
from pathlib import Path

from PyQt5 import QtWidgets, QtGui  # type: ignore
from PyQt5.QtCore import Qt, pyqtSignal  # type: ignore
from PyQt5.QtWidgets import (  # type: ignore
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QTextEdit, QMessageBox
)

from file_organizer.v1.organizer import (
    load_config, save_config, build_preview, perform_moves,
    undo_last_run, append_log, DATA_DIR
)

ICON_PATH = Path(__file__).resolve().parents[1] / "icons" / "app_icon.png"


class FolderDropWidget(QLabel):
    """A simple label that accepts drag & drop of one folder."""
    folderDropped = pyqtSignal(str)

    def __init__(self):
        super().__init__("Drag & drop a folder here\n(or click Browse...)")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel{border: 2px dashed #888; padding: 20px;}")
        self.setMinimumHeight(100)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            folder = Path(urls[0].toLocalFile())
            if folder.exists() and folder.is_dir():
                self.folderDropped.emit(str(folder))


class ConfigEditorDialog(QtWidgets.QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Rules / Config")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.text = QTextEdit(self)
        self.text.setPlainText(json.dumps(cfg, indent=2))
        layout.addWidget(self.text)
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def save(self):
        try:
            newcfg = json.loads(self.text.toPlainText())
            save_config(newcfg)
            QMessageBox.information(self, "Saved", "Config saved.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer (Basic v1)")
        if ICON_PATH.exists():
            self.setWindowIcon(QtGui.QIcon(str(ICON_PATH)))
        self.resize(800, 500)
        self.config = load_config()
        self.source: Path | None = None

        self._setup_ui()
        self.update_status("Ready")

    def _setup_ui(self):
        v = QVBoxLayout(self)

        # drag/drop
        self.drop = FolderDropWidget()
        self.drop.folderDropped.connect(self.set_source_folder)
        v.addWidget(self.drop)

        # browse
        browse_btn = QPushButton("Browse Folder...")
        browse_btn.clicked.connect(self.browse_folder)
        v.addWidget(browse_btn)

        # preview table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Source File", "Category", "Planned Destination"])
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table)

        # buttons
        hb = QHBoxLayout()
        preview_btn = QPushButton("Preview Moves")
        preview_btn.clicked.connect(self.preview_moves)
        hb.addWidget(preview_btn)

        organize_btn = QPushButton("Organize (Move)")
        organize_btn.clicked.connect(self.organize_now)
        hb.addWidget(organize_btn)

        undo_btn = QPushButton("Undo Last")
        undo_btn.clicked.connect(self.undo_last)
        hb.addWidget(undo_btn)

        config_btn = QPushButton("Edit Rules")
        config_btn.clicked.connect(self.open_config_editor)
        hb.addWidget(config_btn)

        v.addLayout(hb)

        # status + log
        self.status = QLabel()
        v.addWidget(self.status)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        v.addWidget(QLabel("Log (recent)"))
        v.addWidget(self.log_view)

    def set_source_folder(self, path: str):
        self.source = Path(path)
        self.update_status(f"Source folder set: {self.source}")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        if folder:
            self.set_source_folder(folder)

    def update_status(self, text: str):
        self.status.setText(text)
        append_log(text)
        self._refresh_log_view()

    def _refresh_log_view(self):
        try:
            logpath = Path(DATA_DIR) / "organizer.log"
            if logpath.exists():
                lines = logpath.read_text(encoding="utf-8").splitlines()
                tail = "\n".join(lines[-200:])
                self.log_view.setPlainText(tail)
        except Exception:
            pass

    def preview_moves(self):
        if not self.source:
            QMessageBox.warning(self, "No folder",
                                "Please select a folder first.")
            return
        self.config = load_config()
        plan = build_preview([self.source], self.config)
        self.table.setRowCount(0)
        for row, item in enumerate(plan):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item["src"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["category"]))
            self.table.setItem(row, 2, QTableWidgetItem(item["planned_dest"]))
        self.update_status(f"Preview built: {len(plan)} files.")

    def organize_now(self):
        if self.table.rowCount() == 0:
            self.preview_moves()
            if self.table.rowCount() == 0:
                return
        cnt = self.table.rowCount()
        reply = QMessageBox.question(
            self, "Confirm", f"Organize {cnt} files?", QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        plan = []
        for r in range(self.table.rowCount()):
            plan.append({
                "src": self.table.item(r, 0).text(),
                "category": self.table.item(r, 1).text(),
                "planned_dest": self.table.item(r, 2).text()
            })
        performed = perform_moves(plan)
        self.update_status(f"Organized {len(performed)} files.")
        self.preview_moves()

    def undo_last(self):
        _, msg = undo_last_run()
        self.update_status(msg)
        QMessageBox.information(self, "Undo", msg)
        self.preview_moves()

    def open_config_editor(self):
        cfg = load_config()
        dlg = ConfigEditorDialog(cfg, self)
        if dlg.exec_():
            self.config = load_config()
            self.update_status("Config updated.")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
