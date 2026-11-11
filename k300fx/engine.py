"""Efekt motoru: kendi thread'inde kare uretir, cihaza yollar, onizleme sinyali verir."""
from __future__ import annotations

import ctypes
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal

from . import inputs
from .device import MODE_ZONES, ZoneOutput
from .effects import EFFECTS, Context, Effect


# Dongu hizi SABIT 60 kare/sn. Cihaza gonderim, kare SAYISIYLA belirlenir (zaman karsilastirmasi
# degil): her SEND_EVERY karede bir -> 60/4 = saniyede tam 15 kare. Bilerek DEGISTIRILEMEZ.
#
# Neden: 30 kare/sn'de klavye hizli yazarken tus kacirdi (USB trafigi). Kullanicinin "20" ve "25"
# olarak denedigi ayarlar, cizim 30 fps oldugu icin gercekte 15/sn gonderiyordu ve sorunsuzdu;
# yani DOGRULANAN deger 15/sn'dir. 20 (SEND_EVERY=3) ve 25 gercekte denenmedi.
LOOP_FPS = 60
SEND_EVERY = 4          # 60/4 = 15 kare/sn
QUIET_EVERY = 6         # isik cok yavas degisirken: 10 kare/sn
LEGACY = {"Akış": "Sörf"}   # eski ayar dosyalarindaki efekt adi


class Engine(QObject):
    frame = Signal(list)        # 5 x (r, g, b)
    status = Signal(str)        # "searching" | "connected" | "lost" (ceviri arayuzde)
    auto_effect = Signal(str)   # kural nedeniyle degisen efekt ("" = kural yok)
    sends = Signal(int)         # son saniyede cihaza giden kare sayisi
    key_hit = Signal(int)       # basilan tusun duzendeki sirasi (onizlemede parlatilir)

    def __init__(self, output: ZoneOutput, settings: dict) -> None:
        super().__init__()
        self.output = output
        self.s = settings
        self.ctx = Context()
        self.sysstats = inputs.SysStats()
        self.audio = inputs.AudioTap()
        self.keys = inputs.KeyListener()
        self.keys.layout = settings.get("layout", "tr")
        self._effect: Effect = self._make(settings["effect"])
        self._lock = threading.Lock()
        self._run = False
        self._thread: threading.Thread | None = None
        self._rule_effect = ""
        self._last_fg_check = 0.0
        self._connected = False
        self._t0 = time.time()
        self.last_status = "searching"   # pencere yeniden kurulunca (dil degisimi) okunur

    def _set_status(self, code: str) -> None:
        self.last_status = code
        self.status.emit(code)

    # ------------------------------------------------------------- efekt
    def _make(self, name: str) -> Effect:
        name = LEGACY.get(name, name)
        cls = EFFECTS.get(name) or next(iter(EFFECTS.values()))
        return cls(self.s["params"].get(cls.name))

    def set_effect(self, name: str) -> None:
        eff = self._make(name)
        with self._lock:
            self._effect = eff
            self.s["effect"] = eff.name
        self._sync_inputs()

    def set_param(self, key: str, value) -> None:
        with self._lock:
            self._effect.p[key] = value
            self.s["params"].setdefault(self._effect.name, {})[key] = value

    @property
    def effect(self) -> Effect:
        return self._effect

    def _sync_inputs(self) -> None:
        """Efektin ihtiyac duydugu dis kaynaklari ac/kapa."""
        name = self._effect.name
        if self._effect.uses_keys:
            self.keys.start()
        else:
            self.keys.stop()        # tus gerekmiyorsa sistem capinda kanca birakma
        if name == "Ses tepkili":
            self.audio.start()
        else:
            self.audio.stop()

    def set_layout(self, name: str) -> None:
        self.keys.layout = name
        self.s["layout"] = name

    def _on_key(self, idx: int, x: float, ts: float) -> None:
        zone = inputs.x_to_zone(x)
        with self._lock:
            self._effect.on_key(zone, ts - self._t0)
        self.key_hit.emit(idx)

    def _drain_keys(self) -> None:
        for idx, x, ts in self.keys.poll():
            self._on_key(idx, x, ts)

    # ------------------------------------------------------------- dongu
    def start(self) -> None:
        if self._run:
            return
        self._run = True
        self._t0 = time.time()
        self._sync_inputs()
        if sys.platform == "win32":     # varsayilan 15.6 ms zamanlayici kare hizini bozar
            ctypes.windll.winmm.timeBeginPeriod(1)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._run:
            return
        self._run = False
        self.keys.stop()
        self.audio.stop()
        if self._thread:
            self._thread.join(timeout=4)
        if sys.platform == "win32":
            ctypes.windll.winmm.timeEndPeriod(1)

    def _check_rules(self, now: float) -> None:
        if not self.s["rules_enabled"] or now - self._last_fg_check < 1.0:
            return
        self._last_fg_check = now
        proc = inputs.foreground_process()
        target = self.s["rules"].get(proc, "")
        if target != self._rule_effect:
            self._rule_effect = target
            self.auto_effect.emit(target)
            self.set_effect(target or self.s["effect"])

    def _loop(self) -> None:
        last_sent, last_t, last_push = None, time.time(), 0.0
        sent_n, sent_t = 0, time.time()
        frames_since = SEND_EVERY
        retry_at = 0.0
        next_t = time.perf_counter()
        # Mod gecisi ENGELLEMEDEN yapilir: klavye ~2 sn veri kabul etmez; bu sure boyunca onizleme
        # akmaya devam eder (eskiden motor 2 sn uyuyordu: ilk tiklamada donma).
        dev_mode, ready_at, hw_sent, cur = None, 0.0, None, None
        stored = self.s.setdefault("hw_speeds", {})
        while self._run:
            now = time.time()
            dt = max(0.001, now - last_t)
            last_t = now
            self._check_rules(now)
            self.sysstats.poll()
            self.ctx.cpu, self.ctx.ram = self.sysstats.cpu, self.sysstats.ram
            self._drain_keys()
            self.ctx.typing_rate = self.keys.rate()
            self.ctx.audio = list(self.audio.bands)

            if not self._connected:
                if now >= retry_at:
                    self._set_status("searching")
                    self._connected = self.output.connect()
                    retry_at = now + 2.0
                    if self._connected:
                        self._set_status("connected")
                        last_sent = hw_sent = dev_mode = None

            with self._lock:
                eff = self._effect
            hw = getattr(eff, "hardware", 0)
            if eff is not cur:
                # Ayni donanim efekti yeniden secildiyse klavye bastan baslamaz: onizleme fazi korunur
                if hw and cur is not None and getattr(cur, "hardware", 0) == hw and dev_mode == hw:
                    eff.phase, eff.active_speed = cur.phase, cur.active_speed
                cur = eff
            target = hw or MODE_ZONES
            if self._connected and dev_mode != target:
                try:
                    self.output.select_mode(target)
                    sel_t = time.time()     # 'now' bayat olabilir (dongu bu karede gecikmis olabilir)
                    dev_mode, ready_at = target, sel_t + self.output.switch_delay
                    last_sent = hw_sent = None
                    if hw:          # klavye efekti SIMDI, sakladigi son hizla baslatir
                        eff.restart()
                        eff.active_speed = stored.get(str(hw))
                        dt, last_t = 0.0, sel_t   # faz secim anindan sayilir, oncesi eklenmez
                except OSError:
                    self._connected = False
                    self._set_status("lost")
            ready = self._connected and now >= ready_at
            if hw:
                want = eff.hw_speed()
                if ready and want != hw_sent:
                    try:
                        self.output.push_hardware(hw, want)     # hiz degisir, efekt bastan baslamaz
                        hw_sent = eff.active_speed = want
                        stored[str(hw)] = want
                        sent_n += 1
                    except OSError:
                        self._connected = False
                        self._set_status("lost")
                if not self._connected:
                    eff.active_speed = None

            with self._lock:
                colors = eff.render(now - self._t0, dt, self.ctx)
            # Donanim efektinde parlaklik klavyeye gitmez: onizleme de olceklenmez (klavyeyle ayni gorunsun)
            k = 1.0 if hw else float(self.s["brightness"])
            colors = [tuple(max(0, min(255, int(c * k))) for c in col) for col in colors]
            self.frame.emit(colors)

            if not hw:
                # Isik yavas degisiyorsa (sonen kuyruk, nefes) kareler gozle ayirt edilmez: seyrek gonder.
                frames_since += 1
                diff = 255 if last_sent is None else max(
                    abs(a - b) for ca, cb in zip(colors, last_sent) for a, b in zip(ca, cb))
                every = QUIET_EVERY if diff <= 4 else SEND_EVERY
                if (ready and frames_since >= every
                        and (diff > 0 or now - last_push > 1.0)):
                    try:
                        self.output.show(colors)
                        last_sent, last_push = colors, now
                        frames_since = 0
                        sent_n += 1
                    except OSError:
                        self._connected = False
                        self._set_status("lost")
            if now - sent_t >= 1.0:
                self.sends.emit(sent_n)
                sent_n, sent_t = 0, now
            step = 1.0 / LOOP_FPS
            next_t += step
            wait = next_t - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            elif wait < -step * 3:          # cok geride kaldiysak takvimi sifirla
                next_t = time.perf_counter()
