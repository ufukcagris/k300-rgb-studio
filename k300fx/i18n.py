"""Cok dilli arayuz (Turkce / English).

Kodda ve ayar dosyasinda KIMLIK olarak Turkce metinler kullanilir; ekranda gosterirken
`tr()` ile cevrilir. Ingilizce secilmediyse metin oldugu gibi doner. Ceviri tablosunda
olmayan metin de oldugu gibi gosterilir (hata vermez).
"""
from __future__ import annotations

_lang = "tr"

LANGUAGES = ("auto", "tr", "en")


def resolve(setting: str) -> str:
    """'auto' ise sistem diline bak: Turkce ise tr, degilse en."""
    if setting in ("tr", "en"):
        return setting
    try:
        from PySide6.QtCore import QLocale
        return "tr" if QLocale.system().language() == QLocale.Language.Turkish else "en"
    except Exception:   # noqa: BLE001
        return "en"


def set_language(code: str) -> None:
    global _lang
    _lang = code if code in ("tr", "en") else "tr"


def language() -> str:
    return _lang


def tr(text: str) -> str:
    return EN.get(text, text) if _lang == "en" else text


EN = {
    # ---- efektler
    "Tuştan yayılan dalga": "Key ripple",
    "Bastığın tuştan su dalgası gibi yayılır, kenarlardan yansır.":
        "Spreads like a water wave from the key you press and bounces off the edges.",
    "Basış parlaması": "Press glow",
    "Basılan bölge beyaz-sıcak parlar, renge dönüp söner.":
        "The pressed zone flashes white-hot, turns to colour and fades.",
    "Yazma hızı ısısı": "Typing heat",
    "Yavaş yazarken mavi, hızlandıkça kırmızıya döner.": "Blue when you type slowly, turning red as you speed up.",
    "Sörf": "Surf",
    "Sürükleme": "Drift",
    "Gökkuşağı renkleri klavye boyunca soldan sağa kayar (klavyenin kendi efekti, renkler sabit).": "Rainbow colours slide along the keyboard from left to right (built-in keyboard effect, fixed colours).",
    "Dalga ortadan uçlara yayılır, sonraki renkte uçlardan ortaya döner; renkler sırayla değişir (klavyenin kendi efekti, renkler sabit).": "A wave spreads from the middle to the ends, the next colour returns from the ends to the middle; colours change in turn (built-in keyboard effect, fixed colours).",
    "Seçtiğin renk teması klavye boyunca akar.": "Your colour theme flows across the keyboard.",
    "Nefes": "Breathe",
    "Yumuşakça parlar ve söner.": "Glows and fades softly.",
    "Aurora": "Aurora",
    "Kutup ışıkları gibi salınan yumuşak renkler.": "Soft colours swaying like the northern lights.",
    "Ateş": "Fire",
    "Titreyen kor renkleri.": "Flickering ember colours.",
    "Sabit renk": "Static colour",
    "Seçtiğin renk teması 5 bölgeye yayılır; Özel'de her bölgeye ayrı renk seçersin.":
        "Your colour theme is spread over the 5 zones; with Custom you pick a colour for each zone.",
    "Ses tepkili": "Audio reactive",
    "Müzik 5 frekans bandına ayrılır: bas solda, tiz sağda.":
        "Music is split into 5 frequency bands: bass on the left, treble on the right.",
    "Sistem yükü": "System load",
    "İşlemci ya da RAM kullanımı bölgelerde bar olarak görünür.": "CPU or RAM usage shown as a bar across the zones.",
    # ---- kaydirici ve secenekler
    "Dalga hızı": "Ripple speed",
    "Parlama süresi": "Glow duration",
    "Hız": "Speed",
    "Hassasiyet": "Sensitivity",
    "Kırmızı için hız": "Speed for full red",
    "{:.0f} tuş/sn": "{:.0f} keys/s",
    "Kaynak": "Source",
    "Parlaklık": "Brightness",
    # ---- renk temalari
    "Gökkuşağı": "Rainbow", "Neon": "Neon", "Okyanus": "Ocean", "Gün batımı": "Sunset",
    "Orman": "Forest", "Buz": "Ice", "Siberpunk": "Cyberpunk", "Retro dalga": "Retrowave",
    "Şeker": "Candy", "Lavanta": "Lavender", "Matrix": "Matrix", "Altın": "Gold", "Sakura": "Sakura",
    "Özel": "Custom",
    # ---- ana pencere
    "K300 RGB Stüdyo": "K300 RGB Studio",
    "EFEKTLER": "EFFECTS", "RENK TEMASI": "COLOUR THEME",
    "Ayarlar": "Settings", "Başlatılıyor…": "Starting…",
    "Klavye bağlı": "Keyboard connected", "Klavye aranıyor…": "Looking for keyboard…",
    "Klavye bağlantısı koptu, yeniden deneniyor…": "Keyboard disconnected, retrying…",
    "Tuş dinleyici başlatılamadı:": "Key listener could not start:",
    "bilinmeyen hata": "unknown error", "Ses yakalanamadı:": "Could not capture audio:",
    "Pencereyi göster": "Show window", "Çıkış": "Exit",
    "Simge durumuna küçült": "Minimise", "Büyüt": "Maximise", "Önceki boyut": "Restore", "Kapat": "Close",
    # ---- ayarlar penceresi
    "Dil": "Language", "Otomatik (sistem dili)": "Automatic (system language)",
    "Klavye düzeni": "Keyboard layout", "Türkçe Q": "Turkish Q", "Global Q (ABD)": "Global Q (US)",
    "Windows ile birlikte başlat": "Start with Windows",
    "Pencereyi kapatınca sistem tepsisinde çalışmaya devam et": "Keep running in the system tray when the window is closed",
    "Uygulamaya özel profiller…": "Per-application profiles…", "Hakkında…": "About…",
    "Tamam": "OK", "İptal": "Cancel",
    "Tuş dinleyici yalnızca basılan tuşun klavyedeki konumunu kullanır; hangi harfe bastığın hiçbir yerde saklanmaz.":
        "The key listener only uses the position of the pressed key on the keyboard; what you type is never stored anywhere.",
    # ---- kurallar
    "Uygulamaya özel profil": "Per-application profile",
    "Bir uygulama ön plandayken otomatik olarak seçtiğin efekte geçilir. İşlem adını Görev Yöneticisi'nde görebilirsin (ör. game.exe).":
        "While an application is in the foreground, the effect you choose is applied automatically. "
        "You can find the process name in Task Manager (e.g. game.exe).",
    "Kuralları etkinleştir": "Enable rules", "İşlem adı": "Process name", "Efekt": "Effect",
    "Kural ekle": "Add rule", "Seçileni sil": "Delete selected",
    # ---- ozel renk
    "Özel renk": "Custom colour", "Renk 1": "Colour 1", "Renk 2": "Colour 2",
    "Bölge renkleri": "Zone colours", "Bölge": "Zone",
    "Her bölgeye ayrı renk seç (soldan sağa).": "Pick a colour for each zone (left to right).",
    "Tema bu iki renk arasında geçiş yapar.": "The theme blends between these two colours.",
    # ---- hakkinda
    "Hakkında": "About", "Sürüm": "Version", "Geliştirici": "Developer", "GitHub profili": "GitHub profile",
    "Lenovo Legion K300 klavye için açık kaynak ışık efekti programı.":
        "Open-source lighting effects app for the Lenovo Legion K300 keyboard.",
    "MIT lisansı altında açık kaynaktır.": "Open source under the MIT licence.",
    "Resmî bir Lenovo ürünü değildir; Lenovo ile bağlantısı yoktur. Lenovo ve Legion ilgili sahiplerinin ticari markalarıdır.":
        "Not an official Lenovo product and not affiliated with Lenovo. "
        "Lenovo and Legion are trademarks of their respective owners.",
    "Program zaten çalışıyor (sistem tepsisine bak).": "The app is already running (check the system tray).",
}
