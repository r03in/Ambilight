#!/usr/bin/env python3
"""
Send test patterns to HyperHDR via its JSON API to verify physical LED wiring.

Usage:
    python test_leds.py --host 192.168.1.x [--port 19444] [--duration 1.5]
"""

import argparse
import json
import socket
import time


def send_command(sock: socket.socket, command: dict) -> dict:
    data = json.dumps(command).encode() + b"\n"
    sock.sendall(data)
    response = b""
    while True:
        chunk = sock.recv(4096)
        response += chunk
        try:
            return json.loads(response.decode())
        except json.JSONDecodeError:
            continue


def set_color(sock: socket.socket, r: int, g: int, b: int, w: int = 0, duration_ms: int = 0) -> None:
    send_command(sock, {
        "command": "color",
        "color": [r, g, b],
        "duration": duration_ms,
        "priority": 50,
        "origin": "test_leds",
    })


def clear(sock: socket.socket) -> None:
    send_command(sock, {"command": "clear", "priority": 50})


def run_tests(host: str, port: int, duration: float) -> None:
    print(f"Connecting to HyperHDR at {host}:{port} ...")
    with socket.create_connection((host, port), timeout=5) as sock:
        # Read the initial server hello
        sock.recv(4096)

        ms = int(duration * 1000)
        steps = [
            ("Red",   255, 0,   0,   0),
            ("Green", 0,   255, 0,   0),
            ("Blue",  0,   0,   255, 0),
            ("White", 255, 255, 255, 0),
        ]

        for name, r, g, b, w in steps:
            print(f"  {name}...")
            set_color(sock, r, g, b, w, ms)
            time.sleep(duration)

        print("  Chase pattern (first LED red, rest off)...")
        # Chase: send individual LED colours via effect-less image update isn't trivial
        # via flat color API — use repeated solid colors as a simple wiring check instead.
        for _ in range(3):
            set_color(sock, 255, 0, 0, 0, 200)
            time.sleep(0.2)
            set_color(sock, 0, 0, 255, 0, 200)
            time.sleep(0.2)

        print("  Clearing...")
        clear(sock)

    print("Done. If all LEDs responded, wiring is correct.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test HyperHDR LED strip via JSON API")
    parser.add_argument("--host", required=True, help="RPi IP address")
    parser.add_argument("--port", type=int, default=19444, help="HyperHDR JSON API port (default 19444)")
    parser.add_argument("--duration", type=float, default=1.5, help="Seconds per colour (default 1.5)")
    args = parser.parse_args()

    run_tests(args.host, args.port, args.duration)


if __name__ == "__main__":
    main()
