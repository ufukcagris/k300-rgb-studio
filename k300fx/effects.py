"""Efektler. Her efekt 5 bolge icin RGB (0-255) uretir.

Kullaniciya yalnizca iki sey sunulur: renk temasi ve tek bir kaydirici. Fizik ve zamanlama
sabitleri (yayilma kalinligi, sonme suresi, yansima...) elle ayarlanmis degerlerle gomulu.

Efekt, tema ve secenek adlari ayar dosyasinda KIMLIK olarak saklanir (Turkce); ekranda
gosterilen ceviri k300fx/i18n.py icindedir.
"""
from __future__ import annotations

import colorsys
import math
import random
import re
from dataclasses import dataclass, field

ZONES = 5

# --------------------------------------------------------------------- renk temalari
RAINBOW = "Gökkuşağı"
CUSTOM = "Özel"
THEMES: dict[str, list | None] = {
    RAINBOW: None,                                            # ton dongusu
    "Aurora": [(0, 255, 150), (0, 200, 255), (140, 80, 255), (255, 70, 190)],
    "Neon": [(255, 0, 200), (0, 220, 255), (140, 40, 255)],
    "Okyanus": [(0, 90, 255), (0, 210, 255), (0, 255, 190)],
    "Gün batımı": [(255, 70, 40), (255, 0, 120), (150, 40, 255)],
    "Orman": [(0, 255, 110), (150, 255, 0), (0, 190, 160)],
    "Buz": [(200, 235, 255), (60, 170, 255), (120, 100, 255)],
    "Ateş": [(255, 30, 0), (255, 130, 0), (255, 220, 40)],
    "Siberpunk": [(255, 230, 0), (255, 0, 170), (0, 230, 255)],
    "Retro dalga": [(255, 0, 140), (255, 120, 0), (120, 0, 255)],
    "Şeker": [(255, 120, 200), (120, 255, 220), (255, 230, 120)],
    "Lavanta": [(190, 140, 255), (255, 160, 230), (120, 170, 255)],
    "Matrix": [(0, 255, 70), (0, 140, 40), (160, 255, 160)],
    "Altın": [(255, 200, 40), (255, 140, 0), (255, 240, 170)],
    "Sakura": [(255, 150, 190), (255, 220, 235), (255, 100, 150)],
    CUSTOM: None,                                             # iki renk, kullanici secer
}
THEME_ORDER = tuple(THEMES)
DEFAULT_ZONES = ("#ff2a00", "#ff9000", "#ffffff", "#0090ff", "#2a00ff")      # "Sabit renk" > Ozel icin baslangic


@dataclass
class Param:
    key: str
    label: str
    kind: str          # choice
    default: object
    choices: tuple = ()


@dataclass
class Context:
    """Dis kaynaklardan gelen canli veriler (motor gunceller)."""
    typing_rate: float = 0.0          # tus/sn
    cpu: float = 0.0                  # 0-100
    ram: float = 0.0                  # 0-100
    audio: list = field(default_factory=lambda: [0.0] * ZONES)  # 0-1


def hsv(h: float, s: float = 1.0, v: float = 1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return (r * 255, g * 255, b * 255)


def hex_rgb(s: str):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def scale(c, k: float):
    return (c[0] * k, c[1] * k, c[2] * k)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def lerp(a, b, t: float):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def led(x: float) -> float:
    """Algisal parlaklik (0-1) -> LED degeri. LED'ler dogrusal oldugundan solmalar karanlik
    uctan aniden degil, goze esit hizda gorunsun diye gamma uygulanir."""
    return max(0.0, min(1.0, x)) ** 1.8


def theme_stops(theme: str, custom: str = "#00c8ff", custom2: str = "#ff2bd6"):
    """Temanin renk duraklari (0-255); Gokkusagi icin None."""
    if theme == CUSTOM:
        return [hex_rgb(custom), hex_rgb(custom2)]
    return THEMES.get(theme)


def rainbow_rgb(u: float):
    """Gokkusagi rengi, parlakligi dengelenmis. Saf hsv'de sari/camgobegi mavi/kirmiziya gore ~13 kat
    daha parlak (LED'ler dogrusal): ton dondukce parlaklik inip cikar, "akis"in yerine nefes gibi
    gorunur. Parlak tonlar kisilir (kirmizi/mavi/macenta zaten sonuk, dokunulmaz)."""
    r, g, b = hsv(u)
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    k = min(1.0, (0.35 / y) ** 0.75) if y > 0 else 1.0
    return (r * k, g * k, b * k)


def theme_rgb(theme: str, custom: str, u: float, custom2: str = "#ff2bd6", equalize: bool = False):
    """Temadan 0-1 arasi konuma gore renk (0-255). Duraklar dairesel gecilir.

    equalize=True: Gokkusagi'nda parlakligi dengeler (rainbow_rgb). Yalnizca tonun SUREKLI kaydigi
    efektlerde (Akis, Nefes, Aurora) kullanilir; parlama efektlerinde (dalga, basis) canli renk istenir."""
    stops = theme_stops(theme, custom, custom2)
    if stops is None:
        return rainbow_rgb(u) if equalize else hsv(u)
    n = len(stops)
    p = (u % 1.0) * n
    i = int(p)
    return lerp(stops[i % n], stops[(i + 1) % n], p - i)


class Effect:
    name = ""
    description = ""
    uses_keys = False
    theme: str | None = None          # varsayilan tema; None -> tema secimi gosterilmez
    speed_label: str | None = None    # None -> kaydirici gosterilmez
    speed_range = (0.5, 2.0)
    speed_fmt = "{:.1f}×"
    speed_default = 1.0
    extras: tuple = ()                # ek secimler (Param)
    zone_custom = False               # True: "Ozel" tema 5 bolgeye ayri renk secilir (Sabit renk)
    accent: tuple = ((255, 255, 255), (120, 120, 120))   # kart simgesi

    def __init__(self, values: dict | None = None) -> None:
        self.p: dict = {"theme": self.theme or RAINBOW, "custom": "#00c8ff", "custom2": "#ff2bd6",
                        "speed": self.speed_default, "zones": list(DEFAULT_ZONES)}
        self.p.update({x.key: x.default for x in self.extras})
        if values:
            for k, v in values.items():
                if k in self.p:
                    self.p[k] = v
        if self.p["theme"] not in THEMES:
            self.p["theme"] = self.theme or RAINBOW
        z = self.p["zones"]                              # 5 bolge rengi (Sabit renk > Ozel); gecersizse varsayilan
        ok = isinstance(z, (list, tuple)) and len(z) == ZONES and all(
            isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in z)
        self.p["zones"] = list(z) if ok else list(DEFAULT_ZONES)          # kopya: ayar sozlugu paylasilmasin
        lo, hi = self.speed_range
        try:
            self.p["speed"] = min(hi, max(lo, float(self.p["speed"])))
        except (TypeError, ValueError):
            self.p["speed"] = self.speed_default

    def col(self, u: float, equalize: bool = False):
        return theme_rgb(self.p["theme"], self.p["custom"], u, self.p["custom2"], equalize)

    def on_key(self, zone_pos: float, t: float) -> None:
        pass

    def render(self, t: float, dt: float, ctx: Context):
        raise NotImplementedError


# ---------------------------------------------------------------------- tus efektleri
class Ripple(Effect):
    name = "Tuştan yayılan dalga"
    description = "Bastığın tuştan su dalgası gibi yayılır, kenarlardan yansır."
    uses_keys = True
    theme = RAINBOW
    speed_label = "Dalga hızı"
    accent = ((0, 220, 255), (170, 60, 255))
    GAIN = 2.4        # tek halka zirvesi ~%93 parlaklik, ust uste binince yumusak sikisir

    def __init__(self, values=None) -> None:
        super().__init__(values)
        self._ripples: list[list[float]] = []   # [konum, t0, renk konumu, genlik]
        self._u = random.random()

    def on_key(self, zone_pos, t):
        self._u = (self._u + 0.13) % 1.0
        self._ripples.append([zone_pos, t, self._u, random.uniform(0.85, 1.0)])
        del self._ripples[:-20]

    def render(self, t, dt, ctx):
        sp, w0, dec, refl, split = 6.0 * self.p["speed"], 0.9, 1.1, 0.45, 0.35
        ks = (1.0, 1.0 - split * 0.3, 1.0 - split * 0.6)       # R, G, B halka yaricaplari
        acc = [[0.0, 0.0, 0.0] for _ in range(ZONES)]
        alive = []
        for rp in self._ripples:
            pos, t0, u, amp = rp
            age = t - t0
            if age > dec * 5:
                continue
            alive.append(rp)
            col = tuple(c / 255 for c in self.col(u))
            w = w0 * (1 + 0.45 * age)                          # dalga yayildikca kalinlasir
            fade = math.exp(-age / dec) * amp
            r = sp * age
            images = ((pos, 1.0), (-1 - pos, refl), (9 - pos, refl),     # kaynak + duvar yansimalari
                      (-10 + pos, refl * refl), (10 + pos, refl * refl))
            flash = math.exp(-age * 10) * amp
            glow = math.exp(-age / (dec * 1.8)) * 0.22 * amp
            for z in range(ZONES):
                for ip, ia in images:
                    d = abs(z - ip)
                    for c in range(3):
                        ring = math.exp(-(((d - r * ks[c]) / w) ** 2))
                        acc[z][c] += col[c] * ring * ia * fade
                d0 = abs(z - pos)
                core = math.exp(-((d0 / (w * 0.9)) ** 2)) * flash * 1.4
                tail = math.exp(-((d0 / (w * 2.2)) ** 2)) * glow
                for c in range(3):
                    acc[z][c] += (col[c] * 0.25 + 0.75) * core + col[c] * tail
        self._ripples = alive
        amb = self.col(t * 0.03)
        bk = led(0.16)
        return [tuple(min(255.0, 255 * led(1 - math.exp(-acc[z][c] * self.GAIN)) + amb[c] * bk)
                      for c in range(3)) for z in range(ZONES)]


class PressGlow(Effect):
    name = "Basış parlaması"
    description = "Basılan bölge beyaz-sıcak parlar, renge dönüp söner."
    uses_keys = True
    theme = "Neon"
    speed_label = "Parlama süresi"
    accent = ((255, 255, 255), (255, 40, 140))

    def __init__(self, values=None) -> None:
        super().__init__(values)
        self._fast = [0.0] * ZONES   # hizli sonen "sicak" enerji
        self._slow = [0.0] * ZONES   # yavas sonen renkli enerji
        self._col = [(1.0, 0.2, 0.4)] * ZONES
        self._u = random.random()

    def on_key(self, zone_pos, t):
        self._u = (self._u + 0.11) % 1.0
        new = tuple(c / 255 for c in self.col(self._u))
        for z in range(ZONES):
            k = math.exp(-(((z - zone_pos) / 0.8) ** 2))
            if k < 0.02:
                continue
            self._fast[z] = min(2.0, self._fast[z] + k)
            self._slow[z] = min(2.5, self._slow[z] + 0.9 * k)
            self._col[z] = lerp(self._col[z], new, min(1.0, k))

    def render(self, t, dt, ctx):
        af = math.exp(-dt / 0.10)
        a_s = math.exp(-dt / (0.9 * self.p["speed"]))
        dif = min(0.5, 0.5 * dt * 5)
        s = self._slow
        new = list(s)
        for z in range(ZONES):                                 # komsulara sizma
            nb = [s[j] for j in (z - 1, z + 1) if 0 <= j < ZONES]
            new[z] = s[z] + dif * (sum(nb) / len(nb) - s[z])
        self._slow = [v * a_s for v in new]
        self._fast = [v * af for v in self._fast]
        amb = self.col(t * 0.03)
        pulse = 0.10 + 0.04 * math.sin(t * 1.1)
        out = []
        for z in range(ZONES):
            e = self._fast[z] * 0.9 + self._slow[z] * 0.6
            v = led(1 - math.exp(-e * 1.8))
            col = lerp(self._col[z], (1.0, 1.0, 1.0), max(0.0, min(1.0, self._fast[z] * 0.8)))
            out.append(tuple(min(255.0, 255 * col[c] * v + amb[c] * pulse) for c in range(3)))
        return out


class TypingHeat(Effect):
    name = "Yazma hızı ısısı"
    description = "Yavaş yazarken mavi, hızlandıkça kırmızıya döner."
    uses_keys = True
    speed_label = "Kırmızı için hız"
    speed_range = (3.0, 15.0)
    speed_fmt = "{:.0f} tuş/sn"
    speed_default = 8.0
    accent = ((40, 120, 255), (255, 40, 20))

    def __init__(self, values=None) -> None:
        super().__init__(values)
        self._heat = 0.0

    def render(self, t, dt, ctx):
        target = min(1.0, ctx.typing_rate / self.p["speed"])     # speed = tam kirmizi icin tus/sn
        s = 0.6 ** (dt * 30)
        self._heat = self._heat * s + target * (1 - s)
        return [hsv(0.62 * (1 - self._heat) + 0.03 * math.sin(t * 2 + z), 1.0,
                    0.35 + 0.65 * (0.4 + 0.6 * self._heat)) for z in range(ZONES)]


# ------------------------------------------------------------------ ambiyans efektleri
# Klavyenin kendi paleti (Sorf/Surukleme/Nefes gokkusagi icin klavyeden geri okundu, degistirilemez)
HW_PALETTE = ((255, 0, 0), (128, 255, 128), (0, 255, 0), (0, 0, 255), (255, 0, 255), (255, 255, 0), (0, 255, 255))
HW_SAMPLES = 48                     # donanim efekti onizlemesi: klavye boyunca nokta sayisi (5 bolge yerine)


class HardwareEffect(Effect):
    """Klavyenin KENDI icinde calisan efekt: tek paket yollanir, akitma yok. Palet klavyede sabit
    (Legion surucusu de renk gondermez; yalnizca hiz 0-3). Onizleme, klavyenin 30 fps videoyla
    olculen davranisini taklit eder (scripts/measure_hw.py ile cekildi)."""
    hardware = 0
    START_PHASE = 0.0               # mod secildiginde klavyenin basladigi faz
    speed_label = "Hız"
    speed_range = (0, 3)
    speed_fmt = "{:.0f} / 3"
    speed_default = 2

    def __init__(self, values: dict | None = None) -> None:
        super().__init__(values)
        self.phase = self.START_PHASE   # klavyedeki efektin ilerleyisi (efekte ozgu birim)
        self.active_speed: int | None = None   # klavyenin SU AN oynattigi hiz (motor ayarlar)

    def hw_speed(self) -> int:
        return max(0, min(3, int(round(float(self.p["speed"])))))

    def restart(self) -> None:
        """Klavye modu sectiginde (ayni mod bile olsa) efekti bastan baslatir: onizleme de bastan."""
        self.phase = self.START_PHASE

    def rate(self, speed: int) -> float:
        raise NotImplementedError

    def at(self, u: float):
        raise NotImplementedError

    def render(self, t, dt, ctx):
        speed = self.hw_speed() if self.active_speed is None else self.active_speed
        self.phase += self.rate(speed) * dt     # hiz degisince klavye de bastan baslamaz: faz surer
        return [self.at((i + 0.5) / HW_SAMPLES) for i in range(HW_SAMPLES)]


class Surf(HardwareEffect):
    name = "Sörf"
    description = "Gökkuşağı renkleri klavye boyunca soldan sağa kayar (klavyenin kendi efekti, renkler sabit)."
    hardware = 0x0B
    accent = ((255, 60, 120), (60, 140, 255))
    # Olculen (iki video, gercek kare zamanlari + senkron flaslari): ton sabit hizla geri doner,
    # klavye ayni anda tonun ~%40'ini gosterir (sag uc soldan geride: desen soldan saga kayar),
    # mod secilince sol uc ~yesilden (0.33 tur) baslar.
    TURNS_PER_S = (0.314, 0.461, 0.613, 0.695)
    SPAN = 0.40
    HUE0 = 0.33

    def rate(self, speed):              # faz birimi: ton turu
        return self.TURNS_PER_S[speed]

    def at(self, u):
        return hsv(self.HUE0 + self.SPAN * u - self.phase)


class Drift(HardwareEffect):
    name = "Sürükleme"
    description = ("Dalga ortadan uçlara yayılır, sonraki renkte uçlardan ortaya döner; renkler sırayla "
                   "değişir (klavyenin kendi efekti, renkler sabit).")
    hardware = 0x04
    accent = ((255, 170, 40), (160, 60, 255))
    # Olculen: her renk 6 ADIM (5 aydinlik + 1 karanlik), hareket kesintisiz degil adim adim.
    # Renkler paletin sirasiyla; bir renk ortadan uclara, sonraki uclardan ortaya gider.
    COLOR_PERIOD = (1.50, 1.18, 0.689, 0.443)          # bir rengin suresi (sn), hiz 0..3
    START_PHASE = 1.0                                  # mod secilince ilk adim (yalniz ortasi) atlanir
    FRONT = (0.0, 0.22, 0.47, 0.67, 0.86)              # adim basina dalga onunun ortadan uzakligi
    CENTER, SIGMA = 0.48, 0.17

    def rate(self, speed):              # faz birimi: adim (renk basina 6)
        return 6 / self.COLOR_PERIOD[speed]

    def at(self, u):
        k, step = divmod(int(self.phase), 6)    # mod secilince kirmizi, ortadan uclara baslar
        if step == 5:
            return (0, 0, 0)
        if k % 2:                                       # tek renkler uclardan ortaya
            step = 4 - step
        c = self.CENTER
        d = (c - u) / c if u < c else (u - c) / (1 - c)
        x = d - self.FRONT[step]
        # dar parlak on + genis sonuk hale (olculen profil: onden 0.35 uzakta ~%40, en uzakta ~%10)
        v = 0.55 * math.exp(-0.5 * (x / self.SIGMA) ** 2) + 0.45 * math.exp(-0.5 * (x / 0.5) ** 2)
        return scale(HW_PALETTE[k % len(HW_PALETTE)], v)


class Breathe(Effect):
    name = "Nefes"
    description = "Yumuşakça parlar ve söner."
    theme = "Okyanus"
    speed_label = "Hız"
    accent = ((0, 150, 255), (0, 60, 160))

    def render(self, t, dt, ctx):
        # Tum klavye AYNI anda nefes alir (bolgeler arasi faz/renk farki yok; yoksa dalga gibi suzulur).
        v = 0.5 + 0.5 * math.sin(t * 1.9 * self.p["speed"] - math.pi / 2)
        return [scale(self.col(t * 0.03 * self.p["speed"], equalize=True), led(0.05 + 0.95 * v))] * ZONES


class Aurora(Effect):
    name = "Aurora"
    description = "Kutup ışıkları gibi salınan yumuşak renkler."
    theme = "Aurora"
    speed_label = "Hız"
    accent = ((0, 255, 140), (150, 60, 255))

    def render(self, t, dt, ctx):
        s = self.p["speed"]
        return [scale(self.col(0.5 + 0.5 * math.sin(t * 0.35 * s + z * 0.8), equalize=True),
                      led(0.3 + 0.7 * math.sin(t * 0.7 * s - z * 0.6) ** 2)) for z in range(ZONES)]


class Fire(Effect):
    name = "Ateş"
    description = "Titreyen kor renkleri."
    accent = ((255, 200, 0), (255, 30, 0))

    def __init__(self, values=None) -> None:
        super().__init__(values)
        self._v = [0.5] * ZONES

    def render(self, t, dt, ctx):
        self._v = [max(0.05, min(1.0, v + random.uniform(-0.25, 0.25) * dt * 8)) for v in self._v]
        return [hsv(0.01 + 0.08 * v, 1.0, 0.25 + 0.75 * v) for v in self._v]


class Static(Effect):
    name = "Sabit renk"
    description = "Seçtiğin renk teması 5 bölgeye yayılır; Özel'de her bölgeye ayrı renk seçersin."
    theme = "Neon"
    zone_custom = True            # "Ozel" = 5 bolgenin her birine ayri renk (digerlerinde 2 renk)
    accent = ((255, 0, 200), (0, 220, 255))

    def render(self, t, dt, ctx):
        if self.p["theme"] == CUSTOM:
            return [hex_rgb(c) for c in self.p["zones"]]
        return [self.col(z / (ZONES - 1) * 0.9) for z in range(ZONES)]


# ---------------------------------------------------------------------- veri efektleri
class AudioReactive(Effect):
    name = "Ses tepkili"
    description = "Müzik 5 frekans bandına ayrılır: bas solda, tiz sağda."
    theme = "Neon"
    speed_label = "Hassasiyet"
    accent = ((255, 0, 200), (0, 220, 255))

    def __init__(self, values=None) -> None:
        super().__init__(values)
        self._lv = [0.0] * ZONES

    def render(self, t, dt, ctx):
        out = []
        for z in range(ZONES):
            target = min(1.0, ctx.audio[z] * 1.2 * self.p["speed"])
            a = 0.6 if target > self._lv[z] else 0.12   # hizli yukselis, yavas dusus
            self._lv[z] += (target - self._lv[z]) * a
            out.append(scale(self.col(z / (ZONES - 1) * 0.9), led(0.04 + 0.96 * self._lv[z])))
        return out


class SystemLoad(Effect):
    name = "Sistem yükü"
    description = "İşlemci ya da RAM kullanımı bölgelerde bar olarak görünür."
    extras = (Param("source", "Kaynak", "choice", "CPU", choices=("CPU", "RAM")),)
    accent = ((60, 255, 90), (255, 40, 40))

    def render(self, t, dt, ctx):
        pct = ctx.cpu if self.p["source"] == "CPU" else ctx.ram
        level = pct / 100 * ZONES
        hue = 0.33 * (1 - pct / 100)
        return [hsv(hue, 1.0, 0.06 + 0.94 * max(0.0, min(1.0, level - z))) for z in range(ZONES)]


EFFECT_CLASSES = (Ripple, PressGlow, Surf, Drift, Breathe, Aurora, Fire, Static,
                  AudioReactive, TypingHeat, SystemLoad)
EFFECTS = {c.name: c for c in EFFECT_CLASSES}
