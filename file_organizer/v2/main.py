# file_organizer/v2/main.py

"""
File Organizer - v2 with advanced log viewer
Features:
- Drag & drop or browse folders
- Preview with checkboxes
- Organize selected files
- Undo last run
- Config editor GUI (table)
- Dark mode
- Monitoring with watchdog (QThread)
- Tray icon background agent (minimize to tray/restore)
- Advanced log viewer (timestamps, auto-scroll, export, clear)
"""

import sys
import datetime
from pathlib import Path
from typing import List

from PyQt5 import QtWidgets, QtGui  # type: ignore
from PyQt5.QtCore import Qt, QThread, pyqtSignal  # type: ignore
from PyQt5.QtWidgets import (  # type: ignore
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QCheckBox,
    QSystemTrayIcon, QStyle, QMenu, QMessageBox, QTextEdit
)

from file_organizer.v2.organizer import (
    load_config, save_config, build_preview, perform_moves, undo_last_run
)

ICON_PATH = Path(__file__).resolve().parents[1] / "icons" / "app_icon.png"

# Optional watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler
    WATCHDOG = True
except ImportError:
    WATCHDOG = False


class FolderDrop(QLabel):
    foldersDropped = pyqtSignal(list)

    def __init__(self):
        super().__init__("Drag & drop folders here\n(or click Browse...)")
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border:2px dashed #888; padding:20px;")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        self.foldersDropped.emit(paths)


class WatchdogThread(QThread):
    fileCreated = pyqtSignal(str)

    def __init__(self, folder, patterns):
        super().__init__()
        self.folder, self.patterns = folder, patterns
        self.observer = None

    def run(self):
        if not WATCHDOG:
            return
        ev = PatternMatchingEventHandler(
            patterns=self.patterns, ignore_directories=True)
        ev.on_created = lambda e: self.fileCreated.emit(e.src_path)
        self.observer = Observer()
        self.observer.schedule(ev, self.folder, recursive=False)
        self.observer.start()
        try:
            self.exec_()
        finally:
            if self.observer:
                self.observer.stop()
                self.observer.join()

    def stop(self):
        if self.observer:
            self.observer.stop()
        self.quit()
        self.wait()


class ConfigEditor(QtWidgets.QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Categories")
        self.resize(700, 400)
        self.cfg = cfg
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Category", "Extensions", "Destination"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.load()
        btns = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add)
        rm_btn = QPushButton("Remove Selected")
        rm_btn.clicked.connect(self.remove)
        browse_btn = QPushButton("Set Destination")
        browse_btn.clicked.connect(self.set_dest)
        btns.addWidget(add_btn)
        btns.addWidget(rm_btn)
        btns.addWidget(browse_btn)
        layout.addLayout(btns)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)

    def load(self):
        self.table.setRowCount(0)
        for cat, info in self.cfg.get("categories", {}).items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cat))
            self.table.setItem(row, 1, QTableWidgetItem(
                ",".join(info.get("extensions", []))))
            self.table.setItem(row, 2, QTableWidgetItem(
                info.get("destination", "")))

    def add(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("NewCategory"))
        self.table.setItem(r, 1, QTableWidgetItem(".ext"))
        self.table.setItem(r, 2, QTableWidgetItem(""))

    def remove(self):
        for r in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(r)

    def set_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination")
        if folder:
            for r in {i.row() for i in self.table.selectedIndexes()}:
                self.table.setItem(r, 2, QTableWidgetItem(folder))

    def save(self):
        cats = {}
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0).text().strip()
            exts = [e.strip() for e in self.table.item(
                r, 1).text().split(",") if e.strip()]
            dest = self.table.item(r, 2).text().strip()
            if name:
                cats[name] = {"extensions": exts, "destination": dest}
        self.cfg["categories"] = cats
        save_config(self.cfg)
        self.accept()


class LogViewer(QWidget):
    """Advanced log viewer with timestamped entries, clear/export, auto-scroll."""

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)

        hb = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        export_btn = QPushButton("Export Log")
        export_btn.clicked.connect(self.export_log)
        self.autoscroll_chk = QCheckBox("Auto-scroll")
        self.autoscroll_chk.setChecked(True)
        hb.addWidget(clear_btn)
        hb.addWidget(export_btn)
        hb.addStretch()
        hb.addWidget(self.autoscroll_chk)
        v.addLayout(hb)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(120)
        v.addWidget(self.text)

    def log(self, message: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.text.append(entry)
        if self.autoscroll_chk.isChecked():
            self.text.moveCursor(QtGui.QTextCursor.End)

    def clear_log(self):
        self.text.clear()

    def export_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "log.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.toPlainText())


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer")
        if ICON_PATH.exists():
            self.setWindowIcon(QtGui.QIcon(str(ICON_PATH)))
        self.resize(900, 650)
        self.cfg = load_config()
        self.sources: List[Path] = []
        self.monitors = {}  # path -> WatchdogThread

        v = QVBoxLayout(self)
        self.drop = FolderDrop()
        self.drop.foldersDropped.connect(self.add_sources)
        v.addWidget(self.drop)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        v.addWidget(browse)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["✔", "Source", "Category", "Destination"])
        self.table.setColumnWidth(0, 30)
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table)

        hb = QHBoxLayout()
        prev = QPushButton("Preview")
        prev.clicked.connect(self.preview)
        org = QPushButton("Organize")
        org.clicked.connect(self.organize)
        undo = QPushButton("Undo Last")
        undo.clicked.connect(self.undo)
        conf = QPushButton("Edit Rules")
        conf.clicked.connect(self.edit_rules)
        self.monitor_chk = QCheckBox("Monitor Folders")
        self.monitor_chk.stateChanged.connect(self.toggle_monitoring)
        dark = QCheckBox("Dark mode")
        dark.stateChanged.connect(lambda s: self.dark(s))
        hb.addWidget(prev)
        hb.addWidget(org)
        hb.addWidget(undo)
        hb.addWidget(conf)
        hb.addWidget(self.monitor_chk)
        hb.addWidget(dark)
        v.addLayout(hb)

        self.status = QLabel("Ready")
        v.addWidget(self.status)

        # Advanced log viewer
        v.addWidget(QLabel("Activity Log:"))
        self.log_viewer = LogViewer()
        v.addWidget(self.log_viewer)

        self._setup_tray()
        self.log("Application started.")

    def log(self, msg: str):
        self.log_viewer.log(msg)
        self.status.setText(msg)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray.setVisible(True)
        m = QMenu()
        m.addAction("Show", self.showNormal)
        m.addAction("Quit", QApplication.quit)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Minimize to tray",
            "Minimize to tray and keep monitoring in background?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        if reply == QMessageBox.Yes:
            self.hide()
            event.ignore()
            self.tray.showMessage(
                "File Organizer", "Minimized to tray. Right-click tray icon to Quit.")
        elif reply == QMessageBox.No:
            QApplication.quit()
        else:
            event.ignore()

    def add_sources(self, paths):
        for p in paths:
            pp = Path(p)
            if pp.exists() and pp not in self.sources:
                self.sources.append(pp)
        self.log(f"Sources: {', '.join(map(str, self.sources))}")

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self.add_sources([d])

    def preview(self):
        self.cfg = load_config()
        if not self.sources:
            QMessageBox.warning(self, "No sources",
                                "Please add one or more folders.")
            return

        plan = build_preview(self.sources, self.cfg)

        # Reset table
        self.table.setRowCount(0)
        for row, it in enumerate(plan):
            self.table.insertRow(row)

            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked)
            self.table.setItem(row, 0, chk)

            # Source folder column (multi-source clarity)
            src_folder = str(Path(it["src"]).parent)
            src_item = QTableWidgetItem(src_folder)
            src_item.setToolTip(it["src"])  # full path tooltip
            self.table.setItem(row, 1, src_item)

            self.table.setItem(row, 2, QTableWidgetItem(it["category"]))
            self.table.setItem(row, 3, QTableWidgetItem(it["planned_dest"]))

        self.log(f"Preview {len(plan)} files from {len(self.sources)} sources")

    def organize(self):
        plan = []
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).checkState() == Qt.Checked:
                plan.append({
                    "src": self.table.item(r, 1).toolTip() or self.table.item(r, 1).text(),
                    "category": self.table.item(r, 2).text(),
                    "planned_dest": self.table.item(r, 3).text()
                })
        if not plan:
            QMessageBox.information(
                self, "No selection", "Please select at least one file to organize.")
            return

        moved = perform_moves(plan)
        self.log(
            f"Moved {len(moved)} files across {len(self.sources)} sources")
        self.preview()

    def undo(self):
        _, msg = undo_last_run()
        QMessageBox.information(self, "Undo", msg)
        self.log(msg)
        self.preview()

    def edit_rules(self):
        dlg = ConfigEditor(self.cfg, self)
        if dlg.exec_():
            self.cfg = load_config()
            self.log("Config updated.")

    def dark(self, s):
        """
        Robust dark-mode toggle. Accepts bool-like `s` (0/1 or True/False).
        Applies Fusion style + full dark palette + widget stylesheet fallbacks.
        """
        app = QApplication.instance()
        if app is None:
            return

        if bool(s):
            self._apply_dark_theme(app)
        else:
            self._reset_theme(app)

        self._refresh_ui(app)

    def _apply_dark_theme(self, app: QApplication) -> None:
        app.setStyle("Fusion")

        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.WindowText,
                            QtGui.QColor(235, 235, 235))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(35, 35, 35))
        palette.setColor(QtGui.QPalette.AlternateBase,
                            QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ToolTipBase,
                            QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ToolTipText,
                            QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(235, 235, 235))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ButtonText,
                            QtGui.QColor(235, 235, 235))
        palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 0, 0))
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(0, 0, 0))
        app.setPalette(palette)

        app.setStyleSheet("""
            QWidget { color: #EBEBEB; background-color: #353535; }
            QToolTip { color: #ffffff; background-color: #2a2a2a; border: 1px solid #ffffff; }
            QHeaderView::section { background-color: #3b3b3b; color: #ffffff; padding: 4px; }
            QPushButton { background-color: #5A5A5A; border: 1px solid #3a3a3a; color: #ffffff; padding: 4px; }
            QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget { background-color: #1e1e1e; color: #EBEBEB; }
            QCheckBox, QLabel { color: #EBEBEB; }
        """)

        log_widget = self._get_log_widget()
        if log_widget is not None:
            log_widget.setStyleSheet("""
                background-color: #1e1e1e;
                color: #00ff88;
                font-family: Consolas, "Courier New", monospace;
                font-size: 12px;
                border: 1px solid #333;
                padding: 4px;
            """)
            try:
                log_widget.moveCursor(QtGui.QTextCursor.End)
            except Exception:
                pass

        if getattr(self, "table", None) is not None:
            self.table.setAlternatingRowColors(True)
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: #2b2b2b;
                    color: #EBEBEB;
                    gridline-color: #3a3a3a;
                }
                QHeaderView::section { background-color: #3b3b3b; color: #ffffff; padding: 6px; }
            """)

    def _reset_theme(self, app: QApplication) -> None:
        app.setPalette(QApplication.style().standardPalette())
        app.setStyleSheet("")

        log_widget = self._get_log_widget()
        if log_widget is not None:
            log_widget.setStyleSheet("")

        if getattr(self, "table", None) is not None:
            self.table.setAlternatingRowColors(False)
            self.table.setStyleSheet("")

    def _get_log_widget(self):
        candidates = []
        if hasattr(self, "log_viewer"):
            candidates.extend([
                getattr(self.log_viewer, "text", None),
                getattr(self.log_viewer, "textEdit", None),
            ])
        candidates.append(getattr(self, "log_view", None))
        for w in candidates:
            if w is not None:
                return w
        return None

    def _refresh_ui(self, app: QApplication) -> None:
        try:
            app.processEvents()
            self.repaint()
        except Exception:
            pass

    def toggle_monitoring(self, state):
        enabled = bool(state)
        if enabled:
            for src in self.sources:
                self.start_monitoring(src)
        else:
            for t in self.monitors.values():
                try:
                    t.stop()
                except Exception:
                    pass
            self.monitors.clear()
        self.log("Monitoring " + ("enabled" if enabled else "disabled"))

    def start_monitoring(self, folder):
        if not WATCHDOG:
            QMessageBox.warning(self, "Watchdog not installed",
                                "Folder monitoring requires watchdog package.")
            return
        if folder in self.monitors:
            return
        patterns = self.cfg.get("monitor_patterns", ["*"])
        t = WatchdogThread(str(folder), patterns)
        t.fileCreated.connect(self.on_file_created)
        t.start()
        self.monitors[folder] = t
        self.log(f"Monitoring: {folder}")

    def on_file_created(self, path):
        p = Path(path)
        containing = p.parent
        if containing not in self.sources:
            self.add_sources([str(containing)])
        self.preview()
        cfg = load_config()
        plan = build_preview([containing], cfg)
        plan = [entry for entry in plan if entry["src"] == str(p)]
        if plan:
            moved = perform_moves(plan)
            if moved:
                self.log(f"Auto-moved new file: {p.name}")


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(app.style().standardIcon(
        QtWidgets.QStyle.SP_ComputerIcon))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
