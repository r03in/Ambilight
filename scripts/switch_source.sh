#!/usr/bin/env bash
# Phase 2: Switch HyperHDR between DRM grabber (Kodi/RPi active) and USB grabber (Switch/PS5 active).
# Usage: bash scripts/switch_source.sh <rpi-ip> drm|usb
set -euo pipefail

RPI_IP="${1:?Usage: switch_source.sh <rpi-ip> drm|usb}"
SOURCE="${2:?Specify source: drm or usb}"
API="http://${RPI_IP}:8090/json-rpc"

case "$SOURCE" in
    drm)
        echo "Switching to DRM framebuffer grabber (Kodi/Jellyfin)..."
        curl -sf -X POST "$API" -H "Content-Type: application/json" \
            -d '{"command":"sourceselect","priority":250}' > /dev/null
        curl -sf -X POST "$API" -H "Content-Type: application/json" \
            -d '{"command":"componentstate","componentstate":{"component":"GRABBER","state":true}}' > /dev/null
        curl -sf -X POST "$API" -H "Content-Type: application/json" \
            -d '{"command":"componentstate","componentstate":{"component":"V4L","state":false}}' > /dev/null
        ;;
    usb)
        echo "Switching to USB video capture (Switch/PS5)..."
        curl -sf -X POST "$API" -H "Content-Type: application/json" \
            -d '{"command":"componentstate","componentstate":{"component":"GRABBER","state":false}}' > /dev/null
        curl -sf -X POST "$API" -H "Content-Type: application/json" \
            -d '{"command":"componentstate","componentstate":{"component":"V4L","state":true}}' > /dev/null
        ;;
    *)
        echo "Unknown source '$SOURCE'. Use: drm or usb" >&2
        exit 1
        ;;
esac

echo "Done."
