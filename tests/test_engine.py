"""Motor testleri: cihaza gonderim hizi (klavyeyi tus kacirtmamak icin kritik) ve kanca yonetimi."""
import time

import pytest

from k300fx import settings
from k300fx.device import FakeDevice
from k300fx.engine import LOOP_FPS, QUIET_EVERY, SEND_EVERY, Engine


class TimedDevice(FakeDevice):
    def __init__(self):
        super().__init__()
        self.ts = []

    def show(self, colors):
        self.ts.append(time.perf_counter())
        super().show(colors)


def _run(qapp, effect, secs=3.0):
    s = settings.load()
    s["effect"], s["params"] = effect, {}
    dev = TimedDevice()
    eng = Engine(dev, s)
    eng.start()
    t = time.time()
    while time.time() - t < secs:
        qapp.processEvents()
        time.sleep(0.004)
    eng.stop()
    return dev, eng


def test_send_rate_is_constant_15_per_second(qapp):
    assert (LOOP_FPS, SEND_EVERY) == (60, 4)       # 30 kare/sn ve ustu hizli yazarken tus kacirtti
    dev, _ = _run(qapp, "Aurora")
    rate = len(dev.ts) / 3.0
    assert 14.0 <= rate <= 16.0, rate
    gaps = [(b - a) * 1000 for a, b in zip(dev.ts, dev.ts[1:])]
    assert max(gaps) < 90                          # takilma yok


def test_static_effect_barely_talks_to_keyboard(qapp):
    dev, _ = _run(qapp, "Sabit renk")
    assert len(dev.ts) / 3.0 <= 2.0                # yalnizca canlilik kontrolu (~1/sn)


def test_slow_changes_are_sent_less_often(qapp):
    assert QUIET_EVERY > SEND_EVERY


def test_key_hook_only_runs_for_key_effects(qapp):
    s = settings.load()
    s["effect"] = "Nefes"
    eng = Engine(FakeDevice(), s)
    eng.start()
    try:
        time.sleep(0.3)
        assert not eng.keys.active
        eng.set_effect("Tuştan yayılan dalga")
        time.sleep(0.4)
        assert eng.keys.active == eng.keys.available
        eng.set_effect("Nefes")
        time.sleep(0.4)
        assert not eng.keys.active
    finally:
        eng.stop()
    assert not eng.keys.active


def test_params_reach_the_effect_and_are_saved(qapp):
    s = settings.load()
    s["params"] = {}
    eng = Engine(FakeDevice(), s)
    eng.set_effect("Aurora")
    eng.set_param("theme", "Okyanus")
    assert eng.effect.p["theme"] == "Okyanus"
    assert s["params"]["Aurora"]["theme"] == "Okyanus"
    eng.set_effect("Nefes")
    eng.set_effect("Aurora")
    assert eng.effect.p["theme"] == "Okyanus"      # secim hatirlanir
