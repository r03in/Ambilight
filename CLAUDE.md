# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Ambilight (bias lighting) for a 75" Samsung TV driven by a Raspberry Pi 5 2GB. The RPi replaces an existing Chromecast and serves dual duty: Jellyfin media player (via Kodi) and ambilight controller driving an SK6812 RGBW LED strip mounted behind the TV.

Primary use case is Jellyfin content streamed from a home server. A Nintendo Switch and PS5 are also connected to the receiver — Phase 2 adds ambilight support for those sources using an HDMI splitter and USB capture card. All Phase 1 and Phase 2 hardware has been sourced and ordered.

---

## Signal chain

**Phase 1:**
```
Switch ──┐
PS5   ──┤── Home Theatre Receiver ── TV
RPi 5 ──┘   (HDMI out)
```
RPi 5 connects to the receiver like any other source. It outputs video to the TV via the receiver and simultaneously drives the LED strip via SPI GPIO. HyperHDR uses the DRM framebuffer grabber to capture what Kodi is displaying.

**Phase 2:**
```
Receiver (HDMI out) ── EZCOO EZ-SP12H2 ──── TV  (OUT 1, 4K HDR)
                               └── Rullz MS2109 ── RPi 5 USB  (OUT 2, 1080p scaled)
```
The EZCOO splitter sits between the receiver and the TV. Its built-in scaler outputs 1080p on OUT 2 to the Rullz capture card. HyperHDR switches to the USB grabber and automatically captures whatever the receiver is outputting — no manual source switching needed when changing between Kodi, PS5, and Switch.

---

## Decision log

Key decisions made during design — record here so they don't get relitigated.

**Why replace the Chromecast rather than keep it?**
The RPi 5 is significantly more capable than a Chromecast and handles 4K Jellyfin playback + ambilight simultaneously with headroom. Replacing it costs nothing extra and reduces the setup to one device.

**Why LibreELEC, not Raspberry Pi OS?**
LibreELEC boots straight to Kodi, has an official HyperHDR add-on installable via the Kodi UI, and is optimised for media. RPi OS is the fallback only if LED SPI control causes driver issues on LibreELEC.

**Why HyperHDR, not Hyperion.ng?**
Hyperion.ng cannot correctly handle HDR10. HyperHDR has real-time HDR tone mapping, is actively maintained, and has native ARM64 builds for RPi 5.

**Why SK6812 RGBW, not APA102/SK9822?**
SK6812 RGBW has a dedicated white LED channel. For movie content — neutral scenes, skin tones, bright daylight, near-white backgrounds — this produces noticeably cleaner whites compared to RGB-mixed white. APA102 has a slight SPI reliability advantage but no white channel. The quality difference is visible on a 75" screen in a dark room.

**Critical RPi 5 constraint — SPI only, no PWM:**
PWM does not work for LED strips on RPi 5. The GPIO hardware was redesigned and the PWM output is no longer compatible with WS2812B/SK6812 data timing. Every online tutorial targeting RPi 4 uses PWM on GPIO 18 — this will produce nothing on RPi 5. Use SPI (GPIO 10, MOSI) instead. This is not a software fix; it is a hardware difference. SK6812 is a 5V data protocol; RPi 5 GPIO is 3.3V — the 74AHCT125 level shifter is required.

**Why no aluminium LED channels or diffuser?**
Reference point: Philips Ambilight at 47mm LED spacing looks great. SK6812 at 60 LEDs/m is 16.7mm spacing — nearly 3× denser. Hotspotting is not a problem at this density. Skipping channels also means the strip can bend around TV corners rather than being cut and joined, which is more reliable.

**Why no JST connectors at corners?**
The strip bends cleanly around a 75" TV's corners without cutting. L-shape solderless clip connectors are a known weak point (contact oxidation, intermittent failures). A continuous bent strip is more reliable for a permanent install.

**Why Rullz MS2109 Mini Coffee specifically?**
No loop-out needed — the EZCOO EZ-SP12H2 already handles the signal split. The Mini Coffee is the simplest and cheapest Rullz variant. Confirmed working with HyperHDR and reviewed on the official HyperHDR blog.

**Why Phase 2 source switching is fully automatic:**
The EZCOO splitter sits downstream of the receiver. The capture card always sees whatever the receiver is currently outputting — Kodi, PS5, or Switch. No switching logic is needed in HyperHDR. The DRM framebuffer grabber is disabled in Phase 2 and the USB grabber runs permanently.

**Server side (Jellyfin, Sonarr, Radarr, Jellyseerr) needs zero changes:**
These are all client-agnostic. The Jellyfin for Kodi add-on connects via the same API as any other Jellyfin client. The only difference worth verifying post-install is that the RPi 5 hardware-decodes H.264, H.265/HEVC, and AV1 natively, so Jellyfin should switch from transcoding (as it did for the Chromecast) to direct play — reducing server CPU load.

**PS5 HDCP handling:**
HDCP disabled in PS5 settings (Settings → System → HDMI → Enable HDCP → off). Side effect: Netflix/Disney+ on PS5 require HDCP re-enabled, which is acceptable since Jellyfin is the primary use. Nintendo Switch has no HDCP at all.

---

## Hardware

### All hardware ordered

| Item | Source | Detail |
|------|--------|--------|
| Raspberry Pi 5 2GB | Already owned | — |
| RPi 5 case with fan | Electrokit | Active cooling, temp-controlled 4-pin fan, snap-open for GPIO access |
| RPi 5 USB-C 27W PSU | Electrokit | Official RPi 5 power adapter ×2 |
| Meanwell LRS-50-5 | Electrokit | 5V 10A 50W PSU for LED strip |
| SN74AHCT125N DIP-14 | Electrokit | Texas Instruments, 3 units |
| SK6812 RGBW 5m | AliExpress | BTF-Lighting, 60 LEDs/m, RGB CW, IP30, White PCB |
| 22AWG silicone hookup wire | AliExpress | Flexible, for GPIO→level shifter→strip wiring |
| EZCOO EZ-SP12H2 | Amazon.se | HDMI 1-in 2-out, 4K HDR passthrough + built-in 1080p scaler on OUT 2 |
| Rullz MS2109 Mini Coffee | AliExpress | USB 2.0 capture card, 1080p30 MJPEG |

**LED count for 75" TV (top + left + right sides, bottom skipped):**
- 75" diagonal = 166cm wide × 93cm tall (16:9)
- Top: 100 LEDs, each side: 56 LEDs → **212 LEDs total**, ~353cm of strip
- 5m reel ordered — ~147cm of spare strip after installation
- Run `python scripts/led_geometry.py --tv-size 75 --density 60` for the exact HyperHDR layout JSON

### RPi 5 SPI wiring

```
RPi 5 pin 19  (GPIO 10, MOSI) → 74AHCT125 input → SK6812 DATA IN
RPi 5 pin 6   (GND)           → 74AHCT125 GND   → SK6812 GND  → PSU GND (shared)
PSU 5V                        → 74AHCT125 VCC   → SK6812 5V
```

Full wiring diagram with chip pinout: `docs/wiring.md`.

---

## Software stack

| Component | Role |
|-----------|------|
| LibreELEC 12+ (RPi 5 image) | OS — boots to Kodi, read-only rootfs |
| Kodi | Media frontend |
| Jellyfin for Kodi add-on | Connects Kodi to Jellyfin server |
| HyperHDR | Ambilight engine — framebuffer/USB grabber + LED driver |

**Install HyperHDR:** Kodi → Add-ons → Install from repository → LibreELEC Add-ons → Services → HyperHDR. Runs as a systemd service.

**HyperHDR web UI:** `http://<rpi-ip>:8090`
**Kodi web UI:** `http://<rpi-ip>:8080`
**SSH:** `ssh root@<rpi-ip>` (password: `libreelec`)

**Phase 1 grabber:** DRM/KMS framebuffer grabber in HyperHDR. Captures directly from the Kodi framebuffer including HDR-tone-mapped content. No capture card required.

**Phase 2 grabber:** USB grabber (/dev/video0) used exclusively — DRM grabber disabled. Captures all sources automatically. Requires the MS2109 udev rule deployed via `setup.sh`.

---

## Repository layout

```
config/
  hyperhdr/        HyperHDR exported config JSON (LED layout, smoothing, grabber)
  kodi/            Kodi advancedsettings.xml and Jellyfin add-on config
  99-ms2109.rules  (Phase 2) udev rule to fix MS2109 USB capture card detection
scripts/
  led_geometry.py  Calculates LED positions for a TV size; outputs HyperHDR layout JSON
  test_leds.py     Sends test patterns to HyperHDR API for physical LED verification
  setup.sh         Deploys configs to RPi via SCP and restarts HyperHDR
docs/
  wiring.md        SPI pinout and 74AHCT125 level shifter wiring diagrams
```

---

## Common commands

**Generate LED layout:**
```bash
python scripts/led_geometry.py --tv-size 75 --density 60
```

**Deploy config to RPi:**
```bash
bash scripts/setup.sh <rpi-ip>
```

**Test LED strip physically:**
```bash
python scripts/test_leds.py --host <rpi-ip>
```

**SSH / service management:**
```bash
ssh root@<rpi-ip>
systemctl restart service.hyperhdr
journalctl -u service.hyperhdr -f
```

---

## LibreELEC filesystem notes

LibreELEC rootfs is read-only. Writable paths that persist across reboots:
- `/storage/` — Kodi config, add-on data
- `/storage/.config/` — system overrides (udev rules, autostart.sh)
- `/storage/.hyperhdr/` — HyperHDR config

`setup.sh` copies everything under `config/` to the appropriate `/storage/` paths via SCP.

---

## Post-install verification checklist

### Phase 1
- [ ] LibreELEC boots and Kodi loads on TV
- [ ] SSH accessible: `ssh root@<rpi-ip>`
- [ ] Jellyfin for Kodi add-on connects to Jellyfin server
- [ ] RPi 5 appears as a new device in Jellyfin dashboard (Settings → Dashboard → Devices)
- [ ] Watch status and resume points sync correctly between Kodi and Jellyfin
- [ ] Direct play enabled in Jellyfin for Kodi add-on settings
- [ ] During a test stream, Jellyfin dashboard (Dashboard → Playback) shows "Direct Play" not "Transcoding" — server CPU load should drop vs old Chromecast
- [ ] LED strip lights up and colours match screen content
- [ ] HyperHDR DRM framebuffer grabber active during playback (HyperHDR web UI `:8090` — signal indicator green)
- [ ] LED strip corners align with TV corners (adjust LED geometry in HyperHDR if needed)
- [ ] No colour shift or dimming toward far end of strip — if visible, inject power at both ends

### Phase 2
- [ ] PS5 HDCP disabled (PS5 Settings → System → HDMI → Enable HDCP → off)
- [ ] EZCOO EZ-SP12H2 connected: receiver HDMI out → EZCOO IN, EZCOO OUT 1 → TV, EZCOO OUT 2 → Rullz capture card
- [ ] MS2109 udev rule deployed via `setup.sh` — capture card appears as `/dev/video0` not a USB audio device
- [ ] HyperHDR switched from DRM grabber to USB grabber (/dev/video0)
- [ ] Rullz MS2109 set to **1080p30 MJPEG** in HyperHDR — do NOT use 1080p60 (known crash bug)
- [ ] Ambilight works when Kodi/Jellyfin is active source on receiver
- [ ] Ambilight works when PS5 is active source on receiver (no manual switching needed)
- [ ] Ambilight works when Switch is active source on receiver
