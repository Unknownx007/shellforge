# SHELLFORGE — SPDX-License-Identifier: AGPL-3.0-or-later
import base64, gzip, urllib.parse


def _b64(d):
    return base64.b64encode(d if isinstance(d, bytes) else d.encode())


def _gzip(d):
    return gzip.compress(d if isinstance(d, bytes) else d.encode())


def _hex(d):
    return (d if isinstance(d, bytes) else d.encode()).hex().encode()


def _url(d):
    s = d.decode() if isinstance(d, bytes) else d
    return urllib.parse.quote(s, safe="").encode()


ENCODERS = {"b64": _b64, "gzip": _gzip, "hex": _hex, "url": _url}


def encode(payload, chain):
    data = payload.encode() if isinstance(payload, str) else payload
    for step in chain:
        if step not in ENCODERS:
            raise ValueError(f"unknown encoder: {step}")
        data = ENCODERS[step](data)
    return data


def decode_wrapper(payload, chain):
    py = "import base64,gzip,sys,urllib.parse\n"
    py += f"d={payload!r}\n"
    for step in reversed(chain):
        if step == "b64":
            py += "d=base64.b64decode(d)\n"
        elif step == "gzip":
            py += "d=gzip.decompress(d)\n"
        elif step == "hex":
            py += "d=bytes.fromhex(d.decode())\n"
        elif step == "url":
            py += "d=urllib.parse.unquote_to_bytes(d)\n"
    py += "exec(d.decode() if isinstance(d,bytes) else d)\n"
    return py
