#!/usr/bin/env python3
"""
Calculate LED positions for a given TV diagonal and output a HyperHDR-compatible
LED layout JSON (suitable for pasting into HyperHDR's LED Hardware config).

Layout: top edge (left→right), right edge (top→bottom), bottom edge (right→left, optional),
left edge (bottom→top). Bottom row is skipped by default (common ambilight practice).

Usage:
    python led_geometry.py --tv-size 75 --density 60
    python led_geometry.py --tv-size 75 --density 30 --include-bottom
"""

import argparse
import json
import math


# Standard 16:9 aspect ratio
ASPECT_W = 16
ASPECT_H = 9


def tv_dimensions_cm(diagonal_inches: float) -> tuple[float, float]:
    diag_cm = diagonal_inches * 2.54
    w = diag_cm * ASPECT_W / math.sqrt(ASPECT_W**2 + ASPECT_H**2)
    h = diag_cm * ASPECT_H / math.sqrt(ASPECT_W**2 + ASPECT_H**2)
    return w, h


def led_count(length_cm: float, density_per_meter: int) -> int:
    return max(1, round(length_cm * density_per_meter / 100))


def build_layout(
    tv_size: float,
    density: int,
    include_bottom: bool,
    h_overlap: float = 0.05,
    v_overlap: float = 0.05,
) -> list[dict]:
    """
    Returns a list of HyperHDR LED position dicts.
    Each LED covers a rectangular region of the screen expressed as
    fractional coordinates: x_min, x_max, y_min, y_max in [0.0, 1.0].
    """
    width_cm, height_cm = tv_dimensions_cm(tv_size)

    n_top = led_count(width_cm, density)
    n_side = led_count(height_cm, density)
    n_bottom = led_count(width_cm, density) if include_bottom else 0

    leds = []

    # ── Top edge: left → right ──────────────────────────────────────────────
    for i in range(n_top):
        x0 = i / n_top
        x1 = (i + 1) / n_top
        leds.append({
            "index": len(leds),
            "hscan": {"minimum": round(x0, 4), "maximum": round(x1, 4)},
            "vscan": {"minimum": 0.0, "maximum": round(v_overlap, 4)},
        })

    # ── Right edge: top → bottom ─────────────────────────────────────────────
    for i in range(n_side):
        y0 = i / n_side
        y1 = (i + 1) / n_side
        leds.append({
            "index": len(leds),
            "hscan": {"minimum": round(1.0 - h_overlap, 4), "maximum": 1.0},
            "vscan": {"minimum": round(y0, 4), "maximum": round(y1, 4)},
        })

    # ── Bottom edge: right → left (optional) ─────────────────────────────────
    if include_bottom:
        for i in range(n_bottom - 1, -1, -1):
            x0 = i / n_bottom
            x1 = (i + 1) / n_bottom
            leds.append({
                "index": len(leds),
                "hscan": {"minimum": round(x0, 4), "maximum": round(x1, 4)},
                "vscan": {"minimum": round(1.0 - v_overlap, 4), "maximum": 1.0},
            })

    # ── Left edge: bottom → top ──────────────────────────────────────────────
    for i in range(n_side - 1, -1, -1):
        y0 = i / n_side
        y1 = (i + 1) / n_side
        leds.append({
            "index": len(leds),
            "hscan": {"minimum": 0.0, "maximum": round(h_overlap, 4)},
            "vscan": {"minimum": round(y0, 4), "maximum": round(y1, 4)},
        })

    return leds


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HyperHDR LED layout JSON")
    parser.add_argument("--tv-size", type=float, default=75.0, help="TV diagonal in inches")
    parser.add_argument("--density", type=int, default=60, help="LEDs per meter")
    parser.add_argument("--include-bottom", action="store_true", help="Include bottom edge LEDs")
    parser.add_argument(
        "--h-overlap", type=float, default=0.05,
        help="Horizontal capture overlap fraction (default 0.05 = 5%% of screen width)",
    )
    parser.add_argument(
        "--v-overlap", type=float, default=0.05,
        help="Vertical capture overlap fraction (default 0.05 = 5%% of screen height)",
    )
    args = parser.parse_args()

    w, h = tv_dimensions_cm(args.tv_size)
    n_top = led_count(w, args.density)
    n_side = led_count(h, args.density)
    n_bottom = led_count(w, args.density) if args.include_bottom else 0
    total = n_top + 2 * n_side + n_bottom

    print(f"TV: {args.tv_size}\" ({w:.0f}cm × {h:.0f}cm, 16:9)")
    print(f"Density: {args.density} LEDs/m")
    print(f"  Top:    {n_top} LEDs  ({w:.0f}cm)")
    print(f"  Sides:  {n_side} LEDs each  ({h:.0f}cm)")
    if args.include_bottom:
        print(f"  Bottom: {n_bottom} LEDs  ({w:.0f}cm)")
    print(f"  Total:  {total} LEDs")
    print(f"  Strip length needed: ~{(w + 2*h + (w if args.include_bottom else 0)):.0f}cm")
    print()

    leds = build_layout(args.tv_size, args.density, args.include_bottom, args.h_overlap, args.v_overlap)
    print(json.dumps(leds, indent=2))


if __name__ == "__main__":
    main()
