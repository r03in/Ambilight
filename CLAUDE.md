# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Ambilight (bias lighting) for a 75" Samsung TV driven by a Raspberry Pi 5 2GB. The RPi replaces an existing Chromecast and serves dual duty: Jellyfin media player (via Kodi) and ambilight controller driving an LED strip mounted behind the TV.

Primary use case is Jellyfin content streamed from a home server. A Nintendo Switch and PS5 are also connected to the receiver but are rarely used — ambilight support for those is a future Phase 2 addition.

---

## Signal chain

**Phase 1 (current goal):**
```
Switch ──┐
PS5   ──┤── Home Theatre Receiver ── TV
RPi 5 ──┘   (HDMI out)
```
RPi 5 connects to the receiver like any other source. It outputs video to the TV via the receiver and simultaneously drives the LED strip via SPI GPIO.

**Phase 2 (optional future, ~€40–80 extra hardware):**
```
Receiver (HDMI out) ── HDMI Splitter ──── TV
                              └── USB Capture Card ── RPi 5 (HyperHDR USB grabber)
```
Adds ambilight for Switch and PS5 inputs. Not worth building until Phase 1 is working.

---

## Decision log

Key decisions made during design — record here so they don't get relitigated.

**Why replace the Chromecast rather than keep it?**
The RPi 5 is significantly more capable than a Chromecast and can handle 4K Jellyfin playback + ambilight simultaneously. Replacing it costs nothing extra and simplifies the setup to one device.

**Why LibreELEC, not Raspberry Pi OS?**
LibreELEC boots straight to Kodi, has an official HyperHDR add-on installable via the Kodi UI, and is optimised for media. RPi OS is the fallback only if LED SPI control causes driver issues on LibreELEC.

**Why HyperHDR, not Hyperion.ng?**
Hyperion.ng cannot correctly handle HDR10 content from the HDMI grabber. HyperHDR has real-time HDR tone mapping, is actively maintained, and has native ARM64 builds for RPi 5.

**Why SK6812 RGBW, not APA102/SK9822?**
SK6812 RGBW has a dedicated white LED channel. For movie and TV content — neutral scenes, skin tones, bright daylight, near-white backgrounds — this produces noticeably cleaner, warmer whites compared to RGB-mixed white. APA102 has a slight reliability advantage on SPI but no white channel. The quality difference is visible on a 75" screen in a dark room.

**Why SK6812 over WS2812B?**
Same protocol, same wiring, but SK6812 RGBW adds the white channel. No downside.

**Critical RPi 5 constraint — SPI only, no PWM:**
PWM does not work for LED strips on RPi 5. The GPIO hardware was redesigned and the PWM output is no longer compatible with WS2812B/SK6812 data timing. Every online tutorial targeting RPi 4 uses PWM on GPIO 18 — this will produce nothing on RPi 5. Use SPI (GPIO 10, MOSI) instead. This is not a software fix; it is a hardware difference.

SK6812 is a 5V data protocol; RPi 5 GPIO is 3.3V. A 74AHCT125 level shifter is required. It is a single cheap chip (~€1) and one extra wiring step — not a meaningful obstacle.

---

## Hardware

### Phase 1 shopping list

| Item | Spec | Notes |
|------|------|-------|
| SK6812 RGBW LED strip | 5V, 60 LEDs/m, IP30 (indoor) | Buy ~4m to have margin. See LED count below. |
| 5V 10A PSU | 50W | 200 LEDs × 60mA max = 12A theoretical. 10A covers real-world content (typically 20–40% of max draw). Inject power at both ends of the strip. |
| 74AHCT125 level shifter | DIP or SMD | Boosts RPi 3.3V SPI data to 5V for SK6812. One chip, 4 connections. |
| Aluminium LED channel + diffuser cover | 4m | Optional but recommended — diffuses hotspots and protects the strip. |
| JST-SM connectors + hookup wire | — | For connecting strip sections and running wire to RPi |

**LED count for 75" TV (top + left + right sides, bottom skipped):**
- 75" diagonal = 166cm wide × 93cm tall (16:9)
- Top: 100 LEDs, each side: 56 LEDs → **212 LEDs total**, ~353cm of strip
- Run `python scripts/led_geometry.py --tv-size 75 --density 60` for the exact HyperHDR layout JSON.

### RPi 5 SPI wiring

```
RPi 5 pin 19  (GPIO 10, MOSI) → 74AHCT125 input → SK6812 DATA IN
RPi 5 pin 6   (GND)           → 74AHCT125 GND   → SK6812 GND  → PSU GND (shared)
PSU 5V                        → 74AHCT125 VCC   → SK6812 5V
```

Full wiring diagram with chip pinout: `docs/wiring.md`.

### Phase 2 additions

| Item | Spec | Notes |
|------|------|-------|
| HDMI 1-in 2-out splitter | 4K HDR passthrough | Sits between receiver HDMI out and TV. ~€25–40. |
| MS2109-based USB capture card | 1080p30 MJPEG max | Sufficient for LED colour sampling. ~€10–15. |
| HDCP-stripping splitter | HDCP 2.2/2.3 bypass | Only needed to avoid disabling PS5 HDCP. ~€40–60 (e.g. HBAVLINK). Optional — see PS5 note below. |

**PS5 HDCP:** PS5 enables HDCP by default, which blocks all capture cards. Disable it: PS5 Settings → System → HDMI → Enable HDCP → off. Side effect: Netflix/Disney+ on PS5 require HDCP re-enabled. Acceptable since Jellyfin is the primary use. Nintendo Switch has no HDCP at all.

---

## Software stack

| Component | Role |
|-----------|------|
| LibreELEC 12+ (RPi 5 image) | OS — boots to Kodi, read-only rootfs |
| Kodi | Media frontend |
| Jellyfin for Kodi add-on | Connects Kodi to a Jellyfin server |
| HyperHDR | Ambilight engine — framebuffer grabber + LED driver |

**Install HyperHDR:** Kodi → Add-ons → Install from repository → LibreELEC Add-ons → Services → HyperHDR. Runs as a systemd service.

**HyperHDR web UI:** `http://<rpi-ip>:8090`
**Kodi web UI:** `http://<rpi-ip>:8080`
**SSH:** `ssh root@<rpi-ip>` (password: `libreelec`)

**Phase 1 grabber:** DRM/KMS framebuffer grabber in HyperHDR. Captures directly from the Kodi framebuffer including HDR-tone-mapped content. No capture card required.

**Phase 2 grabber:** USB grabber (/dev/video0) used exclusively — no source switching needed. The splitter sits downstream of the receiver, so the capture card always sees whatever the receiver is outputting (Kodi, PS5, or Switch). HyperHDR captures the correct content automatically when you change receiver input. The DRM framebuffer grabber is disabled in Phase 2.

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
  switch_source.sh (Phase 2) Switches HyperHDR between DRM and USB grabber via API
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

**Phase 2 — no source switching needed.** The USB grabber captures whatever the receiver outputs. Only one-time setup: resolve PS5 HDCP (disable in PS5 settings, or use HDCP-stripping splitter).

---

## LibreELEC filesystem notes

LibreELEC rootfs is read-only. Writable paths that persist across reboots:
- `/storage/` — Kodi config, add-on data
- `/storage/.config/` — system overrides (udev rules, autostart.sh)
- `/storage/.hyperhdr/` — HyperHDR config

`setup.sh` copies everything under `config/` to the appropriate `/storage/` paths via SCP.

---

## Post-install verification checklist

- [ ] Jellyfin for Kodi add-on connects to Jellyfin server successfully
- [ ] RPi 5 appears as a new device in Jellyfin dashboard (Settings → Dashboard → Devices)
- [ ] Watch status and resume points sync correctly between Kodi and Jellyfin
- [ ] Confirm direct play is enabled in the Jellyfin for Kodi add-on settings
- [ ] During a test stream, check Jellyfin dashboard (Dashboard → Playback) shows "Direct Play" not "Transcoding" — RPi 5 hardware-decodes H.264, H.265/HEVC, and AV1 natively so server CPU load should drop vs the old Chromecast
- [ ] HyperHDR DRM framebuffer grabber is active during playback (check HyperHDR web UI at `:8090` — signal indicator should be green)
- [ ] LED strip lights up and colours match screen content
- [ ] LED strip corners align with TV corners (adjust LED geometry in HyperHDR if needed)
- [ ] No colour shift or dimming toward the far end of the strip — if visible, inject power at both ends
