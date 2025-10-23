import sys
from typing import Optional

import serial
import pyperclip
from serial.tools import list_ports

from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QGroupBox,
    QTextEdit,
)
from PyQt5.QtGui import QFont


class DongleLockWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dongle Lock GUI")
        self.setFixedSize(720, 600)
        self.setFont(QFont("Segoe UI", 10))

        self.connect_label: Optional[QLabel] = None
        self.connect_button: Optional[QPushButton] = None
        self.detected_port: Optional[str] = None
        self.serial_conn: Optional[serial.Serial] = None
        self.handshake_complete: bool = False
        self.get_code_buttons: list[QPushButton] = []
        self.disconnect_button: Optional[QPushButton] = None
        self.status_output: Optional[QTextEdit] = None
        self.test_mode_label: Optional[QLabel] = None
        # Test mode toggle: Set True to simulate STM32 responses without hardware.
        # When ready to test with the actual STM32 device, set this to False.
        self.test_mode = True

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.get_code_buttons = []

        connection_group = QGroupBox("Connection")
        connection_group.setStyleSheet("margin-top: 10px; font-weight: bold;")
        connection_layout = QVBoxLayout()
        connection_layout.setContentsMargins(10, 10, 10, 10)
        connection_layout.setSpacing(8)

        self.connect_label = QLabel("Connect Dongle")
        self.connect_label.setStyleSheet("font-weight: bold; color: #333;")

        self.connect_button = QPushButton("Connect")
        self.connect_button.setStyleSheet("padding: 8px; font-size: 14px;")
        self.connect_button.setMinimumHeight(32)
        self.connect_button.setMinimumWidth(160)
        self.connect_button.clicked.connect(self.attempt_connection)

        connection_layout.addWidget(self.connect_label)
        connection_layout.addWidget(self.connect_button)
        connection_group.setLayout(connection_layout)

        code_group = QGroupBox("Code Management")
        code_group.setStyleSheet("margin-top: 10px; font-weight: bold;")
        code_layout = QVBoxLayout()
        code_layout.setContentsMargins(10, 10, 10, 10)
        code_layout.setSpacing(8)
        for idx in range(1, 4):
            button = QPushButton(f"Get Code {idx}")
            button.setEnabled(False)
            button.setStyleSheet("padding: 8px; font-size: 14px;")
            button.setMinimumHeight(32)
            button.clicked.connect(lambda _checked, index=idx: self._handle_get_code(index))
            code_layout.addWidget(button)
            self.get_code_buttons.append(button)
        code_group.setLayout(code_layout)

        settings_group = QGroupBox("Settings")
        settings_group.setStyleSheet("margin-top: 10px; font-weight: bold;")
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(8)

        self.test_mode_label = QLabel("🧪 Test Mode: ON")
        self.test_mode_label.setStyleSheet("color: orange; font-weight: bold;")

        toggle_test_mode_button = QPushButton("Toggle Test Mode")
        toggle_test_mode_button.setStyleSheet("padding: 8px; font-size: 14px;")
        toggle_test_mode_button.setMinimumHeight(32)
        toggle_test_mode_button.setMinimumWidth(160)
        toggle_test_mode_button.clicked.connect(self._toggle_test_mode)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.setStyleSheet("padding: 8px; font-size: 14px;")
        self.disconnect_button.setMinimumHeight(32)
        self.disconnect_button.clicked.connect(self._handle_disconnect)

        settings_layout.addWidget(self.test_mode_label)
        settings_layout.addWidget(toggle_test_mode_button)
        settings_layout.addWidget(self.disconnect_button)
        settings_group.setLayout(settings_layout)

        self.status_output = QTextEdit()
        self.status_output.setReadOnly(True)
        self.status_output.setMinimumHeight(80)
        self.status_output.setStyleSheet("padding: 6px; font-size: 12px;")
        self.status_output.setFont(QFont("Courier New", 10))

        layout.addWidget(connection_group)
        layout.addWidget(code_group)
        layout.addWidget(settings_group)
        layout.addWidget(self.status_output)

        self.setLayout(layout)
        self._update_status("Status: Idle")

    def attempt_connection(self) -> None:
        """Attempt to locate an attached STM32 device via serial."""
        self.detected_port = None

        # Scan all serial ports and look for STM device
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
            self._update_status(f"STM32 detected on {self.detected_port}")
            self._update_status("Attempting handshake with STM32...")

            if (
                self.serial_conn is not None
                and self.serial_conn.is_open
                and self.serial_conn.port == self.detected_port
                and self.handshake_complete
            ):
                self._update_status("Handshake already established with STM32.")
                self._set_disconnect_enabled(True)
                return

            self.establish_handshake()
        else:
            if self.connect_label is not None:
                self.connect_label.setText("Device Not Found")
            self._update_status("No STM32-compatible serial port detected.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)

    def establish_handshake(self) -> None:
        """Open a serial connection to perform an STM32 handshake."""
        if self.detected_port is None:
            self._update_status("No detected port available for handshake.")
            return

        connection = self.serial_conn

        if connection is None or not connection.is_open or connection.port != self.detected_port:
            try:
                # Open serial connection and initiate handshake
                self.serial_conn = serial.Serial(self.detected_port, baudrate=115200, timeout=2)
            except serial.SerialException as exc:
                self._update_status(f"Serial error: {exc}")
                self.serial_conn = None
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return
            except OSError as exc:
                self._update_status(f"I/O error: {exc}")
                self.serial_conn = None
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return
            connection = self.serial_conn

        if connection is None or not connection.is_open:
            self._update_status("Failed to open serial connection.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)
            return

        # Perform handshake sequence: send CONNECT and await OK response.
        # When test_mode is enabled, this simulates an STM32 response.
        self._update_status("Waiting for STM32 response...")
        if self.test_mode:
            response = "OK"
        else:
            try:
                connection.write(b"CONNECT\n")
                response_bytes = connection.readline()
                response = response_bytes.decode("utf-8", errors="replace").strip()
            except serial.SerialException as exc:
                self._update_status(f"Serial error: {exc}")
                self.handshake_complete = False
                self._set_get_code_buttons_enabled(False)
                self._set_disconnect_enabled(False)
                return

        # Check for OK handshake response
        if response == "OK":
            self._update_status("Handshake successful with STM32.")
            self.handshake_complete = True
            self._set_get_code_buttons_enabled(True)
            self._set_disconnect_enabled(True)
        elif response:
            self._update_status(f"Unexpected response: {response}")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)
        else:
            self._update_status("No response received from STM32.")
            self.handshake_complete = False
            self._set_get_code_buttons_enabled(False)
            self._set_disconnect_enabled(False)

    def _update_status(self, message: str) -> None:
        if self.status_output is None:
            return
        self.status_output.append(message)
        self.status_output.ensureCursorVisible()
        QApplication.processEvents()

    def _set_get_code_buttons_enabled(self, enabled: bool) -> None:
        for button in self.get_code_buttons:
            button.setEnabled(enabled)

    def _set_disconnect_enabled(self, enabled: bool) -> None:
        if self.disconnect_button is not None:
            self.disconnect_button.setEnabled(enabled)

    def _toggle_test_mode(self) -> None:
        self.test_mode = not self.test_mode

        if self.test_mode_label is not None:
            if self.test_mode:
                self.test_mode_label.setText("🧪 Test Mode: ON")
                self.test_mode_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.test_mode_label.setText("✅ Real STM32 Mode")
                self.test_mode_label.setStyleSheet("color: green; font-weight: bold;")

        # Reset handshake state when switching modes
        self.handshake_complete = False
        self._set_get_code_buttons_enabled(False)
        self._set_disconnect_enabled(False)

        state_text = "ON" if self.test_mode else "OFF"
        self._update_status(f"Test mode toggled: {state_text}. Handshake reset.")

    def _handle_get_code(self, code_index: int) -> None:
        if self.serial_conn is None or not self.serial_conn.is_open:
            self._update_status("Serial connection not available. Please reconnect.")
            return

        # Send GET request for a specific code index
        command = f"GET_CODE_{code_index}\n".encode("utf-8")

        self._update_status(f"Requesting Code {code_index} from STM32...")
        self._update_status("Waiting for STM32 response...")

        try:
            self.serial_conn.write(command)
            if self.test_mode:
                response_bytes = b"NOT_FOUND"
            else:
                response_bytes = self.serial_conn.readline()
        except serial.SerialException as exc:
            self._update_status(f"Serial error: {exc}")
            return

        response = response_bytes.decode("utf-8", errors="replace").strip()

        if not response:
            self._update_status(f"No response received for Code {code_index}.")
            return

        # If code is found, copy to clipboard
        if response.startswith("CODE:"):
            _, _, code = response.partition("CODE:")
            code = code.strip()
            pyperclip.copy(code)
            self._update_status(f"Code {code_index} copied to clipboard: {code}")
        # If code doesn't exist, prompt user to enter new code
        elif response == "NOT_FOUND":
            self._update_status(f"Code {code_index} not found on device.")
            new_code, accepted = QInputDialog.getText(
                self,
                "Set Code",
                f"Enter new code for Code {code_index}:",
            )

            if not accepted or not new_code.strip():
                self._update_status("Code entry cancelled.")
                return

            code_value = new_code.strip()
            set_command = f"SET_CODE_{code_index}:{code_value}\n".encode("utf-8")

            self._update_status("Waiting for STM32 response...")

            try:
                self.serial_conn.write(set_command)
                # Simulate STM32 behavior in test mode
                if self.test_mode:
                    # Simulate STM32 confirmation when saving a new code in test mode
                    confirmation = "SAVED"
                else:
                    confirmation_bytes = self.serial_conn.readline()
                    confirmation = confirmation_bytes.decode("utf-8", errors="replace").strip()
            except serial.SerialException as exc:
                self._update_status(f"Serial error while saving: {exc}")
                return

            # Copy retrieved or saved code to clipboard
            if confirmation == "SAVED":
                pyperclip.copy(code_value)
                self._update_status(
                    f"Code {code_index} saved and copied to clipboard: {code_value}"
                )
            elif confirmation:
                self._update_status(f"Unexpected response after saving: {confirmation}")
            else:
                self._update_status("No confirmation received after saving code.")
        else:
            self._update_status(f"Unexpected response: {response}")

    def _handle_disconnect(self) -> None:
        # Handle disconnect and clear clipboard
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

        pyperclip.copy("")  # Clear clipboard

        self._update_status("Disconnected. Clipboard cleared.")

        self.close()


def main() -> None:
    app = QApplication(sys.argv)
    window = DongleLockWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()