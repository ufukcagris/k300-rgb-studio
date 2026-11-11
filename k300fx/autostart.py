"""Windows ile baslat: HKCU\\...\\Run anahtari (yonetici yetkisi gerekmez).

Yalnizca paketlenmis (.exe) surumde calisir; kaynak koddan calistirirken desteklenmez.
"""
from __future__ import annotations

import sys

try:
    import winreg
except ImportError:  # pragma: no cover  (Windows disi)
    winreg = None

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "K300RGBStudio"


def supported() -> bool:
    return winreg is not None and bool(getattr(sys, "frozen", False))


def _command() -> str:
    return f'"{sys.executable}" --minimized'


def is_enabled() -> bool:
    if not supported():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as k:
            return winreg.QueryValueEx(k, _NAME)[0] == _command()
    except OSError:
        return False


def set_enabled(on: bool) -> bool:
    """True: istenen durum uygulandi."""
    if not supported():
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, _NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(k, _NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
