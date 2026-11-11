"""Efektlerin DAVRANIŞI: yön, nefes hissi, bölge renkleri, geçişte kalıntı, ses normalleştirmesi.

Bunlar kullanıcının gözle fark ettiği hatalardı (Nefes soldan
sağa süpürüyordu, Sabit renk'te bölgelere ayrı renk seçilemiyordu); artık sayıyla korunuyor.
"""
import random
import threading
import time

import pytest

from k300fx import inputs, settings
from k300fx.device import FakeDevice
from k300fx.effects import (CUSTOM, DEFAULT_ZONES, EFFECT_CLASSES, EFFECTS, THEME_ORDER, ZONES, Context,
                            hex_rgb, theme_rgb)
from k300fx.effects import HW_PALETTE, HW_SAMPLES
from k300fx.engine import Engine

CTX = Context(typing_rate=4, cpu=40, ram=55, audio=[0.4, 0.5, 0.6, 0.5, 0.3])


def lum(c):                      # LED'ler dogrusal surulur: dogrusal isik parlakligi
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def close(a, b, tol=2.5):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


# ----------------------------------------------------------------------------- Donanim efektleri
def test_surf_and_drift_are_hardware_effects_with_speed_0_to_3():
    for name, mode in (("Sörf", 0x0B), ("Sürükleme", 0x04)):
        e = EFFECTS[name]()
        assert e.hardware == mode and e.theme is None and e.speed_range == (0, 3)
        assert len(e.render(1.0, 1 / 30, CTX)) == HW_SAMPLES
    assert EFFECTS["Sörf"]({"speed": 9}).hw_speed() == 3 and EFFECTS["Sörf"]({"speed": -1}).hw_speed() == 0


@pytest.mark.parametrize("speed", [0, 1, 2, 3])
def test_surf_matches_measured_keyboard(speed):
    """Videodan olculen: ton hizi (tur/sn), klavye boyunca ~0.23 tur, desen soldan saga."""
    import colorsys
    e = EFFECTS["Sörf"]({"speed": speed})
    rate = (0.314, 0.461, 0.613, 0.695)[speed]

    def h(u, t):
        e.phase = e.rate(speed) * t
        r, g, b = e.at(u)
        return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0]
    assert abs(((h(0.5, 0) - h(0.5, 1.0)) % 1) - rate) < 0.01           # zamanla ton geri doner
    assert abs(((h(1.0, 0) - h(0.0, 0)) % 1) - 0.40) < 0.01             # sag uc, solun gecmisi
    assert abs(h(0.0, 0) - 0.33) < 0.01                                # mod secilince sol uc yesil


@pytest.mark.parametrize("speed", [0, 1, 2, 3])
def test_drift_matches_measured_keyboard(speed):
    """Olculen: palet sirasi, renk basina 6 adim (5 aydinlik + 1 karanlik), ortadan uclara / uclardan ortaya."""
    e = EFFECTS["Sürükleme"]({"speed": speed})
    assert abs(e.rate(speed) - 6 / (1.50, 1.18, 0.689, 0.443)[speed]) < 1e-9          # adim/sn

    def at(u, steps):
        e.phase = steps
        return e.at(u)
    for k in range(7):
        frame = [at(u, k * 6 + 2.5) for u in (0.2, 0.48, 0.8)]
        peak = max(frame, key=max)
        assert tuple(round(c / max(peak) * 255) for c in peak) == HW_PALETTE[k]     # palet sirasi
        assert max(map(max, [at(u, k * 6 + 5.5) for u in (0.1, 0.48, 0.9)])) == 0  # karanlik adim
    first = [max(at(u, 0.5)) for u in (0.05, 0.48, 0.95)]                        # 1. renk: ortadan
    second = [max(at(u, 6.5)) for u in (0.05, 0.48, 0.95)]                       # 2. renk: uclardan
    assert first[1] > 200 > max(first[0], first[2]) and second[1] < 50 < min(second[0], second[2])


def test_engine_sends_hardware_effect_once_and_resends_on_speed_change(qapp):
    s = settings.load()
    s["effect"] = "Sörf"
    dev = FakeDevice()
    eng = Engine(dev, s)
    eng.start()
    try:
        time.sleep(0.8)
        assert dev.modes == [0x0B] and dev.hardware == [(0x0B, [], 2)] and dev.frames == []  # tek paket
        eng.set_param("speed", 3)
        time.sleep(0.5)
        assert dev.hardware[-1] == (0x0B, [], 3) and len(dev.hardware) == 2
        eng.set_effect("Sürükleme")
        time.sleep(0.5)
        assert dev.hardware[-1][0] == 0x04
    finally:
        eng.stop()


def test_mode_switch_does_not_freeze_preview_and_matches_keyboard_timing(qapp):
    """Klavye efekti mod secilince SAKLI hizla baslar, hiz paketi ~2 sn sonra gider, faz surer.
    Eskiden motor bu 2 sn boyunca uyuyordu: onizleme donuyor, sonra klavyeyle kayik devam ediyordu."""
    s = settings.load()
    s["effect"], s["params"] = "Tuştan yayılan dalga", {"Sürükleme": {"speed": 3}}
    s["hw_speeds"] = {str(0x04): 0}                     # klavyede sakli: hiz 0
    dev = FakeDevice()
    dev.switch_delay = 0.6
    eng = Engine(dev, s)
    got = []
    from PySide6.QtCore import Qt
    eng.frame.connect(lambda c: got.append(time.time()), Qt.DirectConnection)   # motor thread'inde zamanla
    eng.start()
    try:
        time.sleep(0.9)                                 # yazilim efekti hazir
        t0 = time.time()
        eng.set_effect("Sürükleme")
        assert time.time() - t0 < 0.1                   # secim arayuzu bekletmez
        time.sleep(0.3)
        assert eng.effect.active_speed == 0             # paket gitmeden: klavyenin sakli hizi
        during = [t for t in got if t0 < t < t0 + 0.3]
        assert len(during) > 10                         # onizleme donmadi (~60 kare/sn)
        time.sleep(0.6)
        assert dev.hardware[-1] == (0x04, [], 3) and eng.effect.active_speed == 3
        assert s["hw_speeds"][str(0x04)] == 3
        ph, el = eng.effect.phase, time.time() - t0
        expect = 1 + 0.6 * 6 / 1.50 + (el - 0.6) * 6 / 0.443   # ilk adim atlanir; 0.6 sn sakli hiz 0, sonra hiz 3
        assert abs(ph - expect) < 0.6, (ph, expect)
        eng.set_param("speed", 1)
        time.sleep(0.1)
        assert eng.effect.phase >= ph                   # hiz degisimi bastan baslatmaz
        eng.set_effect("Sürükleme")                     # ayni efekti yeniden secmek de baslatmaz
        time.sleep(0.1)
        assert eng.effect.phase >= ph and dev.modes.count(0x04) == 1
    finally:
        eng.stop()


def test_old_flow_name_maps_to_surf():
    s = settings.load()
    s["effect"] = "Akış"
    assert Engine(FakeDevice(), s).effect.name == "Sörf"


def test_rainbow_equalization_only_where_hue_sweeps():
    plain = theme_rgb("Gökkuşağı", "#000000", 0.17)                    # sari: parlama efektleri icin canli
    eq = theme_rgb("Gökkuşağı", "#000000", 0.17, equalize=True)         # sari kisilir: akista parlak olmasin
    assert max(plain) > 250 and max(eq) < 0.7 * max(plain)
    blue = theme_rgb("Gökkuşağı", "#000000", 0.66, equalize=True)
    assert max(blue) > 250                                              # sonuk tonlar kisilmez


# ----------------------------------------------------------------------------- Nefes
@pytest.mark.parametrize("theme", ["Okyanus", "Gökkuşağı", "Özel", "Ateş"])
def test_breathe_is_in_unison_not_a_travelling_wave(theme):
    eff = EFFECTS["Nefes"]({"theme": theme})
    lows, highs = [], []
    for i in range(30 * 12):
        f = eff.render(i / 30, 1 / 30, CTX)
        assert all(f[z] == f[0] for z in range(ZONES)), (theme, i)       # tum bolgeler birebir ayni
        lows.append(lum(f[0]))
    assert max(lows) > 5 * (min(lows) + 1)                               # gercekten nefes aliyor (belirgin inip cikiyor)


def test_breathe_speed_changes_breathing_rate():
    def cycles(speed):
        eff = EFFECTS["Nefes"]({"speed": speed})
        ys = [lum(eff.render(i / 30, 1 / 30, CTX)[0]) for i in range(30 * 20)]
        mid = (max(ys) + min(ys)) / 2
        return sum(1 for a, b in zip(ys, ys[1:]) if a < mid <= b)
    assert cycles(2.0) > cycles(1.0) * 1.6


# ----------------------------------------------------------------------- Sabit renk (5 bolge)
def test_static_custom_gives_every_zone_its_own_colour():
    zones = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"]
    eff = EFFECTS["Sabit renk"]({"theme": CUSTOM, "zones": zones})
    assert [tuple(int(v) for v in c) for c in eff.render(0, 1 / 30, CTX)] == [hex_rgb(c) for c in zones]
    assert EFFECTS["Sabit renk"].zone_custom and not any(c.zone_custom for c in EFFECT_CLASSES if c.name != "Sabit renk")


def test_static_theme_still_spreads_a_gradient_and_ignores_zones():
    eff = EFFECTS["Sabit renk"]({"theme": "Neon", "zones": ["#ff0000"] * ZONES})
    f = eff.render(0, 1 / 30, CTX)
    assert len({tuple(round(v) for v in c) for c in f}) == ZONES        # 5 farkli renk, kirmizi degil


@pytest.mark.parametrize("bad", [None, [], ["#fff"] * 5, ["#12345"] * 5, ["red"] * 5, ["#ff0000"] * 4, 7])
def test_invalid_zone_settings_fall_back_to_defaults(bad):
    assert EFFECTS["Sabit renk"]({"theme": CUSTOM, "zones": bad}).p["zones"] == list(DEFAULT_ZONES)


def test_zone_list_is_copied_not_shared_with_the_settings_dict():
    saved = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"]
    a = EFFECTS["Sabit renk"]({"zones": saved})
    a.p["zones"][0] = "#123456"
    assert saved[0] == "#ff0000"


def test_zone_colours_survive_the_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = settings.load()
    eng = Engine(FakeDevice(), s)
    eng.set_effect("Sabit renk")
    zones = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"]
    eng.set_param("theme", CUSTOM)
    eng.set_param("zones", zones)
    settings.save(s)
    again = settings.load()
    eff = EFFECTS["Sabit renk"](again["params"]["Sabit renk"])
    assert eff.p["theme"] == CUSTOM and eff.p["zones"] == zones


# ------------------------------------------------------------- efektten efekte geciste kalinti
def _state(e):
    return {k: v for k, v in vars(e).items() if not k.startswith("__")}


@pytest.mark.parametrize("a", [c.name for c in EFFECT_CLASSES])
@pytest.mark.parametrize("b", [c.name for c in EFFECT_CLASSES])
def test_switching_effects_leaves_no_residue(a, b, tmp_path, monkeypatch):
    """A'dan B'ye gecince B, hic A calismamis gibi (ayni zaman ve rastgelelikle) davranmali."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = settings.load()
    s["effect"], s["params"] = a, {}
    eng = Engine(FakeDevice(), s)
    random.seed(1)
    for i in range(90):                                     # A bir sure calissin, tuslarla kirlensin
        eng.effect.on_key(i % 5 * 1.0, i / 30)
        eng.effect.render(i / 30, 1 / 30, CTX)
    eng.set_effect(b)
    random.seed(7)
    got = [eng.effect.render(3 + i / 30, 1 / 30, CTX) for i in range(20)]
    random.seed(7)
    fresh = EFFECTS[b](s["params"].get(b))
    want = [fresh.render(3 + i / 30, 1 / 30, CTX) for i in range(20)]
    assert got == want
    assert eng.effect is not fresh and type(eng.effect) is EFFECTS[b]


def test_switching_stops_the_inputs_the_new_effect_does_not_need(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = settings.load()
    s["effect"] = "Tuştan yayılan dalga"
    eng = Engine(FakeDevice(), s)
    eng.start()
    try:
        time.sleep(0.3)
        eng.set_effect("Aurora")
        time.sleep(0.4)
        assert not eng.keys.active                           # tus kancasi birakildi
        assert eng.audio.bands == [0.0] * ZONES
    finally:
        eng.stop()


# --------------------------------------------------------------------------------- ses
def test_audio_tap_ignores_near_silence_but_follows_music():
    tap = inputs.AudioTap()
    assert all(tap._feed(0, 0.05) < 0.06 for _ in range(500))            # gurultu: karanlik kalir (eskiden %100)
    assert tap._feed(0, 80.0) == 1.0                                     # yuksek muzik: tam
    assert 0.05 < tap._feed(0, 8.0) < 0.12                               # tepeye gore daha sessiz: orantili


def test_audio_tap_restart_is_not_killed_by_the_old_loop():
    """stop() hemen ardindan start(): eski dongu cikarken yeni oturumun bayragini kapatmamali."""
    started, finished = [], []

    class FakeTap(inputs.AudioTap):
        def _loop(self, gen):
            started.append(gen)
            try:
                while self._alive(gen):
                    time.sleep(0.01)
            finally:
                finished.append(gen)
                if gen == self._gen:
                    self._run = False

    tap = FakeTap()
    tap.start()
    time.sleep(0.05)
    tap.stop()
    tap.start()                                              # eski dongu henuz cikmamis olabilir
    time.sleep(0.3)
    assert tap._run and tap.active                           # yeni oturum yasiyor
    assert started == [1, 3] and finished == [1]             # yalniz eski dongu bitti
    tap.stop()
    time.sleep(0.2)
    assert sorted(finished) == [1, 3]


def test_audio_effect_reads_five_bands_from_bass_to_treble():
    eff = EFFECTS["Ses tepkili"]()
    loud_left = Context(audio=[1, 0, 0, 0, 0])
    for _ in range(40):
        f = eff.render(0, 1 / 30, loud_left)
    assert lum(f[0]) > 6 * lum(f[4])                                     # bas solda yanar
