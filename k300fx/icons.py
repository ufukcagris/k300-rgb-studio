"""Uygulama ve efekt simgeleri (hepsi kodla cizilir, dosya gerekmez)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

def app_icon() -> QIcon:
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, 256, 256)
    bg.setColorAt(0, QColor("#1a1d2b"))
    bg.setColorAt(1, QColor("#0d0e13"))
    p.setPen(Qt.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(8, 8, 240, 240, 56, 56)
    for i, c in enumerate(("#ff2a6d", "#ffb000", "#27e08a", "#22d3ee", "#7c5cff")):
        p.setBrush(QColor(c))
        p.drawRoundedRect(36 + i * 38, 58, 28, 140, 14, 14)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------- efekt simgeleri
# Her simge 40x40'lik bir birim karede, beyaz cizgi/dolgu ile cizilir; karo gradyani uzerine biner.
def _wp(a: int = 255, w: float = 2.4) -> QPen:
    return QPen(QColor(255, 255, 255, a), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _white(p: QPainter, a: int = 255) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, a))


def _g_ripple(p, S, w):
    """Tustan yayilan dalga: bir noktadan genisleyen, soluklasan halkalar."""
    c = QPointF(13 * S, 25 * S)
    for rad, a in ((6, 255), (13, 205), (21, 140), (29, 80)):
        p.setPen(_wp(a, w))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, rad * S, rad * S)
    _white(p)
    p.drawEllipse(c, 3 * S, 3 * S)


def _g_glow(p, S, w):
    """Basis parlamasi: tus kapagi + ustunden saclan isik."""
    halo = QRadialGradient(QPointF(20 * S, 24 * S), 20 * S)
    halo.setColorAt(0, QColor(255, 255, 255, 150))
    halo.setColorAt(1, QColor(255, 255, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(halo)
    p.drawEllipse(QPointF(20 * S, 24 * S), 20 * S, 20 * S)
    p.setPen(_wp(255, w))
    p.setBrush(QColor(255, 255, 255, 45))
    p.drawRoundedRect(QRectF(10 * S, 17 * S, 20 * S, 17 * S), 4 * S, 4 * S)
    p.drawLine(QPointF(14 * S, 22 * S), QPointF(26 * S, 22 * S))
    for x1, y1, x2, y2 in ((20, 12, 20, 6), (12.5, 13.5, 9, 9.5), (27.5, 13.5, 31, 9.5)):
        p.drawLine(QPointF(x1 * S, y1 * S), QPointF(x2 * S, y2 * S))


def _g_flow(p, S, w):
    """Akis: yan yana akan uc dalgali serit."""
    import math as _m
    for base, a, ph in ((12, 255, 0.0), (20, 190, 1.3), (28, 120, 2.6)):
        path = QPainterPath()
        for i in range(0, 31):
            x = 6 + i
            y = base + 3.2 * _m.sin(i / 30 * 2 * _m.pi + ph)
            (path.moveTo if i == 0 else path.lineTo)(QPointF(x * S, y * S))
        p.setPen(_wp(a, w * 1.1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


def _g_drift(p, S, w):
    """Surukleme: sagdan sola suzulen noktalar."""
    for i, (x, y, a) in enumerate(((10, 14, 255), (18, 22, 200), (26, 14, 150), (34, 22, 100), (14, 30, 170), (30, 30, 230))):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, a))
        p.drawEllipse(QPointF(x * S, y * S), 3.2 * S, 3.2 * S)


def _g_breathe(p, S, w):
    """Nefes: yumusak genisleyip daralan isik topu."""
    halo = QRadialGradient(QPointF(20 * S, 20 * S), 19 * S)
    halo.setColorAt(0, QColor(255, 255, 255, 255))
    halo.setColorAt(0.38, QColor(255, 255, 255, 230))
    halo.setColorAt(0.42, QColor(255, 255, 255, 120))
    halo.setColorAt(1, QColor(255, 255, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(halo)
    p.drawEllipse(QPointF(20 * S, 20 * S), 19 * S, 19 * S)


def _g_aurora(p, S, w):
    """Aurora: yukari dogru sonen dalgali isik perdeleri + yildizlar."""
    for x, top, a in ((10, 12, 235), (16.5, 7, 255), (23, 10, 245), (29.5, 14, 220)):
        g = QLinearGradient(0, top * S, 0, 34 * S)
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.55, QColor(255, 255, 255, a))
        g.setColorAt(1, QColor(255, 255, 255, 90))
        path = QPainterPath()
        path.moveTo((x - 2.4) * S, 34 * S)
        path.cubicTo((x - 4) * S, 24 * S, (x + 2) * S, 18 * S, (x - 0.5) * S, top * S)
        path.cubicTo((x + 3.5) * S, 17 * S, (x + 5) * S, 26 * S, (x + 2.4) * S, 34 * S)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(path)
    _white(p, 230)
    for x, y, r in ((7, 8, 1.1), (33, 10, 1.4), (27, 5, 0.9)):
        p.drawEllipse(QPointF(x * S, y * S), r * S, r * S)


def _g_fire(p, S, w):
    """Ates: alev, ortasinda daha koyu ic alev."""
    path = QPainterPath()

    def m(x, y):
        return QPointF(x * S, y * S)
    path.moveTo(m(20, 4))
    path.cubicTo(m(28, 12), m(33, 20), m(30, 27))
    path.cubicTo(m(28.5, 32), m(24, 35), m(20, 35))
    path.cubicTo(m(15, 35), m(10, 31), m(10, 25))
    path.cubicTo(m(10, 20), m(14, 17), m(15.5, 12))
    path.cubicTo(m(17.5, 15), m(19, 16), m(21, 15))
    path.cubicTo(m(22, 11), m(18, 8), m(20, 4))
    path.closeSubpath()
    _white(p, 255)
    p.drawPath(path)
    inner = QPainterPath()
    inner.moveTo(m(20, 22))
    inner.cubicTo(m(25, 27), m(24, 33), m(20, 33))
    inner.cubicTo(m(16, 33), m(15, 28), m(20, 22))
    p.setBrush(QColor(255, 140, 0, 190))
    p.drawPath(inner)


def _g_static(p, S, w):
    """Sabit renk: 5 bolge = 5 dikey cubuk."""
    for i in range(5):
        _white(p, 255 - i * 22)
        p.drawRoundedRect(QRectF((6 + i * 6.3) * S, 9 * S, 4.6 * S, 22 * S), 2.3 * S, 2.3 * S)


def _g_audio(p, S, w):
    """Ses tepkili: ekolayzer cubuklari."""
    for i, h in enumerate((11, 19, 27, 17, 9)):
        _white(p, 255 - abs(i - 2) * 25)
        p.drawRoundedRect(QRectF((6 + i * 6.3) * S, (33 - h) * S, 4.6 * S, h * S), 2.3 * S, 2.3 * S)


def _g_heat(p, S, w):
    """Yazma hizi isisi: termometre."""
    p.setPen(_wp(255, w))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(16.5 * S, 6 * S, 7 * S, 20 * S), 3.5 * S, 3.5 * S)
    _white(p)
    p.drawEllipse(QPointF(20 * S, 29.5 * S), 6.6 * S, 6.6 * S)
    p.drawRoundedRect(QRectF(18.3 * S, 14 * S, 3.4 * S, 16 * S), 1.7 * S, 1.7 * S)
    p.setPen(_wp(190, w * 0.8))
    for y in (10, 15, 20):
        p.drawLine(QPointF(27 * S, y * S), QPointF(31 * S, y * S))


def _g_load(p, S, w):
    """Sistem yuku: olcer + ibre."""
    import math as _m
    c = QPointF(20 * S, 22 * S)
    r = QRectF(c.x() - 14 * S, c.y() - 14 * S, 28 * S, 28 * S)
    p.setBrush(Qt.NoBrush)
    p.setPen(_wp(110, w * 1.3))
    p.drawArc(r, 210 * 16, -240 * 16)
    p.setPen(_wp(255, w * 1.3))
    p.drawArc(r, 210 * 16, int(-240 * 0.7 * 16))
    th = _m.radians(210 - 240 * 0.7)
    p.setPen(_wp(255, w))
    p.drawLine(c, QPointF(c.x() + 10 * S * _m.cos(th), c.y() - 10 * S * _m.sin(th)))
    _white(p)
    p.drawEllipse(c, 2.6 * S, 2.6 * S)


EFFECT_GLYPHS = {
    "Tuştan yayılan dalga": _g_ripple, "Basış parlaması": _g_glow, "Sörf": _g_flow, "Sürükleme": _g_drift,
    "Nefes": _g_breathe, "Aurora": _g_aurora, "Ateş": _g_fire, "Sabit renk": _g_static,
    "Ses tepkili": _g_audio, "Yazma hızı ısısı": _g_heat, "Sistem yükü": _g_load,
}


def paint_tile(p: QPainter, rect: QRectF, cls, radius: float = 0.28) -> None:
    """Efekt simgesi: gradyanli yuvarlak karo + o efekte ozel beyaz cizim."""
    a0, a1 = cls.accent
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor(*a0))
    g.setColorAt(1, QColor(*a1))
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(rect, rect.width() * radius, rect.width() * radius)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawPath(clip)
    p.setClipPath(clip)
    p.translate(rect.topLeft())
    S = rect.width() / 40.0
    fn = EFFECT_GLYPHS.get(cls.name)
    if fn:
        fn(p, S, 2.4 * S)
    p.restore()


class IconTile(QWidget):
    def __init__(self, size: int = 52) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self.cls = None

    def set_effect(self, cls) -> None:
        self.cls = cls
        self.update()

    def paintEvent(self, _e) -> None:
        if self.cls is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint_tile(p, QRectF(self.rect()), self.cls)
