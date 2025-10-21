import sys
from typing import Optional

import serial
import pyperclip
from serial.tools import list_ports

from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QInputDialog


class DongleLockWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dongle Lock GUI")
        self.setFixedSize(400, 300)

        self.connect_label: Optional[QLabel] = None
        self.connect_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self.detected_port: Optional[str] = None
        self.serial_conn: Optional[serial.Serial] = None
        self.handshake_complete: bool = False
        self.get_code_buttons: list[QPushButton] = []
        self.disconnect_button: Optional[QPushButton] = None
        # Test mode toggle: Set True to simulate STM32 responses without hardware.
        # When ready to test with the actual STM32 device, set this to False.
        self.test_mode = True

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

        for idx in range(1, 4):
            button = QPushButton(f"Get Code {idx}")
            button.setEnabled(False)
            button.clicked.connect(lambda _checked, index=idx: self._handle_get_code(index))
            layout.addWidget(button)
            self.get_code_buttons.append(button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self._handle_disconnect)
        layout.addWidget(self.disconnect_button)

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
                self.status_label.setText("Attempting handshake with STM32...")

            if (
                self.serial_conn is not None
                and self.serial_conn.is_open
                and self.serial_conn.port == self.detected_port
                and self.handshake_complete
            ):
                if self.status_label is not None:
                    self.status_label.setText("Handshake already established with STM32.")
                self._set_disconnect_enabled(True)
                return

            self.establish_handshake()
        else:
            if self.connect_label is not None:
                self.connect_label.setText("Device Not Found")
            if self.status_label is not None:
                self.status_label.setText("No STM32-compatible serial port detected.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)

    def establish_handshake(self) -> None:
        """Open a serial connection to perform an STM32 handshake."""
        if self.detected_port is None:
            if self.status_label is not None:
                self.status_label.setText("No detected port available for handshake.")
            return

        connection = self.serial_conn

        if connection is None or not connection.is_open or connection.port != self.detected_port:
            try:
                self.serial_conn = serial.Serial(self.detected_port, baudrate=115200, timeout=2)
            except serial.SerialException as exc:
                if self.status_label is not None:
                    self.status_label.setText(f"Serial error: {exc}")
                self.serial_conn = None
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return
            except OSError as exc:
                if self.status_label is not None:
                    self.status_label.setText(f"I/O error: {exc}")
                self.serial_conn = None
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return
            connection = self.serial_conn

        if connection is None or not connection.is_open:
            if self.status_label is not None:
                self.status_label.setText("Failed to open serial connection.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)
            return

        # Perform handshake sequence: send CONNECT and await OK response.
        # When test_mode is enabled, this simulates an STM32 response.
        if self.test_mode:
            response = "OK"
        else:
            try:
                connection.write(b"CONNECT\n")
                response_bytes = connection.readline()
                response = response_bytes.decode("utf-8", errors="replace").strip()
            except serial.SerialException as exc:
                if self.status_label is not None:
                    self.status_label.setText(f"Serial error: {exc}")
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return

        if self.status_label is None:
            return

        if response == "OK":
            self.status_label.setText("Handshake successful with STM32.")
            self.handshake_complete = True
            self._set_get_code_buttons_enabled(True)
            self._set_disconnect_enabled(True)
        elif response:
            self.status_label.setText(f"Unexpected response: {response}")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)
        else:
            self.status_label.setText("No response received from STM32.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)

    def _set_get_code_buttons_enabled(self, enabled: bool) -> None:
        for button in self.get_code_buttons:
            button.setEnabled(enabled)

    def _set_disconnect_enabled(self, enabled: bool) -> None:
        if self.disconnect_button is not None:
            self.disconnect_button.setEnabled(enabled)

    def _handle_get_code(self, code_index: int) -> None:
        if self.serial_conn is None or not self.serial_conn.is_open:
            if self.status_label is not None:
                self.status_label.setText("Serial connection not available. Please reconnect.")
            return

        command = f"GET_CODE_{code_index}\n".encode("utf-8")

        try:
            self.serial_conn.write(command)
            if self.test_mode:
                # Simulate STM32 response when in test mode
                response = "NOT_FOUND"
                response_bytes = response.encode("utf-8")
            else:
                response_bytes = self.serial_conn.readline()
        except serial.SerialException as exc:
            if self.status_label is not None:
                self.status_label.setText(f"Serial error: {exc}")
            return

        response = response_bytes.decode("utf-8", errors="replace").strip()

        if self.status_label is None:
            return

        if not response:
            self.status_label.setText(f"No response received for Code {code_index}.")
            return

        if response.startswith("CODE:"):
            _, _, code = response.partition("CODE:")
            code = code.strip()
            pyperclip.copy(code)
            self.status_label.setText(f"Code {code_index} copied to clipboard: {code}")
        elif response == "NOT_FOUND":
            self.status_label.setText(f"Code {code_index} not found on device.")
            new_code, accepted = QInputDialog.getText(
                self,
                "Set Code",
                f"Enter new code for Code {code_index}:",
            )

            if not accepted or not new_code.strip():
                self.status_label.setText("Code entry cancelled.")
                return

            code_value = new_code.strip()
            set_command = f"SET_CODE_{code_index}:{code_value}\n".encode("utf-8")

            try:
                self.serial_conn.write(set_command)
                confirmation_bytes = self.serial_conn.readline()
            except serial.SerialException as exc:
                self.status_label.setText(f"Serial error while saving: {exc}")
                return

            confirmation = confirmation_bytes.decode("utf-8", errors="replace").strip()

            if confirmation == "SAVED":
                pyperclip.copy(code_value)
                self.status_label.setText(
                    f"Code {code_index} saved and copied to clipboard: {code_value}"
                )
            elif confirmation:
                self.status_label.setText(f"Unexpected response after saving: {confirmation}")
            else:
                self.status_label.setText("No confirmation received after saving code.")
        else:
            self.status_label.setText(f"Unexpected response: {response}")

    def _handle_disconnect(self) -> None:
        if self.serial_conn is not None and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except serial.SerialException:
                pass
            self.serial_conn = None

        self.handshake_complete = False
        self.detected_port = None
        self._set_get_code_buttons_enabled(False)
        self._set_disconnect_enabled(False)
        if self.connect_button is not None:
            self.connect_button.setEnabled(False)

        pyperclip.copy("")

        if self.status_label is not None:
            self.status_label.setText("Disconnected. Clipboard cleared.")

        self.close()


def main() -> None:
    app = QApplication(sys.argv)
    window = DongleLockWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
