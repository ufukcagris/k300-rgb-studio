import math

import pytest

from k300fx.effects import EFFECT_CLASSES, EFFECTS, HW_SAMPLES, THEME_ORDER, ZONES, Context, theme_rgb


def _valid(frame):
    assert len(frame) in (ZONES, HW_SAMPLES)
    for px in frame:
        assert len(px) == 3
        assert all(math.isfinite(c) and -0.001 <= c <= 255.001 for c in px), px


@pytest.mark.parametrize("cls", EFFECT_CLASSES, ids=lambda c: c.name)
def test_effect_renders_valid_frames(cls):
    ctx = Context(typing_rate=6, cpu=55, ram=70, audio=[0.1, 0.5, 0.9, 0.4, 0.2])
    themes = THEME_ORDER if cls.theme is not None else (None,)
    for theme in themes:
        eff = cls({"theme": theme} if theme else None)
        eff.on_key(1.0, 0.0)
        eff.on_key(3.5, 0.1)
        for i in range(120):
            _valid(eff.render(i / 60, 1 / 60, ctx))


def test_every_theme_samples_in_range():
    for name in THEME_ORDER:
        for u in (0.0, 0.25, 0.5, 0.99, 1.0, 3.7):
            c = theme_rgb(name, "#10c0ff", u)
            assert all(0 <= v <= 255.001 for v in c), (name, u, c)


def test_effect_names_are_unique():
    assert len(EFFECTS) == len(EFFECT_CLASSES)


def test_ripple_spreads_from_center_and_reflects():
    eff = EFFECTS["Tuştan yayılan dalga"]()
    ctx = Context()
    eff.on_key(2.0, 0.0)                       # tam ortadan
    frames = [eff.render(i / 60, 1 / 60, ctx) for i in range(90)]
    peak = lambda i, z: max(frames[i][z])      # noqa: E731
    # t=0: merkez parlak, kenar sonuk
    assert peak(0, 2) > 200 and peak(0, 0) < 120
    # dalga kenarlara ulasir
    assert max(peak(i, 0) for i in range(10, 40)) > 150
    # kenardan yansima: merkez, disari giden dalganin ardindan tekrar parlar
    mid = [peak(i, 2) for i in range(90)]
    assert max(mid[40:80]) > min(mid[15:40]) + 15


def test_ripple_stays_quiet_without_keys():
    eff = EFFECTS["Tuştan yayılan dalga"]()
    frame = eff.render(1.0, 1 / 60, Context())
    assert max(max(px) for px in frame) < 60       # yalnizca hafif ortam isigi


def test_press_glow_heats_up_with_fast_typing():
    def hottest(n):
        g = EFFECTS["Basış parlaması"]({"theme": "Özel", "custom": "#ff2a6d"})
        for _ in range(n):
            g.on_key(2.0, 0.0)
        return min(g.render(0.0, 1 / 60, Context())[2])     # en dusuk kanal: beyaza yaklasma olcusu
    assert hottest(6) > hottest(1)


def test_typing_heat_goes_from_blue_to_red():
    eff = EFFECTS["Yazma hızı ısısı"]()
    slow = eff.render(0.0, 1 / 60, Context(typing_rate=0))
    for i in range(240):
        fast = eff.render(i / 60, 1 / 60, Context(typing_rate=12))
    assert slow[0][2] > slow[0][0]            # mavi baskin
    assert fast[0][0] > fast[0][2]            # kirmizi baskin


def test_system_load_fills_zones():
    eff = EFFECTS["Sistem yükü"]()
    low = eff.render(0, 1 / 60, Context(cpu=10))
    high = eff.render(0, 1 / 60, Context(cpu=100))
    assert sum(map(max, high)) > sum(map(max, low))
