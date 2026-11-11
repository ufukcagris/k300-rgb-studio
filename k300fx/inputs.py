"""Dis girdiler: tus konumlari, ses bantlari, sistem yuku, on plandaki uygulama.

Gizlilik: tus dinleyici yalnizca tusun FIZIKSEL KONUMUNU (x: 0-1) ve zamanini kullanir.
Hangi harfe basildigi hicbir yerde saklanmaz ya da kaydedilmez.
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from collections import deque
from ctypes import wintypes

from . import layouts

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

ZONES = 5


# ------------------------------------------------------------------ tus konumu
def x_to_zone(x: float) -> float:
    """0-1 -> kesirli bolge konumu. Bolge merkezleri 0..4; kenar tuslari biraz disarida kalir."""
    return max(-0.45, min(ZONES - 0.55, x * ZONES - 0.5))


# --------------------------------------------------------------- hafif tus dinleyici
class _KBDLL(ctypes.Structure):
    _fields_ = [("vk", wintypes.DWORD), ("scan", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("extra", ctypes.c_size_t)]


_HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
_WM_KEYDOWN, _WM_SYSKEYDOWN, _WM_QUIT = 0x0100, 0x0104, 0x0012
_LLKHF_EXT, _LLKHF_INJECTED = 0x01, 0x10


def is_fake_shift(scan: int, ext: bool) -> bool:
    """NumLock acikken Shift+gezinme tuslari / Print Screen, Windows'un uydurdugu SAHTE bir sol
    Shift (genisletilmis 0x2A) uretir. Sag Shift (0x36) bazi sistemlerde genisletilmis bayrakla
    gelir ama GERCEKTIR; once yanlislikla ayiklaniyor ve sag Shift hic gorunmuyordu."""
    return ext and scan == 0x2A


def is_fn_report(r) -> bool:
    """Fn tusu Windows'a tus olayi gondermez; klavye bunu ISIK arayuzunden (vendor, 0xFF01) bildirir:
    basinca  ff 00 01 0c ..., birakinca  ff 00 00 00 ...  (2 dk'lik dinlemede 5 basis boyle gozlendi;
    0x0c degerinin tam anlami, ornegin Fn+F tuslarinda baska kod verip vermedigi bilinmiyor)."""
    return bool(r) and len(r) >= 4 and r[0] == 0xFF and r[1] == 0x00 and r[2] == 0x01 and r[3] == 0x0C


def drop_fake_ctrl(events: list, window: float = 0.03) -> list:
    """AltGr basildiginda Windows once SAHTE bir sol Ctrl (0x1D) gonderir; hemen ardindan AltGr
    (0x38, genisletilmis) geliyorsa o Ctrl'yi at. Olaylar: (tarama kodu, genisletilmis, vk, zaman)."""
    out = []
    for i, e in enumerate(events):
        if e[0] == 0x1D and not e[1] and i + 1 < len(events):
            n = events[i + 1]
            if n[0] == 0x38 and n[1] and n[3] - e[3] < window:
                continue
        out.append(e)
    return out


class KeyListener:
    """Global tus dinleyici (WH_KEYBOARD_LL), ozellikle HAFIF tutuldu.

    Kanca fonksiyonu yalnizca ham tarama kodunu kuyruga atar ve hemen geri doner: harf adi
    cozmez (ToUnicode klavye durumunu bozabilir), kilit almaz, sinyal yaymaz. Tuslar efekt
    dongusunde `poll()` ile toplanir. Gizlilik: yalnizca fiziksel konum ve zaman kullanilir.
    """

    def __init__(self) -> None:
        self._q: deque = deque(maxlen=256)
        self._down: set = set()
        self._stamps: deque[float] = deque(maxlen=64)
        self._held: list = []              # sonraki poll'a birakilan olasi sahte Ctrl
        self._thread: threading.Thread | None = None
        self._fn_thread: threading.Thread | None = None
        self._fn_stop = threading.Event()
        self._tid = 0
        self.error: str | None = None
        self.layout = "tr"                # onizleme ile ayni duzen (layouts.py)
        self._allow_injected = bool(os.environ.get("K300FX_ALLOW_INJECTED"))   # yalnizca testler icin

    @property
    def available(self) -> bool:
        return sys.platform == "win32" and self.error is None

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.active or sys.platform != "win32":
            return
        self.error = None
        ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(ready,), daemon=True)
        self._thread.start()
        ready.wait(2)
        self._fn_stop = threading.Event()               # her iş parçacığına kendi durdurma bayrağı
        self._fn_thread = threading.Thread(target=self._fn_loop, args=(self._fn_stop,), daemon=True)
        self._fn_thread.start()

    def stop(self) -> None:
        # Fn okuyucusu BEKLENMEZ: okuma 200 ms zaman asimiyla kendiliginden biter. Beklemek, tus efektinden
        # cikarken arayuzu ~0.2 sn donduruyordu.
        self._fn_stop.set()
        self._fn_thread = None
        if self.active:
            ctypes.windll.user32.PostThreadMessageW(self._tid, _WM_QUIT, 0, 0)
            self._thread.join(timeout=2)
        self._thread = None
        self._down.clear()
        self._q.clear()

    def _fn_loop(self, stop: threading.Event) -> None:
        """Fn tusunu klavyenin vendor arayuzunden OKUR (yalnizca okur, hicbir sey gondermez)."""
        try:
            import hid
        except ImportError:
            return
        dev = None
        while not stop.is_set():
            if dev is None:
                try:
                    for d in hid.enumerate(0x17EF, 0x60F0):
                        if d["usage_page"] == 0xFF01:
                            dev = hid.device()
                            dev.open_path(d["path"])
                            break
                except Exception:   # noqa: BLE001
                    dev = None
                if dev is None:
                    stop.wait(2.0)            # klavye yok/bagli degil: 2 sn sonra tekrar dene
                    continue
            try:
                r = dev.read(64, 200)                   # 200 ms zaman asimi: kapanisi engellemesin
            except Exception:   # noqa: BLE001
                try:
                    dev.close()
                except Exception:   # noqa: BLE001
                    pass
                dev = None
                continue
            if is_fn_report(r) and not stop.is_set():
                self._q.append((0, False, layouts.VK_FN, time.time()))
        if dev is not None:
            try:
                dev.close()
            except Exception:   # noqa: BLE001
                pass

    def _run(self, ready: threading.Event) -> None:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, _HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        self._tid = kernel32.GetCurrentThreadId()
        q, down, inj = self._q, self._down, self._allow_injected

        def cb(n, w, l):
            if n >= 0:
                k = ctypes.cast(l, ctypes.POINTER(_KBDLL)).contents
                f = k.flags
                if inj or not (f & _LLKHF_INJECTED):
                    key = (k.scan, f & _LLKHF_EXT)
                    if w == _WM_KEYDOWN or w == _WM_SYSKEYDOWN:
                        if key not in down:                       # tus tekrarini yok say
                            down.add(key)
                            if not is_fake_shift(k.scan, bool(f & _LLKHF_EXT)):
                                q.append((k.scan, bool(f & _LLKHF_EXT), k.vk, time.time()))
                    else:
                        down.discard(key)
            return user32.CallNextHookEx(None, n, w, l)

        proc = _HOOKPROC(cb)          # referans tutulmali, yoksa cop toplayici kancayi dusurur
        hook = user32.SetWindowsHookExW(13, proc, None, 0)
        if not hook:
            self.error = "klavye kancasi kurulamadi"
            ready.set()
            return
        ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(hook)

    def poll(self) -> list[tuple[int, float, float]]:
        """Son cagridan beri basilan tuslar: [(duzendeki tus sirasi, x 0-1, zaman), ...].
        Duzende olmayan tuslar (medya tuslari vb.) yazma hizina sayilir ama listeye girmez."""
        out = []
        batch = self._held
        self._held = []
        while self._q:
            try:
                batch.append(self._q.popleft())
            except IndexError:
                break
        # AltGr'dan hemen once gelen sahte sol Ctrl'yi ayikla; kareler arasina bolunmesin diye
        # cok yeni bir sol Ctrl sonraki cagriya birakilir.
        if batch and batch[-1][0] == 0x1D and not batch[-1][1] and time.time() - batch[-1][3] < 0.03:
            self._held = [batch.pop()]
        for scan, ext, vk, ts in drop_fake_ctrl(batch):
            self._stamps.append(ts)
            idx = layouts.locate(self.layout, scan, ext, vk)
            if idx >= 0:
                out.append((idx, layouts.x_norm(self.layout, idx), ts))
        return out

    def rate(self, window: float = 2.0) -> float:
        now = time.time()
        return sum(1 for s in list(self._stamps) if now - s <= window) / window


# ------------------------------------------------------------------------- ses
class AudioTap:
    """Sistem sesini (loopback) 5 frekans bandina boler. Opsiyonel."""

    EDGES = (40, 150, 400, 1200, 3500, 12000)
    # Normallestirmenin alt siniri. FFT buyuklugunde genlik A olan sinus ~256*A verir; 1.0 ~ -48 dBFS.
    # Daha dusuk olursa muzik yokken sistem sesindeki ufacik gurultu %100'e yukseltilip titrerdi.
    PEAK_FLOOR = 1.0

    def __init__(self) -> None:
        self.bands = [0.0] * ZONES
        self.error: str | None = None
        self._run = False
        self._gen = 0                      # her start/stop yeni kusak: eski dongu yeni oturumu bozamaz
        self._thread: threading.Thread | None = None
        self._peak = [self.PEAK_FLOOR] * ZONES

    @property
    def active(self) -> bool:
        return self._run and self.error is None

    def start(self) -> None:
        if self._run:
            return
        self.error = None
        self._gen += 1
        self._run = True
        self._thread = threading.Thread(target=self._loop, args=(self._gen,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._run = False
        self._gen += 1                     # calisan eski dongu bu kusaktan degil: kendini bitirir
        self.bands = [0.0] * ZONES

    def _alive(self, gen: int) -> bool:
        return self._run and gen == self._gen

    def _feed(self, band: int, v: float) -> float:
        """Bandin ham seviyesini 0-1'e normallestirir (yavas sonen tepe degerine gore, alt sinirli)."""
        self._peak[band] = max(v, self._peak[band] * 0.995, self.PEAK_FLOOR)
        return min(1.0, v / self._peak[band])

    def _loop(self, gen: int) -> None:
        try:
            import soundcard as sc
            if np is None:
                raise RuntimeError("numpy yok")
            sr, n = 44100, 1024
            mic = sc.get_microphone(str(sc.default_speaker().name), include_loopback=True)
            freqs = np.fft.rfftfreq(n, 1 / sr)
            win = np.hanning(n)
            masks = [(freqs >= self.EDGES[i]) & (freqs < self.EDGES[i + 1]) for i in range(ZONES)]
            with mic.recorder(samplerate=sr, channels=1, blocksize=n) as rec:
                while self._alive(gen):
                    data = rec.record(numframes=n)[:, 0]
                    mag = np.abs(np.fft.rfft(data * win))
                    for i, m in enumerate(masks):
                        v = float(np.sqrt(np.mean(mag[m] ** 2))) if m.any() else 0.0
                        level = self._feed(i, v)
                        if self._alive(gen):
                            self.bands[i] = level
        except Exception as ex:  # ses cihazi yok, paket yok...
            if gen == self._gen:
                self.error = f"{type(ex).__name__}: {ex}"
                self.bands = [0.0] * ZONES
        finally:
            if gen == self._gen:           # yalnizca KENDI oturumunu kapatir
                self._run = False


# ---------------------------------------------------------------- sistem / uygulama
class SysStats:
    def __init__(self) -> None:
        self.cpu = 0.0
        self.ram = 0.0
        self._last = 0.0
        if psutil:
            psutil.cpu_percent(interval=None)

    def poll(self) -> None:
        if not psutil or time.time() - self._last < 0.5:
            return
        self._last = time.time()
        self.cpu = psutil.cpu_percent(interval=None)
        self.ram = psutil.virtual_memory().percent


def foreground_process() -> str:
    """On plandaki penceranin islem adi (kucuk harf), bulunamazsa ''."""
    if psutil is None:
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name().lower()
    except Exception:
        return ""
