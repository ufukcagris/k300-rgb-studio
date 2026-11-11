import pytest

from k300fx import i18n, layouts
from k300fx import settings as cfg
from k300fx.app import Controller
from k300fx.device import FakeDevice
from k300fx.effects import CUSTOM, EFFECT_CLASSES, THEME_ORDER, theme_rgb
from k300fx.engine import Engine


@pytest.fixture(autouse=True)
def _reset_language():
    yield
    i18n.set_language("tr")


def test_every_visible_string_has_an_english_translation():
    import re

    def needs_translation(text):          # "{:.1f}×" gibi harf icermeyen bicimler cevrilmez
        return bool(text) and any(ch.isalpha() for ch in re.sub(r"\{[^}]*\}", "", text))

    missing = []
    for c in EFFECT_CLASSES:
        for text in (c.name, c.description, c.speed_label, c.speed_fmt if c.speed_label else None,
                     *(e.label for e in c.extras)):
            if needs_translation(text) and text not in i18n.EN:
                missing.append(text)
    missing += [t for t in THEME_ORDER if t not in i18n.EN and t != "Aurora"]
    assert not missing, missing


def test_translation_switches_with_language_and_never_fails():
    i18n.set_language("tr")
    assert i18n.tr("Nefes") == "Nefes"
    i18n.set_language("en")
    assert i18n.tr("Nefes") == "Breathe"
    assert i18n.tr("bu metin tabloda yok") == "bu metin tabloda yok"   # eksik ceviri hata vermez
    assert i18n.resolve("tr") == "tr" and i18n.resolve("en") == "en" and i18n.resolve("auto") in ("tr", "en")


def test_custom_theme_blends_two_colours():
    a, b = (255, 0, 0), (0, 0, 255)
    assert theme_rgb(CUSTOM, "#ff0000", 0.0, "#0000ff") == pytest.approx(a)
    assert theme_rgb(CUSTOM, "#ff0000", 0.5, "#0000ff") == pytest.approx(b)
    mid = theme_rgb(CUSTOM, "#ff0000", 0.25, "#0000ff")
    assert 100 < mid[0] < 155 and 100 < mid[2] < 155


def _engine(layout="tr", language="tr"):
    s = cfg.load()
    s.update(params={}, layout=layout, language=language, effect="Tuştan yayılan dalga")
    return Engine(FakeDevice(), s), s


@pytest.mark.parametrize("layout", layouts.LAYOUT_NAMES)
@pytest.mark.parametrize("language", ["tr", "en"])
def test_window_builds_and_paints_in_every_language_and_layout(qapp, layout, language):
    eng, s = _engine(layout, language)
    ctl = Controller(eng, s)
    win = ctl.make()
    win.show()
    qapp.processEvents()
    for name, card in win.cards.items():                 # her efekt secilebilir
        card.click()
        assert win.title.text() == i18n.tr(name)
    eng._on_key(5, 0.5, 0.0)
    win.keyboard.flash(5)
    assert not win.grab().isNull()
    win.dispose()


def test_language_switch_rebuilds_the_window_with_the_same_engine(qapp):
    eng, s = _engine("tr", "tr")
    ctl = Controller(eng, s)
    win = ctl.make()
    win.show()
    win.cards["Aurora"].click()
    assert win.title.text() == "Aurora"
    s["language"] = "en"
    ctl.rebuild()
    qapp.processEvents()
    new = ctl.win
    assert new is not win and new.engine is eng
    assert new.title.text() == "Aurora" and new.titlebar.title.text() == "K300 RGB Studio"
    assert eng.effect.name == "Aurora"                       # secili efekt korunur
    new.dispose()


def test_layout_switch_updates_preview_and_key_mapping(qapp):
    eng, s = _engine("tr")
    ctl = Controller(eng, s)
    win = ctl.make()
    win.apply_layout("us")
    assert eng.keys.layout == "us" and win.keyboard._layout == "us" and s["layout"] == "us"
    assert len(layouts.keys(win.keyboard._layout)) == 104
    win.dispose()


def test_dialogs_construct_in_both_languages(qapp):
    from k300fx import ui
    for lang in ("tr", "en"):
        eng, s = _engine("tr", lang)
        ctl = Controller(eng, s)
        win = ctl.make()
        for dlg in (ui.SettingsDialog(win), ui.AboutDialog(win), ui.RulesDialog(win, {"game.exe": "Ateş"}, True),
                    ui.CustomColorDialog(win, "#ff0000", "#0000ff")):
            assert dlg.windowTitle()
            dlg.deleteLater()
        win.dispose()


def test_dialogs_use_the_app_frame_not_the_windows_one(qapp):
    from PySide6.QtCore import Qt

    from k300fx import ui
    eng, s = _engine()
    win = Controller(eng, s).make()
    dialogs = (ui.SettingsDialog(win), ui.AboutDialog(win), ui.RulesDialog(win, {}, False),
               ui.CustomColorDialog(win, "#ff0000", "#0000ff"), ui.ColorPickerDialog(win, "#112233", "x"))
    for dlg in dialogs:
        assert dlg.windowFlags() & Qt.FramelessWindowHint, type(dlg).__name__
        assert dlg.findChildren(ui.DialogBar), type(dlg).__name__            # ozel baslik cubugu var
    assert dialogs[-1].color() == "#112233"
    win.dispose()


def _spin(qapp, seconds):
    import time
    t = time.time()
    while time.time() - t < seconds:
        qapp.processEvents()
        time.sleep(0.01)


@pytest.mark.parametrize("language", ["tr", "en"])
def test_full_description_is_shown_in_the_side_panel_so_cards_need_no_tooltip(qapp, language):
    from k300fx import ui
    eng, s = _engine("tr", language)
    win = Controller(eng, s).make()
    win.show()
    for name, card in win.cards.items():
        card.click()
        assert win.desc.text() == i18n.tr(card.cls.description)       # kesilmeden, tam metin
        assert win.desc.wordWrap()                                    # uzunsa sarilir, kesilmez
        assert card.toolTip() == "" and not hasattr(card, "_tip")     # kartta balon yok
    win.dispose()


def test_fancy_tip_fades_in_and_out_instead_of_popping(qapp):
    from PySide6.QtCore import QRect

    from k300fx.effects import EFFECTS
    from k300fx.tips import FancyTip
    import time
    tip = FancyTip.instance()
    tip.prewarm()                                                  # uygulama da acilista boyle hazirlar
    tip.popup(QRect(100, 100, 220, 64), "Başlık", "Uzun bir açıklama metni. " * 6, EFFECTS["Aurora"])
    assert tip.isVisible() and tip.windowOpacity() < 0.5          # aniden degil, solarak baslar
    seen, t0 = [], time.time()
    while time.time() - t0 < 0.6:                                  # 10 ms araliklarla opaklik ornekle
        qapp.processEvents()
        seen.append(tip.windowOpacity())
        time.sleep(0.01)
    assert seen == sorted(seen)                                    # tek yone, geri gitmeden artar
    assert len({round(v, 2) for v in seen if 0.02 < v < 0.98}) >= 3   # ara degerlerden geciyor: kademeli
    assert seen[-1] > 0.99                                         # sonunda tam gorunur
    tip.dismiss()
    seen, t0 = [], time.time()
    while time.time() - t0 < 0.5:
        qapp.processEvents()
        seen.append(tip.windowOpacity())
        time.sleep(0.01)
    assert seen == sorted(seen, reverse=True)                      # kaybolurken de kademeli azalir
    assert any(0.02 < v < 0.98 for v in seen)
    assert not tip.isVisible()


def test_fancy_tip_grows_with_its_text_and_stays_on_screen(qapp):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QGuiApplication

    from k300fx.tips import FancyTip
    tip = FancyTip.instance()
    tip.popup(QRect(100, 100, 100, 40), "Kısa")
    small = (tip.width(), tip.height())
    tip.popup(QRect(100, 100, 100, 40), "Başlık", "Çok uzun bir açıklama. " * 12)
    assert tip.width() > small[0] and tip.height() > small[1]
    screen = QGuiApplication.primaryScreen().availableGeometry()
    tip.popup(QRect(screen.right() - 5, screen.bottom() - 5, 40, 40), "Köşede", "Ekranın dışına taşmamalı. " * 4)
    _spin(qapp, 0.3)
    assert screen.contains(tip.geometry().adjusted(0, 0, -1, -1))   # sag-alt kosede bile ekran icinde kalir
    FancyTip.hide_now()
    assert not tip.isVisible()


def test_theme_tip_does_not_flicker(qapp):
    """Titreme: balon fareyi yakalamamali ve daireler arasindaki bosluk balonu kapatmamali."""
    from PySide6.QtCore import QPointF, Qt

    from k300fx import ui
    from k300fx.tips import FancyTip

    tip = FancyTip.instance()
    assert tip.windowFlags() & Qt.WindowTransparentForInput          # fareyi yakalamaz

    class Move:                                                      # fare hareketi taklidi
        def __init__(self, p):
            self._p = p

        def position(self):
            return self._p

        def globalPosition(self):
            return self._p

    chips = ui.ThemeChips()
    chips.show()
    center = lambda i: chips._rect(i).center()                        # noqa: E731
    chips.mouseMoveEvent(Move(center(1)))
    _spin(qapp, 0.4)
    assert tip.isVisible() and not tip._hiding
    gap = QPointF(chips._rect(1).right() + chips.GAP / 2, chips._rect(1).center().y())
    assert chips._at(gap) == -1                                       # bosluktayiz
    chips.mouseMoveEvent(Move(gap))
    assert chips._hide_timer.isActive() and not tip._hiding           # hemen kapanmadi, kisa bekliyor
    chips.mouseMoveEvent(Move(center(2)))                             # yan daireye gecti
    assert not chips._hide_timer.isActive()                           # kapanma iptal
    _spin(qapp, 0.4)
    assert tip.isVisible() and tip.windowOpacity() > 0.99 and not tip._hiding
    chips.mouseMoveEvent(Move(QPointF(-50, -50)))                     # gercekten disari cikti
    _spin(qapp, 0.9)
    assert not tip.isVisible()
    chips.deleteLater()


def test_window_buttons_use_the_fancy_tip_not_the_native_one(qapp):
    from PySide6.QtCore import QEvent

    from k300fx import ui
    btn = ui.WinButton("close")
    btn.setToolTip("Kapat")
    assert btn.event(QEvent(QEvent.ToolTip))                       # yerel balon engellenir (True doner)
    assert btn._tip.interval() == 600


def test_about_shows_author_and_github_link(qapp):
    from k300fx import about, ui
    eng, s = _engine()
    win = Controller(eng, s).make()
    dlg = ui.AboutDialog(win)
    texts = " ".join(lab.text() for lab in dlg.findChildren(ui.QLabel))
    assert about.AUTHOR in texts and about.GITHUB_URL in texts
    win.dispose()
