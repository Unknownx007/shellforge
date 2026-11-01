# SHELLFORGE — SPDX-License-Identifier: AGPL-3.0-or-later
import json
import threading
import time


class Session:
    def __init__(self, sock, addr, info, key=None):
        self.sock = sock
        self.addr = addr
        self.info = info or {}
        self.key = key
        self.created = time.time()
        self.id = f"{addr[0]}:{addr[1]}"
        self._send_lock = threading.Lock()
        self._io_lock = threading.Lock()

    def _x(self, data):
        if not self.key:
            return data
        k = self.key.encode()
        return bytes(b ^ k[i % len(k)] for i, b in enumerate(data))

    def send(self, msg):
        with self._send_lock:
            data = json.dumps(msg).encode()
            if self.key:
                data = self._x(data)
            self.sock.sendall(len(data).to_bytes(4, "big") + data)

    def recv(self):
        hdr = self.sock.recv(4)
        if not hdr:
            return None
        n = int.from_bytes(hdr, "big")
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        if self.key:
            data = self._x(data)
        return json.loads(data)

    def cmd(self, msg):
        """Atomic send+recv pair, safe for concurrent callers."""
        with self._io_lock:
            self.send(msg)
            return self.recv()

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
