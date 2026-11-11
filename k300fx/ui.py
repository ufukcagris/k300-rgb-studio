"""PySide6 arayuzu: cercevesiz modern pencere, canli klavye onizlemesi, efekt kartlari."""
from __future__ import annotations

import ctypes
import sys
import time

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QConicalGradient, QFont, QFontMetrics, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QFormLayout,
    QHBoxLayout, QLabel, QListView, QMainWindow, QMenu, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QSystemTrayIcon, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__, autostart, i18n, layouts
from . import settings as cfg
from .about import AUTHOR, GITHUB_URL, LICENSE_NAME
from .effects import (CUSTOM, DEFAULT_ZONES, EFFECT_CLASSES, EFFECTS, RAINBOW, THEME_ORDER, ZONES,
                      hex_rgb, theme_rgb, theme_stops)
from .engine import Engine
from .i18n import tr
from .icons import IconTile, app_icon, paint_tile
from .tips import FancyTip

APP_NAME = "K300 RGB Stüdyo"

BG, SURFACE, SURFACE2 = "#0d0e13", "#151720", "#1c1f2c"
BORDER, TEXT, MUTED = "#262a3a", "#eceef7", "#8a90aa"
ACCENT, ACCENT2 = "#7c5cff", "#22d3ee"

QSS = f"""
* {{ font-family: 'Segoe UI Variable Display', 'Segoe UI'; font-size: 13px; color: {TEXT}; }}
QMainWindow, QDialog, QWidget#root {{ background: {BG}; }}
QWidget#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px; }}
QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
QLabel#apptitle {{ font-size: 14px; font-weight: 600; }}
QLabel#title {{ font-size: 22px; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#section {{ color: {MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#pill {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 13px; padding: 5px 14px; color: {MUTED}; }}
QPushButton {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px 16px; }}
QPushButton:hover {{ background: #252a3c; border-color: #343a52; }}
QPushButton#primary {{ background: {ACCENT}; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #8d70ff; }}
QComboBox {{ background: {SURFACE2}; border: 1px solid {BORDER}; border-radius: 10px; padding: 7px 12px; min-width: 150px; }}
QComboBox QAbstractItemView {{ background: {SURFACE2}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; outline: 0; }}
QComboBox::drop-down {{ border: 0; width: 22px; }}
QSlider::groove:horizontal {{ height: 6px; background: {SURFACE2}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2}); border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #fff; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}
QCheckBox {{ spacing: 10px; padding: 4px 0; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; border: 1px solid #3a4058; background: {SURFACE2}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c3146; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QTableWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; gridline-color: {BORDER}; }}
QHeaderView::section {{ background: {SURFACE2}; border: 0; padding: 7px; color: {MUTED}; }}
QToolTip {{ background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 8px; }}
"""

FAMILIES = ["Segoe UI Variable Display", "Segoe UI", "Segoe UI Symbol"]


def _font(px: int, weight: int = 400) -> QFont:
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(max(6, int(px)))
    f.setWeight(QFont.Weight(weight))
    return f


def apply_window_frame(widget: QWidget) -> None:
    """Cercevesiz pencere: sistem golgesi, yuvarlak koseler (Windows 11) ve kenarlik rengi."""
    if sys.platform != "win32":
        return
    try:
        class MARGINS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]
        hwnd, dwm = int(widget.winId()), ctypes.windll.dwmapi
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(1, 1, 1, 1)))        # golge
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)            # yuvarlak koseler
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(0x3A2A26)), 4)     # kenarlik #262a3a
    except Exception:   # noqa: BLE001
        pass


# ------------------------------------------------------------------ klavye onizleme
def _key_path(k: layouts.Key, s: float, ox: float, oy: float) -> QPainterPath:
    g, r = 0.07, 0.16 * s
    path = QPainterPath()
    if k.iso_enter:                                    # L seklindeki Turkce Enter
        top = QRectF(ox + (13.5 + g) * s, oy + (2.5 + g) * s, (1.5 - 2 * g) * s, (1 - 2 * g) * s)
        bot = QRectF(ox + (13.75 + g) * s, oy + (3.5 + g) * s, (1.25 - 2 * g) * s, (1 - 2 * g) * s)
        path.addRoundedRect(top, r, r)
        path.addRoundedRect(bot, r, r)
        path.addRect(QRectF(bot.x(), top.bottom() - 2 * r, bot.width(), (bot.top() - top.bottom()) + 4 * r))
        path.setFillRule(Qt.WindingFill)               # tek-cift kurali ust uste binen yeri oyar; birlestir
        return path.simplified()
    path.addRoundedRect(QRectF(ox + (k.x + g) * s, oy + (k.y + g) * s, (k.w - 2 * g) * s, (k.h - 2 * g) * s), r, r)
    return path


def _draw_legend(p: QPainter, k: layouts.Key, s: float, ox: float, oy: float) -> None:
    label = k.label
    if not label.strip():
        return
    x, y, w, h = ox + k.x * s, oy + k.y * s, k.w * s, k.h * s
    if k.iso_enter:
        x, y, w, h = ox + 13.75 * s, oy + 3.5 * s, 1.25 * s, 1.0 * s
    lines = label.split("\n")
    if len(lines) == 2:                                # ust: Shift ile, alt: normal
        pad = 0.17 * s
        p.setFont(_font(0.27 * s, 500))
        p.drawText(QRectF(x + pad, y + 0.08 * s, w - 2 * pad, 0.40 * s), Qt.AlignLeft | Qt.AlignVCenter, lines[0])
        p.setFont(_font(0.34 * s, 600))
        p.drawText(QRectF(x + pad, y + 0.46 * s, w - 2 * pad, 0.46 * s), Qt.AlignLeft | Qt.AlignVCenter, lines[1])
        return
    px = 0.40 * s if len(label) <= 1 else (0.30 * s if len(label) <= 3 else 0.25 * s)
    p.setFont(_font(px, 600))
    p.drawText(QRectF(x, y, w, h), Qt.AlignCenter, label)


class KeyboardView(QWidget):
    """Secili duzende gercek klavye: koyu tus kapaklari, aralardan sizan renkli isik, renkli harfler."""

    def __init__(self, layout: str = "tr") -> None:
        super().__init__()
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sp.setHeightForWidth(True)                     # sahne klavyenin en-boy oranini izler
        self.setSizePolicy(sp)
        self.setMinimumHeight(200)
        self.colors = [(30, 30, 40)] * ZONES
        self._layout = layout
        self._flash: dict[int, float] = {}
        self._cache: dict | None = None
        self._last = 0.0
        self._tick = QTimer(self, interval=33)
        self._tick.timeout.connect(self.update)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return int((w - 56) * layouts.TOTAL_H / layouts.TOTAL_W + 56)

    def set_layout(self, name: str) -> None:
        self._layout = name
        self._cache = None
        self._flash.clear()
        self.update()

    def set_colors(self, colors) -> None:
        self.colors = colors
        now = time.time()
        if now - self._last >= 0.03:                   # onizleme en fazla ~30 kare/sn cizilir
            self._last = now
            self.update()

    def flash(self, idx: int) -> None:
        if idx >= 0:
            self._flash[idx] = time.time()
            if not self._tick.isActive():
                self._tick.start()

    def _color_at(self, x: float) -> tuple:
        n = len(self.colors)                            # 5 bolge ya da donanim efektinde daha sik ornek
        p = max(0.0, min(n - 1.0, x * n - 0.5))
        i = int(p)
        j = min(n - 1, i + 1)
        f = p - i
        a, b = self.colors[i], self.colors[j]
        return tuple(a[c] + (b[c] - a[c]) * f for c in range(3))

    def _build(self) -> None:
        dpr = self.devicePixelRatioF()
        w, h = self.width(), self.height()
        s = min((w - 56) / layouts.TOTAL_W, (h - 56) / layouts.TOTAL_H)
        ox, oy = (w - layouts.TOTAL_W * s) / 2, (h - layouts.TOTAL_H * s) / 2
        keys = layouts.keys(self._layout)
        paths = [_key_path(k, s, ox, oy) for k in keys]

        def blank() -> QPixmap:
            pm = QPixmap(int(w * dpr), int(h * dpr))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            return pm
        caps = blank()                                 # tus kapaklari (aralar saydam kalir)
        p = QPainter(caps)
        p.setRenderHint(QPainter.Antialiasing)
        for path in paths:
            r = path.boundingRect()
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, QColor("#2b2e38"))
            g.setColorAt(1, QColor("#14161b"))
            p.setPen(QPen(QColor("#363a47"), 1))
            p.setBrush(g)
            p.drawPath(path)
            hl = QPainterPath()
            hl.addRoundedRect(QRectF(r.x() + 0.08 * s, r.y() + 0.05 * s, r.width() - 0.16 * s, r.height() * 0.28),
                              0.10 * s, 0.10 * s)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 13))
            p.drawPath(hl)
        p.end()
        masks = []                                     # bolge basina beyaz harf maskesi (renkle boyanir)
        for z in range(ZONES):
            m = blank()
            mp = QPainter(m)
            mp.setRenderHint(QPainter.Antialiasing)
            mp.setPen(QColor(255, 255, 255))
            for k in keys:
                if min(ZONES - 1, int(k.cx / layouts.TOTAL_W * ZONES)) == z:
                    _draw_legend(mp, k, s, ox, oy)
            mp.end()
            masks.append(m)
        self._cache = {"w": w, "h": h, "dpr": dpr, "layout": self._layout, "s": s, "ox": ox, "oy": oy,
                       "paths": paths, "caps": caps, "masks": masks}

    def paintEvent(self, _e) -> None:
        w, h, dpr = self.width(), self.height(), self.devicePixelRatioF()
        c = self._cache
        if c is None or (c["w"], c["h"], c["dpr"]) != (w, h, dpr):
            self._build()
            c = self._cache
        s, ox, oy = c["s"], c["ox"], c["oy"]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        stage = QPainterPath()
        stage.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 20, 20)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QColor("#08090d"))
        p.drawPath(stage)
        p.setClipPath(stage)
        avg = [sum(col[i] for col in self.colors) / len(self.colors) for i in range(3)]
        halo = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.55)      # genel isik halesi
        halo.setColorAt(0, QColor(int(avg[0]), int(avg[1]), int(avg[2]), 52))
        halo.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawRect(self.rect())
        body = QRectF(ox - 0.55 * s, oy - 0.55 * s, layouts.TOTAL_W * s + 1.1 * s, layouts.TOTAL_H * s + 1.1 * s)
        bg = QLinearGradient(body.topLeft(), body.bottomLeft())             # klavye govdesi
        bg.setColorAt(0, QColor("#202228"))
        bg.setColorAt(1, QColor("#15171b"))
        p.setPen(QPen(QColor("#2c2f3a"), 1))
        p.setBrush(bg)
        p.drawRoundedRect(body, 0.5 * s, 0.5 * s)
        keys = layouts.keys(self._layout)
        for k, path in zip(keys, c["paths"]):                              # tus aralarindan sizan isik
            col = self._color_at(k.cx / layouts.TOTAL_W)
            if max(col) < 6:
                continue
            p.setBrush(Qt.NoBrush)
            for width, alpha in ((0.55, 26), (0.34, 64), (0.17, 150)):
                p.setPen(QPen(QColor(int(col[0]), int(col[1]), int(col[2]), alpha), width * s,
                              Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(path)
        p.drawPixmap(0, 0, c["caps"])
        for z in range(ZONES):                                             # renkli harfler
            col = self._color_at((z + 0.5) / ZONES)
            leg = QColor(*(min(255, int(v * 0.85 + 70)) for v in col))
            tint = QPixmap(c["masks"][z])
            tp = QPainter(tint)
            tp.setCompositionMode(QPainter.CompositionMode_SourceIn)
            tp.fillRect(QRectF(0, 0, w, h), leg)
            tp.end()
            p.drawPixmap(0, 0, tint)
        now = time.time()                                                  # basilan tusun parlamasi
        alive: dict[int, float] = {}
        for idx, t0 in self._flash.items():
            age = now - t0
            if age > 0.45 or idx >= len(c["paths"]):
                continue
            alive[idx] = t0
            a = 1 - age / 0.45
            path = c["paths"][idx]
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(120 * a)))
            p.drawPath(path)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, int(190 * a)), 0.3 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(path)
        self._flash = alive
        if not alive:
            self._tick.stop()


# ---------------------------------------------------------------- efekt karti
class EffectCard(QAbstractButton):
    def __init__(self, cls) -> None:
        super().__init__()
        self.cls = cls
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self._hover = False

    # Kartta aciklama kisaltilir (...); tamami secince sagdaki panelde yazar, balon gerekmez.
    def enterEvent(self, e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, e) -> None:
        self._hover = False
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        on = self.isChecked()
        p.setPen(QPen(QColor(ACCENT if on else BORDER), 1.6 if on else 1))
        p.setBrush(QColor(SURFACE2 if on else ("#191c28" if self._hover else SURFACE)))
        p.drawRoundedRect(r, 14, 14)
        sw = QRectF(r.x() + 13, r.y() + (r.height() - 42) / 2, 42, 42)
        paint_tile(p, sw, self.cls)
        tx = sw.right() + 14
        width = r.right() - tx - 12
        p.setPen(QColor(TEXT))
        p.setFont(_font(14, 600))
        p.drawText(QRectF(tx, r.y() + 11, width, 22), Qt.AlignVCenter | Qt.AlignLeft, tr(self.cls.name))
        p.setPen(QColor(MUTED))
        f = _font(11)
        p.setFont(f)
        txt = QFontMetrics(f).elidedText(tr(self.cls.description), Qt.ElideRight, int(width))
        p.drawText(QRectF(tx, r.y() + 33, width, 22), Qt.AlignVCenter | Qt.AlignLeft, txt)


class CheckBox(QCheckBox):
    """Isaretli (✓) ozel cizimli onay kutusu; QSS ile isaret cizilemedigi icin elle cizilir."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(1, (self.height() - 20) / 2, 20, 20)
        on = self.isChecked()
        p.setPen(QPen(QColor(ACCENT if on else "#3a4058"), 1))
        p.setBrush(QColor(ACCENT if on else SURFACE2))
        p.drawRoundedRect(box, 6, 6)
        if on:
            p.setPen(QPen(QColor("#ffffff"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline([QPointF(box.x() + 5, box.y() + 10.5), QPointF(box.x() + 8.6, box.y() + 14),
                            QPointF(box.x() + 15, box.y() + 6.5)])
        p.setPen(QColor(TEXT))
        p.setFont(self.font())
        p.drawText(QRectF(32, 0, self.width() - 32, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


# ---------------------------------------------------------------- diyaloglar
class DialogBar(QWidget):
    """Diyalogun ozel baslik cubugu (ana pencerenin stiliyle ayni)."""
    H = 46

    def __init__(self, dlg: QDialog, title: str) -> None:
        super().__init__(dlg)
        self.dlg = dlg
        self.setFixedHeight(self.H)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 0, 0)
        lay.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(22, 22))
        icon.setFixedSize(22, 22)
        self.title = QLabel(title)
        self.title.setObjectName("apptitle")
        close = WinButton("close")
        close.setFixedSize(46, self.H)
        close.setToolTip(tr("Kapat"))
        close.clicked.connect(dlg.reject)
        lay.addWidget(icon)
        lay.addWidget(self.title)
        lay.addStretch(1)
        lay.addWidget(close)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.dlg.windowHandle():
            self.dlg.windowHandle().startSystemMove()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))
        p.setPen(QColor("#1a1d29"))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class BaseDialog(QDialog):
    """Cercevesiz diyalog: ozel baslik cubugu + `self.content` (icerik yerlesimi)."""

    def __init__(self, parent, title: str) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle(title)
        shell = QVBoxLayout(self)
        shell.setContentsMargins(1, 1, 1, 1)           # 1 px: kenarlik gorunsun
        shell.setSpacing(0)
        shell.addWidget(DialogBar(self, title))
        body = QWidget()
        self.content = QVBoxLayout(body)
        shell.addWidget(body, 1)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))
        p.setPen(QColor(BORDER))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def showEvent(self, e) -> None:
        super().showEvent(e)
        apply_window_frame(self)


_QT_COLOR_TR = {
    "Basic colors": "Temel renkler", "Custom colors": "Özel renkler",
    "Pick Screen Color": "Ekrandan renk seç", "Add to Custom Colors": "Özel renklere ekle",
    "Hue:": "Ton:", "Sat:": "Doygunluk:", "Val:": "Parlaklık:",
    "Red:": "Kırmızı:", "Green:": "Yeşil:", "Blue:": "Mavi:", "HTML:": "HTML:",
}


class ColorPickerDialog(BaseDialog):
    """Uygulamanin kendi stilinde renk secici (Windows'un yerel penceresi yerine)."""

    def __init__(self, parent, color: str, title: str) -> None:
        super().__init__(parent, title)
        lay = self.content
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(12)
        self.picker = QColorDialog(QColor(color))
        self.picker.setWindowFlags(Qt.Widget)           # pencere degil, bu diyaloga gomulu
        self.picker.setOptions(QColorDialog.DontUseNativeDialog | QColorDialog.NoButtons)
        lay.addWidget(self.picker)
        if i18n.language() == "tr":                    # Qt'nin yerlesik cevirileri yuklu degil
            for w in self.picker.findChildren(QLabel) + self.picker.findChildren(QPushButton):
                key = w.text().replace("&", "")
                if key in _QT_COLOR_TR:
                    w.setText(_QT_COLOR_TR[key])
        row = QHBoxLayout()
        row.addStretch(1)
        cancel, ok = QPushButton(tr("İptal")), QPushButton(tr("Tamam"))
        ok.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def color(self) -> str:
        return self.picker.currentColor().name()


def _swatch_style(color: str) -> str:
    fg = "#000" if QColor(color).lightness() > 128 else "#fff"
    return f"background:{color}; color:{fg}; border:1px solid #3a4058; border-radius:10px; padding:10px 18px;"


class CustomColorDialog(BaseDialog):
    """Ozel tema: iki renk secilir, tema bu ikisi arasinda gecis yapar."""

    def __init__(self, parent, c1: str, c2: str) -> None:
        super().__init__(parent, tr("Özel renk"))
        self.setMinimumWidth(380)
        self.c1, self.c2 = c1, c2
        lay = self.content
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(14)
        info = QLabel(tr("Tema bu iki renk arasında geçiş yapar."))
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        self.b1, self.b2 = QPushButton(tr("Renk 1")), QPushButton(tr("Renk 2"))
        for b, which in ((self.b1, 1), (self.b2, 2)):
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, w=which: self._pick(w))
            row.addWidget(b)
        lay.addLayout(row)
        self.bar = QWidget()
        self.bar.setFixedHeight(18)
        lay.addWidget(self.bar)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel, ok = QPushButton(tr("İptal")), QPushButton(tr("Tamam"))
        ok.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)
        self._refresh()

    def _pick(self, which: int) -> None:
        dlg = ColorPickerDialog(self, self.c1 if which == 1 else self.c2, tr("Özel renk"))
        if dlg.exec():
            if which == 1:
                self.c1 = dlg.color()
            else:
                self.c2 = dlg.color()
            self._refresh()

    def _refresh(self) -> None:
        self.b1.setStyleSheet(_swatch_style(self.c1))
        self.b2.setStyleSheet(_swatch_style(self.c2))
        self.bar.setStyleSheet(f"border-radius:9px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
                               f"stop:0 {self.c1}, stop:1 {self.c2});")


class ZoneColorsDialog(BaseDialog):
    """Sabit renk > Ozel: klavyenin 5 bolgesinin HER BIRINE ayri renk secilir (soldan saga)."""

    def __init__(self, parent, colors: list) -> None:
        super().__init__(parent, tr("Bölge renkleri"))
        self.setMinimumWidth(460)
        self.colors = list(colors)
        lay = self.content
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(14)
        info = QLabel(tr("Her bölgeye ayrı renk seç (soldan sağa)."))
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.buttons: list[QPushButton] = []
        for i in range(ZONES):
            b = QPushButton(str(i + 1))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, z=i: self._pick(z))
            row.addWidget(b)
            self.buttons.append(b)
        lay.addLayout(row)
        self.strip = QWidget()
        self.strip.setFixedHeight(22)
        lay.addWidget(self.strip)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel, ok = QPushButton(tr("İptal")), QPushButton(tr("Tamam"))
        ok.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)
        self._refresh()

    def _pick(self, zone: int) -> None:
        dlg = ColorPickerDialog(self, self.colors[zone], f"{tr('Bölge')} {zone + 1}")
        if dlg.exec():
            self.colors[zone] = dlg.color()
            self._refresh()

    def _refresh(self) -> None:
        for b, c in zip(self.buttons, self.colors):
            b.setStyleSheet(_swatch_style(c).replace("padding:10px 18px;", "padding:12px 0;"))
        # 5 NET bolge (klavyenin gercek davranisi): ayni konumdaki iki durak Qt'de birlestigi icin ikincisi biraz onde
        stops = ", ".join(f"stop:{i / ZONES:.4f} {c}, stop:{(i + 1) / ZONES - 0.0015:.4f} {c}"
                          for i, c in enumerate(self.colors))
        self.strip.setStyleSheet(f"border-radius:10px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, {stops});")


class RulesDialog(BaseDialog):
    def __init__(self, parent, rules: dict, enabled: bool) -> None:
        super().__init__(parent, tr("Uygulamaya özel profil"))
        self.resize(580, 440)
        lay = self.content
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(12)
        info = QLabel(tr("Bir uygulama ön plandayken otomatik olarak seçtiğin efekte geçilir. "
                         "İşlem adını Görev Yöneticisi'nde görebilirsin (ör. game.exe)."))
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.enable = CheckBox(tr("Kuralları etkinleştir"))
        self.enable.setChecked(enabled)
        lay.addWidget(self.enable)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr("İşlem adı"), tr("Efekt")])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 240)
        lay.addWidget(self.table, 1)
        for proc, eff in rules.items():
            self._add(proc, eff)
        row = QHBoxLayout()
        add, rem = QPushButton(tr("Kural ekle")), QPushButton(tr("Seçileni sil"))
        add.clicked.connect(lambda: self._add("", next(iter(EFFECTS))))
        rem.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        cancel, ok = QPushButton(tr("İptal")), QPushButton(tr("Tamam"))
        ok.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def _add(self, proc: str, eff: str) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(proc))
        box = QComboBox()
        for name in EFFECTS:                           # gorunen ad cevrilir, kimlik (Turkce) saklanir
            box.addItem(tr(name), name)
        box.setCurrentIndex(max(0, box.findData(eff)))
        self.table.setCellWidget(r, 1, box)

    def result_rules(self) -> dict:
        out = {}
        for r in range(self.table.rowCount()):
            proc = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip().lower()
            if proc:
                out[proc] = self.table.cellWidget(r, 1).currentData()
        return out


class AboutDialog(BaseDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent, tr("Hakkında"))
        self.setMinimumWidth(460)
        lay = self.content
        lay.setContentsMargins(32, 28, 32, 24)
        lay.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(88, 88))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        name = QLabel(tr(APP_NAME))
        name.setObjectName("h1")
        name.setAlignment(Qt.AlignCenter)
        lay.addWidget(name)
        ver = QLabel(f"{tr('Sürüm')} {__version__}")
        ver.setObjectName("muted")
        ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver)
        desc = QLabel(tr("Lenovo Legion K300 klavye için açık kaynak ışık efekti programı."))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        lay.addSpacing(10)
        lay.addWidget(desc)
        lay.addSpacing(14)
        card = QWidget()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(22, 16, 22, 16)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(10)
        dev = QLabel(AUTHOR)
        link = QLabel(f'<a href="{GITHUB_URL}" style="color:#7aa7ff; text-decoration:none;">{GITHUB_URL}</a>')
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link.setCursor(Qt.PointingHandCursor)
        lic = QLabel(f"{LICENSE_NAME}")
        for text, w in ((tr("Geliştirici"), dev), (tr("GitHub profili"), link), ("", lic)):
            lab = QLabel(text) if text else QLabel("Lisans" if i18n.language() == "tr" else "Licence")
            lab.setObjectName("muted")
            form.addRow(lab, w)
        lay.addWidget(card)
        note = QLabel(tr("Resmî bir Lenovo ürünü değildir; Lenovo ile bağlantısı yoktur. "
                         "Lenovo ve Legion ilgili sahiplerinin ticari markalarıdır."))
        note.setObjectName("muted")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("font-size:11px; color:#6c7290;")
        lay.addSpacing(12)
        lay.addWidget(note)
        close = QPushButton(tr("Kapat"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        lay.addSpacing(10)
        lay.addWidget(close)


class SettingsDialog(BaseDialog):
    def __init__(self, win: "MainWindow") -> None:
        super().__init__(win, tr("Ayarlar"))
        self.win = win
        self.setMinimumWidth(480)
        lay = self.content
        lay.setContentsMargins(26, 24, 26, 24)
        lay.setSpacing(12)
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(12)
        self.lang = QComboBox()
        self.lang.addItem(tr("Otomatik (sistem dili)"), "auto")
        self.lang.addItem("Türkçe", "tr")
        self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(max(0, self.lang.findData(win.s["language"])))
        self.lang.currentIndexChanged.connect(self._lang)
        self.layout_box = QComboBox()
        self.layout_box.addItem(tr("Türkçe Q"), "tr")
        self.layout_box.addItem(tr("Global Q (ABD)"), "us")
        self.layout_box.setCurrentIndex(max(0, self.layout_box.findData(win.s["layout"])))
        self.layout_box.currentIndexChanged.connect(self._layout)
        for text, w in ((tr("Dil"), self.lang), (tr("Klavye düzeni"), self.layout_box)):
            lab = QLabel(text)
            lab.setObjectName("muted")
            form.addRow(lab, w)
        lay.addLayout(form)
        lay.addSpacing(4)
        if autostart.supported():
            self.auto = CheckBox(tr("Windows ile birlikte başlat"))
            self.auto.setChecked(autostart.is_enabled())
            self.auto.toggled.connect(self._auto)
            lay.addWidget(self.auto)
        self.tray = CheckBox(tr("Pencereyi kapatınca sistem tepsisinde çalışmaya devam et"))
        self.tray.setChecked(win.s["minimize_to_tray"])
        self.tray.toggled.connect(self._tray)
        lay.addWidget(self.tray)
        row = QHBoxLayout()
        rules = QPushButton(tr("Uygulamaya özel profiller…"))
        rules.clicked.connect(win.open_rules)
        about = QPushButton(tr("Hakkında…"))
        about.clicked.connect(win.open_about)
        row.addWidget(rules)
        row.addWidget(about)
        row.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(row)
        note = QLabel(tr("Tuş dinleyici yalnızca basılan tuşun klavyedeki konumunu kullanır; "
                         "hangi harfe bastığın hiçbir yerde saklanmaz."))
        note.setObjectName("muted")
        note.setWordWrap(True)
        lay.addSpacing(6)
        lay.addWidget(note)
        close = QPushButton(tr("Tamam"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        lay.addSpacing(8)
        lay.addWidget(close)

    def _lang(self, _i: int) -> None:
        self.win.s["language"] = self.lang.currentData()
        self.win.save_soon()
        self.accept()                 # pencere dil icin yeniden kurulur (open_settings sonrasi)

    def _layout(self, _i: int) -> None:
        self.win.apply_layout(self.layout_box.currentData())

    def _auto(self, on: bool) -> None:
        if not autostart.set_enabled(on):
            self.auto.blockSignals(True)
            self.auto.setChecked(autostart.is_enabled())
            self.auto.blockSignals(False)

    def _tray(self, on: bool) -> None:
        self.win.s["minimize_to_tray"] = on
        self.win.save_soon()


# ---------------------------------------------------------------- renk temasi
class ThemeChips(QWidget):
    changed = Signal(str)
    custom_changed = Signal(str, str)
    zones_changed = Signal(list)            # Sabit renk > Ozel: 5 bolgenin ayri renkleri
    D, GAP, COLS = 32, 12, 8

    def __init__(self) -> None:
        super().__init__()
        rows = -(-len(THEME_ORDER) // self.COLS)
        self.setFixedHeight(rows * (self.D + self.GAP) + 4)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.theme, self.custom, self.custom2 = RAINBOW, "#00c8ff", "#ff2bd6"
        self.zone_mode = False              # True: "Ozel" 5 bolgeye ayri renk (Sabit renk efekti)
        self.zones = list(DEFAULT_ZONES)
        self._hover_i = -1
        self._hide_timer = QTimer(self, singleShot=True, interval=140)
        self._hide_timer.timeout.connect(lambda: FancyTip.instance().dismiss())

    def set_state(self, theme: str, custom: str, custom2: str) -> None:
        self.theme, self.custom, self.custom2 = theme, custom, custom2
        self.update()

    def _rect(self, i: int) -> QRectF:
        col, row = i % self.COLS, i // self.COLS
        return QRectF(7 + col * (self.D + self.GAP), 7 + row * (self.D + self.GAP), self.D, self.D)

    def _at(self, pos) -> int:
        for i in range(len(THEME_ORDER)):
            if self._rect(i).adjusted(-5, -5, 5, 5).contains(QPointF(pos)):
                return i
        return -1

    def sizeHint(self) -> QSize:
        return QSize(14 + self.COLS * (self.D + self.GAP), self.height())

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i, name in enumerate(THEME_ORDER):
            r = self._rect(i)
            p.setPen(Qt.NoPen)
            stops = theme_stops(name, self.custom, self.custom2)
            if name == CUSTOM and self.zone_mode:
                stops = [hex_rgb(c) for c in self.zones]            # 5 bolgenin gercek renkleri
            if stops is None:
                g = QConicalGradient(r.center(), 90)
                for k in range(7):
                    g.setColorAt(k / 6, QColor.fromHsvF((k % 6) / 6, 0.85, 1.0))
                p.setBrush(g)
            else:
                g = QLinearGradient(r.topLeft(), r.bottomRight())
                for k, c in enumerate(stops):
                    g.setColorAt(k / (len(stops) - 1), QColor(*c))
                p.setBrush(g)
            p.drawEllipse(r)
            if name == CUSTOM:                          # renk secici ipucu: arti isareti
                p.setPen(QPen(QColor(255, 255, 255, 235 if self.theme == CUSTOM else 175), 2,
                              Qt.SolidLine, Qt.RoundCap))
                c = r.center()
                p.drawLine(QPointF(c.x() - 5, c.y()), QPointF(c.x() + 5, c.y()))
                p.drawLine(QPointF(c.x(), c.y() - 5), QPointF(c.x(), c.y() + 5))
            if name == self.theme:
                p.setPen(QPen(QColor("#ffffff"), 2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(r.adjusted(-5, -5, 5, 5))

    def mouseMoveEvent(self, e) -> None:
        i = self._at(e.position())
        if i == self._hover_i:
            return
        self._hover_i = i
        if i < 0:                                          # daireler arasi bosluk: hemen kapatma, kisa bekle
            self._hide_timer.start()
            return
        self._hide_timer.stop()
        r = self._rect(i)                                  # tema adi: dairenin hemen ustunde, bekleme yok
        anchor = QRect(self.mapToGlobal(QPoint(int(r.x()), int(r.y()))), QSize(int(r.width()), int(r.height())))
        FancyTip.instance().popup(anchor, tr(THEME_ORDER[i]), side="above")

    def leaveEvent(self, e) -> None:
        self._hover_i = -1
        self._hide_timer.stop()
        FancyTip.instance().dismiss()

    def mousePressEvent(self, e) -> None:
        i = self._at(e.position())
        if i < 0:
            return
        name = THEME_ORDER[i]
        FancyTip.hide_now()
        if name == CUSTOM and self.zone_mode:
            if self.theme == CUSTOM or tuple(self.zones) != DEFAULT_ZONES:
                start = list(self.zones)                            # daha once secilen renkler korunur
            else:                                                   # hic ozellestirilmedi: secili temanin 5 rengiyle basla
                start = ["#%02x%02x%02x" % tuple(int(max(0, min(255, v))) for v in
                                                  theme_rgb(self.theme, self.custom, z / (ZONES - 1) * 0.9, self.custom2))
                         for z in range(ZONES)]
            dlg = ZoneColorsDialog(self.window(), start)
            if not dlg.exec():
                return
            self.zones = list(dlg.colors)
            self.zones_changed.emit(self.zones)
        elif name == CUSTOM:
            dlg = CustomColorDialog(self.window(), self.custom, self.custom2)
            if not dlg.exec():
                return
            self.custom, self.custom2 = dlg.c1, dlg.c2
            self.custom_changed.emit(self.custom, self.custom2)
        self.theme = name
        self.update()
        self.changed.emit(name)


class SliderRow(QWidget):
    changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._lo, self._hi, self._fmt = 0.0, 1.0, "{:.1f}"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.lab = QLabel()
        self.lab.setObjectName("muted")
        self.lab.setMinimumWidth(130)
        self.sl = QSlider(Qt.Horizontal)
        self.sl.setRange(0, 1000)
        self.val = QLabel()
        self.val.setMinimumWidth(78)
        self.val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.lab)
        lay.addWidget(self.sl, 1)
        lay.addWidget(self.val)
        self.sl.valueChanged.connect(self._moved)

    def _moved(self, v: int) -> None:
        x = self._lo + v / 1000 * (self._hi - self._lo)
        self.val.setText(self._fmt.format(x))
        self.changed.emit(x)

    def configure(self, label: str, lo: float, hi: float, fmt: str, value: float) -> None:
        self._lo, self._hi, self._fmt = lo, hi, fmt
        self.lab.setText(label)
        self.sl.blockSignals(True)
        self.sl.setValue(int((value - lo) / (hi - lo) * 1000))
        self.sl.blockSignals(False)
        self.val.setText(fmt.format(value))


class KeyGuard(QObject):
    """Klavye test modu: ana penceredeki HICBIR oge klavye olayi almaz (harf listede atlamasin,
    Bosluk dugmeye basmasin). Acilan diyaloglar ayri pencere oldugu icin etkilenmez."""

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._win = window

    def eventFilter(self, obj, ev) -> bool:
        if ev.type() not in (QEvent.KeyPress, QEvent.KeyRelease, QEvent.ShortcutOverride):
            return False
        if isinstance(obj, (QListView, QComboBox, QSlider)):
            return True
        return isinstance(obj, QWidget) and obj.window() is self._win


# ------------------------------------------------------------- cercevesiz pencere
class WinButton(QAbstractButton):
    def __init__(self, kind: str) -> None:
        super().__init__()
        self.kind = kind
        self.setFixedSize(48, 52)
        self._hover = False
        self._tip = QTimer(self, singleShot=True, interval=600)
        self._tip.timeout.connect(self._show_tip)

    def event(self, e) -> bool:
        if e.type() == QEvent.ToolTip:                  # yerel (kasan) balonu engelle; kendi balonumuz var
            return True
        return super().event(e)

    def _show_tip(self) -> None:
        if self.underMouse() and self.toolTip():
            anchor = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            FancyTip.instance().popup(anchor, self.toolTip(), side="below")

    def enterEvent(self, e) -> None:
        self._hover = True
        self._tip.start()
        self.update()

    def leaveEvent(self, e) -> None:
        self._hover = False
        self._tip.stop()
        FancyTip.instance().dismiss()
        self.update()

    def mousePressEvent(self, e) -> None:
        self._tip.stop()
        FancyTip.hide_now()
        super().mousePressEvent(e)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover:
            p.fillRect(self.rect(), QColor("#e5484d") if self.kind == "close" else QColor(255, 255, 255, 20))
        p.setPen(QPen(QColor(255, 255, 255, 235 if self._hover else 190), 1.3))
        p.setBrush(Qt.NoBrush)
        c = QPointF(self.width() / 2, self.height() / 2)
        if self.kind == "min":
            p.drawLine(QPointF(c.x() - 5, c.y()), QPointF(c.x() + 5, c.y()))
        elif self.kind == "max":
            p.drawRect(QRectF(c.x() - 5, c.y() - 5, 10, 10))
        elif self.kind == "restore":
            p.drawRect(QRectF(c.x() - 5, c.y() - 2, 8, 8))
            p.drawLine(QPointF(c.x() - 2, c.y() - 5), QPointF(c.x() + 5, c.y() - 5))
            p.drawLine(QPointF(c.x() + 5, c.y() - 5), QPointF(c.x() + 5, c.y() + 3))
        else:
            p.drawLine(QPointF(c.x() - 5, c.y() - 5), QPointF(c.x() + 5, c.y() + 5))
            p.drawLine(QPointF(c.x() + 5, c.y() - 5), QPointF(c.x() - 5, c.y() + 5))


class TitleBar(QWidget):
    H = 52

    def __init__(self, win: "MainWindow") -> None:
        super().__init__(win)
        self.win = win
        self.setFixedHeight(self.H)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 0, 0)
        lay.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(28, 28))
        icon.setFixedSize(28, 28)
        self.title = QLabel(tr(APP_NAME))
        self.title.setObjectName("apptitle")
        self.status = QLabel()
        self.status.setObjectName("pill")
        self.settings = QPushButton(tr("Ayarlar"))
        self.settings.setCursor(Qt.PointingHandCursor)
        lay.addWidget(icon)
        lay.addWidget(self.title)
        lay.addStretch(1)
        lay.addWidget(self.status, 0, Qt.AlignVCenter)
        lay.addSpacing(6)
        lay.addWidget(self.settings, 0, Qt.AlignVCenter)
        lay.addSpacing(14)
        self.b_min, self.b_max, self.b_close = WinButton("min"), WinButton("max"), WinButton("close")
        self.b_min.setToolTip(tr("Simge durumuna küçült"))
        self.b_close.setToolTip(tr("Kapat"))
        for b in (self.b_min, self.b_max, self.b_close):
            lay.addWidget(b)
        self.b_min.clicked.connect(win.showMinimized)
        self.b_max.clicked.connect(win.toggle_max)
        self.b_close.clicked.connect(win.close)
        self.sync_max()

    def sync_max(self) -> None:
        maxed = bool(self.win.windowState() & Qt.WindowMaximized)
        self.b_max.kind = "restore" if maxed else "max"
        self.b_max.setToolTip(tr("Önceki boyut") if maxed else tr("Büyüt"))
        self.b_max.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.win.windowHandle():
            self.win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self.win.toggle_max()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))
        p.setPen(QColor("#1a1d29"))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class Grip(QWidget):
    """Pencere kenarindan/kosesinden boyutlandirma (yerel sistem boyutlandirmasi)."""

    def __init__(self, win: "MainWindow", edges, cursor) -> None:
        super().__init__(win)
        self.win, self.edges = win, edges
        self.setCursor(cursor)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self.win.windowHandle():
            self.win.windowHandle().startSystemResize(self.edges)


# ----------------------------------------------------------------- ana pencere
class MainWindow(QMainWindow):
    language_changed = Signal()

    def __init__(self, engine: Engine, settings: dict) -> None:
        super().__init__()
        self.engine, self.s = engine, settings
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowTitle(tr(APP_NAME))
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1060, 700)
        self.resize(1140, 760)
        self.setStyleSheet(QSS)
        self._quitting = False
        self._dwm_done = False
        self._guard = KeyGuard(self)
        QApplication.instance().installEventFilter(self._guard)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.titlebar = TitleBar(self)
        self.titlebar.settings.clicked.connect(self.open_settings)
        v.addWidget(self.titlebar)
        body = QWidget()
        outer = QHBoxLayout(body)
        outer.setContentsMargins(22, 18, 22, 22)
        outer.setSpacing(22)
        v.addWidget(body, 1)

        # ---- sol: efekt kartlari
        left = QVBoxLayout()
        left.setSpacing(12)
        sec = QLabel(tr("EFEKTLER"))
        sec.setObjectName("section")
        left.addWidget(sec)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(330)
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 0, 8, 0)
        col.setSpacing(8)
        self.cards: dict[str, EffectCard] = {}
        for c in EFFECT_CLASSES:
            card = EffectCard(c)
            card.clicked.connect(lambda _=False, n=c.name: self._select(n))
            self.cards[c.name] = card
            col.addWidget(card)
        col.addStretch(1)
        scroll.setWidget(holder)
        left.addWidget(scroll, 1)
        outer.addLayout(left)

        # ---- sag
        right = QVBoxLayout()
        right.setSpacing(14)
        self.keyboard = KeyboardView(self.s.get("layout", "tr"))
        right.addWidget(self.keyboard)
        self.title = QLabel()
        self.title.setObjectName("title")
        self.desc = QLabel()
        self.desc.setObjectName("muted")
        self.desc.setWordWrap(True)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color:#ffb454;")
        self.icon = IconTile(54)
        trow = QHBoxLayout()
        trow.setSpacing(14)
        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        tcol.addWidget(self.title)
        tcol.addWidget(self.desc)
        trow.addWidget(self.icon, 0, Qt.AlignTop)
        trow.addLayout(tcol, 1)
        right.addLayout(trow)
        right.addWidget(self.note)

        card = QWidget()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(10)
        self.theme_lbl = QLabel(tr("RENK TEMASI"))
        self.theme_lbl.setObjectName("section")
        self.chips = ThemeChips()
        self.chips.changed.connect(lambda n: self._param("theme", n))
        self.chips.custom_changed.connect(self._custom)
        self.chips.zones_changed.connect(lambda z: self._param("zones", list(z)))
        self.speed = SliderRow()
        self.speed.changed.connect(lambda x: self._param("speed", round(x, 2)))
        self.extra_row = QWidget()
        er = QHBoxLayout(self.extra_row)
        er.setContentsMargins(0, 0, 0, 0)
        self.extra_lbl = QLabel()
        self.extra_lbl.setObjectName("muted")
        self.extra_lbl.setMinimumWidth(130)
        self.extra_box = QComboBox()
        er.addWidget(self.extra_lbl)
        er.addWidget(self.extra_box)
        er.addStretch(1)
        self.extra_key = ""
        self.extra_box.currentTextChanged.connect(
            lambda t: self._param(self.extra_key, t) if self.extra_key else None)
        self.bright = SliderRow()
        self.bright.configure(tr("Parlaklık"), 0.05, 1.0, "{:.0%}", float(self.s["brightness"]))
        self.bright.changed.connect(self._brightness)
        cl.addWidget(self.theme_lbl)
        cl.addWidget(self.chips)
        cl.addWidget(self.speed)
        cl.addWidget(self.extra_row)
        cl.addWidget(self.bright)
        right.addWidget(card)
        right.addStretch(1)
        outer.addLayout(right, 1)

        # ---- boyutlandirma tutamaclari (kenar + kose)
        E = Qt.Edge
        self._grips = [
            (Grip(self, E.TopEdge, Qt.SizeVerCursor), "t"), (Grip(self, E.BottomEdge, Qt.SizeVerCursor), "b"),
            (Grip(self, E.LeftEdge, Qt.SizeHorCursor), "l"), (Grip(self, E.RightEdge, Qt.SizeHorCursor), "r"),
            (Grip(self, E.TopEdge | E.LeftEdge, Qt.SizeFDiagCursor), "tl"),
            (Grip(self, E.BottomEdge | E.RightEdge, Qt.SizeFDiagCursor), "br"),
            (Grip(self, E.TopEdge | E.RightEdge, Qt.SizeBDiagCursor), "tr"),
            (Grip(self, E.BottomEdge | E.LeftEdge, Qt.SizeBDiagCursor), "bl"),
        ]

        self._save_timer = QTimer(self, singleShot=True, interval=600)
        self._save_timer.timeout.connect(lambda: cfg.save(self.s))
        self._note_timer = QTimer(self, interval=800)
        self._note_timer.timeout.connect(self._update_note)
        self._note_timer.start()

        engine.frame.connect(self.keyboard.set_colors)
        engine.key_hit.connect(self.keyboard.flash)
        engine.status.connect(self._status)
        self._status(engine.last_status)
        self._build_tray()
        names = [c.name for c in EFFECT_CLASSES]
        self._select(self.s["effect"] if self.s["effect"] in names else names[0])
        QTimer.singleShot(0, FancyTip.instance().prewarm)      # ilk balon da pürüzsüz acilsin

    # ------------------------------------------------------------------ pencere
    def toggle_max(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            self.titlebar.sync_max()
            for g, _ in self._grips:
                g.setVisible(not self.isMaximized())

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        w, h, t, c = self.width(), self.height(), 6, 12
        geo = {"t": (c, 0, w - 2 * c, t), "b": (c, h - t, w - 2 * c, t), "l": (0, c, t, h - 2 * c),
               "r": (w - t, c, t, h - 2 * c), "tl": (0, 0, c, c), "tr": (w - c, 0, c, c),
               "bl": (0, h - c, c, c), "br": (w - c, h - c, c, c)}
        for g, key in self._grips:
            g.setGeometry(*geo[key])
            g.raise_()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._dwm_done:
            self._dwm_done = True
            apply_window_frame(self)

    # ------------------------------------------------------------------ yardimci
    def save_soon(self) -> None:
        self._save_timer.start()

    def _status(self, code: str) -> None:
        text = {"searching": tr("Klavye aranıyor…"), "connected": tr("Klavye bağlı"),
                "lost": tr("Klavye bağlantısı koptu, yeniden deneniyor…")}.get(code, tr("Başlatılıyor…"))
        ok = code == "connected"
        self.titlebar.status.setText(("●  " if ok else "○  ") + text)
        self.titlebar.status.setStyleSheet(f"color:{'#3ddc97' if ok else '#ffb454'};")

    # ------------------------------------------------------------------ secim
    def _select(self, name: str) -> None:
        self.engine.set_effect(name)
        for n, card in self.cards.items():
            card.setChecked(n == name)
        eff = self.engine.effect
        self.title.setText(tr(eff.name))
        self.icon.set_effect(type(eff))
        self.desc.setText(tr(eff.description))
        has_theme = eff.theme is not None
        self.theme_lbl.setVisible(has_theme)
        self.chips.setVisible(has_theme)
        if has_theme:
            self.chips.zone_mode = eff.zone_custom
            self.chips.zones = list(eff.p["zones"])
            self.chips.set_state(eff.p["theme"], eff.p["custom"], eff.p["custom2"])
        self.speed.setVisible(eff.speed_label is not None)
        if eff.speed_label:
            lo, hi = eff.speed_range
            self.speed.configure(tr(eff.speed_label), lo, hi, tr(eff.speed_fmt), float(eff.p["speed"]))
        ex = eff.extras[0] if eff.extras else None
        self.extra_row.setVisible(ex is not None)
        self.extra_key = ""
        if ex:
            self.extra_lbl.setText(tr(ex.label))
            self.extra_box.blockSignals(True)
            self.extra_box.clear()
            self.extra_box.addItems(list(ex.choices))
            self.extra_box.setCurrentText(str(eff.p[ex.key]))
            self.extra_box.blockSignals(False)
            self.extra_key = ex.key
        self._update_note()
        self.s["effect"] = name
        self.save_soon()

    def _param(self, key: str, value) -> None:
        self.engine.set_param(key, value)
        self.save_soon()

    def _custom(self, c1: str, c2: str) -> None:
        self.engine.set_param("custom", c1)
        self.engine.set_param("custom2", c2)
        self.save_soon()

    def _brightness(self, x: float) -> None:
        self.s["brightness"] = x
        self.save_soon()

    def _update_note(self) -> None:
        eff, msgs = self.engine.effect, []
        if eff.uses_keys and not self.engine.keys.available:
            msgs.append(f"{tr('Tuş dinleyici başlatılamadı:')} {self.engine.keys.error or tr('bilinmeyen hata')}")
        if eff.name == "Ses tepkili" and self.engine.audio.error:
            msgs.append(f"{tr('Ses yakalanamadı:')} {self.engine.audio.error}")
        self.note.setText("  ".join(msgs))
        self.note.setVisible(bool(msgs))

    def apply_layout(self, name: str) -> None:
        self.engine.set_layout(name)
        self.keyboard.set_layout(name)
        self.save_soon()

    # ------------------------------------------------------------------ diyaloglar
    def open_settings(self) -> None:
        before = self.s["language"]
        SettingsDialog(self).exec()
        if self.s["language"] != before:
            cfg.save(self.s)
            self.language_changed.emit()

    def open_rules(self) -> None:
        dlg = RulesDialog(self, self.s["rules"], self.s["rules_enabled"])
        if dlg.exec():
            self.s["rules"] = dlg.result_rules()
            self.s["rules_enabled"] = dlg.enable.isChecked()
            self.save_soon()

    def open_about(self) -> None:
        AboutDialog(self).exec()

    # ------------------------------------------------------------------ tepsi
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu()
        show = QAction(tr("Pencereyi göster"), self)
        show.triggered.connect(self._show)
        quit_ = QAction(tr("Çıkış"), self)
        quit_.triggered.connect(self.quit)
        menu.addAction(show)
        menu.addSeparator()
        menu.addAction(quit_)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(tr(APP_NAME))
        self.tray.activated.connect(lambda r: self._show() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _show(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def dispose(self) -> None:
        """Dil degisiminde eski pencereyi uygulamayi kapatmadan kaldir."""
        FancyTip.hide_now()
        self._quitting = True
        self._note_timer.stop()
        self.tray.hide()
        self.close()
        self.deleteLater()

    def quit(self) -> None:
        self._quitting = True
        cfg.save(self.s)
        self.engine.stop()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e) -> None:
        FancyTip.hide_now()
        if self.s["minimize_to_tray"] and not self._quitting and self.tray.isVisible():
            e.ignore()
            self.hide()
            return
        if not self._quitting:
            self.quit()
        e.accept()
