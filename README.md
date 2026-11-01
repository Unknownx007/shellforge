<div align="center">

<img width="925" height="320" alt="1" src="https://github.com/user-attachments/assets/fdf3dd2f-450c-4e96-96f4-a0355ff0d87e" />

# SHELLFORGE

**Web GUI payload forge + multi-session reverse-shell handler**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Author](https://img.shields.io/badge/author-DEDSEC-brightgreen.svg)](https://github.com/Unknownx007)

</div>

---

## 📌 What is SHELLFORGE?

SHELLFORGE is a **browser-based red-team operator console** for generating and handling reverse-shell payloads. Instead of juggling ten terminal windows and copy-pasting payloads from cheat sheets, you get:

- A **web UI** running on `http://127.0.0.1:8080` — dark, professional, keyboard-friendly
- **12 built-in payloads** for Linux, macOS, and Windows — including persistence-capable ones that survive shell close, terminal close, and reboot
- A **payload crafter** so you can build, save, and edit your own payload templates
- A **multi-session listener** that accepts unlimited concurrent agents on a single port
- **Interactive terminal** per session with `exec`, `upload`, and `download`
- Optional **XOR-encrypted channel** so the protocol bytes don't look like plaintext on the wire

Everything runs locally. No cloud services, no external APIs, no phone-home.

---

## ✨ Features

- 🎨 **Vivid web UI** — violet/cyan dark theme, glowing accents, keyboard-first
- 🔧 **12 payloads** — Python agents (foreground + daemon), Bash (raw + detached), Netcat (mkfifo + detached), PHP, Perl, PowerShell (basic + persist), systemd user service, launchd LaunchAgent
- 🧬 **Payload crafter** — build custom payloads in the browser, save them to `localStorage`, edit any time
- ⚡ **Live preview** — payload code updates as you change LHOST/LPORT/key
- 🎯 **Multi-session handler** — one port, unlimited agents, each session isolated
- 💻 **Interactive terminal** — scrollback, color-coded stdout/stderr, exit codes
- 📁 **File transfer** — upload from browser → agent, download agent → browser
- 🔒 **XOR channel** — encrypt the whole protocol with a single key on both ends
- 🖥️ **Startup banner** — Rich-rendered ASCII logo with clickable URL
- 🌍 **Cross-platform** — Windows, Linux, macOS (x86_64 + ARM64)
- 🛡️ **Graceful failures** — clear errors on port conflict, missing deps, dead sessions

---

## 📸 UI Overview

| View | Purpose |
|---|---|
| **Sessions** | Live cards for every connected agent — OS, hostname, user, current directory |
| **Interact** | Terminal attached to a session — type commands, upload, download, kill |
| **Payloads** | Browse the catalog, generate payloads, or craft your own |
| **Listener** | Start / stop the TCP listener, view the current bind state |

The **Sessions** view also shows a mini-list in the sidebar so you can jump between agents without losing context.

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/Unknownx007/shellforge
cd shellforge

# 2. Virtualenv
python3 -m venv venv
source venv/bin/activate           # Linux / macOS
# venv\Scripts\activate            # Windows

# 3. Install
pip install -r requirements.txt

# 4. Run
python3 run.py
```

You'll see:

```
╭──────────────────────── ◆ SHELLFORGE ◆ ────────────────────────╮
│                        (magenta ASCII logo)                    │
╰────────────────────────────────────────────────────────────────╯
     payload forge   ·   multi-session handler   ·   web GUI
     by DEDSEC  ·  github.com/Unknownx007  ·  v1.0

╭─ ◆  Server ────────────────────────────────────────────────────╮
│  Local    :  http://127.0.0.1:8080                             │
│  Bind     :  127.0.0.1:8080                                    │
│  Debug    :  off                                               │
│  Press Ctrl+C to stop the server.                              │
╰────────────────────────────────────────────────────────────────╯
```

Open **http://127.0.0.1:8080** in your browser.

---

## 🖥️ First Time Using It

1. Click **Listener** in the sidebar → set Port `4444` → **Start listener**
2. Click **Payloads** → pick a payload (e.g. **Python Agent**) → LHOST/LPORT auto-fill → **Download**
3. Transfer the payload file to the target machine (or for testing, just run it on `127.0.0.1`)
4. Run it: `python3 agent.py`
5. **Sessions** tab instantly shows a new card — click **Interact** to open the terminal
6. Type commands: `exec ls -la`, `exec uname -a`, `exec pwd`
7. Use **Upload** / **Download** buttons in the interact header for file transfers
8. Click **Kill** when you're done — the session is torn down cleanly

---

## 📦 Payload Catalog

| # | Name | Category | OS | Persistence | Requires |
|---|---|---|---|---|---|
| 1 | Python Agent | agent | 🐧 🍎 🪟 | ❌ | `python3 >= 3.6` |
| 2 | Python Agent (daemon) | agent | 🐧 🍎 🪟 | ✅ | `python3 >= 3.6` |
| 3 | Bash (raw) | raw | 🐧 | ❌ | `bash >= 4.0` + `/dev/tcp` |
| 4 | Bash (detached) | persistence | 🐧 | ✅ | `bash >= 4.0`, `setsid` |
| 5 | Netcat (mkfifo) | raw | 🐧 🍎 | ❌ | `nc` / `netcat` / `ncat` |
| 6 | Netcat (detached) | persistence | 🐧 🍎 | ✅ | `nc`, `setsid` |
| 7 | PHP | raw | 🐧 🍎 🪟 | ❌ | `php >= 5.0` |
| 8 | Perl | raw | 🐧 🍎 | ❌ | `perl >= 5.8` |
| 9 | PowerShell | raw | 🪟 | ❌ | PowerShell 2.0+ |
| 10 | PowerShell (persist) | persistence | 🪟 | ✅ | PowerShell 2.0+, user login |
| 11 | systemd user service | persistence | 🐧 | ✅ | systemd 226+ |
| 12 | launchd LaunchAgent | persistence | 🍎 | ✅ | macOS 10.10+ |

### What "persistence" means

Payloads marked ✅ survive the original shell closing:

- **Python Agent (daemon)** — double-forks on POSIX, `DETACHED_PROCESS` on Windows. Parent PID becomes 1.
- **Bash (detached)** — runs the shell in a `setsid` group, retries every 5 seconds.
- **Netcat (detached)** — `setsid` + mkfifo retry loop.
- **PowerShell (persist)** — installs an `HKCU` Run key that fires the shell on every user login.
- **systemd user service** — installs a user unit with `Restart=always`. Survives reboot.
- **launchd LaunchAgent** — macOS plist with `KeepAlive=true`. Survives reboot.

> ⚠️ Persistence payloads modify the target system. Only use them against hosts you **own** or have **explicit written permission** to test. See [Legal notice](#-legal--ethical-notice).

---

## 🧬 Payload Crafter

Click **+ New** in the Payloads view to open the crafter:

- **Start from** — pick any built-in payload as a starting template, or **Blank template**
- **Name / Filename / Description** — set metadata for the saved payload
- **Target OS** — tag as `linux` / `macos` / `windows`
- **Flags** — toggle persistence, XOR key support
- **Payload code** — edit the template directly. Use placeholders:
  - `{lhost}` — substituted with the LHOST you enter on the detail page
  - `{lport}` — substituted with the LPORT
  - `{key_repr}` — substituted with the XOR key (as a Python repr) or `None`
  - `{filename}` — substituted with the filename

Click **Save to catalog** → your payload appears in the list with a violet **custom** badge. Click it any time to view, edit, or delete.

Custom payloads are stored in your browser's `localStorage` under `shellforge_custom_payloads`. They survive page reloads but aren't synced to the server, so they stay private to you.

---

## 🎛️ CLI Options

```bash
python3 run.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Bind address. Use `0.0.0.0` to accept connections from other devices on your LAN. |
| `--port` | `8080` | Port for the web UI. |
| `--debug` | off | Enable Flask debug mode (auto-reload on file changes). |
| `--no-banner` | off | Skip the startup banner (useful for Docker / systemd / CI). |

Examples:

```bash
# Default — local only
python3 run.py

# Share on LAN (auto-detects and shows your 192.168.x.x URL)
python3 run.py --host 0.0.0.0

# Custom port
python3 run.py --port 9000

# Silent (no banner) for Docker
python3 run.py --host 0.0.0.0 --no-banner
```

---

## 🔌 Protocol

The operator ↔ agent protocol is simple, robust, and deliberately inspectable:

1. **Agent → Operator**: hello message (JSON: `type`, `os`, `platform`, `host`, `user`, `cwd`, `pid`)
2. **Operator → Agent**: length-prefixed JSON frames (`{type, ...}`)
3. **Message types**:
   - `exec` → runs a command, returns `{stdout, stderr, rc}`
   - `upload` → receives base64 data + path, writes to filesystem
   - `download` → reads a path, returns base64 data
   - `info` → returns fresh session metadata
   - `kill` → closes the connection

If a **XOR key** is set in the Listener view, all frames (both directions) are XOR-encoded with that key. The key must match on both ends or the agent won't be able to decode commands. This is not cryptography — it's obfuscation to hide the protocol structure from casual packet inspection.

**Transport:** The web UI uses **Socket.IO polling transport** (not WebSocket) for maximum reliability across all terminal environments. If you ever migrate to `eventlet` or `gevent`, WebSocket will work too, but it's not required.

---

## 📁 Project Structure

```
shellforge/
├── README.md
├── LICENSE
├── requirements.txt
├── run.py                        ← launcher + startup banner
├── shellforge/
│   ├── __init__.py
│   ├── app.py                    ← Flask + SocketIO backend
│   ├── listener.py               ← multi-session TCP listener
│   ├── session.py                ← per-session send/recv
│   ├── payloads.py               ← 12 payload templates + catalog
│   ├── encoders.py               ← encoder chain (gzip / b64 / url / hex)
│   └── obfuscate.py              ← cosmetic obfuscation transforms
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

---

## 🧪 Testing Locally

You don't need a second machine to test the whole loop — the agent and the operator can run on the same host:

```bash
# Terminal A — start the server
python3 run.py

# In the browser: Listener → Port 4444 → Start listener
# In the browser: Payloads → Python Agent → download agent.py

# Terminal B — run the agent
python3 agent.py

# Back in the browser: Sessions → your session appears
# Click Interact → type `exec id`, `exec pwd`, etc.
```

To test multi-session: open three more terminals and run `agent.py` in each. Three cards appear; all interactive independently.

To test upload/download:
- **Upload**: interact view → **Upload** button → pick any local file → specify remote path (`/tmp/test.bin`) → check `ls /tmp/test.bin` via the terminal
- **Download**: interact view → **Download** button → enter `/etc/hostname` → the file downloads via your browser's normal download flow

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'rich'` | `pip install -r requirements.txt` inside the venv |
| `Address already in use` | `python3 run.py --port 8081` — or `pkill -f "python.*run.py"` to kill the old instance |
| Upload / download disconnect the SocketIO channel | Confirm `static/js/app.js` starts with `const socket = io({transports:['polling'], upgrade:false})` |
| Payload catalog empty, toast says `backend returned non-JSON` | Old `app.py` still loaded — restart the server |
| Agent connects then instantly drops | XOR key mismatch between listener and payload — regenerate the payload with the same key |
| Upload via agent fails silently | Target directory not writable — try `/tmp/` or a user-writable path |
| `systemd-user` payload: `systemctl --user` gives "not found" | Run inside a full user session (SSH may not count). `loginctl enable-linger $USER` fixes it |
| `bash-detached` doesn't survive shell close | Check `ps -p 1 -o comm=` — on some containers, PPID=1 isn't init. Use Python agent (daemon) instead |

---

## ⚠️ Legal & Ethical Notice

SHELLFORGE generates and handles **reverse-shell payloads** — genuine offensive tooling. It is **dual-use**, like `msfvenom`, `revshells.com`, or `pentestmonkey`'s cheat sheets.

**Only use it against systems you own or have explicit written permission to test.**

Permitted uses:

- ✅ CTF challenges and personal labs
- ✅ Authorized red-team engagements with signed scope
- ✅ Security audits under written contract
- ✅ Educational study in a sandboxed VM

**Not permitted:**

- ❌ Any system you do not own
- ❌ Any system you have not been explicitly authorized to test
- ❌ Anything that violates local computer-misuse laws (CFAA in the US, CMA in the UK, and equivalents in nearly every country)

The author is **not responsible** for any misuse. Unauthorized use of these payloads may result in **criminal prosecution**.

---

## 📜 License

**GNU Affero General Public License v3.0 (AGPL-3.0-or-later)**

```
Copyright (C) 2025 DEDSEC <https://github.com/Unknownx007>
```

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

**You must:**

- 📌 Keep the copyright notice (`Copyright (C) 2025 DEDSEC`)
- 📌 Credit the original author in any redistribution
- 📌 Share your source if you distribute or offer this as a network service
- 📌 License your fork under AGPLv3

Full text: [LICENSE](LICENSE) · [gnu.org/licenses/agpl-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

---

## 🙏 Credits

- **[Rich](https://github.com/Textualize/rich)** — terminal banner, tables, and color
- **[Flask](https://flask.palletsprojects.com/)** + **[Flask-SocketIO](https://flask-socketio.readthedocs.io/)** — web backend
- **[Socket.IO](https://socket.io/)** — real-time channel
- Inspired by the reverse-shell cheat sheets from **[pentestmonkey](https://pentestmonkey.net/cheat-sheet/shells/reverse-shell-cheat-sheet)** and **[revshells.com](https://www.revshells.com/)**

---

## 👤 Author

**DEDSEC**

- GitHub: [@Unknownx007](https://github.com/Unknownx007)
- Project: [github.com/Unknownx007/shellforge](https://github.com/Unknownx007/shellforge)

---

<div align="center">

**⭐ Star this repo if you find it useful ⭐**

*"The shell isn't the goal. The operator console is."*

</div>
