import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QLinearGradient,
    QPainterPath, QMouseEvent
)
from PySide6.QtCore import Qt, QRectF, QPointF

class CurrencyChartWidget(QWidget):
    """
    Modern high-DPI interactive 30-day currency trend chart widget
    with smooth bezier curves, glowing area gradients, and rich hover tooltips.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(190)

        self.history = []  # list of {'date': '...', 'short_date': '...', 'rate': float}
        self.hovered_index = -1
        self.hover_point = None

        # Colors
        self.bg_color = QColor(24, 26, 33)
        self.grid_color = QColor(42, 46, 58)
        self.text_color = QColor(140, 147, 166)
        self.accent_color = QColor(0, 195, 137)       # Bright Emerald/Teal
        self.accent_red = QColor(255, 77, 79)
        self.tooltip_bg = QColor(32, 36, 47, 240)
        self.tooltip_border = QColor(64, 72, 94)

    def set_history(self, history):
        self.history = history or []
        self.hovered_index = -1
        self.hover_point = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.history or len(self.history) < 2:
            return

        pos = event.position()
        w = self.width()
        padding_l = 48.0
        padding_r = 20.0
        chart_w = w - padding_l - padding_r

        if chart_w <= 0:
            return

        x = pos.x()
        if x < padding_l:
            x = padding_l
        elif x > w - padding_r:
            x = w - padding_r

        rel_x = (x - padding_l) / chart_w
        idx = int(round(rel_x * (len(self.history) - 1)))
        idx = max(0, min(len(self.history) - 1, idx))

        if idx != self.hovered_index:
            self.hovered_index = idx
            self.update()

    def leaveEvent(self, event):
        self.hovered_index = -1
        self.hover_point = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Draw widget background with subtle rounded border
        card_rect = QRectF(0, 0, w, h)
        painter.setPen(QPen(QColor(36, 40, 52), 1))
        painter.setBrush(QBrush(self.bg_color))
        painter.drawRoundedRect(card_rect, 10, 10)

        if not self.history or len(self.history) < 2:
            painter.setPen(self.text_color)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, "Загрузка данных графика...")
            painter.end()
            return

        padding_l = 52.0
        padding_r = 24.0
        padding_t = 26.0
        padding_b = 32.0

        chart_w = w - padding_l - padding_r
        chart_h = h - padding_t - padding_b

        if chart_w <= 10 or chart_h <= 10:
            painter.end()
            return

        rates = [item['rate'] for item in self.history]
        min_rate = min(rates)
        max_rate = max(rates)

        # Add 10% breathing room to Y axis
        rate_range = max_rate - min_rate
        if rate_range <= 0.0001:
            rate_range = 0.1
        margin = rate_range * 0.12
        y_min = min_rate - margin
        y_max = max_rate + margin

        # Draw Horizontal Grid Lines & Y-axis labels
        painter.setFont(QFont("Segoe UI", 9))
        num_grid_lines = 4
        for i in range(num_grid_lines + 1):
            val = y_min + (y_max - y_min) * (i / num_grid_lines)
            y_pos = padding_t + chart_h - (i / num_grid_lines) * chart_h

            painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(padding_l, y_pos), QPointF(w - padding_r, y_pos))

            painter.setPen(self.text_color)
            text_rect = QRectF(2, y_pos - 8, padding_l - 8, 16)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{val:.2f}")

        # Compute point coordinates
        points = []
        n = len(self.history)
        for i, item in enumerate(self.history):
            px = padding_l + (i / (n - 1)) * chart_w
            py = padding_t + chart_h - ((item['rate'] - y_min) / (y_max - y_min)) * chart_h
            points.append(QPointF(px, py))

        # Check overall 30-day trend color
        is_up = self.history[-1]['rate'] >= self.history[0]['rate']
        line_color = self.accent_color if is_up else self.accent_red

        # Build smooth path using Cubic Bezier Spline
        curve_path = QPainterPath()
        curve_path.moveTo(points[0])

        for i in range(len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            # Catmull-Rom to Cubic Bezier conversion
            c1x = p1.x() + (p2.x() - p0.x()) / 6.0
            c1y = p1.y() + (p2.y() - p0.y()) / 6.0
            c2x = p2.x() - (p3.x() - p1.x()) / 6.0
            c2y = p2.y() - (p3.y() - p1.y()) / 6.0

            curve_path.cubicTo(QPointF(c1x, c1y), QPointF(c2x, c2y), p2)

        # Fill under curve with gradient
        fill_path = QPainterPath(curve_path)
        fill_path.lineTo(points[-1].x(), padding_t + chart_h)
        fill_path.lineTo(points[0].x(), padding_t + chart_h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, padding_t, 0, padding_t + chart_h)
        c_start = QColor(line_color.red(), line_color.green(), line_color.blue(), 75)
        c_end = QColor(line_color.red(), line_color.green(), line_color.blue(), 2)
        grad.setColorAt(0.0, c_start)
        grad.setColorAt(1.0, c_end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(fill_path)

        # Draw main curve
        painter.setPen(QPen(line_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve_path)

        # Draw X-axis date labels (e.g. 5 dates across 30 days)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(self.text_color)
        step = max(1, (n - 1) // 5)
        indices_to_label = list(range(0, n, step))
        if indices_to_label[-1] != n - 1:
            indices_to_label.append(n - 1)

        for idx in indices_to_label:
            pt = points[idx]
            d_text = self.history[idx].get('short_date', '')
            t_rect = QRectF(pt.x() - 25, padding_t + chart_h + 8, 50, 16)
            painter.drawText(t_rect, Qt.AlignmentFlag.AlignCenter, d_text)

        # Highlight Min and Max points
        min_idx = rates.index(min_rate)
        max_idx = rates.index(max_rate)

        # Draw hover state / crosshair and tooltip
        if 0 <= self.hovered_index < len(points):
            h_pt = points[self.hovered_index]
            h_data = self.history[self.hovered_index]

            # Crosshair vertical dashed line
            painter.setPen(QPen(QColor(160, 170, 195, 140), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(h_pt.x(), padding_t), QPointF(h_pt.x(), padding_t + chart_h))

            # Outer glowing halo
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(line_color.red(), line_color.green(), line_color.blue(), 70)))
            painter.drawEllipse(h_pt, 9, 9)

            # Inner bright point
            painter.setBrush(QBrush(line_color))
            painter.drawEllipse(h_pt, 4.5, 4.5)

            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(h_pt, 2, 2)

            # Draw Tooltip
            tooltip_text_date = f"{h_data.get('date', '')}"
            tooltip_text_rate = f"{h_data.get('rate', 0.0):.4f} ₴"

            # Delta calculation compared to prev day
            delta_str = ""
            if self.hovered_index > 0:
                p_rate = self.history[self.hovered_index - 1]['rate']
                d = h_data['rate'] - p_rate
                sign = "+" if d > 0 else ""
                delta_str = f" ({sign}{d:.4f})"

            tooltip_w = 135
            tooltip_h = 52

            # Tooltip placement (keep inside chart bounds)
            tx = h_pt.x() - tooltip_w / 2
            if tx < padding_l:
                tx = padding_l + 4
            elif tx + tooltip_w > w - padding_r:
                tx = w - padding_r - tooltip_w - 4

            ty = h_pt.y() - tooltip_h - 12
            if ty < padding_t:
                ty = h_pt.y() + 12

            t_rect = QRectF(tx, ty, tooltip_w, tooltip_h)

            painter.setPen(QPen(self.tooltip_border, 1.2))
            painter.setBrush(QBrush(self.tooltip_bg))
            painter.drawRoundedRect(t_rect, 6, 6)

            # Date in tooltip
            painter.setPen(QColor(160, 170, 190))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(tx + 8, ty + 6, tooltip_w - 16, 16), Qt.AlignmentFlag.AlignLeft, tooltip_text_date)

            # Rate in tooltip
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRectF(tx + 8, ty + 24, tooltip_w - 16, 20), Qt.AlignmentFlag.AlignLeft, tooltip_text_rate)

            if delta_str:
                d_color = self.accent_color if "+" in delta_str else self.accent_red
                painter.setPen(d_color)
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
                painter.drawText(QRectF(tx + 75, ty + 7, tooltip_w - 83, 16), Qt.AlignmentFlag.AlignRight, delta_str.strip(" ()"))

        painter.end()
