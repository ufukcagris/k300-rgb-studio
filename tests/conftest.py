import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


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


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
