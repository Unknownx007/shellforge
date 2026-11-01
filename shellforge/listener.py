# SHELLFORGE — SPDX-License-Identifier: AGPL-3.0-or-later
import json
import socket
import threading
from .session import Session


class Listener:
    def __init__(self, host, port, key=None, on_new=None, on_gone=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(20)
        self.host = host
        self.port = self.sock.getsockname()[1]
        self.key = key
        self.sessions = []
        self._stop = False
        self._lock = threading.Lock()
        self.on_new = on_new
        self.on_gone = on_gone

    def start(self):
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _handshake(self, client):
        try:
            client.settimeout(5)
            hdr = client.recv(4)
            if not hdr:
                return None
            n = int.from_bytes(hdr, "big")
            data = b""
            while len(data) < n:
                chunk = client.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            if self.key:
                k = self.key.encode()
                data = bytes(b ^ k[i % len(k)] for i, b in enumerate(data))
            msg = json.loads(data)
            if msg.get("type") == "hello":
                return msg
        except Exception:
            return None
        return None

    def _accept_loop(self):
        while not self._stop:
            try:
                client, addr = self.sock.accept()
            except OSError:
                return
            try:
                client.settimeout(None)
            except Exception:
                pass
            info = self._handshake(client)
            if not info:
                client.close()
                continue
            sess = Session(client, addr, info, key=self.key)
            with self._lock:
                self.sessions.append(sess)
            if self.on_new:
                try:
                    self.on_new(sess)
                except Exception:
                    pass

    def snapshot(self):
        with self._lock:
            return list(self.sessions)

    def get(self, session_id):
        for s in self.snapshot():
            if s.id == session_id:
                return s
        return None

    def remove(self, sess):
        with self._lock:
            try:
                self.sessions.remove(sess)
            except ValueError:
                pass
        if self.on_gone:
            try:
                self.on_gone(sess)
            except Exception:
                pass

    def stop(self):
        self._stop = True
        try:
            self.sock.close()
        except Exception:
            pass
        for s in list(self.sessions):
            s.close()

