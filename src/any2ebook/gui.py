import any2ebook
from PyQt5 import QtWidgets
import sys

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('any2ebook')
        self.resize(300, 200)

        layout = QtWidgets.QVBoxLayout(self)
        self.generate_btn = QtWidgets.QPushButton("Generate EPUB")
        self.generate_btn.clicked.connect(self.on_generate)
        layout.addWidget(self.generate_btn)        

    def on_generate(self):
        any2ebook.main()

def run_gui():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_gui()