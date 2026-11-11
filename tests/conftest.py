import gc
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

gc.disable()        # uygulamadaki gibi: cop yalnizca ana is parcaciginda toplanir (_stop_engines)


@pytest.fixture(autouse=True)
def _isolated_appdata(tmp_path, monkeypatch):
    """Testler gercek kullanici ayarlarina (%APPDATA%\\K300FX) ASLA dokunmasin."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))


@pytest.fixture(autouse=True)
def _no_real_audio_capture(monkeypatch):
    """Testler bilgisayarin sesini (loopback) ASLA dinlemesin: "Ses tepkili" secilince gercek yakalama
    baslamasin. (Alt siniflar kendi `_loop`unu tanimlayabilir; yalnizca gercek dongu kapatilir.)"""
    from k300fx import inputs
    monkeypatch.setattr(inputs.AudioTap, "_loop", lambda self, gen: None)


@pytest.fixture(autouse=True)
def _stop_engines(monkeypatch):
    """Testte olusan her motoru (ve tus kancasi / Fn okuyucu / ses is parcaciklarini) test sonunda durdur,
    sonra copu ANA is parcaciginda topla. Aksi halde sizan is parcaciklarinda tetiklenen otomatik cop
    toplama sahipsiz Qt nesnelerini yanlis is parcaciginda siler: CI'da (Python 3.12) bellek bozulmasi."""
    from k300fx import engine as eng_mod
    made = []
    orig = eng_mod.Engine.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        made.append(self)
    monkeypatch.setattr(eng_mod.Engine, "__init__", init)
    yield
    for e in made:
        e.stop()
        e.keys.stop()
        e.audio.stop()
    made.clear()
    from PySide6.QtCore import QCoreApplication, QEvent
    if QCoreApplication.instance() is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)    # deleteLater'lar simdi
    gc.collect()


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
