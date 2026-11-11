"""Calistirma:  python -m k300fx   (veya paketlenmis K300RGBStudio.exe)

Bayraklar:
  --minimized        pencereyi acmadan sistem tepsisinde baslat
  --fake             klavye olmadan dene (sahte cihaz)
  --selftest <dosya> paketlenmis surumun bagimliliklarini sinar, sonucu dosyaya yazar, cikar
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


def selftest(out: str) -> int:
    """Paketlenmis exe'nin tum bagimliliklarini pencere acmadan dogrular."""
    res: dict = {}

    def check(name, fn):
        try:
            res[name] = {"ok": True, "detay": fn()}
        except Exception as ex:   # noqa: BLE001
            res[name] = {"ok": False, "hata": f"{type(ex).__name__}: {ex}"}

    def qt():
        from PySide6 import QtCore
        return QtCore.__version__

    def hid_():
        import hid
        devs = [d for d in hid.enumerate(0x17EF, 0x60F0) if d["usage_page"] == 0xFF01]
        return f"K300 vendor arayuzu: {len(devs)}"

    def audio():
        import numpy
        import soundcard as sc
        return f"numpy {numpy.__version__}, hoparlor: {sc.default_speaker().name}"

    def psutil_():
        import psutil
        return f"cpu {psutil.cpu_percent(interval=0.1)}"

    def pkg():
        from k300fx import __version__, layouts
        from k300fx.effects import EFFECTS
        return f"surum {__version__}, {len(EFFECTS)} efekt, duzenler: {','.join(layouts.LAYOUT_NAMES)}"

    for n, f in (("qt", qt), ("hid", hid_), ("ses", audio), ("psutil", psutil_), ("paket", pkg)):
        check(n, f)
    Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(v["ok"] for k, v in res.items() if k != "ses") else 1


def gui_thread_gc():
    """Cop toplamayi YALNIZCA arayuz is parcaciginda yap. Otomatik toplama, bellek ayiran herhangi bir
    is parcaciginda (motor dongusu, Fn okuyucu) tetiklenebilir; orada sahipsiz kalmis bir Qt nesnesi
    (or. dil degisiminden kalan eski pencere) silinirse Qt'nin bellegi bozulur (0xc0000374)."""
    import gc

    from PySide6.QtCore import QTimer
    gc.disable()
    t = QTimer(interval=2000)
    t.timeout.connect(lambda: gc.collect())
    t.start()
    return t


def main() -> int:
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        return selftest(sys.argv[i + 1] if i + 1 < len(sys.argv) else "selftest.json")

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QApplication, QMessageBox

    from . import i18n
    from . import settings as cfg
    from .device import FakeDevice, K300Device
    from .app import Controller
    from .engine import Engine
    from .i18n import tr
    from .ui import APP_NAME

    s = cfg.load()
    i18n.set_language(i18n.resolve(s["language"]))
    app = QApplication(sys.argv)
    app.setApplicationName(tr(APP_NAME))
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(Path(tempfile.gettempdir()) / "k300fx.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, tr(APP_NAME), tr("Program zaten çalışıyor (sistem tepsisine bak)."))
        return 0

    gui_gc = gui_thread_gc()
    engine = Engine(FakeDevice() if "--fake" in sys.argv else K300Device(), s)
    ctl = Controller(engine, s)
    win = ctl.make()
    engine.start()
    if "--minimized" not in sys.argv:
        win.show()
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
