from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QCheckBox, QPushButton, QFrame, QMessageBox
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки мониторинга USD")
        self.setFixedSize(460, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.settings = dict(current_settings)

        self.init_ui()
        self.apply_dark_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("⚙ Параметры приложения")
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        # 1. Update interval
        int_frame = QFrame()
        int_frame.setObjectName("settingCard")
        int_layout = QHBoxLayout(int_frame)
        int_layout.setContentsMargins(14, 12, 14, 12)

        lbl_int = QLabel("Интервал автообновления:")
        lbl_int.setStyleSheet("color: #DDE2EC; font-size: 13px;")

        self.combo_interval = QComboBox()
        self.intervals_map = {
            "15 минут": 15,
            "30 минут": 30,
            "1 час (по умолчанию)": 60,
            "2 часа": 120,
            "3 часа": 180,
            "6 часов": 360,
        }
        for label, mins in self.intervals_map.items():
            self.combo_interval.addItem(label, mins)

        # Select current interval
        cur_min = self.settings.get("update_interval_minutes", 60)
        idx = 2  # default 60
        for i in range(self.combo_interval.count()):
            if self.combo_interval.itemData(i) == cur_min:
                idx = i
                break
        self.combo_interval.setCurrentIndex(idx)

        int_layout.addWidget(lbl_int)
        int_layout.addStretch()
        int_layout.addWidget(self.combo_interval)
        layout.addWidget(int_frame)

        # 2. Notification threshold
        thr_frame = QFrame()
        thr_frame.setObjectName("settingCard")
        thr_layout = QVBoxLayout(thr_frame)
        thr_layout.setContentsMargins(14, 12, 14, 12)
        thr_layout.setSpacing(10)

        self.chk_notif = QCheckBox("Включить уведомления об изменении курса")
        self.chk_notif.setChecked(self.settings.get("notifications_enabled", True))
        self.chk_notif.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600;")
        thr_layout.addWidget(self.chk_notif)

        sub_thr_layout = QHBoxLayout()
        lbl_thr = QLabel("Порог изменения для уведомления:")
        lbl_thr.setStyleSheet("color: #A0AABF; font-size: 12px;")

        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.01, 2.00)
        self.spin_threshold.setSingleStep(0.01)
        self.spin_threshold.setValue(self.settings.get("notification_threshold", 0.04))
        self.spin_threshold.setSuffix(" ₴")
        self.spin_threshold.setDecimals(2)

        sub_thr_layout.addWidget(lbl_thr)
        sub_thr_layout.addStretch()
        sub_thr_layout.addWidget(self.spin_threshold)
        thr_layout.addLayout(sub_thr_layout)
        layout.addWidget(thr_frame)

        # 3. System integration
        sys_frame = QFrame()
        sys_frame.setObjectName("settingCard")
        sys_layout = QVBoxLayout(sys_frame)
        sys_layout.setContentsMargins(14, 12, 14, 12)
        sys_layout.setSpacing(8)

        self.chk_autostart = QCheckBox("Автозапуск при старте Windows")
        self.chk_autostart.setChecked(self.settings.get("autostart", False))
        self.chk_autostart.setStyleSheet("color: #DDE2EC; font-size: 13px;")

        self.chk_min_tray = QCheckBox("Сворачивать в системный трей при минимизации")
        self.chk_min_tray.setChecked(self.settings.get("minimize_to_tray", True))
        self.chk_min_tray.setStyleSheet("color: #DDE2EC; font-size: 13px;")

        self.chk_close_tray = QCheckBox("Сворачивать в трей при закрытии (крестик)")
        self.chk_close_tray.setChecked(self.settings.get("close_to_tray", True))
        self.chk_close_tray.setStyleSheet("color: #DDE2EC; font-size: 13px;")

        sys_layout.addWidget(self.chk_autostart)
        sys_layout.addWidget(self.chk_min_tray)
        sys_layout.addWidget(self.chk_close_tray)
        layout.addWidget(sys_frame)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self.save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def save(self):
        self.settings["update_interval_minutes"] = self.combo_interval.currentData()
        self.settings["notifications_enabled"] = self.chk_notif.isChecked()
        self.settings["notification_threshold"] = round(self.spin_threshold.value(), 2)
        self.settings["autostart"] = self.chk_autostart.isChecked()
        self.settings["minimize_to_tray"] = self.chk_min_tray.isChecked()
        self.settings["close_to_tray"] = self.chk_close_tray.isChecked()
        self.accept()

    def get_settings(self):
        return self.settings

    def apply_dark_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #16181F;
                color: #FFFFFF;
            }
            QFrame#settingCard {
                background-color: #21242E;
                border: 1px solid #2F3342;
                border-radius: 8px;
            }
            QComboBox {
                background-color: #2B2F3D;
                border: 1px solid #3F4457;
                border-radius: 6px;
                padding: 6px 12px;
                color: #FFFFFF;
                font-size: 12px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #00C389;
            }
            QComboBox QAbstractItemView {
                background-color: #21242E;
                border: 1px solid #3F4457;
                selection-background-color: #00C389;
                selection-color: #000000;
                color: #FFFFFF;
            }
            QDoubleSpinBox {
                background-color: #2B2F3D;
                border: 1px solid #3F4457;
                border-radius: 6px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }
            QDoubleSpinBox:hover {
                border-color: #00C389;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3F4457;
                background-color: #2B2F3D;
            }
            QCheckBox::indicator:hover {
                border-color: #00C389;
            }
            QCheckBox::indicator:checked {
                background-color: #00C389;
                border-color: #00C389;
                image: none;
            }
            QPushButton#btnSecondary {
                background-color: #2B2F3D;
                color: #DDE2EC;
                border: 1px solid #3F4457;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#btnSecondary:hover {
                background-color: #353A4B;
            }
            QPushButton#btnPrimary {
                background-color: #00C389;
                color: #0F1A15;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btnPrimary:hover {
                background-color: #00D898;
            }
        """)
