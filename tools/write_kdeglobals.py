#!/usr/bin/env python3
"""Merge the Eink scheme selection and its colour groups into kdeglobals.

Usage: write_kdeglobals.py [KDEGLOBALS]   (default: ~/.config/kdeglobals)
The colour groups are copied in as well because KDE apps that never activate a scheme
(e.g. Krusader) read KColorScheme straight from kdeglobals. Everything else in the file is kept.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COLOUR_GROUPS = ("[Colors:", "[ColorEffects:", "[WM]")


def blocks(text):
    """KConfig text as [header, lines] pairs; the first pair holds anything before the first group."""
    out = [[None, []]]
    for line in text.splitlines():
        if line.startswith("["):
            out.append([line.strip(), []])
        else:
            out[-1][1].append(line)
    return out


def settings(text):
    return {header: dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
            for header, lines in blocks(text) if header}


def merge(current, wanted, colour_blocks):
    kept = [b for b in blocks(current) if not (b[0] and b[0].startswith(COLOUR_GROUPS))]
    missing = {header: dict(keys) for header, keys in wanted.items()}
    # KConfig lets a repeated group's later keys win, so every occurrence is updated.
    for header, lines in kept:
        for i, line in enumerate(lines):
            key = line.split("=", 1)[0]
            if header in wanted and "=" in line and key in wanted[header]:
                lines[i] = f"{key}={wanted[header][key]}"
                missing[header].pop(key, None)
    out = []
    for header, lines in kept:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [f"{k}={v}" for k, v in missing.pop(header, {}).items()]
        out.append(([header] if header else []) + lines)
    out += [[header] + [f"{k}={v}" for k, v in keys.items()] for header, keys in missing.items()]
    out += [[header] + [line for line in lines if line.strip()] for header, lines in colour_blocks]
    return "\n\n".join("\n".join(block) for block in out if block).strip() + "\n"


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".config/kdeglobals"
    wanted = settings((REPO / "config/kdeglobals").read_text())
    colours = [b for b in blocks((REPO / "kde/Eink.colors").read_text()) if b[0] and b[0].startswith(COLOUR_GROUPS)]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(merge(target.read_text() if target.exists() else "", wanted, colours))
    print(f"{target}: Eink colour scheme, Eink icons, Kvantum, no animations")


if __name__ == "__main__":
    main()
