"""Donanim efektlerini (Sorf 0x0B, Surukleme 0x04) her hizda sirayla oynatir; telefonla cekilen
videodan hareket/hiz/renk olcmek icin. Bolumler arasinda 1.5 sn BEYAZ isaret yanar.

Kullanim:  python scripts/measure_hw.py      (once K300 RGB Studio'yu kapat)
Zaman cizelgesi scripts/measure_hw_log.txt dosyasina yazilir.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from k300fx.device import K300Device  # noqa: E402

SEGMENTS = [(0x0B, "Sorf"), (0x04, "Surukleme")]
DURATION = {0: 24, 1: 18, 2: 14, 3: 12}         # yavas hizlarda en az bir tam tur gorulsun
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "measure_hw_log.txt")

from k300fx import device as _device  # noqa: E402

d = K300Device()
if not d.connect():
    if _device.hid is None:
        sys.exit(f"'hid' modulu yuklenemedi: {_device.HID_ERROR} | Python: {sys.executable} | sys.path: {sys.path}")
    found = [hex(x["usage_page"]) for x in _device.hid.enumerate(0x17EF, 0x60F0)]
    sys.exit(f"Klavye bulunamadi. Gorunen K300 arayuzleri: {found or 'hic yok'}")
input("Telefonla kayda basla (klavye yatay, tamami kadrajda), sonra Enter'a bas... ")
t0 = time.time()
log = open(LOG, "w", encoding="utf-8")


def mark(text):
    line = "%7.2f  %s" % (time.time() - t0, text)
    print(line)
    log.write(line + "\n")
    log.flush()


def white_marker():
    d.show_hardware(0x01, [(255, 255, 255)], 3)      # mod 1: tek renk (gerekirse ~2 sn bekler)
    mark("BEYAZ isaret")
    time.sleep(1.5)


try:
    for mode, name in SEGMENTS:
        for speed in (0, 1, 2, 3):
            white_marker()
            d.show_hardware(mode, [], speed)
            mark(f"{name} hiz {speed} BASLADI")
            time.sleep(DURATION[speed])
    white_marker()
    mark("BITTI - kaydi durdurabilirsin")
finally:
    d.close()
    log.close()
