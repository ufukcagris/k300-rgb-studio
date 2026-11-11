"""Klavye duzenleri: her tus geometrisi + tarama koduyla tanimli.

Hem onizleme cizimi hem de "hangi tusa basildi" eslemesi bu tablodan beslenir; ikisi
birbirinden sapamaz. Birim = 1 tus genisligi; tam boy klavye 22.5 x 6.5 birimdir
(ana blok 15, bosluk .25, gezinme 3, bosluk .25, numpad 4).

  tr : Turkce Q (ISO): buyuk L seklinde Enter, kisa sol Shift + "<>" tusu
  us : Global Q (ANSI): genis Enter, "\\" tusu, uzun sol Shift

`scan`/`ext` Windows dusuk seviyeli klavye kancasindan gelen tarama kodu ve "genisletilmis"
bayragidir. NumLock, Pause, PrintScreen gibi tuslar bayragi tutarsiz bildirdigi icin sanal
tus koduyla (`vk`) taninir.
"""
from __future__ import annotations

from dataclasses import dataclass

TOTAL_W, TOTAL_H = 22.5, 6.5
LAYOUT_NAMES = ("tr", "us")

VK_PAUSE, VK_SNAPSHOT, VK_NUMLOCK, VK_SCROLL = 0x13, 0x2C, 0x90, 0x91
# Sag taraftaki degistiriciler bayragi tutarsiz bildirebilir (sag Shift genisletilmis gelebilir):
VK_LWIN, VK_APPS, VK_RSHIFT, VK_RCONTROL, VK_RMENU = 0x5B, 0x5D, 0xA1, 0xA3, 0xA5
# Fn Windows'a tus olarak gelmez; klavyenin isik arayuzunden okunur (inputs.is_fn_report).
# Gercek sanal tus kodlari 0-255 arasi oldugundan bu sahte kod hicbir tusla cakismaz.
VK_FN = 0x10000


@dataclass(frozen=True)
class Key:
    label: str                 # "ust\nalt" (ust: Shift ile, alt: normal) ya da tek satir
    x: float
    y: float
    w: float = 1.0
    h: float = 1.0
    scan: int | None = None
    ext: bool = False
    vk: int | None = None
    iso_enter: bool = False    # L seklindeki Turkce Enter

    @property
    def cx(self) -> float:
        """Tusun yatay merkezi (efekt konumu buradan turetilir)."""
        return 14.25 if self.iso_enter else self.x + self.w / 2


def _row(y: float, x: float, items) -> list[Key]:
    """items: (etiket, genislik, scan[, ext[, vk]]); etiket None ise bosluk."""
    out: list[Key] = []
    for it in items:
        label, w = it[0], it[1]
        if label is None:
            x += w
            continue
        scan = it[2] if len(it) > 2 else None
        ext = it[3] if len(it) > 3 else False
        vk = it[4] if len(it) > 4 else None
        out.append(Key(label, x, y, w, 1.0, scan, ext, vk))
        x += w
    return out


def _right_side() -> list[Key]:
    """F satirinin sagi, gezinme blogu, oklar ve numpad (iki duzende de ayni)."""
    k: list[Key] = []
    k += _row(0, 15.25, [("PrtSc", 1, None, False, VK_SNAPSHOT), ("ScrLk", 1, 0x46, False, VK_SCROLL),
                         ("Pause", 1, None, False, VK_PAUSE)])
    k += _row(1.5, 15.25, [("Ins", 1, 0x52, True), ("Home", 1, 0x47, True), ("PgUp", 1, 0x49, True)])
    k += _row(2.5, 15.25, [("Del", 1, 0x53, True), ("End", 1, 0x4F, True), ("PgDn", 1, 0x51, True)])
    k += _row(4.5, 16.25, [("↑", 1, 0x48, True)])
    k += _row(5.5, 15.25, [("←", 1, 0x4B, True), ("↓", 1, 0x50, True), ("→", 1, 0x4D, True)])
    # numpad (x = 18.5)
    k += _row(1.5, 18.5, [("Num", 1, None, False, VK_NUMLOCK), ("/", 1, 0x35, True),
                          ("*", 1, 0x37), ("-", 1, 0x4A)])
    k += _row(2.5, 18.5, [("7", 1, 0x47), ("8", 1, 0x48), ("9", 1, 0x49)])
    k.append(Key("+", 21.5, 2.5, 1.0, 2.0, 0x4E))
    k += _row(3.5, 18.5, [("4", 1, 0x4B), ("5", 1, 0x4C), ("6", 1, 0x4D)])
    k += _row(4.5, 18.5, [("1", 1, 0x4F), ("2", 1, 0x50), ("3", 1, 0x51)])
    k.append(Key("↵", 21.5, 4.5, 1.0, 2.0, 0x1C, True))
    k += _row(5.5, 18.5, [("0", 2, 0x52), (".", 1, 0x53)])
    return k


def _frow() -> list[Key]:
    items = [("Esc", 1, 0x01), (None, 1)]
    items += [(f"F{i + 1}", 1, 0x3B + i) for i in range(4)]
    items += [(None, 0.5)] + [(f"F{i + 5}", 1, 0x3F + i) for i in range(4)]
    items += [(None, 0.5), ("F9", 1, 0x43), ("F10", 1, 0x44), ("F11", 1, 0x57), ("F12", 1, 0x58)]
    return _row(0, 0, items)


def _bottom_row() -> list[Key]:
    return _row(5.5, 0, [("Ctrl", 1.25, 0x1D), ("⊞", 1.25, 0x5B, True, VK_LWIN), ("Alt", 1.25, 0x38),
                         ("", 6.25, 0x39), ("AltGr", 1.25, 0x38, True, VK_RMENU), ("Fn", 1.25, None, False, VK_FN),
                         ("☰", 1.25, 0x5D, True, VK_APPS), ("Ctrl", 1.25, 0x1D, True, VK_RCONTROL)])


def _tr() -> list[Key]:
    k = _frow()
    k += _row(1.5, 0, [("\"\né", 1, 0x29), ("!\n1", 1, 0x02), ("'\n2", 1, 0x03), ("^\n3", 1, 0x04),
                       ("+\n4", 1, 0x05), ("%\n5", 1, 0x06), ("&\n6", 1, 0x07), ("/\n7", 1, 0x08),
                       ("(\n8", 1, 0x09), (")\n9", 1, 0x0A), ("=\n0", 1, 0x0B), ("?\n*", 1, 0x0C),
                       ("_\n-", 1, 0x0D), ("⌫", 2, 0x0E)])
    letters = "QWERTYUIOPĞÜ"
    k += _row(2.5, 0, [("⇥", 1.5, 0x0F)] + [(c, 1, 0x10 + i) for i, c in enumerate(letters)])
    k.append(Key("↵", 13.5, 2.5, 1.5, 1.0, 0x1C, False, None, True))
    row3 = "ASDFGHJKLŞİ"
    k += _row(3.5, 0, [("Caps", 1.75, 0x3A)] + [(c, 1, 0x1E + i) for i, c in enumerate(row3)]
              + [(";\n,", 1, 0x2B)])
    row4 = "ZXCVBNMÖÇ"
    k += _row(4.5, 0, [("⇧", 1.25, 0x2A), (">\n<", 1, 0x56)] + [(c, 1, 0x2C + i) for i, c in enumerate(row4)]
              + [(":\n.", 1, 0x35), ("⇧", 2.75, 0x36, False, VK_RSHIFT)])
    return k + _bottom_row() + _right_side()


def _us() -> list[Key]:
    k = _frow()
    k += _row(1.5, 0, [("~\n`", 1, 0x29), ("!\n1", 1, 0x02), ("@\n2", 1, 0x03), ("#\n3", 1, 0x04),
                       ("$\n4", 1, 0x05), ("%\n5", 1, 0x06), ("^\n6", 1, 0x07), ("&\n7", 1, 0x08),
                       ("*\n8", 1, 0x09), ("(\n9", 1, 0x0A), (")\n0", 1, 0x0B), ("_\n-", 1, 0x0C),
                       ("+\n=", 1, 0x0D), ("⌫", 2, 0x0E)])
    row2 = "QWERTYUIOP"
    k += _row(2.5, 0, [("⇥", 1.5, 0x0F)] + [(c, 1, 0x10 + i) for i, c in enumerate(row2)]
              + [("{\n[", 1, 0x1A), ("}\n]", 1, 0x1B), ("|\n\\", 1.5, 0x2B)])
    row3 = "ASDFGHJKL"
    k += _row(3.5, 0, [("Caps", 1.75, 0x3A)] + [(c, 1, 0x1E + i) for i, c in enumerate(row3)]
              + [(":\n;", 1, 0x27), ("\"\n'", 1, 0x28), ("↵", 2.25, 0x1C)])
    row4 = "ZXCVBNM"
    k += _row(4.5, 0, [("⇧", 2.25, 0x2A)] + [(c, 1, 0x2C + i) for i, c in enumerate(row4)]
              + [("<\n,", 1, 0x33), (">\n.", 1, 0x34), ("?\n/", 1, 0x35), ("⇧", 2.75, 0x36, False, VK_RSHIFT)])
    return k + _bottom_row() + _right_side()


LAYOUTS: dict[str, list[Key]] = {"tr": _tr(), "us": _us()}

_LOOKUP: dict[str, tuple[dict, dict]] = {}


def keys(name: str) -> list[Key]:
    return LAYOUTS.get(name) or LAYOUTS["tr"]


def _lookup(name: str) -> tuple[dict, dict]:
    if name not in _LOOKUP:
        by_scan: dict = {}
        by_vk: dict = {}
        for i, key in enumerate(keys(name)):
            if key.vk is not None:
                by_vk[key.vk] = i
            if key.scan is not None:
                by_scan[(key.scan, key.ext)] = i
        _LOOKUP[name] = (by_scan, by_vk)
    return _LOOKUP[name]


def locate(name: str, scan: int, ext: bool, vk: int) -> int:
    """Basilan tusun duzendeki sira numarasi; tanimsiz tus (medya tuslari vb.) icin -1.

    Once sanal tus koduna bakilir (NumLock/Pause/PrintScreen/ScrollLock bayragi tutarsiz
    bildirir), sonra (tarama kodu, genisletilmis) cifti.
    """
    by_scan, by_vk = _lookup(name)
    if vk in by_vk:
        return by_vk[vk]
    return by_scan.get((scan, bool(ext)), -1)


def x_norm(name: str, index: int) -> float:
    """Tusun yatay konumu 0-1 (0 = klavyenin solu, 1 = sagi)."""
    return keys(name)[index].cx / TOTAL_W
