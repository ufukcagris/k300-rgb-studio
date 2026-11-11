"""macOS tarzi aciklama balonu.

Yumusak golge, hafif saydam koyu govde, ince kenarlik; belirirken hafifce solar ve yukari kayar,
kaybolurken solar. Windows'un yerel balonu (QToolTip) yerine kullanilir: yerel balon kareli bir
cizimle aniden ve "kasarak" aciliyordu.

Tek bir pencere paylasilir (`FancyTip.instance()`); ayni anda yalnizca bir balon gorunur.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .icons import paint_tile

SHADOW = 22          # golge icin pencere kenar boslugu (px)
PAD = 15             # govde ic boslugu
RADIUS = 13
FADE_IN_MS, SLIDE_MS, FADE_OUT_MS = 170, 220, 120
FAMILIES = ["Segoe UI Variable Display", "Segoe UI", "Segoe UI Symbol"]


def _font(px: int, weight: int) -> QFont:
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    return f


class FancyTip(QWidget):
    _inst: "FancyTip | None" = None

    @classmethod
    def instance(cls) -> "FancyTip":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @classmethod
    def hide_now(cls) -> None:
        """Balon varsa aninda gizle (pencere kapanirken/degisirken)."""
        if cls._inst is not None:
            cls._inst.dismiss(immediate=True)

    def __init__(self) -> None:
        # WindowTransparentForInput: balon penceresi fareyi HIC yakalamaz. Yoksa imlecin altina girince
        # alttaki oge "fare ayrildi" sanip balonu kapatir, fare donunce yeniden acilir: titreme dongusu.
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.NoDropShadowWindowHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._title, self._body, self._icon = "", "", None
        self._rect = QRectF()
        self._text_w = 0
        self._hiding = False
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.finished.connect(self._after_fade)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)

    def prewarm(self) -> None:
        """Ilk gosterimdeki takilmayi onler: yerel pencere ve ilk cizim (yazi tipleri) simdiden hazirlanir.
        Yapilmazsa ilk balon, pencere olusturulurken donup 'kasarak' acilir."""
        self._title, self._body, self._icon = "K300", "x", None
        self._measure()
        self.winId()
        self.grab()
        self._title, self._body = "", ""

    # ------------------------------------------------------------------ yerlesim
    def _measure(self) -> None:
        tf, bf = QFontMetrics(_font(13, 600)), QFontMetrics(_font(12, 400))
        icon = 28 if self._icon is not None else 0
        title_w = tf.horizontalAdvance(self._title) + (icon + 10 if icon else 0)
        body_w = 0
        if self._body:
            body_w = bf.boundingRect(QRect(0, 0, 290, 4000), Qt.TextWordWrap, self._body).width()
        self._text_w = int(min(300, max(110, title_w, body_w)))
        head_h = max(icon, tf.height())
        body_h = 0
        if self._body:
            body_h = 8 + bf.boundingRect(QRect(0, 0, self._text_w, 4000), Qt.TextWordWrap, self._body).height()
        w, h = self._text_w + 2 * PAD, head_h + body_h + 2 * PAD
        self._rect = QRectF(SHADOW, SHADOW - 4, w, h)                      # golge asagi dogru biraz uzar
        self.resize(int(w + 2 * SHADOW), int(h + 2 * SHADOW))

    # ------------------------------------------------------------------ goster / gizle
    def popup(self, anchor: QRect, title: str, body: str = "", icon_cls=None, side: str = "right") -> None:
        """`anchor`: ilgili ogenin EKRAN koordinatli dikdortgeni."""
        self._title, self._body, self._icon = title, body, icon_cls
        self._measure()
        screen = QGuiApplication.screenAt(anchor.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        body_h = int(self._rect.height())
        if side == "below":
            x = anchor.center().x() - self.width() // 2
            y = anchor.bottom() + 6 - SHADOW + 4
        elif side == "above":
            x = anchor.center().x() - self.width() // 2
            y = anchor.top() - 8 - body_h - (SHADOW - 4)
        else:
            x = anchor.right() + 10 - SHADOW
            y = anchor.center().y() - body_h // 2 - (SHADOW - 4)
        x = max(avail.left(), min(x, avail.right() - self.width()))
        y = max(avail.top(), min(y, avail.bottom() - self.height()))
        target = QPoint(x, y)
        self._hiding = False
        self._fade.stop()
        self._slide.stop()
        self.update()
        if not self.isVisible():                        # belirirken: solarak + 7 px yukari kayarak
            self.setWindowOpacity(0.0)
            self.move(target + QPoint(0, 7))
            self.show()
            start_pos = self.pos()
        else:                                           # zaten acik (baska ogeye gecis): kaydir
            start_pos = self.pos()
        self._fade.setDuration(FADE_IN_MS)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._slide.setDuration(SLIDE_MS)
        self._slide.setStartValue(start_pos)
        self._slide.setEndValue(target)
        self._fade.start()
        self._slide.start()

    def dismiss(self, immediate: bool = False) -> None:
        if not self.isVisible():
            return
        self._fade.stop()
        self._slide.stop()
        if immediate:
            self._hiding = False
            self.hide()
            return
        self._hiding = True
        self._fade.setDuration(FADE_OUT_MS)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _after_fade(self) -> None:
        if self._hiding:                                # yalniz solma bitince gizle (belirme bitince degil)
            self._hiding = False
            self.hide()

    # ------------------------------------------------------------------ cizim
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        body = self._rect
        p.setPen(Qt.NoPen)
        for i in range(11, 0, -1):                      # yumusak golge: buyuk, cok saydam katmanlar
            grow = i * 1.7
            p.setBrush(QColor(0, 0, 0, 5))
            p.drawRoundedRect(body.adjusted(-grow, -grow + 5, grow, grow + 5), RADIUS + grow, RADIUS + grow)
        g = QLinearGradient(body.topLeft(), body.bottomLeft())
        g.setColorAt(0, QColor(46, 50, 68, 242))        # hafif saydam: arkadaki ogeler ince seyrek gorunur
        g.setColorAt(1, QColor(30, 33, 48, 242))
        p.setBrush(g)
        p.setPen(QPen(QColor(255, 255, 255, 38), 1))
        p.drawRoundedRect(body, RADIUS, RADIUS)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))    # ust kenarda ince isik cizgisi (cam hissi)
        p.drawLine(QPoint(int(body.left() + RADIUS), int(body.top() + 1)),
                   QPoint(int(body.right() - RADIUS), int(body.top() + 1)))
        x, y = body.left() + PAD, body.top() + PAD
        tf = QFontMetrics(_font(13, 600))
        head_h = max(28 if self._icon is not None else 0, tf.height())
        if self._icon is not None:
            paint_tile(p, QRectF(x, y, 28, 28), self._icon)
            x_text = x + 38
        else:
            x_text = x
        p.setPen(QColor("#f4f5fb"))
        p.setFont(_font(13, 600))
        p.drawText(QRectF(x_text, y, self._text_w, head_h), Qt.AlignVCenter | Qt.AlignLeft, self._title)
        if self._body:
            p.setPen(QColor("#a9afc7"))
            p.setFont(_font(12, 400))
            p.drawText(QRectF(x, y + head_h + 8, self._text_w, body.height()),
                       Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap, self._body)
