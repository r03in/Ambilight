# Wiring reference

## RPi 5 SPI pinout

```
RPi 5 GPIO header (40-pin)

 3V3  [ 1] [ 2] 5V
      [ 3] [ 4] 5V     ← LED strip 5V power (from PSU, NOT from RPi)
      [ 5] [ 6] GND    ← Shared GND (RPi GND + LED strip GND + PSU GND)
      ...
MOSI  [19] [20] GND
SCLK  [23] [24] CE0
```

> **Note:** The LED strip must be powered from its own 5V PSU, not from the RPi's 5V pin.
> Share a common GND between the RPi and the PSU.

---

## APA102 / SK9822 (recommended — no level shifter needed)

```
RPi 5                   APA102/SK9822 strip
────────────────────    ───────────────────
GPIO 10 (MOSI, pin 19) → DATA IN
GPIO 11 (SCLK, pin 23) → CLOCK IN
GND           (pin  6) → GND           ← also connect PSU GND here
                         5V            ← from 5V PSU (not RPi)
```

HyperHDR device: **SPI (APA102/SK9822)**, `/dev/spidev0.0`

---

## SK6812 RGBW / WS2812B (single-wire, needs level shifter)

The RPi 5 GPIO outputs 3.3V. SK6812/WS2812B need a 5V data signal.
Use a **74AHCT125** (or 74HCT125) as a level shifter.

```
RPi 5                74AHCT125              SK6812 strip
────────────────     ───────────────────    ────────────
GPIO 10 (MOSI) →    A (pin 2)              
3.3V           →    OE/ (pin 1, active low, tie to GND to always enable)
                    Y (pin 3)          →   DATA IN
5V PSU         →    VCC (pin 14)
GND            →    GND (pin 7)        →   GND
                                           5V ← from 5V PSU
```

HyperHDR device: **SPI (WS2812B/SK6812)**, `/dev/spidev0.0`, 3-byte (RGB) or 4-byte (RGBW) mode

> Tip: SK6812 RGBW in RGBW mode gives noticeably better neutral/white tones for movies.

---

## Power supply sizing

| LEDs | Max draw (60mA/LED) | Recommended PSU |
|------|---------------------|-----------------|
| 100  | 6A                  | 5V 8A           |
| 150  | 9A                  | 5V 10A          |
| 220  | 13.2A               | 5V 15A          |

Real-world draw is typically 20–40% of max (ambilight content is rarely full white).
A 5V 10A (50W) supply covers most 75" setups comfortably.

**Inject power at both ends of the strip** for runs over 100 LEDs to avoid voltage drop and colour shift at the far end.

---

## Phase 2: MS2109 USB capture card udev fix

The MS2109 chip is misidentified as a USB audio device. Create
`/storage/.config/udev.rules.d/99-ms2109.rules` with:

```
# Prevent MS2109 HDMI capture from loading snd-usb-audio
SUBSYSTEM=="usb", ATTRS{idVendor}=="534d", ATTRS{idProduct}=="2109", RUN+="/bin/sh -c 'echo 0 > /sys$DEVPATH/authorized'"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="534d", ATTR{idProduct}=="2109", ATTR{bInterfaceClass}=="01", RUN+="/bin/sh -c 'echo -1 > /sys$DEVPATH/uevent'"
```

Then reload: `udevadm control --reload && udevadm trigger`
