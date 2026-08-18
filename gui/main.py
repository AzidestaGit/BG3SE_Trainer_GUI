#!/usr/bin/env python3
"""
BG3_SE_GUI — external control panel for the BG3GuiBridge Script Extender mod.

Run while the game is running (or not — the mod just won't be there to receive
commands, and Status will show "not connected"):

    python3 gui/main.py
"""
import json
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QFileDialog,
)

from bridge import Bridge, find_bridge_dir

SHARED_DIR = Path(__file__).resolve().parent.parent / "shared"
COMMANDS_FILE = SHARED_DIR / "commands.json"

CONFIDENCE_HINT = {
    "verified-pattern": "✅ verified-pattern",
    "needs-testing": "⚠️ needs-testing — check in-game console first",
}


def load_commands() -> list[dict]:
    data = json.loads(COMMANDS_FILE.read_text())
    return data["commands"]


class ParamRow(QWidget):
    """A single labeled input for a command parameter."""

    def __init__(self, spec: dict):
        super().__init__()
        self.spec = spec
        self.edit = QLineEdit(str(spec.get("default", "")))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(spec["name"]))
        layout.addWidget(self.edit)

    def value(self):
        text = self.edit.text()
        if self.spec.get("type") == "int":
            try:
                return int(text)
            except ValueError:
                return self.spec.get("default", 0)
        return text


class CommandButton(QGroupBox):
    def __init__(self, cmd: dict, bridge: Bridge, log_fn):
        super().__init__(cmd["label"])
        self.cmd = cmd
        self.bridge = bridge
        self.log_fn = log_fn
        self.param_rows: list[ParamRow] = []

        layout = QVBoxLayout(self)

        hint = CONFIDENCE_HINT.get(cmd.get("confidence"), cmd.get("confidence", ""))
        hint_label = QLabel(hint)
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint_label)

        if cmd.get("description"):
            desc = QLabel(cmd["description"])
            desc.setWordWrap(True)
            desc.setStyleSheet("font-size: 11px;")
            layout.addWidget(desc)

        if cmd.get("params"):
            form = QWidget()
            form_layout = QVBoxLayout(form)
            form_layout.setContentsMargins(0, 0, 0, 0)
            for spec in cmd["params"]:
                row = ParamRow(spec)
                self.param_rows.append(row)
                form_layout.addWidget(row)
            layout.addWidget(form)

        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run)
        layout.addWidget(run_btn)

    def run(self):
        if not self.bridge.is_configured():
            QMessageBox.warning(self, "Not connected", "Set the bridge folder first (Settings tab).")
            return
        params = {row.spec["name"]: row.value() for row in self.param_rows}
        cmd_id = self.bridge.send_action(self.cmd["id"], params)
        self.log_fn(f"sent '{self.cmd['id']}' ({cmd_id[:8]}) params={params}")


class SettingsTab(QWidget):
    def __init__(self, bridge: Bridge, log_fn):
        super().__init__()
        self.bridge = bridge
        self.log_fn = log_fn

        layout = QVBoxLayout(self)

        self.path_label = QLabel(self._path_text())
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        btn_row = QHBoxLayout()
        auto_btn = QPushButton("Auto-detect bridge folder")
        auto_btn.clicked.connect(self.autodetect)
        browse_btn = QPushButton("Browse manually…")
        browse_btn.clicked.connect(self.browse)
        btn_row.addWidget(auto_btn)
        btn_row.addWidget(browse_btn)
        layout.addLayout(btn_row)

        info = QLabel(
            "Auto-detect looks for BG3GuiBridge/probe.txt under known Steam compatdata "
            "prefixes. That file only exists after you've launched BG3 at least once with "
            "the mod installed and enabled. See README.md if auto-detect finds nothing."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)
        layout.addStretch()

    def _path_text(self) -> str:
        if self.bridge.is_configured():
            return f"Bridge folder: {self.bridge.bridge_dir}"
        return "Bridge folder: not set"

    def autodetect(self):
        found = find_bridge_dir()
        if found:
            self.bridge.set_bridge_dir(found)
            self.path_label.setText(self._path_text())
            self.log_fn(f"bridge folder set to {found}")
        else:
            QMessageBox.information(
                self,
                "Not found",
                "No probe.txt found yet. Launch BG3 with the mod enabled once, then try again.",
            )

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select BG3GuiBridge folder")
        if d:
            self.bridge.set_bridge_dir(Path(d))
            self.path_label.setText(self._path_text())
            self.log_fn(f"bridge folder set to {d}")


class ConsoleTab(QWidget):
    def __init__(self, bridge: Bridge, log_fn):
        super().__init__()
        self.bridge = bridge
        self.log_fn = log_fn

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Run arbitrary Lua server-side (paste community BG3SE snippets here). "
            "This is the most powerful and most \"guaranteed correct\" panel — it just "
            "forwards whatever you type to load()/pcall() in the game."
        ))
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("-- e.g.\nOsiris.ApplyStatus(Osiris.DB_IsPlayer:Get(nil)[1][1], 'SG_Immortal', -1, 0)")
        layout.addWidget(self.editor)

        run_btn = QPushButton("Run Lua")
        run_btn.clicked.connect(self.run)
        layout.addWidget(run_btn)

    def run(self):
        if not self.bridge.is_configured():
            QMessageBox.warning(self, "Not connected", "Set the bridge folder first (Settings tab).")
            return
        code = self.editor.toPlainText()
        if not code.strip():
            return
        cmd_id = self.bridge.send_raw_lua(code)
        self.log_fn(f"sent raw lua ({cmd_id[:8]})")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BG3 SE GUI")
        self.resize(720, 640)

        self.bridge = Bridge()
        self.bridge.autodetect()

        outer = QVBoxLayout(self)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, stretch=1)

        commands = load_commands()
        categories: dict[str, list[dict]] = {}
        for cmd in commands:
            categories.setdefault(cmd.get("category", "Misc"), []).append(cmd)

        for category, cmds in categories.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            for cmd in cmds:
                tab_layout.addWidget(CommandButton(cmd, self.bridge, self.append_log))
            tab_layout.addStretch()
            self.tabs.addTab(tab, category)

        self.tabs.addTab(ConsoleTab(self.bridge, self.append_log), "Console")
        self.tabs.addTab(SettingsTab(self.bridge, self.append_log), "Settings")

        # Status / log footer
        self.status_label = QLabel("Status: unknown")
        outer.addWidget(self.status_label)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        outer.addWidget(self.log_view)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(1000)
        self.poll()

    def append_log(self, msg: str):
        self.log_view.appendPlainText(msg)

    def poll(self):
        if not self.bridge.is_configured():
            self.status_label.setText("Status: bridge folder not set (see Settings tab)")
            return
        status = self.bridge.read_status()
        if status is None:
            self.status_label.setText("Status: no status.json yet (mod not loaded / game not running?)")
            return
        ok = status.get("ok")
        msg = status.get("message")
        action = status.get("lastAction")
        icon = "✅" if ok else "❌"
        self.status_label.setText(f"Status: {icon} last action '{action}': {msg}")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
