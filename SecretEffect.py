from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
import sys
import random

class EvaUnit02Berserk(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("暴走 - UNIT 02")
        self.setAutoFillBackground(True)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # CODE 999 ACTIVATED 表示用ラベル（最初だけ表示）
        self.label_code = QLabel("")
        self.label_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_code.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        self.label_code.setStyleSheet("color: #ff0000;")
        self.layout.addWidget(self.label_code)

        # メインラベルは最初は非表示
        self.label_main = QLabel("BLOOD CONTACT")
        self.label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_main.setFont(QFont("Arial", 64, QFont.Weight.Bold))
        self.label_main.setStyleSheet("color: #ff0000;")
        self.label_main.hide()
        self.layout.addWidget(self.label_main)

        self.label_sub = QLabel("LIMITER OVERRIDE")
        self.label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_sub.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self.label_sub.setStyleSheet("color: white;")
        self.label_sub.hide()
        self.layout.addWidget(self.label_sub)

        self.bg_colors = ["#2a0000", "#000000", "#8b0000"]
        self.text_variants = [
            ("SYSTEM OVERDRIVE", "#ff0000"),
            ("LIMITER OVERRIDE", "#FF4500"),
            ("CONTROL LOST", "white"),
            ("OUTPUT ANOMALY", "#ff2222")
        ]

        # CODE 999 ACTIVATED を1文字ずつ表示する演出用
        self.code_text = "CODE:999 ACTIVATED..."
        self.code_index = 0
        self.code_timer = QTimer(self)
        self.code_timer.timeout.connect(self.show_next_code_char)
        self.code_timer.start(90)  # 文字送り速度

        # SYSTEM REBOOTの1文字ずつ表示用タイマー
        self.reboot_text = "SYSTEM REBOOT"
        self.reboot_index = 0
        self.reboot_timer = QTimer(self)
        self.reboot_timer.timeout.connect(self.show_next_reboot_char)

        # メインの演出タイマーは後でスタート
        self.timer_interval = 410  # 初期インターバル(ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_effect)

        # ブラックアウト用タイマー（単発）
        self.blackout_timer = QTimer(self)
        self.blackout_timer.setSingleShot(True)
        self.blackout_timer.timeout.connect(self.start_end_sequence)

        # ブラックアウト開始用タイマー（単発）
        self.end_timer = QTimer(self)
        self.end_timer.setSingleShot(True)
        self.end_timer.timeout.connect(self.start_blackout_sequence)

        self.showFullScreen()

    def show_next_code_char(self):
        if self.code_index < len(self.code_text):
            self.label_code.setText(self.label_code.text() + self.code_text[self.code_index])
            self.code_index += 1
            self.setStyleSheet("background-color: #000000;")
        else:
            self.code_timer.stop()
            QTimer.singleShot(1500, self.start_main_sequence)

    def start_main_sequence(self):
        self.label_code.hide()
        self.label_main.show()
        self.label_sub.show()
        self.timer.start(self.timer_interval)
        self.end_timer.start(7000)

    def update_effect(self):
        bg = random.choice(self.bg_colors)
        txt, color = random.choice(self.text_variants)

        self.setStyleSheet(f"background-color: {bg};")
        self.label_main.setText(txt)
        self.label_main.setStyleSheet(f"color: {color};")
        self.label_sub.setStyleSheet(f"color: {random.choice(['white', '#ffaaaa', '#ff3333'])};")

        if self.timer_interval > 100:
            self.timer_interval -= 20
            self.timer.setInterval(self.timer_interval)

    def start_blackout_sequence(self):
        self.setStyleSheet("background-color: black;")
        self.label_main.hide()
        self.label_sub.hide()
        self.timer.stop()
        self.blackout_timer.start(2000)

    def start_end_sequence(self):
        self.timer.stop()
        self.label_sub.show()
        self.label_sub.setText("CONTROL RECOVERED")
        self.label_sub.setStyleSheet("color:#00FF00")
        self.label_main.setStyleSheet("color:#00FF00")
        self.label_main.setText("")
        self.label_main.show()
        self.reboot_index = 0
        self.reboot_timer.start(100)

    def show_next_reboot_char(self):
        if self.reboot_index < len(self.reboot_text):
            current_text = self.label_main.text() + self.reboot_text[self.reboot_index]
            self.label_main.setText(current_text)
            self.reboot_index += 1
        else:
            self.reboot_timer.stop()
            QTimer.singleShot(2000, self.close)

def run_emergency():
    app = QApplication(sys.argv)
    window = EvaUnit02Berserk()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_emergency()