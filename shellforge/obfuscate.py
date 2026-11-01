# SHELLFORGE — SPDX-License-Identifier: AGPL-3.0-or-later
import random, string


def split_strings(code, min_len=4):
    out, i, in_str, quote, buf = [], 0, False, "", ""
    while i < len(code):
        c = code[i]
        if not in_str and c in "\"'":
            in_str, quote, buf = True, c, c
        elif in_str and c == quote and (i == 0 or code[i-1] != "\\"):
            in_str = False
            buf += c
            if len(buf) > min_len + 2:
                inner = buf[1:-1]
                mid = len(inner) // 2
                out.append(f"{quote}{inner[:mid]}{quote}+{quote}{inner[mid:]}{quote}")
            else:
                out.append(buf)
            buf = ""
        elif in_str:
            buf += c
        else:
            out.append(c)
        i += 1
    if buf:
        out.append(buf)
    return "".join(out)


def comment_noise(code, density=0.03):
    out = []
    for line in code.split("\n"):
        out.append(line)
        if line.strip() and random.random() < density:
            out.append(f"# {''.join(random.choices(string.ascii_lowercase, k=8))}")
    return "\n".join(out)


PRESETS = {"light": ["split"], "heavy": ["split", "comments"]}


def apply(code, preset):
    if preset == "none":
        return code
    for step in PRESETS.get(preset, []):
        if step == "split":
            code = split_strings(code)
        elif step == "comments":
            code = comment_noise(code)
    return code
