"""Donanim efektlerinin ZAMANLAMASINI olcer: mod secimi, hiz paketi, ayni hiz paketi ve ayni modu yeniden
secme efekti bastan baslatiyor mu, yoksa surduruyor mu? Telefonla cekilen videoyla birlikte incelenir.

Kullanim:  python scripts/measure_sync.py      (once K300 RGB Studio'yu kapat)
Zaman cizelgesi scripts/measure_sync_log.txt dosyasina yazilir. Toplam ~75 sn.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from k300fx import device as _device  # noqa: E402
from k300fx.device import K300Device  # noqa: E402

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "measure_sync_log.txt")
WAIT = 2.2          # mod seciminden sonra veri gondermeden once

d = K300Device()
if not d.connect():
    sys.exit(f"Klavye bulunamadi. ('hid' hatasi: {_device.HID_ERROR or 'yok'})")
input("Telefonla kayda basla (klavye yatay, tamami kadrajda), sonra Enter'a bas... ")
t0 = time.perf_counter()
log = open(LOG, "w", encoding="utf-8")


def mark(text):
    line = "%8.3f  %s" % (time.perf_counter() - t0, text)
    print(line)
    log.write(line + "\n")
    log.flush()


def select(mode, text):
    d.select_mode(mode)
    mark(f"SEC {mode:#04x} {text}")


def speed(mode, s, text):
    d.push_hardware(mode, s)
    mark(f"HIZ {mode:#04x} -> {s} {text}")


def static(rgb, text):
    d._push(0x01, [rgb], 3)
    mark(f"SABIT {rgb} {text}")


def sync_flashes(tag):
    select(0x01, "senkron icin tek renk")
    time.sleep(WAIT)
    for i in range(3):
        static((255, 255, 255), f"{tag} beyaz {i}")
        time.sleep(0.5)
        static((0, 0, 0), f"{tag} siyah {i}")
        time.sleep(0.5)


try:
    sync_flashes("BAS")
    # Klavyenin sakli hizlarini bilinen bir degere (0) getir
    for mode in (0x04, 0x0B):
        select(mode, "sakli hizi hazirla")
        time.sleep(WAIT)
        speed(mode, 0, "sakli hiz = 0")
        time.sleep(1.0)
    for mode, name in ((0x04, "Surukleme"), (0x0B, "Sorf")):
        select(0x01, "ara")
        time.sleep(WAIT)
        static((0, 0, 0), "ara siyah")
        time.sleep(1.0)
        select(mode, f"{name} A: mod sec (sakli hiz 0)")
        time.sleep(4.0)
        speed(mode, 3, f"{name} B: hiz 3")
        time.sleep(4.0)
        speed(mode, 3, f"{name} C: AYNI hiz 3 tekrar")
        time.sleep(4.0)
        speed(mode, 1, f"{name} D: hiz 1")
        time.sleep(5.0)
        select(mode, f"{name} E: AYNI modu tekrar sec")
        time.sleep(5.0)
    sync_flashes("SON")
    mark("BITTI - kaydi durdurabilirsin")
finally:
    d.close()
    log.close()
