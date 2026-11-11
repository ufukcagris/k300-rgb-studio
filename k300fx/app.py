"""Pencere yasam dongusu: olusturma ve dil degisiminde (motoru durdurmadan) yeniden kurma."""
from __future__ import annotations

from PySide6.QtCore import QTimer

from . import i18n
from .engine import Engine
from .ui import MainWindow


class Controller:
    def __init__(self, engine: Engine, settings: dict) -> None:
        self.engine, self.s = engine, settings
        self.win: MainWindow | None = None

    def make(self) -> MainWindow:
        i18n.set_language(i18n.resolve(self.s["language"]))
        win = MainWindow(self.engine, self.s)
        win.language_changed.connect(lambda: QTimer.singleShot(0, self.rebuild))
        self.win = win
        return win

    def rebuild(self) -> None:
        """Dil degisti: ayni motorla, ayni konum/boyutla pencereyi yeni dilde yeniden kur."""
        old = self.win
        geo, visible = old.saveGeometry(), old.isVisible()
        new = self.make()
        new.restoreGeometry(geo)
        if visible:
            new.show()
        old.dispose()
