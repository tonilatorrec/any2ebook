import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .any2ebook import run as cli_run
from .config import Config, user_config_dir


class SuccessWindow(QtWidgets.QWidget):
    def __init__(self):
        self.setWindowTitle("Success")
        self.resize

class ConfigItemLayout(QHBoxLayout):
    def __init__(self, dialog: QDialog, value: Any = None):
        super().__init__()
        self.dialog = dialog
        self.edit = QLineEdit(str(value) if value is not None else None)
        self.select_dir_btn = QPushButton()
        self.select_dir_btn.clicked.connect(self.select_directory)
        self.addWidget(self.edit)
        self.addWidget(self.select_dir_btn)

    def select_directory(self) -> None:
        try:
            dir_name, _ = QFileDialog.getExistingDirectory(self.dialog, "Select directory", "", QFileDialog.ShowDirsOnly)
            self.edit.text = dir_name
        except ValueError:
            pass

class ConfigDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")

        self.config = config   # work on a copy

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.clippings_layout = ConfigItemLayout(self, self.config.clippings_path)
        self.input_layout = ConfigItemLayout(self, self.config.input_path)
        self.output_layout = ConfigItemLayout(self, self.config.output_path)

        form.addRow("Clippings path:", self.clippings_layout)
        form.addRow("Input path:", self.input_layout)
        form.addRow("Output path:", self.output_layout)

        layout.addLayout(form)

        # Buttons
        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def get_config(self) -> None:
        """Return updated config (call only if accepted)."""
        # TODO improve syntax
        self.config.clippings_path = Path(self.clippings_layout.edit.text()) if self.clippings_layout.edit.text() != "" else None
        self.config.input_path = Path(self.input_layout.edit.text()) if self.input_layout.edit.text() != "" else None
        self.config.output_path = Path(self.output_layout.edit.text()) if self.output_layout.edit.text() != "" else None
    
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("any2ebook")
        self.resize(300, 200)

        self.path_to_config = user_config_dir() / "config.yaml"

        if not self.path_to_config.exists():
            # load dummy config, then ask user to provide actual config
            self.config = Config.load(Path(files('any2ebook').joinpath('config_sample.yaml')))
            self.show_prompt_ask_for_config()
        else:
            self.config = Config.load(Path(self.path_to_config))

        layout = QtWidgets.QVBoxLayout(self)
        self.generate_btn = QPushButton("Generate EPUB")
        self.generate_btn.clicked.connect(self.on_generate)
        self.config_btn = QPushButton("Config")
        self.config_btn.clicked.connect(self.open_config_dialog)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.config_btn)
    
    def on_generate(self):
        success = cli_run(self.config)
        if success:
            QMessageBox.information(self, "Success", "Success!")
        else:
            QMessageBox.critical(self, "Error", "Failed")

    def open_config_dialog(self):
        dlg = ConfigDialog(self.config, self)
        if dlg.exec_() == dlg.Accepted:
            dlg.get_config()
            self.config.save(self.path_to_config)
            # TODO: inform user when the config is not correct (e.g. clippings folder is not a valid path) - use pydantic?

    def show_prompt_ask_for_config(self):
        QMessageBox.information(self, 'Information', "No configuration yet. Press OK to introduce config...", QMessageBox.StandardButton.Ok)
        self.open_config_dialog()

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
