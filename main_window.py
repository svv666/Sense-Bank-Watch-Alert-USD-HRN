import os
import sys
import webbrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QButtonGroup, QRadioButton,
    QSystemTrayIcon, QMenu, QApplication, QToolTip
)
from PySide6.QtGui import (
    QIcon, QFont, QColor, QCursor, QAction, QKeySequence, QShortcut
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPoint, QSize
)

from data_service import fetch_all_rates
from chart_widget import CurrencyChartWidget
from settings_manager import load_settings, save_settings
from settings_dialog import SettingsDialog

class FetchWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            data = fetch_all_rates()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class ClickableRateCard(QFrame):
    """
    Card displaying rate with click-to-copy functionality and visual feedback.
    """
    def __init__(self, title, sub_title="", accent_color="#00C389", parent=None):
        super().__init__(parent)
        self.accent_color = accent_color
        self.rate_value = 0.0
        self.rate_str = "—"
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("rateCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        top_layout = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #8C93A6; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        top_layout.addWidget(self.lbl_title)
        top_layout.addStretch()

        self.lbl_copy_hint = QLabel("📋 Копировать")
        self.lbl_copy_hint.setStyleSheet("color: #555E70; font-size: 10px;")
        top_layout.addWidget(self.lbl_copy_hint)
        layout.addLayout(top_layout)

        self.lbl_rate = QLabel("— ₴")
        self.lbl_rate.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.lbl_rate.setStyleSheet(f"color: {self.accent_color};")
        layout.addWidget(self.lbl_rate)

        self.lbl_sub = QLabel(sub_title)
        self.lbl_sub.setStyleSheet("color: #727B8E; font-size: 11px;")
        layout.addWidget(self.lbl_sub)

    def set_rate(self, value, text_suffix=" ₴", sub_text=None):
        self.rate_value = value
        self.rate_str = f"{value:.2f}" if isinstance(value, float) and value > 0 else "—"
        self.lbl_rate.setText(f"{self.rate_str}{text_suffix}")
        if sub_text is not None:
            self.lbl_sub.setText(sub_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rate_str != "—":
            clipboard = QApplication.clipboard()
            clipboard.setText(self.rate_str)

            # Flash visual feedback
            self.lbl_copy_hint.setText("✓ Скопировано!")
            self.lbl_copy_hint.setStyleSheet("color: #00C389; font-weight: bold; font-size: 10px;")
            QTimer.singleShot(1800, lambda: (
                self.lbl_copy_hint.setText("📋 Копировать"),
                self.lbl_copy_hint.setStyleSheet("color: #555E70; font-size: 10px;")
            ))

            # Also show tooltip
            pos = self.mapToGlobal(QPoint(self.width() // 2, 0))
            QToolTip.showText(pos, f"Курс {self.rate_str} ₴ скопирован в буфер обмена!", self, QPoint(), 1800)

        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USD / UAH Монитор курсов")
        self.resize(720, 680)
        self.setMinimumSize(640, 600)

        self.settings = load_settings()
        self.current_data = None
        self.current_mode = "online"  # 'online', 'department', 'card'
        self.seconds_until_update = self.settings.get("update_interval_minutes", 60) * 60
        self.is_fetching = False
        self.first_close_warning_shown = False

        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.png"))
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = self.style().standardIcon(QIcon.ThemeIcon.ApplicationXExecutable)

        self.init_ui()
        self.init_tray()
        self.init_shortcuts()
        self.init_timers()
        self.apply_dark_styles()

        # Initial fetch
        self.start_fetch()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(14)

        # 1. Header (Logo, Bank Title, Status, Refresh, Settings)
        header = QHBoxLayout()
        header.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        h_title = QLabel("USD / UAH Монитор")
        h_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        h_title.setStyleSheet("color: #FFFFFF;")
        title_col.addWidget(h_title)

        self.lbl_bank_source = QLabel("Источник: Sense Bank")
        self.lbl_bank_source.setStyleSheet("color: #8C93A6; font-size: 11px;")
        title_col.addWidget(self.lbl_bank_source)

        header.addLayout(title_col)
        header.addStretch()

        # Status badge
        self.badge_status = QLabel("● Обновление...")
        self.badge_status.setStyleSheet("""
            background-color: #212530;
            color: #00C389;
            border: 1px solid #2F3647;
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        header.addWidget(self.badge_status)

        # Refresh button (F5)
        self.btn_refresh = QPushButton("🔄 Обновить (F5)")
        self.btn_refresh.setObjectName("btnAction")
        self.btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_refresh.clicked.connect(self.start_fetch)
        header.addWidget(self.btn_refresh)

        # Settings button
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setObjectName("btnIcon")
        self.btn_settings.setToolTip("Настройки")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.clicked.connect(self.open_settings)
        header.addWidget(self.btn_settings)

        main_layout.addLayout(header)

        # 2. Sense Bank Mode Switcher («Онлайн», «В отделении», «По карте»)
        mode_frame = QFrame()
        mode_frame.setObjectName("modeBar")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(6, 6, 6, 6)
        mode_layout.setSpacing(8)

        lbl_mode = QLabel("Режим Sense Bank:")
        lbl_mode.setStyleSheet("color: #8C93A6; font-size: 11px; font-weight: 600; margin-left: 6px;")
        mode_layout.addWidget(lbl_mode)

        self.mode_group = QButtonGroup(self)

        modes = [
            ("online", "📱 Онлайн (SuperApp)"),
            ("department", "🏛 В отделении"),
            ("card", "💳 По карте")
        ]

        for code, name in modes:
            rb = QRadioButton(name)
            rb.setObjectName(f"mode_{code}")
            rb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if code == "online":
                rb.setChecked(True)
            self.mode_group.addButton(rb)
            mode_layout.addWidget(rb)
            rb.toggled.connect(lambda checked, c=code: self.on_mode_changed(c, checked))

        mode_layout.addStretch()
        main_layout.addWidget(mode_frame)

        # 3. Bank Rate Cards: Buy, Sell, Spread
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_buy = ClickableRateCard("Покупка USD", "Банк покупает у вас", accent_color="#00C389")
        self.card_sell = ClickableRateCard("Продажа USD", "Банк продает вам", accent_color="#38BDF8")
        self.card_spread = ClickableRateCard("Спред (разница)", "Разница продажи и покупки", accent_color="#FBBF24")

        cards_layout.addWidget(self.card_buy)
        cards_layout.addWidget(self.card_sell)
        cards_layout.addWidget(self.card_spread)
        main_layout.addLayout(cards_layout)

        # 4. NBU Official Rate Card
        self.nbu_card = QFrame()
        self.nbu_card.setObjectName("nbuCard")
        self.nbu_card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.nbu_card.mousePressEvent = self.copy_nbu_rate

        nbu_layout = QHBoxLayout(self.nbu_card)
        nbu_layout.setContentsMargins(18, 12, 18, 12)

        nbu_left = QVBoxLayout()
        nbu_left.setSpacing(2)
        self.lbl_nbu_title = QLabel("Официальный курс НБУ")
        self.lbl_nbu_title.setStyleSheet("color: #8C93A6; font-size: 11px; font-weight: 600; text-transform: uppercase;")
        nbu_left.addWidget(self.lbl_nbu_title)

        self.lbl_nbu_rate = QLabel("— ₴")
        self.lbl_nbu_rate.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_nbu_rate.setStyleSheet("color: #E2E8F0;")
        nbu_left.addWidget(self.lbl_nbu_rate)

        self.lbl_nbu_date = QLabel("Дата курса: —")
        self.lbl_nbu_date.setStyleSheet("color: #727B8E; font-size: 11px;")
        nbu_left.addWidget(self.lbl_nbu_date)

        nbu_layout.addLayout(nbu_left)
        nbu_layout.addStretch()

        nbu_right = QVBoxLayout()
        nbu_right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        nbu_right.setSpacing(4)

        self.lbl_nbu_delta = QLabel("—")
        self.lbl_nbu_delta.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_nbu_delta.setStyleSheet("color: #00C389;")
        nbu_right.addWidget(self.lbl_nbu_delta)

        self.lbl_nbu_copy_hint = QLabel("📋 Нажмите для копирования")
        self.lbl_nbu_copy_hint.setStyleSheet("color: #555E70; font-size: 10px;")
        nbu_right.addWidget(self.lbl_nbu_copy_hint)

        nbu_layout.addLayout(nbu_right)
        main_layout.addWidget(self.nbu_card)

        # 5. Chart 30 days
        chart_header = QHBoxLayout()
        lbl_chart = QLabel("Динамика официального курса НБУ за 30 дней")
        lbl_chart.setStyleSheet("color: #A0AABF; font-size: 12px; font-weight: 600;")
        chart_header.addWidget(lbl_chart)
        chart_header.addStretch()

        self.lbl_chart_summary = QLabel("Мин: — · Макс: —")
        self.lbl_chart_summary.setStyleSheet("color: #727B8E; font-size: 11px;")
        chart_header.addWidget(self.lbl_chart_summary)

        main_layout.addLayout(chart_header)

        self.chart_widget = CurrencyChartWidget()
        main_layout.addWidget(self.chart_widget, 1)

        # 6. Fallback warning banner (hidden by default)
        self.banner_fallback = QLabel("⚠️ Sense Bank временно недоступен. Отображаются курсы ПриватБанка")
        self.banner_fallback.setStyleSheet("""
            background-color: #3B2A15;
            color: #FBBF24;
            border: 1px solid #784C0F;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.banner_fallback.setVisible(False)
        main_layout.addWidget(self.banner_fallback)

        # 7. Footer
        footer = QHBoxLayout()
        self.lbl_updated_at = QLabel("Обновление данных...")
        self.lbl_updated_at.setStyleSheet("color: #727B8E; font-size: 11px;")
        footer.addWidget(self.lbl_updated_at)
        footer.addStretch()

        self.lbl_next_update = QLabel("Следующее обновление через: --:--")
        self.lbl_next_update.setStyleSheet("color: #5A6275; font-size: 11px;")
        footer.addWidget(self.lbl_next_update)

        main_layout.addLayout(footer)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("USD / UAH Монитор курсов")

        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1E212A;
                color: #FFFFFF;
                border: 1px solid #2F3342;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #00C389;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2F3342;
                margin: 4px 6px;
            }
        """)

        # Rate preview item
        self.tray_item_rate = QAction("USD: Загрузка...", self)
        self.tray_item_rate.setEnabled(False)
        self.tray_menu.addAction(self.tray_item_rate)

        self.tray_item_nbu = QAction("НБУ: Загрузка...", self)
        self.tray_item_nbu.setEnabled(False)
        self.tray_menu.addAction(self.tray_item_nbu)

        self.tray_menu.addSeparator()

        act_show = QAction("Показать окно", self)
        act_show.triggered.connect(self.restore_window)
        self.tray_menu.addAction(act_show)

        act_refresh = QAction("🔄 Обновить сейчас (F5)", self)
        act_refresh.triggered.connect(self.start_fetch)
        self.tray_menu.addAction(act_refresh)

        act_settings = QAction("⚙ Настройки...", self)
        act_settings.triggered.connect(self.open_settings)
        self.tray_menu.addAction(act_settings)

        self.tray_menu.addSeparator()

        act_sense = QAction("🌐 Сайт Sense Bank", self)
        act_sense.triggered.connect(lambda: webbrowser.open("https://sensebank.ua/currency-exchange"))
        self.tray_menu.addAction(act_sense)

        act_nbu = QAction("🌐 Официальный сайт НБУ", self)
        act_nbu.triggered.connect(lambda: webbrowser.open("https://bank.gov.ua"))
        self.tray_menu.addAction(act_nbu)

        self.tray_menu.addSeparator()

        act_quit = QAction("❌ Выход", self)
        act_quit.triggered.connect(self.quit_application)
        self.tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def init_shortcuts(self):
        f5 = QShortcut(QKeySequence("F5"), self)
        f5.activated.connect(self.start_fetch)

    def init_timers(self):
        # 1-second countdown timer for UI updates
        self.timer_second = QTimer(self)
        self.timer_second.timeout.connect(self.on_second_tick)
        self.timer_second.start(1000)

        # Retry timer (5 min on network error)
        self.timer_retry = QTimer(self)
        self.timer_retry.setSingleShot(True)
        self.timer_retry.timeout.connect(self.start_fetch)

    def on_second_tick(self):
        if self.is_fetching:
            return

        self.seconds_until_update -= 1
        if self.seconds_until_update <= 0:
            self.start_fetch()
        else:
            mins = self.seconds_until_update // 60
            secs = self.seconds_until_update % 60
            self.lbl_next_update.setText(f"Следующее обновление через: {mins:02d}:{secs:02d}")

    def start_fetch(self):
        if self.is_fetching:
            return

        self.is_fetching = True
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("🔄 Загрузка...")
        self.badge_status.setText("● Загрузка данных...")
        self.badge_status.setStyleSheet("""
            background-color: #212530;
            color: #38BDF8;
            border: 1px solid #2F3647;
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)

        self.worker = FetchWorker()
        self.worker.finished.connect(self.on_fetch_success)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()

    def on_fetch_success(self, data):
        self.is_fetching = False
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄 Обновить (F5)")
        self.current_data = data

        interval_m = self.settings.get("update_interval_minutes", 60)
        self.seconds_until_update = interval_m * 60

        is_offline = data.get("is_offline", False)
        is_fallback = data.get("is_fallback", False)
        bank_source = data.get("bank_source", "Sense Bank")

        # Update status badge
        if is_offline:
            self.badge_status.setText("● Офлайн-режим")
            self.badge_status.setStyleSheet("""
                background-color: #352125;
                color: #FF4D4F;
                border: 1px solid #572A2E;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            """)
        else:
            self.badge_status.setText("● Онлайн")
            self.badge_status.setStyleSheet("""
                background-color: #172B23;
                color: #00C389;
                border: 1px solid #1D4B39;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            """)

        # Fallback banner
        if is_fallback:
            self.lbl_bank_source.setText(f"Источник: {bank_source}")
            self.banner_fallback.setText("⚠️ Sense Bank временно недоступен. Отображаются курсы ПриватБанка")
            self.banner_fallback.setVisible(True)
        else:
            self.lbl_bank_source.setText("Источник: Sense Bank (официальный)")
            self.banner_fallback.setVisible(False)

        # Update cards and chart
        self.update_rates_view()

        # Update chart
        nbu_hist = data.get("nbu", {}).get("history", [])
        self.chart_widget.set_history(nbu_hist)

        if nbu_hist:
            rates = [x['rate'] for x in nbu_hist]
            min_r = min(rates)
            max_r = max(rates)
            span = max_r - min_r
            self.lbl_chart_summary.setText(f"Мин: {min_r:.2f} ₴  ·  Макс: {max_r:.2f} ₴  ·  Размах: {span:.2f} ₴")

        # Footer update
        self.lbl_updated_at.setText(f"Обновлено: {data.get('updated_at', '')}")

        # Check notification
        self.check_rate_notifications(data)

    def on_fetch_error(self, err_msg):
        self.is_fetching = False
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄 Обновить (F5)")

        self.badge_status.setText("● Ошибка сети")
        self.badge_status.setStyleSheet("""
            background-color: #352125;
            color: #FF4D4F;
            border: 1px solid #572A2E;
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)

        self.lbl_updated_at.setText(f"Ошибка соединения. Повтор через 5 минут.")
        self.seconds_until_update = 300  # 5 minutes
        self.timer_retry.start(300 * 1000)

    def on_mode_changed(self, mode, checked):
        if checked:
            self.current_mode = mode
            self.update_rates_view()

    def update_rates_view(self):
        if not self.current_data:
            return

        bank_rates = self.current_data.get("bank_rates", {})
        mode_data = bank_rates.get(self.current_mode, {})

        buy = mode_data.get("buy", 0.0)
        sell = mode_data.get("sell", 0.0)

        mode_name_map = {
            "online": "в приложении SuperApp",
            "department": "в кассах отделений",
            "card": "при оплате картой"
        }
        sub = mode_name_map.get(self.current_mode, "")

        self.card_buy.set_rate(buy, sub_text=f"Курс {sub}")
        self.card_sell.set_rate(sell, sub_text=f"Курс {sub}")

        if sell > 0 and buy > 0:
            spread = round(sell - buy, 2)
            spread_pct = round((spread / buy) * 100, 2)
            self.card_spread.set_rate(spread, sub_text=f"Маржа: {spread_pct}%")
        else:
            self.card_spread.set_rate(0.0, sub_text="—")

        # NBU Rate
        nbu = self.current_data.get("nbu", {})
        nbu_rate = nbu.get("rate", 0.0)
        nbu_date = nbu.get("date", "")
        nbu_delta = nbu.get("delta", 0.0)
        nbu_pct = nbu.get("delta_percent", 0.0)

        self.lbl_nbu_rate.setText(f"{nbu_rate:.4f} ₴")
        self.lbl_nbu_date.setText(f"Официальный курс НБУ на {nbu_date}")

        sign = "+" if nbu_delta > 0 else ""
        arrow = "▲" if nbu_delta > 0 else ("▼" if nbu_delta < 0 else "●")
        delta_color = "#00C389" if nbu_delta >= 0 else "#FF4D4F"
        self.lbl_nbu_delta.setText(f"{arrow} {sign}{nbu_delta:.4f} ₴ ({sign}{nbu_pct}%)")
        self.lbl_nbu_delta.setStyleSheet(f"color: {delta_color}; font-size: 13px; font-weight: bold;")

        # Update Tray menu items
        mode_label = "Онлайн" if self.current_mode == "online" else ("Отделение" if self.current_mode == "department" else "Карта")
        bank_name = "Sense Bank" if not self.current_data.get("is_fallback") else "ПриватБанк"
        self.tray_item_rate.setText(f"USD ({mode_label}): {buy:.2f} / {sell:.2f} ({bank_name})")
        self.tray_item_nbu.setText(f"НБУ: {nbu_rate:.4f} ₴ ({arrow} {sign}{nbu_delta:.4f})")
        self.tray_icon.setToolTip(f"USD: {buy:.2f} / {sell:.2f} | НБУ: {nbu_rate:.4f} ₴")

    def copy_nbu_rate(self, event):
        if not self.current_data:
            return
        rate = self.current_data.get("nbu", {}).get("rate", 0.0)
        if rate > 0:
            rate_str = f"{rate:.4f}"
            clipboard = QApplication.clipboard()
            clipboard.setText(rate_str)

            self.lbl_nbu_copy_hint.setText("✓ Скопировано в буфер!")
            self.lbl_nbu_copy_hint.setStyleSheet("color: #00C389; font-weight: bold; font-size: 10px;")
            QTimer.singleShot(1800, lambda: (
                self.lbl_nbu_copy_hint.setText("📋 Нажмите для копирования"),
                self.lbl_nbu_copy_hint.setStyleSheet("color: #555E70; font-size: 10px;")
            ))

            pos = self.nbu_card.mapToGlobal(QPoint(self.nbu_card.width() // 2, 0))
            QToolTip.showText(pos, f"Официальный курс НБУ {rate_str} ₴ скопирован!", self.nbu_card, QPoint(), 1800)

    def check_rate_notifications(self, data):
        """
        Shows tray notification if rate changed by >= notification_threshold (default 0.04 UAH).
        """
        if not self.settings.get("notifications_enabled", True):
            return

        threshold = self.settings.get("notification_threshold", 0.04)

        online_rates = data.get("bank_rates", {}).get("online", {})
        cur_buy = online_rates.get("buy", 0.0)
        cur_sell = online_rates.get("sell", 0.0)

        last_buy = self.settings.get("last_notified_buy")
        last_sell = self.settings.get("last_notified_sell")

        if last_buy is not None and last_sell is not None:
            diff_buy = round(cur_buy - last_buy, 2)
            diff_sell = round(cur_sell - last_sell, 2)

            if abs(diff_buy) >= threshold or abs(diff_sell) >= threshold:
                sign_b = "+" if diff_buy > 0 else ""
                sign_s = "+" if diff_sell > 0 else ""
                title = "Изменение курса доллара!"
                msg = f"Sense Bank USD (Онлайн):\nПокупка: {cur_buy:.2f} ₴ ({sign_b}{diff_buy:.2f})\nПродажа: {cur_sell:.2f} ₴ ({sign_s}{diff_sell:.2f})"
                self.tray_icon.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 6000)

                self.settings["last_notified_buy"] = cur_buy
                self.settings["last_notified_sell"] = cur_sell
                save_settings(self.settings)
        else:
            # First run, record initial rates
            self.settings["last_notified_buy"] = cur_buy
            self.settings["last_notified_sell"] = cur_sell
            save_settings(self.settings)

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.get_settings()
            save_settings(self.settings)

            # Re-sync update interval
            interval_m = self.settings.get("update_interval_minutes", 60)
            self.seconds_until_update = interval_m * 60

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore_window()

    def restore_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized() and self.settings.get("minimize_to_tray", True):
                QTimer.singleShot(0, self.hide)
                event.ignore()
                return
        super().changeEvent(event)

    def closeEvent(self, event):
        if self.settings.get("close_to_tray", True):
            event.ignore()
            self.hide()

            if not self.first_close_warning_shown:
                self.first_close_warning_shown = True
                self.tray_icon.showMessage(
                    "USD / UAH Монитор свернут",
                    "Приложение продолжает работать в системном трее. Выход доступен через меню трея.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )
        else:
            self.quit_application()

    def quit_application(self):
        self.tray_icon.hide()
        QApplication.quit()

    def apply_dark_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #12141A;
            }
            QWidget {
                color: #FFFFFF;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            QFrame#modeBar {
                background-color: #1A1D26;
                border: 1px solid #282C3A;
                border-radius: 8px;
            }
            QRadioButton {
                color: #A0AABF;
                font-size: 12px;
                padding: 4px 8px;
            }
            QRadioButton:hover {
                color: #FFFFFF;
            }
            QRadioButton:checked {
                color: #00C389;
                font-weight: bold;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid #3F4457;
                background-color: #21242E;
            }
            QRadioButton::indicator:checked {
                border-color: #00C389;
                background-color: #00C389;
            }
            QFrame#rateCard {
                background-color: #1A1D26;
                border: 1px solid #262B38;
                border-radius: 10px;
            }
            QFrame#rateCard:hover {
                border-color: #3B4256;
                background-color: #1E222D;
            }
            QFrame#nbuCard {
                background-color: #1A1D26;
                border: 1px solid #262B38;
                border-radius: 10px;
            }
            QFrame#nbuCard:hover {
                border-color: #3B4256;
                background-color: #1E222D;
            }
            QPushButton#btnAction {
                background-color: #212530;
                color: #E2E8F0;
                border: 1px solid #313848;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#btnAction:hover {
                background-color: #2A303F;
                border-color: #00C389;
                color: #00C389;
            }
            QPushButton#btnAction:disabled {
                color: #555E70;
                border-color: #262B38;
            }
            QPushButton#btnIcon {
                background-color: #212530;
                color: #E2E8F0;
                border: 1px solid #313848;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnIcon:hover {
                background-color: #2A303F;
                border-color: #00C389;
            }
            QToolTip {
                background-color: #20242F;
                color: #FFFFFF;
                border: 1px solid #3B4256;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)
