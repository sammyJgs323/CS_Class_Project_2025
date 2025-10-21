import sys
from typing import Optional

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class DongleLockWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dongle Lock GUI")
        self.setFixedSize(400, 200)

        self.connect_label: Optional[QLabel] = None
        self.connect_button: Optional[QPushButton] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        self.connect_label = QLabel("Connect Dongle")
        self.connect_button = QPushButton("Connect")

        layout.addWidget(self.connect_label)
        layout.addWidget(self.connect_button)

        self.setLayout(layout)


def main() -> None:
    app = QApplication(sys.argv)
    window = DongleLockWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
