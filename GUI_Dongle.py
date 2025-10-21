import sys
from typing import Optional

from serial.tools import list_ports

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget


class DongleLockWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dongle Lock GUI")
        self.setFixedSize(400, 220)

        self.connect_label: Optional[QLabel] = None
        self.connect_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self.detected_port: Optional[str] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        self.connect_label = QLabel("Connect Dongle")
        self.connect_button = QPushButton("Connect")
        self.status_label = QLabel("Status: Idle")

        self.connect_button.clicked.connect(self.attempt_connection)

        layout.addWidget(self.connect_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def attempt_connection(self) -> None:
        """Attempt to locate an attached STM32 device via serial."""
        self.detected_port = None

        candidate_port = None
        for port_info in list_ports.comports():
            description = (port_info.description or "").upper()
            if "STM" in description or "USB" in description:
                candidate_port = port_info
                break

        if candidate_port:
            self.detected_port = candidate_port.device
            if self.connect_label is not None:
                self.connect_label.setText(f"STM32 detected on {self.detected_port}")
            if self.status_label is not None:
                self.status_label.setText("Ready to establish connection.")
        else:
            if self.connect_label is not None:
                self.connect_label.setText("Device Not Found")
            if self.status_label is not None:
                self.status_label.setText("No STM32-compatible serial port detected.")


def main() -> None:
    app = QApplication(sys.argv)
    window = DongleLockWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
