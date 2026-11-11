# Lenovo Legion K300 lighting protocol (reverse-engineered notes)

These notes describe what the K300's vendor HID interface accepts for lighting, as observed from
the official *Legion Accessory Central* software and verified by sending packets to a real
keyboard. They were produced for **interoperability** with a device owned by the author. No Lenovo
code or firmware is included in this repository.

> **Safety.** Only the two commands documented below (`0x19`, `0x14`) were ever sent to the device.
> The official driver uses other commands (see [Unknown](#unknown--not-done)) that may touch key
> remaps, macros or the firmware-update path. **Do not fuzz the command space.**

## Device

| | |
|---|---|
| Name | Lenovo Legion K300 RGB Gaming Keyboard |
| USB ID | `17EF:60F0` |
| Interfaces | `MI_00` keyboard, `MI_01` consumer/mouse, `MI_02` keyboard, **`MI_03` vendor, usage page `0xFF01`** |

The lighting interface (`MI_03`) has this report descriptor (47 bytes, no report IDs):

```
06 01 FF  09 01  A1 01
  09 03  15 00 26 FF 00  75 08 95 40  81 02     ; input,   64 bytes
  09 02  15 00 26 FF 00  75 08 95 40  91 02     ; output,  64 bytes
  09 01  15 00 26 FF 00  75 08 95 08  B1 02     ; feature,  8 bytes
C0
```

With `hidapi`, report ID `0x00` is prepended: feature reports are 9 bytes, output reports 65.

## Commands

Feature report (9 bytes with hidapi): `00 <cmd> 00 5A <arg> 00 00 00 00`

| cmd | meaning |
|---|---|
| `0x19` | **Select mode.** `arg` = mode id. Wait about 2 s before sending data (see Timing). |
| `0x14` | **Data follows.** Must be sent before *every* 64-byte output report. A data report without it is ignored (verified visually). |

### Modes

| mode | effect | colour slots |
|---|---|---|
| `0x01` | static, single colour | slot 0 |
| `0x04` | **drifting** ("Sürükleme", per-key, firmware) | none: fixed rainbow palette; header byte 3 = speed 0 (slow) - 3 (fast) |
| `0x08` | breathing rainbow (firmware) | no data packet |
| `0x0B` | **surfing** ("Sörf", per-key, firmware) | none: fixed rainbow palette; header byte 3 = speed 0-3 |
| `0x0C` | **static, 5 zones** | slots 0-4, left to right |
| `0x0D` | breathing, 5 zones (firmware) | slots 0-4 + speed |

Names come from `ldm_k300.dll` (Legion's driver). Its `/content/effect` handler sends colours only for
modes `0x01`, `0x0C`, `0x0D`; for `0x04`, `0x08`, `0x0B` it only parses one 0-3 value into header byte 3.
Palettes sent to `0x04`/`0x0B` are ignored by the firmware (read-back returns the default rainbow), so
those effects cannot be recoloured.

Read-back of the stored palette for `0x04`/`0x08`/`0x0B` (reply `f0 <mode> 02 ..`, slots at offset 16):
`FF0000 80FF80 00FF00 0000FF FF00FF FFFF00 00FFFF`.

Behaviour measured from two phone videos (real frame timestamps, synchronised to the PC clock with
light flashes; `scripts/measure_hw.py`, `scripts/measure_sync.py`):

| effect | speed 0 | 1 | 2 | 3 | motion |
|---|---|---|---|---|---|
| surfing `0x0B` | 0.314 | 0.461 | 0.613 | 0.695 hue turns/s | smooth hue wheel turning backwards (R→M→B→C→G→Y); the keyboard shows ~0.40 of the wheel at once, left leads right (moves left → right); on mode select the left end starts at ~0.33 turn (green) |
| drifting `0x04` | 1.50 | 1.18 | 0.689 | 0.443 s per colour | stepped: 6 steps per colour (5 lit + 1 dark); colours in palette order; one colour travels centre → ends, the next ends → centre; on mode select it starts at step 1 (red, centre) |

Timing rules (verified to ±0.1 s over 20 s):
* `0x19` mode select (even of the current mode) restarts the effect **immediately**, at the speed the
  keyboard has stored from the last speed packet for that mode.
* A speed packet (`01 <mode> 02 <speed>`) only changes the speed; the effect keeps its phase.
* The keyboard accepts the data packet only ~2 s after a mode select.

Mode ids `0x00`, `0x02-0x0A`, `0x0E-0x1F` return an identical default reply: treated as
unimplemented.

### Output report (64 bytes after the report ID)

```
offset  0   1     2   3   4..15    16..19   20..23   ...   44..47
        01  mode  02  b3  00 x12   R G B 00 R G B 00 ...   (8 slots of R G B 00)
```

* `b3` is `0x03` for modes `0x01` and `0x0C`; in wave mode it varied 0-3 with a slider.
* Colours are plain 8-bit RGB. There is **no** per-key colour data: the packet holds 8 colours.

Streaming 5-zone frames: after selecting mode `0x0C` once, repeat `0x14` + data report for every
frame. No mode re-selection is needed.

### Minimal example (Python, `hidapi`)

```python
import hid, time
dev = hid.device()
path = next(d["path"] for d in hid.enumerate(0x17EF, 0x60F0) if d["usage_page"] == 0xFF01)
dev.open_path(path)

dev.send_feature_report(bytes([0, 0x19, 0, 0x5A, 0x0C, 0, 0, 0, 0]))   # 5-zone mode
time.sleep(2)

pkt = bytearray(65)
pkt[1:5] = bytes([0x01, 0x0C, 0x02, 0x03])
for i, rgb in enumerate([(255, 0, 0), (255, 160, 0), (0, 255, 0), (0, 160, 255), (160, 0, 255)]):
    pkt[17 + 4 * i: 20 + 4 * i] = bytes(rgb)
dev.send_feature_report(bytes([0, 0x14, 0, 0x5A, 0, 0, 0, 0, 0]))
dev.write(bytes(pkt))
```

## Timing and USB traffic (important)

* Sending the data immediately after `0x19` showed no change; the official app waits 2-15 s. This
  project waits **2 s**.
* Each frame is two host transfers (~2 ms). The device accepts **500+ frames/s** without errors.
* **But the firmware drops key presses while being streamed fast.** With the lighting stream at
  30 frames/s the keyboard lost characters during fast typing; at 15 frames/s it did not. The
  rates between (20, 25) were *not* tested with exact timing. The app therefore sends a **fixed
  15 frames/s** (every 4th frame at a 60 Hz render loop) and sends far less while the light is
  barely changing.

## Input reports: the Fn key

`Fn` never reaches Windows as a key event (a low-level keyboard hook sees nothing). The keyboard
reports it on the vendor interface instead, as a 64-byte **input report** that can simply be read:

```
Fn pressed   ff 00 01 0c 00 00 ...
Fn released  ff 00 00 00 00 00 ...
```

Observed in a 2-minute capture with five Fn presses (10 reports). Not known: whether `0x0c` is "Fn"
itself or an ID that changes for Fn+F-key combinations (only Fn on its own was tried), and whether
other keys use the same report. Reading is passive: the app only opens the interface and calls
`read()`; each opener has its own report queue, so it does not disturb other software that also
reads from the device.

## No per-key lighting

* The vendor interface only offers the modes above; the stored profile (`ProfileRawPacket` in the
  official app's LiteDB) contains the **key matrix** (HID usage codes), not lighting.
* The official K300 driver (`ldm_k300.dll`) exposes only `static`, `static_5zone`,
  `breathing_5zone` and `breathing_rainbow`.
* The official updater ships firmware only for mice and the K500, with RSA-3072 signature checks.

The firmware's wave effect colours individual keys, so the LED hardware may be addressable per
key, but nothing reachable from the host exposes that.

## Key positions

The app identifies a pressed key from the scan code and the *extended* flag
(`LLKHF_EXTENDED`) of a low-level keyboard hook, looks it up in a per-layout table
(`k300fx/layouts.py`: Turkish Q / ISO and Global Q / ANSI, 22.5 u wide: main block 15 u,
navigation cluster 3 u, numpad 4 u, 0.25 u gaps) and uses the key's horizontal centre.

Quirks worth knowing: Windows reports **NumLock, Pause, Print Screen and Scroll Lock**
inconsistently (NumLock often carries the extended flag, Pause uses an `E1` prefix), so those four
are matched by virtual-key code instead. The extended flag separates the navigation cluster from the
numpad (same scan codes), numpad Enter and `/` from the main block, and right Ctrl / AltGr / Menu
from their left counterparts. AltGr also produces a fake left Ctrl, and Print Screen / Shift+nav
produce fake Shift events (`0x2A`/`0x36` with the extended flag): the latter are dropped.

## Unknown / not done

* Header byte 3 for mode `0x0D` and whether `0x0D` is usable from this app (not exposed yet).
* Official-driver commands `0x12, 0x13, 0x15, 0x16, 0x17, 0x18, 0x88, 0x89` (not sent, not understood).
* Whether `20-25` frames/s is safe; the exact firmware limit.

## How this was found

1. Hooked `hid_write` / `hid_send_feature_report` in the official software with
   [Frida](https://frida.re) while changing one setting at a time, and diffed the packets.
2. Listed the HID report descriptor and enumerated the commands the official driver uses with
   static disassembly (no device access).
3. Verified every claim by sending packets and watching the keyboard.

Corrections and additional findings are welcome.
