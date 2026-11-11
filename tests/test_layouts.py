import pytest

from k300fx import layouts as L


def _label(name, scan, ext=False, vk=0):
    i = L.locate(name, scan, ext, vk)
    return L.keys(name)[i].label.split("\n")[-1] if i >= 0 else None


@pytest.mark.parametrize("name", L.LAYOUT_NAMES)
def test_scan_codes_are_unique_and_inside_the_board(name):
    seen = set()
    for k in L.keys(name):
        if k.scan is not None:
            assert (k.scan, k.ext) not in seen, (name, k.label)
            seen.add((k.scan, k.ext))
        assert k.x >= 0 and k.y >= 0
        assert k.x + k.w <= L.TOTAL_W + 1e-9 and k.y + k.h <= L.TOTAL_H + 1e-9


def test_key_counts_match_the_physical_boards():
    assert len(L.keys("us")) == 104          # ANSI tam boy
    assert len(L.keys("tr")) == 105          # ISO: fazladan "<>" tusu


def test_turkish_letters_sit_on_the_right_physical_keys():
    for scan, letter in ((0x1A, "Ğ"), (0x1B, "Ü"), (0x27, "Ş"), (0x28, "İ"), (0x33, "Ö"), (0x34, "Ç")):
        assert _label("tr", scan) == letter
    # ayni fiziksel tuslar Global Q'da noktalama isaretleridir
    assert _label("us", 0x1A) == "[" and _label("us", 0x27) == ";"


def test_layouts_differ_where_iso_and_ansi_differ():
    tr, us = L.keys("tr"), L.keys("us")
    assert any(k.iso_enter for k in tr) and not any(k.iso_enter for k in us)
    assert L.locate("tr", 0x56, False, 0) >= 0 and L.locate("us", 0x56, False, 0) == -1   # "<>" yalniz ISO'da
    assert _label("us", 0x2B) == "\\" and _label("tr", 0x2B) == ","
    us_enter = us[L.locate("us", 0x1C, False, 0)]
    assert us_enter.w == 2.25                                  # ANSI Enter genis
    shift = lambda keys: keys[L.locate("tr" if keys is tr else "us", 0x2A, False, 0)].w   # noqa: E731
    assert shift(tr) == 1.25 and shift(us) == 2.25            # ISO'da sol Shift kisa


def test_numlock_pause_printscreen_found_by_virtual_key_even_with_odd_flags():
    for name in L.LAYOUT_NAMES:
        # Windows NumLock'u genisletilmis bayrakla bildirebilir: tarama koduyla bulunamaz, vk ile bulunur
        for ext in (False, True):
            assert _label(name, 0x45, ext, L.VK_NUMLOCK) == "Num"
        assert _label(name, 0x45, False, L.VK_PAUSE) == "Pause"
        assert _label(name, 0x37, True, L.VK_SNAPSHOT) == "PrtSc"
        assert _label(name, 0x46, False, L.VK_SCROLL) == "ScrLk"


def test_extended_flag_separates_navigation_from_numpad():
    for name in L.LAYOUT_NAMES:
        assert _label(name, 0x47, True) == "Home" and _label(name, 0x47, False) == "7"
        assert _label(name, 0x4D, True) == "→" and _label(name, 0x4D, False) == "6"
        assert _label(name, 0x1C, False) == "↵" and _label(name, 0x1C, True) == "↵"
        assert L.locate(name, 0x1C, True, 0) != L.locate(name, 0x1C, False, 0)      # numpad Enter != Enter
        assert L.locate(name, 0x35, True, 0) != L.locate(name, 0x35, False, 0)      # numpad / != ana /
        assert L.locate(name, 0x1D, True, 0) != L.locate(name, 0x1D, False, 0)      # sag Ctrl != sol Ctrl
        assert L.locate(name, 0x38, True, 0) != L.locate(name, 0x38, False, 0)      # AltGr != Alt


def test_right_shift_and_right_modifiers_are_found_whatever_flags_windows_reports():
    """Gercek hata: sag Shift genisletilmis bayrakla gelince hic gorunmuyordu."""
    for name in L.LAYOUT_NAMES:
        keys = L.keys(name)
        for ext in (False, True):
            rshift = L.locate(name, 0x36, ext, L.VK_RSHIFT)
            assert rshift >= 0 and keys[rshift].w == 2.75 and keys[rshift].label == "⇧"
            assert keys[L.locate(name, 0x1D, ext, L.VK_RCONTROL)].x > 13       # sag Ctrl (sol degil)
            assert keys[L.locate(name, 0x38, ext, L.VK_RMENU)].label == "AltGr"
        assert L.locate(name, 0x2A, False, 0xA0) == L.locate(name, 0x2A, False, 0)   # sol Shift tarama koduyla


def test_unknown_keys_are_ignored_not_misplaced():
    for name in L.LAYOUT_NAMES:
        assert L.locate(name, 0x20, True, 0xAF) == -1            # ses acma gibi medya tuslari
        assert L.locate(name, 0x7F, False, 0) == -1


def test_positions_run_left_to_right():
    for name in L.LAYOUT_NAMES:
        def x(scan, ext=False, vk=0):
            return L.x_norm(name, L.locate(name, scan, ext, vk))
        assert x(0x01) < x(0x10) < x(0x19) < x(0x47, True) < x(0x4C) < x(0x1C, True)
        assert 0 < x(0x01) < x(0x1C, True) < 1


def test_iso_enter_is_solid_in_the_preview_path():
    from PySide6.QtCore import QPointF

    from k300fx import ui
    key = next(k for k in L.keys("tr") if k.iso_enter)
    s = 30.0
    path = ui._key_path(key, s, 0.0, 0.0)
    assert path.contains(QPointF(14.25 * s, 3.0 * s))        # ust kol
    assert path.contains(QPointF(14.4 * s, 4.0 * s))         # alt kol
    assert path.contains(QPointF(14.4 * s, 3.5 * s))         # birlesme noktasi (delik olmamali)
    assert not path.contains(QPointF(13.6 * s, 4.0 * s))     # L'nin disinda kalan kose
