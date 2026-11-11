"""Ayarlar: %APPDATA%\\K300FX\\settings.json"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "version": 8,
    "language": "auto",      # auto | tr | en
    "layout": "tr",          # tr = Turkce Q (ISO) | us = Global Q (ANSI)
    "effect": "Tuştan yayılan dalga",
    "params": {},            # {efekt_adi: {param: deger}}
    "brightness": 1.0,
    "rules": {},             # {"islem.exe": "efekt adi"}
    "rules_enabled": False,
    "minimize_to_tray": True,
    "hw_speeds": {},         # {"mod": hiz} klavyenin sakladigi son donanim efekti hizi (mod secilince ilk 2 sn bu hizla oynar)
}


def path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "K300FX" / "settings.json"


def load() -> dict:
    data = dict(DEFAULTS)
    saved: dict = {}
    try:
        saved = json.loads(path().read_text(encoding="utf-8"))
        data.update(saved)
    except (OSError, ValueError):
        pass
    # Surum, DEFAULTS'tan degil KAYITLI dosyadan okunur (yoksa 1). Aksi halde varsayilan
    # surum numarasi eski dosyayi "guncel" gosterir ve tasima hic calismaz.
    ver = saved.get("version", 1) if isinstance(saved, dict) else 1
    if ver < 7:      # v7: efekt ayarlari sadelesti (renk temasi + hiz); eski ayarlar uyumsuz
        data["params"] = {}
    # v6: kare hizi ve gonderim hizi artik sabit (engine.py); eski ayarlar silinir
    data.pop("fps", None)
    data.pop("send_fps", None)
    if ver < 8:      # v8: "Yazma hizi isisi" kaydirici anlami degisti (tus/sn esigi)
        data["params"].pop("Yazma hızı ısısı", None)
    data["version"] = 8
    return data


def save(data: dict) -> None:
    p = path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass
