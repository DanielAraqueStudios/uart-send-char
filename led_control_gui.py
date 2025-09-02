"""
ESP32-S3 LED Control Frontend

A PyQt6 GUI to control two LEDs on ESP32-S3 via UART.
Author: Professional Mechatronics Engineer
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QPalette, QColor, QIcon, QFont
from PyQt6.QtCore import Qt
import serial
import serial.tools.list_ports
import os

BAUD_RATE = 115200

class LedControlUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ESP32-S3 LED Control')
        self.resize(900, 800)
        self.setup_dark_mode()
        self.serial = None
        self.init_ui()

    def setup_dark_mode(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(24, 24, 32))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 56))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(32, 32, 44))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(palette)

    def list_serial_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def icon_path(self, name):
        # Use emoji as icons for simplicity
        return None

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel('ESP32-S3 LED Control')
        title.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel('Status: Ready')
        self.status_label.setFont(QFont('Arial', 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Serial port selection
        port_layout = QHBoxLayout()
        port_layout.setSpacing(10)
        self.port_combo = QComboBox()
        self.port_combo.setFont(QFont('Arial', 11))
        self.port_combo.addItems(self.list_serial_ports())
        self.port_combo.setMinimumWidth(160)
        port_layout.addWidget(QLabel('Serial Port:'))
        port_layout.addWidget(self.port_combo)
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        self.connect_btn.setStyleSheet('QPushButton { background-color: #0078d7; color: white; border-radius: 8px; padding: 6px 18px; } QPushButton:pressed { background-color: #005fa3; }')
        self.connect_btn.clicked.connect(self.connect_serial)
        port_layout.addWidget(self.connect_btn)
        layout.addLayout(port_layout)

        # LED1 controls
        led1_layout = QHBoxLayout()
        led1_layout.setSpacing(16)
        led1_on_btn = QPushButton('💡 LED1 ON')
        led1_off_btn = QPushButton('🔌 LED1 OFF')
        for btn in [led1_on_btn, led1_off_btn]:
            btn.setFont(QFont('Arial', 13))
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet('QPushButton { background-color: #222244; color: #00ff99; border-radius: 12px; } QPushButton:pressed { background-color: #0078d7; color: white; }')
        led1_on_btn.clicked.connect(lambda: self.send_command('LED1 ON'))
        led1_off_btn.clicked.connect(lambda: self.send_command('LED1 OFF'))
        led1_layout.addWidget(led1_on_btn)
        led1_layout.addWidget(led1_off_btn)
        layout.addLayout(led1_layout)

        # LED2 controls
        led2_layout = QHBoxLayout()
        led2_layout.setSpacing(16)
        led2_on_btn = QPushButton('💡 LED2 ON')
        led2_off_btn = QPushButton('🔌 LED2 OFF')
        for btn in [led2_on_btn, led2_off_btn]:
            btn.setFont(QFont('Arial', 13))
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet('QPushButton { background-color: #222244; color: #00bfff; border-radius: 12px; } QPushButton:pressed { background-color: #0078d7; color: white; }')
        led2_on_btn.clicked.connect(lambda: self.send_command('LED2 ON'))
        led2_off_btn.clicked.connect(lambda: self.send_command('LED2 OFF'))
        led2_layout.addWidget(led2_on_btn)
        led2_layout.addWidget(led2_off_btn)
        layout.addLayout(led2_layout)

        self.setLayout(layout)

        # Add university, course, and team info at the top with improved UI/UX
        info_card = QWidget()
        info_card_layout = QVBoxLayout()
        info_card_layout.setSpacing(4)
        info_card_layout.setContentsMargins(8, 8, 8, 8)
        info_card.setLayout(info_card_layout)
        info_card.setStyleSheet('''
            background-color: #23233a;
            border-radius: 12px;
            border: 1px solid #0078d7;
        ''')

        uni_label = QLabel('Universidad Militar Nueva Granada')
        uni_label.setFont(QFont('Arial', 22, QFont.Weight.Bold))
        uni_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uni_label.setStyleSheet('color: #00bfff;')
        info_card_layout.addWidget(uni_label)

        info_label = QLabel('Materia: Electricidad y Electrónica')
        info_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet('color: #00ff99;')
        info_card_layout.addWidget(info_label)

        # Display team members in a list with bigger 'Nombres:' label
        names_label = QLabel('Nombres:')
        names_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        names_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        names_label.setStyleSheet('color: #ffffff;')
        info_card_layout.addWidget(names_label)

        names_list = QWidget()
        names_list_layout = QVBoxLayout()
        names_list_layout.setSpacing(2)
        names_list_layout.setContentsMargins(0, 0, 0, 0)
        names_list.setLayout(names_list_layout)
        for name in [
            'Julied Gomez',
            'Valeria Bolivar',
            'Juliana Torres',
            'Nikol Gomez',
            'Fabian Moncada',
            'Manuela Cortes'
        ]:
            name_label = QLabel(name)
            name_label.setFont(QFont('Arial', 11))
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet('color: #ffffff;')
            names_list_layout.addWidget(name_label)
        info_card_layout.addWidget(names_list)

        layout.insertWidget(0, info_card)

    def connect_serial(self):
        port = self.port_combo.currentText()
        try:
            self.serial = serial.Serial(port, BAUD_RATE, timeout=1)
            self.status_label.setText(f'Connected to {port}')
        except Exception as e:
            self.status_label.setText(f'Connection error: {e}')

    def send_command(self, cmd):
        if self.serial and self.serial.is_open:
            try:
                self.serial.write((cmd + '\n').encode())
                self.status_label.setText(f'Sent: {cmd}')
            except Exception as e:
                self.status_label.setText(f'Error: {e}')
        else:
            self.status_label.setText('Serial not connected')

    def closeEvent(self, event):
        if self.serial and self.serial.is_open:
            self.serial.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LedControlUI()
    window.show()
    sys.exit(app.exec())
