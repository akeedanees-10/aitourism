#!/usr/bin/env python3
"""AI Tourism Recommendation System - Unified Web Application Launcher.

Starts the FastAPI server with the embedded web application frontend,
automatically opens the default web browser, and provides an all-in-one execution experience.
"""

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to Python search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_local_ip() -> str:
    """Determine the machine's local IPv4 address on the Wi-Fi/LAN."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def open_browser(url: str, delay_seconds: float = 1.2):
    """Wait briefly for server to bind then launch the web browser."""
    time.sleep(delay_seconds)
    try:
        print(f"\n[Browser] Opening {url} in your default browser...")
        webbrowser.open(url)
    except Exception as exc:
        print(f"[Browser] Notice: Could not open browser automatically ({exc}).")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch the AI Tourism Recommendation Web Application."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind the server to (default: 0.0.0.0 to allow access from phones on the same Wi-Fi).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to run the server on (default: 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code modifications.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically launch the web browser on this PC.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    local_ip = get_local_ip()

    # Browser on this PC always connects via loopback
    pc_url = f"http://127.0.0.1:{args.port}"
    phone_url = f"http://{local_ip}:{args.port}" if local_ip != "127.0.0.1" else pc_url

    print("=" * 70)
    print("  AI-Based Personalized Tourism Recommendation System (VoyAIge)")
    print("=" * 70)
    print(f"  * On this PC          : {pc_url}")
    print(f"  * On your Phone       : {phone_url}  (Connect to same Wi-Fi)")
    print(f"  * API Documentation   : {pc_url}/docs")
    print(f"  * System Health Check : {pc_url}/health")
    print("=" * 70)
    print("  Press Ctrl+C at any time to gracefully stop the web server.\n")

    # Launch browser on PC in a background daemon thread
    if not args.no_browser:
        browser_thread = threading.Thread(
            target=open_browser,
            args=(pc_url,),
            daemon=True,
        )
        browser_thread.start()

    # Import uvicorn and launch server
    try:
        import uvicorn
        uvicorn.run(
            "backend.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    except KeyboardInterrupt:
        print("\n[Server] Web application server shutdown cleanly. Goodbye!")
    except Exception as exc:
        print(f"\n[Error] Failed to start server: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
