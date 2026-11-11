"""Lenovo Legion K300 (17EF:60F0) HID cikis katmani.

Protokol (Legion Accessory Central trafiginden cikarildi):
  feature report  00 19 00 5A <mod>   -> mod sec (sonra ~2 sn bekle)
  feature report  00 14 00 5A         -> veri paketi geliyor
  write (65 bayt) 00 01 <mod> 02 <b3> + 12 sifir + 8 x [R G B 00]
Modlar (Legion uygulamasindaki adlariyla; hepsi klavyenin KENDI ICINDE calisan donanim efektleridir,
tek paket yeter, klavye kendisi oynatir; 0x0C haric hepsi tus tus calisir):
  0x01 tek renk (slot 0)        0x04 Surukleme (drifting)       0x08 Nefes gokkusagi (veri paketi yok)
  0x0B Sorf (surfing)           0x0C bes bolge (ilk 5 renk slotu, YAZILIMLA akitilir)
Sorf/Surukleme: 7 renk paleti + hiz baytı (b3: 0 en yavas ... 3 en hizli).

Efekt motoru yalnizca `ZoneOutput` arayuzunu bilir; ileride tuş bazli protokol
bulunursa sadece bu katman degisir.
"""
from __future__ import annotations

import time

HID_ERROR = ""
try:
    import hid
except ImportError as _e:  # pragma: no cover
    hid = None
    HID_ERROR = str(_e)

VID, PID = 0x17EF, 0x60F0
MODE_STATIC, MODE_DRIFT, MODE_BREATH_RAINBOW, MODE_SURF, MODE_ZONES = 0x01, 0x04, 0x08, 0x0B, 0x0C
MODE_WAVE = MODE_SURF           # eski ad
HW_PALETTE = 7                  # Sorf/Surukleme paletindeki renk sayisi
ZONES = 5
MODE_SWITCH_DELAY = 2.0


def _clamp(v: float) -> int:
    return max(0, min(255, int(v)))


class ZoneOutput:
    """Efekt motorunun gordugu arayuz."""

    zones = ZONES
    switch_delay = MODE_SWITCH_DELAY    # mod secildikten sonra veri kabul edilene kadar beklenecek sure

    def connect(self) -> bool:
        raise NotImplementedError

    def show(self, colors) -> None:
        raise NotImplementedError

    def select_mode(self, mode: int) -> None:
        """Mod sec, BEKLEMEDEN don. Klavye donanim efektini bu anda, sakli hizla baslatir; yeni hiz
        paketi ancak ~MODE_SWITCH_DELAY sonra gonderilebilir (push_hardware)."""
        raise NotImplementedError

    def push_hardware(self, mode: int, speed: int) -> None:
        """Secili donanim efektinin hizini gonder (efekt bastan baslamaz, hizi degisir)."""
        raise NotImplementedError

    def show_hardware(self, mode: int, palette, speed: int) -> None:
        """Betikler icin: mod sec, gerekirse bekle, paketi gonder (bloklar)."""
        raise NotImplementedError

    def close(self) -> None:
        pass


class K300Device(ZoneOutput):
    def __init__(self) -> None:
        self._dev = None
        self._mode: int | None = None

    @property
    def connected(self) -> bool:
        return self._dev is not None

    def connect(self) -> bool:
        if hid is None:
            return False
        self.close()
        try:
            for d in hid.enumerate(VID, PID):
                if d["usage_page"] == 0xFF01:
                    dev = hid.device()
                    dev.open_path(d["path"])
                    self._dev, self._mode = dev, None
                    return True
        except (OSError, IOError, ValueError):
            pass
        return False

    def close(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
        self._dev, self._mode = None, None

    def _ensure_mode(self, mode: int) -> None:
        if self._mode == mode:
            return
        self._dev.send_feature_report(bytes([0x00, 0x19, 0x00, 0x5A, mode, 0, 0, 0, 0]))
        time.sleep(MODE_SWITCH_DELAY)
        self._mode = mode

    def _push(self, mode: int, colors, b3: int = 3) -> None:
        slots = (list(colors) + [(0, 0, 0)] * 8)[:8]
        pkt = bytearray(65)
        pkt[1:5] = bytes([0x01, mode, 0x02, b3])
        for i, (r, g, b) in enumerate(slots):
            pkt[17 + 4 * i: 20 + 4 * i] = bytes([_clamp(r), _clamp(g), _clamp(b)])
        self._dev.send_feature_report(bytes([0x00, 0x14, 0x00, 0x5A, 0, 0, 0, 0, 0]))
        self._dev.write(bytes(pkt))

    def show(self, colors) -> None:
        """5 bolge rengi gonder. Baglanti koparsa OSError firlatir."""
        if self._dev is None:
            raise OSError("cihaz bagli degil")
        try:
            self._ensure_mode(MODE_ZONES)
            self._push(MODE_ZONES, colors)
        except (OSError, IOError, ValueError):
            self.close()
            raise OSError("cihaz baglantisi koptu")

    def select_mode(self, mode: int) -> None:
        if self._dev is None:
            raise OSError("cihaz bagli degil")
        try:
            self._dev.send_feature_report(bytes([0x00, 0x19, 0x00, 0x5A, mode, 0, 0, 0, 0]))
        except (OSError, IOError, ValueError):
            self.close()
            raise OSError("cihaz baglantisi koptu")
        self._mode = mode

    def push_hardware(self, mode: int, speed: int) -> None:
        if self._dev is None:
            raise OSError("cihaz bagli degil")
        try:
            self._push(mode, [], b3=max(0, min(3, int(speed))))
        except (OSError, IOError, ValueError):
            self.close()
            raise OSError("cihaz baglantisi koptu")

    def show_hardware(self, mode: int, palette, speed: int) -> None:
        """Donanim efekti: mod secilir (gerekirse ~2 sn bekler), palet + hiz tek pakette gider."""
        if self._dev is None:
            raise OSError("cihaz bagli degil")
        try:
            self._ensure_mode(mode)
            self._push(mode, list(palette)[:HW_PALETTE], b3=max(0, min(3, int(speed))))
        except (OSError, IOError, ValueError):
            self.close()
            raise OSError("cihaz baglantisi koptu")


class FakeDevice(ZoneOutput):
    """Test icin: gonderilen kareleri ve donanim efektlerini saklar."""

    switch_delay = 0.0

    def __init__(self) -> None:
        self.frames: list = []
        self.hardware: list = []
        self.modes: list = []

    def connect(self) -> bool:
        return True

    def show(self, colors) -> None:
        self.frames.append([tuple(c) for c in colors])

    def select_mode(self, mode: int) -> None:
        self.modes.append(mode)

    def push_hardware(self, mode: int, speed: int) -> None:
        self.hardware.append((mode, [], speed))

    def show_hardware(self, mode: int, palette, speed: int) -> None:
        self.hardware.append((mode, [tuple(c) for c in palette], speed))
