import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox
)

from .any2ebook import main as cli_main
from .paths import user_config_dir, ensure_config
from importlib.resources import files

import yaml


class SuccessWindow(QtWidgets.QWidget):
    def __init__(self):
        self.setWindowTitle("Success")
        self.resize

class ConfigDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")

        self._config = config.copy()   # work on a copy

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.clippings_edit = QLineEdit(config.get("clippings_path", ""))
        self.input_edit = QLineEdit(config.get("input_path", ""))
        self.output_edit = QLineEdit(config.get("output_path", ""))

        form.addRow("Clippings path:", self.clippings_edit)
        form.addRow("Input path:", self.input_edit)
        form.addRow("Output path:", self.output_edit)

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

    def get_config(self) -> dict:
        """Return updated config (call only if accepted)."""
        self._config["clippings_path"] = self.clippings_edit.text()
        self._config["input_path"] = self.input_edit.text()
        self._config["output_path"] = self.output_edit.text()
        return self._config
    
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("any2ebook")
        self.resize(300, 200)

        self.path_to_config = user_config_dir() / "config.yaml"
        if not self.path_to_config.exists():
            with open(files('any2ebook').joinpath('config_sample.yaml')) as f:
                self.config = yaml.safe_load(f)
            self.show_prompt_ask_for_config()
        else:
            with open(self.path_to_config, 'r') as f:
                self.config = yaml.safe_load(f)

        layout = QtWidgets.QVBoxLayout(self)
        self.generate_btn = QPushButton("Generate EPUB")
        self.generate_btn.clicked.connect(self.on_generate)
        self.config_btn = QPushButton("Config")
        self.config_btn.clicked.connect(self.open_config)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.config_btn)
    
    def on_generate(self):
        success = cli_main()
        if success:
            QMessageBox.information(self, "Success", "Success!")
        else:
            QMessageBox.critical(self, "Error", "Failed")

    def open_config(self):
        dlg = ConfigDialog(self.config, self)
        if dlg.exec_() == dlg.Accepted:
            self.config = dlg.get_config()
            self.save_config()
            # TODO: inform user when the config is not correct (e.g. clippings folder is not a valid path) - use pydantic?

    def save_config(self):
        with open(self.path_to_config, 'w') as f:
            yaml.dump(self.config, f)

    def show_prompt_ask_for_config(self):
        msg_box = QMessageBox.information(self, 'Information', "No configuration yet. Press OK to introduce config...", QMessageBox.StandardButton.Ok)
        self.open_config()

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
