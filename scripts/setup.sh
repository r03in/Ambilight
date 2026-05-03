#!/usr/bin/env bash
# Deploy configs to RPi running LibreELEC and restart HyperHDR.
# Usage: bash scripts/setup.sh <rpi-ip>
set -euo pipefail

RPI_IP="${1:?Usage: setup.sh <rpi-ip>}"
RPI_USER="root"
RPI_PASS="libreelec"
SCP="scp -o StrictHostKeyChecking=no"
SSH="ssh -o StrictHostKeyChecking=no ${RPI_USER}@${RPI_IP}"

echo "==> Deploying to ${RPI_IP}"

# ── HyperHDR config ──────────────────────────────────────────────────────────
if [ -d config/hyperhdr ] && [ "$(ls -A config/hyperhdr)" ]; then
    echo "  Copying HyperHDR config..."
    $SCP -r config/hyperhdr/. "${RPI_USER}@${RPI_IP}:/storage/.hyperhdr/"
fi

# ── Kodi config ──────────────────────────────────────────────────────────────
if [ -d config/kodi ] && [ "$(ls -A config/kodi)" ]; then
    echo "  Copying Kodi config..."
    $SCP -r config/kodi/. "${RPI_USER}@${RPI_IP}:/storage/.kodi/userdata/"
fi

# ── MS2109 udev rule (Phase 2) ───────────────────────────────────────────────
# Prevents the MS2109 USB capture card from being claimed as a USB audio device.
if [ -f config/99-ms2109.rules ]; then
    echo "  Installing MS2109 udev rule..."
    $SCP config/99-ms2109.rules "${RPI_USER}@${RPI_IP}:/storage/.config/udev.rules.d/99-ms2109.rules"
fi

# ── Restart HyperHDR ─────────────────────────────────────────────────────────
echo "  Restarting HyperHDR..."
$SSH "systemctl restart service.hyperhdr" 2>/dev/null || \
    $SSH "killall hyperhdr 2>/dev/null; sleep 1; /storage/.kodi/addons/service.hyperhdr/bin/hyperhdr &"

echo "==> Done. HyperHDR web UI: http://${RPI_IP}:8090"
