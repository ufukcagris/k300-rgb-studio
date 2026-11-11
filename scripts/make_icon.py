"""Uygulama simgesini uretir: assets/icon.png (256x256) ve assets/icon.ico (16-256 px).

Kullanim:  python scripts/make_icon.py
Gereken:   PySide6 ve Pillow
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from k300fx.icons import app_icon  # noqa: E402


def main() -> None:
    app = QApplication.instance() or QApplication([])  # noqa: F841
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    png = out / "icon.png"
    app_icon().pixmap(256, 256).save(str(png), "PNG")
    img = Image.open(png).convert("RGBA")
    img.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("yazildi:", png, out / "icon.ico")


if __name__ == "__main__":
    main()
