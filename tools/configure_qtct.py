#!/usr/bin/env python3
"""Point Kvantum and qt5ct/qt6ct at KvEink, the Eink icons and the GNOME interface fonts.

Usage: configure_qtct.py [CONFIG_DIR]   (default: ~/.config)
Only the keys below are changed; the rest of each file (e.g. Kvantum's per-application themes) is kept.
"""
import re
import subprocess
import sys
from pathlib import Path

# Pango font names may end in style words ("Cantarell Bold 11"); Qt wants the bare family.
STYLE_WORDS = {"bold", "italic", "oblique", "light", "medium", "semibold", "semi-bold", "heavy", "thin",
               "condensed", "regular"}


def gnome_font(key):
    try:
        value = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", key],
                               capture_output=True, text=True, check=True).stdout.strip().strip("'")
    except (OSError, subprocess.CalledProcessError):
        return None
    family, _, size = value.rpartition(" ")
    if not (family and size.replace(".", "", 1).isdigit()):
        return None
    words = family.split()
    while len(words) > 1 and words[-1].lower() in STYLE_WORDS:
        words.pop()
    return " ".join(words), size


def qfont(family, size, qt_major):
    # Qt 5 only parses the older 10-field QFont string.
    return f'"{family},{size},-1,5,50,0,0,0,0,0"' if qt_major == 5 else f'"{family},{size},-1,5,400,0,0,0,0,0,0,0,0,0,0,1"'


def append_keys(out, keys):
    trailing = []
    while out and not out[-1].strip():
        trailing.append(out.pop())
    out.extend(f"{k}={v}" for k, v in keys.items())
    out.extend(trailing)


def set_keys(text, wanted):
    lines, section, pending = text.splitlines(), None, {k: dict(v) for k, v in wanted.items()}
    out = []
    for line in lines:
        header = re.match(r"^\[(.+)\]\s*$", line)
        if header:
            if section in pending:
                append_keys(out, pending.pop(section))
            section = header.group(1)
        else:
            key = line.split("=", 1)[0]
            if section in pending and key in pending[section]:
                line = f"{key}={pending[section].pop(key)}"
        out.append(line)
    if section in pending:
        append_keys(out, pending.pop(section))
    for sec, keys in pending.items():
        out += ["", f"[{sec}]"] + [f"{k}={v}" for k, v in keys.items()]
    return "\n".join(out).strip() + "\n"


def main():
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".config"
    general, fixed = gnome_font("font-name"), gnome_font("monospace-font-name")
    if not (general and fixed):
        print("GNOME's font settings aren't readable (gsettings); leaving the qt5ct/qt6ct fonts as they are.")
    for tool, major in (("qt5ct", 5), ("qt6ct", 6)):
        path = config / tool / f"{tool}.conf"
        path.parent.mkdir(parents=True, exist_ok=True)
        wanted = {"Appearance": {"custom_palette": "false", "icon_theme": "Eink",
                                 "standard_dialogs": "xdgdesktopportal", "style": "kvantum"}}
        if general and fixed:
            wanted["Fonts"] = {"general": qfont(*general, major), "fixed": qfont(*fixed, major)}
        path.write_text(set_keys(path.read_text() if path.exists() else "", wanted))
        fonts = f", {general[0]} {general[1]} / {fixed[0]} {fixed[1]}" if general and fixed else ""
        print(f"{path}: kvantum, Eink icons{fonts}")
    kvantum = config / "Kvantum" / "kvantum.kvconfig"
    kvantum.parent.mkdir(parents=True, exist_ok=True)
    kvantum.write_text(set_keys(kvantum.read_text() if kvantum.exists() else "", {"General": {"theme": "KvEink"}}))
    print(f"{kvantum}: KvEink")


if __name__ == "__main__":
    main()
