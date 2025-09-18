"""
ESP32-S3 LED Control Frontend

A PyQt6 GUI to control two LEDs on ESP32-S3 via UART.
Author: Professional Mechatronics Engineer
"""
import sys
import re
import threading
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QLineEdit, QGridLayout, QStackedLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QFont
import serial
import serial.tools.list_ports


class SerialReader(QObject):
    line_received = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._serial = None
        self._stop = threading.Event()
        self._thread = None

    def start(self, port, baud):
        self.stop()
        try:
            self._serial = serial.Serial(port, baud, timeout=0.2)
        except Exception as e:
            raise
        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self.connected.emit()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.disconnected.emit()

    def write(self, data: bytes):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(data)
            except Exception:
                pass

    def _read_loop(self):
        ser = self._serial
        partial = b""
        while not self._stop.is_set() and ser and ser.is_open:
            try:
                data = ser.read(256)
            except Exception:
                break
            if not data:
                time.sleep(0.01)
                continue
            partial += data
            while b"\n" in partial:
                line, partial = partial.split(b"\n", 1)
                try:
                    text = line.decode(errors='replace').strip()
                except Exception:
                    text = repr(line)
                self.line_received.emit(text)
        # close handled by stop()


class MatrixWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.interval = 50
        self.timer.start(self.interval)
        self.chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%&*()"
        self.columns = []
        self.col_count = 0
        self.font_size = 14
        self.font = QFont('monospace', self.font_size)

    def resizeEvent(self, event):
        w = max(1, self.width())
        self.col_count = max(1, w // self.font_size)
        # initialize drop positions
        import random
        self.columns = [random.randint(0, self.height() // self.font_size) for _ in range(self.col_count)]
        super().resizeEvent(event)

    def _tick(self):
        # advance drops and repaint
        import random
        for i in range(len(self.columns)):
            if random.random() > 0.975:
                self.columns[i] = 0
            else:
                self.columns[i] += 1
        self.update()

    def paintEvent(self, event):
        if not self.columns:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setFont(self.font)
        # draw semi-transparent black overlay to slowly fade previous chars
        fade_color = QColor(0, 0, 0, 40)
        painter.fillRect(self.rect(), fade_color)
        for i, drop in enumerate(self.columns):
            x = i * self.font_size
            y = drop * self.font_size
            ch = self.chars[(x + y) % len(self.chars)]
            # green color gradient
            painter.setPen(QColor(140, 255, 140))
            painter.drawText(x, y, self.font_size, self.font_size, Qt.AlignmentFlag.AlignLeft, ch)
        painter.end()


class LedControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Pulsador ESP32 - Interfaz Oscura")
        self.resize(900, 600)
        self._reader = SerialReader()
        self._reader.line_received.connect(self.on_line)
        self._reader.connected.connect(self.on_connected)
        self._reader.disconnected.connect(self.on_disconnected)
        self._last_letter = "-"
        self._button_state = "Unknown"
        self._setup_ui()
        self._apply_dark_theme()
        self._refresh_ports()

    def _setup_ui(self):
        main = QVBoxLayout()
        # Header card
        header = QVBoxLayout()
        uni_lbl = QLabel("Universidad Militar Nueva Granada")
        uni_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uni_lbl.setStyleSheet("font-size:22px; font-weight:700;")
        course_lbl = QLabel("Materia: Micros")
        course_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        course_lbl.setStyleSheet("font-size:16px; color:#cccccc;")
        names_lbl = QLabel("Nombres: Daniel García Araque, Santiago Rubiano, Karol Daniela Mosquera Prieto")
        names_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        names_lbl.setWordWrap(True)
        names_lbl.setStyleSheet("font-size:13px; color:#aaaaaa;")
        header.addWidget(uni_lbl)
        header.addWidget(course_lbl)
        header.addWidget(names_lbl)
        main.addLayout(header)

        # Controls grid
        grid = QGridLayout()
        grid.setSpacing(12)
        port_label = QLabel("Puerto Serial")
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("Actualizar")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        baud_label = QLabel("Baud")
        self.baud_combo = QComboBox()
        for b in [1200, 9600, 19200, 38400, 57600, 115200, 128000, 230400, 460800]:
            self.baud_combo.addItem(str(b))
        self.baud_combo.setCurrentText("1200")
        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.clicked.connect(self._on_connect_click)
        grid.addWidget(port_label, 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(self.refresh_btn, 0, 2)
        grid.addWidget(baud_label, 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        grid.addWidget(self.connect_btn, 1, 2)
        main.addLayout(grid)

        # Status indicators
        status_layout = QHBoxLayout()
        self.conn_status = QLabel("Desconectado")
        self.conn_status.setStyleSheet("font-weight:600; color:#ff6b6b;")
        self.letter_label = QLabel("Última letra recibida: -")
        self.letter_label.setStyleSheet("font-size:22px; font-weight:800; color:#ffd166;")
        self.button_state_label = QLabel("Estado del pulsador: Desconocido")
        self.button_state_label.setStyleSheet("font-size:16px; color:#9ae66e;")
        status_layout.addWidget(self.conn_status)
        status_layout.addStretch()
        status_layout.addWidget(self.letter_label)
        status_layout.addStretch()
        status_layout.addWidget(self.button_state_label)
        main.addLayout(status_layout)

        # Log viewer and manual send
        lower = QHBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background:#101216; color:#e6eef8; font-family:monospace; font-size:12px;")
        right_col = QVBoxLayout()
        send_label = QLabel("Enviar manual (una letra):")
        self.send_input = QLineEdit()
        self.send_input.setMaxLength(1)
        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self._manual_send)
        right_col.addWidget(send_label)
        right_col.addWidget(self.send_input)
        right_col.addWidget(self.send_btn)
        right_col.addStretch()
        lower.addWidget(self.log_view, 3)
        lower.addLayout(right_col, 1)
        main.addLayout(lower)

        self.setLayout(main)

        # stack matrix background behind the UI content
        content = QWidget()
        content.setLayout(main)
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content.setStyleSheet('background:transparent;')
        stacked = QStackedLayout(self)
        self.matrix = MatrixWidget(self)
        stacked.addWidget(self.matrix)
        stacked.addWidget(content)
        stacked.setCurrentWidget(content)

        # Timer to refresh ports periodically
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._refresh_ports)
        self._port_timer.start(3000)

    def _apply_dark_theme(self):
        self.setStyleSheet("background-color: #0b0f13; color: #e6eef8;")
        self.refresh_btn.setStyleSheet("background:#1f2428; padding:6px; border-radius:6px;")
        self.connect_btn.setStyleSheet("background:#1b8cff; padding:8px; border-radius:8px; color:white; font-weight:600;")
        self.send_btn.setStyleSheet("background:#3bcf7a; padding:8px; border-radius:8px; color:#07120a; font-weight:600;")

    def _refresh_ports(self):
        current = self.port_combo.currentText()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def _on_connect_click(self):
        if self.connect_btn.text() == "Connect":
            port = self.port_combo.currentText()
            if not port:
                self._append_log("No port selected")
                return
            baud = int(self.baud_combo.currentText())
            try:
                self._reader.start(port, baud)
            except Exception as e:
                self._append_log(f"Failed to open port: {e}")
                return
            self.connect_btn.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
        else:
            self._reader.stop()
            self.connect_btn.setText("Connect")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)

    def on_connected(self):
        self.conn_status.setText("Conectado")
        self.conn_status.setStyleSheet("font-weight:600; color:#8df0a3;")
        self._append_log("Conectado al dispositivo")

    def on_disconnected(self):
        self.conn_status.setText("Desconectado")
        self.conn_status.setStyleSheet("font-weight:600; color:#ff6b6b;")
        self._append_log("Desconectado")

    def _append_log(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.log_view.append(f"[{ts}] {text}")
        # auto-scroll
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def on_line(self, line: str):
        self._append_log(line)
        # parse for sent letter
        m = re.search(r"Sent '\\'?(?P<letter>[A-Z])\\'?", line)
        if not m:
            # alternate pattern: Sent 'X' (without escaped quotes)
            m = re.search(r"Sent '\\'?(?P<letter2>[A-Z])\\'?", line)
        # simpler catch
        if not m:
            m2 = re.search(r"Sent\s+'(?P<L>[A-Z])'", line)
            if m2:
                self._last_letter = m2.group('L')
                self.letter_label.setText(f"Última letra recibida: {self._last_letter}")
        else:
            g = m.groupdict()
            letter = g.get('letter') or g.get('letter2')
            if letter:
                self._last_letter = letter
                self.letter_label.setText(f"Última letra recibida: {self._last_letter}")
        # parse for level_at_isr or level= patterns
        m_level = re.search(r"level_at_isr=(?P<v>[01])", line)
        if not m_level:
            m_level = re.search(r"level=(?P<v2>[01])", line)
        if m_level:
            v = m_level.group('v') if 'v' in m_level.groupdict() and m_level.group('v') is not None else m_level.group('v2')
            state = 'ALTO (3.3V)' if v == '1' else 'BAJO (GND)'
            self._button_state = state
            self.button_state_label.setText(f"Estado del pulsador: {self._button_state}")
        # parse debounce / handled logs
        if 'After debounce' in line:
            # optionally extract the level text already handled above
            pass
        if 'handled: valid press detected' in line:
            # keep state unchanged, already updated
            pass

    def _manual_send(self):
        txt = self.send_input.text().strip().upper()
        if not txt or len(txt) != 1 or not txt.isalpha():
            self._append_log("Letra manual inválida. Ingrese una única letra A-Z.")
            return
        data = f"{txt}\n".encode()
        self._reader.write(data)
        self._append_log(f"Enviado manualmente: {txt}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = LedControlGUI()
    win.show()
    sys.exit(app.exec())
