#!/usr/bin/env python3
# SHELLFORGE — Copyright (C) 2025 DEDSEC <https://github.com/Unknownx007>
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
SHELLFORGE web launcher.
Run `python3 run.py` — banner + web link will appear.
"""

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console(highlight=False, force_terminal=True)


# ═══════════════════════════════════════════════════════════════════
#  ⬇⬇⬇  REPLACE THIS BLOCK WITH YOUR OWN ASCII LOGO  ⬇⬇⬇
# ═══════════════════════════════════════════════════════════════════
#  Every line here is rendered as-is (left padding preserved).
#  Keep it under ~80 chars wide so it fits in the panel.
#
#  When you have your own art, replace the string between the triple
#  quotes. Nothing else in this file needs to change.

LOGO = r"""
                       °   O   °                             
                       |\_/-\_/|                       op  op
XXXXXXXXXXXXXX         \+__+__+/    do                 8b  8b
X            ▒  ▒ ▒   ,88P''`  8p   d8.         oo..   8b  8P
X            ▒  ▒ ▒   ]8[       8.  ],ooooo   d8PP88.  8b  8b
X            ▒  ▒ ▒   ]8b.          ,88P"Y8[ d8P  ]88  8b  8b
X            ▒  ▒ ▒    Y88oo.__     `P'  `8b d8bo888P  Y8  8b
X            ▒  ▒ ▒     ``PY8888o.  ]8[   88 d8YP"''_. d8  8b
X▒▒▒▒▒▒▒▒▒▒▒▒▒  ▒ ▒           'Y88b `8'   d8.Y8b_ ,o8P d8  88
                ▒ ▒     .        Y8[      ]8b Y88888P  8P  d8
 ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ▒    d8        ]8[       YP  '''''   8b  d8
                  ▒    d8.      _d8[                   `'  88
 ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒    `88o.__,o88P'                       8b
                        '`Y8888P"'                         `'
"""

# ═══════════════════════════════════════════════════════════════════
#  ⬆⬆⬆  END OF LOGO BLOCK — everything below works automatically  ⬆⬆⬆
# ═══════════════════════════════════════════════════════════════════


def get_local_ip() -> str:
    """Best-effort local network IP (works even without internet)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    except Exception:
        return "unavailable"


def print_banner(host: str, port: int, debug: bool = False):
    """Render the startup banner + URL box."""
    console.print()

    # ── Logo panel ─────────────────────────────────────────────
    logo_text = Text(LOGO, style="bold bright_magenta")
    logo_panel = Panel(
        Align.center(logo_text),
        border_style="bright_magenta",
        padding=(0, 2),
        title="[bold bright_cyan]◆ SHELLFORGE ◆[/]",
        title_align="center",
    )
    console.print(logo_panel)

    # ── Tagline ────────────────────────────────────────────────
    tagline = Text.assemble(
        ("        payload forge", "bold bright_white"),
        ("   ·   ", "dim"),
        ("multi-session handler", "bold bright_white"),
        ("   ·   ", "dim"),
        ("web GUI", "bold bright_white"),
    )
    sub = Text.assemble(
        ("        by ", "dim"),
        ("DEDSEC", "bold bright_magenta"),
        ("   ·   ", "dim"),
        ("github.com/Unknownx007", "cyan underline"),
        ("   ·   ", "dim"),
        ("v1.0", "bright_yellow"),
    )
    console.print(Align.center(Text.assemble(tagline, "\n", sub)))
    console.print()

    # ── URL info panel ─────────────────────────────────────────
    local_url = f"http://127.0.0.1:{port}"
    network_url = f"http://{get_local_ip()}:{port}" if host == "0.0.0.0" else None

    lines = [
        f"[bright_magenta]Local    :[/]  [bold bright_cyan underline]{local_url}[/]",
    ]
    if network_url and "unavailable" not in network_url:
        lines.append(f"[bright_magenta]Network  :[/]  [bold bright_cyan underline]{network_url}[/]")
    lines.append(f"[bright_magenta]Bind     :[/]  [dim]{host}:{port}[/]")
    lines.append(f"[bright_magenta]Debug    :[/]  [dim]{'on' if debug else 'off'}[/]")
    lines.append("")
    lines.append("[dim]Press[/] [bold]Ctrl+C[/] [dim]to stop the server.[/]")

    console.print(Panel(
        "\n".join(lines),
        title="[bold bright_cyan]◆  Server[/]",
        title_align="left",
        border_style="bright_cyan",
        padding=(1, 2),
    ))
    console.print()


def main():
    p = argparse.ArgumentParser(
        description="SHELLFORGE — payload forge + multi-session handler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address (default 127.0.0.1, use 0.0.0.0 for LAN)")
    p.add_argument("--port", type=int, default=8080,
                   help="port to listen on (default 8080)")
    p.add_argument("--debug", action="store_true",
                   help="enable Flask debug mode")
    p.add_argument("--no-banner", action="store_true",
                   help="skip the startup banner")
    args = p.parse_args()

    # ── Banner (before server boot) ────────────────────────────
    if not args.no_banner:
        print_banner(args.host, args.port, args.debug)

    # ── Boot the server ────────────────────────────────────────
    from shellforge.app import run

    try:
        run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        console.print("\n[bold magenta]  [ DEDSEC ][/]  "
                      "[dim]Server stopped. No logs, no noise.[/]\n")
        sys.exit(0)
    except OSError as e:
        # Port already in use, permission denied, etc.
        console.print(f"\n[bold red]  ✗  Cannot start server:[/] {e}")
        if "Address already in use" in str(e) or "in use" in str(e).lower():
            console.print(f"[yellow]     Port {args.port} is already taken.")
            console.print(f"     Try:[/] [bold]python3 run.py --port 8081[/]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
