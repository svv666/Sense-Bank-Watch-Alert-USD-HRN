import sys
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

def create_app_icon():
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Rounded rectangle background with dark gradient
        radius = size * 0.22
        rect = QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(24, 28, 38))
        grad.setColorAt(1.0, QColor(10, 12, 18))
        p.setBrush(QBrush(grad))

        border_pen = QPen(QColor(0, 195, 137, 180), max(1.0, size * 0.04))
        p.setPen(border_pen)
        p.drawRoundedRect(rect, radius, radius)

        # Draw a subtle upward trend chart line in the background
        chart_path = QPainterPath()
        p1 = QPointF(size * 0.15, size * 0.75)
        c1 = QPointF(size * 0.40, size * 0.70)
        c2 = QPointF(size * 0.60, size * 0.40)
        p2 = QPointF(size * 0.85, size * 0.25)
        chart_path.moveTo(p1)
        chart_path.cubicTo(c1, c2, p2)

        chart_pen = QPen(QColor(0, 195, 137, 100), max(1.5, size * 0.05))
        p.strokePath(chart_path, chart_pen)

        # Draw USD symbol $
        font_size = int(size * 0.52)
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        text_rect = QRectF(0, size * 0.05, size, size * 0.7)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "$")

        # Draw small UAH symbol ₴
        sub_font_size = int(size * 0.26)
        sub_font = QFont("Segoe UI", sub_font_size, QFont.Weight.DemiBold)
        p.setFont(sub_font)
        p.setPen(QColor(0, 195, 137))
        sub_rect = QRectF(0, size * 0.52, size, size * 0.4)
        p.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "₴")

        p.end()
        images.append(img)

    # Save 256 as png
    images[-1].save("icon.png")

    # Save ico using PIL if available, or write custom ICO format
    # Simple multi-resolution ICO writer
    with open("icon.ico", "wb") as f:
        # ICO Header
        f.write((0).to_bytes(2, "little")) # Reserved
        f.write((1).to_bytes(2, "little")) # ICO type
        f.write(len(images).to_bytes(2, "little")) # Number of images

        # We will store PNG encoded images in ICO (standard since Vista/Win7)
        png_data_list = []
        for img in images:
            from PySide6.QtCore import QByteArray, QBuffer, QIODevice
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            img.save(buf, "PNG")
            png_data_list.append(ba.data())

        offset = 6 + len(images) * 16
        for i, s in enumerate(sizes):
            w = 0 if s == 256 else s
            h = 0 if s == 256 else s
            data = png_data_list[i]
            size_bytes = len(data)
            f.write(w.to_bytes(1, "little"))
            f.write(h.to_bytes(1, "little"))
            f.write((0).to_bytes(1, "little")) # Colors
            f.write((0).to_bytes(1, "little")) # Reserved
            f.write((1).to_bytes(2, "little")) # Color planes
            f.write((32).to_bytes(2, "little")) # Bits per pixel
            f.write(size_bytes.to_bytes(4, "little"))
            f.write(offset.to_bytes(4, "little"))
            offset += size_bytes

        for data in png_data_list:
            f.write(data)

    print("Icons generated: icon.png, icon.ico")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    create_app_icon()
