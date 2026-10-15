#!/usr/bin/env python3
"""Generate KvEink, a black/white Kvantum theme for e-ink, from KvLibadwaita.

Usage: build_kveink.py OUTPUT_DIR [BASE_THEME_DIR] [--controls gnome|outline]

KvEink keeps libadwaita's grey, borderless buttons and entries; KvEinkOutline draws them white with
1 px black outlines for even less grey.

BASE_THEME_DIR is the directory holding KvLibadwaita*.svg and .kvconfig. Without it, Manjaro's KvLibadwaitaMaia
or an installed upstream KvLibadwaita (https://github.com/GabePoel/KvLibadwaita) is used. Needs PyQt6 or PyQt5
(QtSvg) for element bounds.
"""
import argparse
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Only SVG geometry is needed; a session platform such as wayland would also need a display.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
try:
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtWidgets import QApplication

NAMES = {"gnome": "KvEink", "outline": "KvEinkOutline"}
BASE_CANDIDATES = [Path("/usr/share/Kvantum/KvLibadwaitaMaia"), Path("/usr/share/Kvantum/KvLibadwaita"),
                   Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "Kvantum/KvLibadwaita"]

BLACK, WHITE = "#000000", "#ffffff"
MARK = "#d0d0d0"       # selected rows, marked files, toggled buttons
MARK_PRESS = "#b0b0b0"
HOVER = "#ebebeb"
PRESS = "#c8c8c8"
DISABLED = "#7f7f7f"
# Measured from GTK4/libadwaita 1.9 with high contrast on: popovers, menu items and tabs.
GNOME_FILL = "#e6e6e7"
GNOME_HOVER = "#f1f1f1"
GNOME_OUTLINE = "#8d8d8f"
GNOME_SEPARATOR = "#99999b"

# Accent families of upstream KvLibadwaita (blue) and Manjaro's Maia recolour, in matching order
# (see Manjaro's maia.sh), mapped to neutral greys so checked/active states read as black.
BLUE = ["#3584e4", "#3c84f7", "#587392", "#81abdf", "#4990e7", "#4285f4", "#93cee9", "#3daee9"]
MAIA = ["#16a085", "#16a585", "#3f776c", "#70c2ad", "#159f7f", "#19b391", "#a6d9cc", "#21e0b6"]
NEUTRAL = [BLACK, BLACK, BLACK, "#999999", BLACK, "#333333", PRESS, "#4d4d4d"]

GENERAL_COLORS = {
    "window.color": WHITE, "base.color": WHITE, "alt.base.color": WHITE, "button.color": WHITE,
    "light.color": WHITE, "mid.light.color": "#f2f2f2", "dark.color": BLACK, "mid.color": PRESS,
    "highlight.color": MARK, "inactive.highlight.color": MARK, "text.color": BLACK,
    "window.text.color": BLACK, "button.text.color": BLACK, "highlight.text.color": BLACK,
    "disabled.text.color": DISABLED, "link.color": BLACK, "link.visited.color": BLACK,
    "progress.indicator.text.color": BLACK,
}
# libadwaita menus: 32 px items, highlight radius 9, popover radius 15 with a 7 px padding. Kvantum can't
# round a menu more than its padding, so menus get 10/10; items reach 9 through frame expansion.
MENU_FRAME = 10
MENU_SHADOW = 6
MENUITEM_FRAME = 2
MENUITEM_RADIUS = 9
MENU_SEPARATOR_HEIGHT = 13
# (section, key) -> value; keys missing from the base theme are appended to their section.
FORCED = {
    ("%General", "animate_states"): "false",        # every animation frame is a visible e-ink refresh
    ("%General", "transient_scrollbar"): "false",   # their fade-out is animated regardless of animate_states
    ("%General", "no_inactiveness"): "true",        # focus changes shouldn't repaint whole windows
    ("%General", "group_toolbar_buttons"): "false",
    ("%General", "toolbar_icon_size"): "22",
    ("%General", "menu_shadow_depth"): str(MENU_SHADOW),  # libadwaita popovers have a short, soft shadow
    ("%General", "menu_separator_height"): str(MENU_SEPARATOR_HEIGHT),
    ("%General", "spread_menuitems"): "false",      # keep a padding ring around the highlighted item
    # libadwaita spin buttons sit beside the entry; dropdowns look like buttons with a bold label.
    ("%General", "inline_spin_indicators"): "false",
    ("%General", "spin_button_width"): "32",        # Kvantum's maximum
    ("%General", "combo_as_lineedit"): "false",
    # KvLibadwaita keeps white labels for its blue checked buttons; ours are light grey.
    ("PanelButtonCommand", "text.toggle.color"): BLACK,
    ("PanelButtonTool", "text.toggle.color"): BLACK,
    ("IndicatorSpinBox", "indicator.size"): "14",
    # GNOME menus and text buttons carry no icons; qt6ct's menus_have_icons is overridden by Qt 6.
    ("Hacks", "iconless_menu"): "true",
    ("Hacks", "iconless_pushbutton"): "true",
    ("Menu", "frame.top"): str(MENU_FRAME), ("Menu", "frame.bottom"): str(MENU_FRAME),
    ("Menu", "frame.left"): str(MENU_FRAME), ("Menu", "frame.right"): str(MENU_FRAME),
    ("MenuItem", "indicator.size"): "14",
    ("MenuItem", "frame.top"): str(MENUITEM_FRAME), ("MenuItem", "frame.bottom"): str(MENUITEM_FRAME),
    ("MenuItem", "frame.left"): str(MENUITEM_FRAME), ("MenuItem", "frame.right"): str(MENUITEM_FRAME),
    # With an "expand-" element Kvantum draws corners of half this size whatever the frame is.
    ("MenuItem", "frame.expansion"): str(2 * MENUITEM_RADIUS),
}
BOLD_SECTIONS = {"PanelButtonCommand", "PanelButtonTool", "ToolbarButton", "ComboBox", "HeaderSection", "GroupBox"}
# These inherit PanelButtonCommand, but GNOME keeps their labels regular.
REGULAR_SECTIONS = {"CheckBox", "RadioButton", "ItemView", "Tab", "ToolboxTab", "MenuItem", "MenuBarItem", "LineEdit", "StatusBar"}

ITEMVIEW = {"itemview-toggled": MARK, "itemview-pressed": MARK_PRESS, "itemview-focused": "#f0f0f0"}

# 9-slice families redrawn as fill + 1 px outline: (family, state) -> (fill or None, outline or None, width).
OUTLINED = {
    ("button", "normal"): (WHITE, BLACK, 1), ("button", "focused"): (HOVER, BLACK, 1),
    ("button", "pressed"): (PRESS, BLACK, 1), ("button", "toggled"): (MARK, BLACK, 1),
    ("combo", "normal"): (WHITE, BLACK, 1), ("combo", "focused"): (HOVER, BLACK, 1),
    ("tbutton", "normal"): (None, None, 0), ("tbutton", "pressed"): (PRESS, BLACK, 1),
    ("tbutton", "toggled"): (MARK, BLACK, 1),
    ("lineedit", "normal"): (WHITE, BLACK, 1), ("lineedit", "focused"): (WHITE, BLACK, 2),
    # libadwaita tabs: inactive ones are bare text, hover gets an outline, the selected tab a grey pill.
    ("tab", "normal"): (None, None, 0), ("tab", "focused"): (GNOME_HOVER, GNOME_OUTLINE, 1),
    ("tab", "toggled"): (GNOME_FILL, GNOME_OUTLINE, 1),
}
# --controls gnome: libadwaita's filled, borderless buttons and entries instead of black outlines.
GNOME_CONTROLS = {
    ("button", "normal"): (GNOME_FILL, None, 0), ("button", "focused"): ("#dadadb", None, 0),
    ("button", "pressed"): (PRESS, None, 0), ("button", "toggled"): (PRESS, None, 0),
    ("combo", "normal"): (GNOME_FILL, None, 0), ("combo", "focused"): ("#dadadb", None, 0),
    ("lineedit", "normal"): (GNOME_FILL, None, 0), ("lineedit", "focused"): (GNOME_FILL, BLACK, 2),
}
# Rebuilt from scratch: (corner size, fill, outline). KvLibadwaita's menu-item pieces are 12x4.
FRESH = {"menuitem-normal": (MENUITEM_RADIUS, GNOME_FILL, GNOME_OUTLINE),
         "expand-menuitem-normal": (MENUITEM_RADIUS, GNOME_FILL, GNOME_OUTLINE),
         # Uncomposited menus: KvLibadwaita's 8 px pieces would be stretched to MENU_FRAME.
         "menu-normal": (MENU_FRAME, WHITE, GNOME_OUTLINE)}
CHECK = "M 3.5,8.5 6.5,11.5 12.5,4.5"   # libadwaita-style check mark in a 16x16 box
GLYPHS = {
    "menu-checkbox-normal": "", "menu-checkbox-focused": "",
    "menu-checkbox-checked-normal": f'<path d="{CHECK}" fill="none" stroke="{BLACK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "menu-checkbox-tristate-normal": f'<path d="M 4,8 H 12" stroke="{BLACK}" stroke-width="2" stroke-linecap="round"/>',
    "menu-radio-normal": "", "menu-radio-focused": "",
    "menu-radio-checked-normal": f'<circle cx="8" cy="8" r="3" fill="{BLACK}"/>',
}
for _state in ("checkbox-checked", "checkbox-tristate", "radio-checked"):
    GLYPHS[f"menu-{_state}-focused"] = GLYPHS[f"menu-{_state}-normal"]
PIECES = ("topleft", "topright", "bottomleft", "bottomright", "top", "bottom", "left", "right")
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def recolor_accent(text):
    for family in (BLUE, MAIA):
        for old, new in zip(family, NEUTRAL):
            text = re.sub(re.escape(old), new, text, flags=re.I)
    return text


def first_pass_svg(svg):
    svg = recolor_accent(svg)

    def fill_all(match, colour):
        return re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", colour, match.group(0))

    for prefix, colour in ITEMVIEW.items():
        svg = re.sub(r'<(?:rect|path|g)\b[^>]*\bid="' + prefix + r'[^"]*"[^>]*>', lambda m: fill_all(m, colour), svg)
    return svg


def piece_shapes(piece, x, y, w, h, fill, outline, width):
    """SVG for one 9-slice piece in absolute coordinates: 1 SVG unit is 1 px for frame pieces."""
    fill_attr = f'fill="{fill}"' if fill else 'fill="#000000" fill-opacity="0"'
    if piece in (None, "top", "bottom", "left", "right"):
        shapes = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" {fill_attr}/>']
        if outline and piece:
            ex, ey, ew, eh = {"top": (x, y, w, width), "bottom": (x, y + h - width, w, width),
                              "left": (x, y, width, h), "right": (x + w - width, y, width, h)}[piece]
            shapes.append(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" fill="{outline}"/>')
        return shapes
    # Corner: quarter ellipse centred on the piece's inner corner.
    cx = x + w if "left" in piece else x
    cy = y + h if piece.startswith("top") else y
    sx = -1 if "left" in piece else 1
    sy = -1 if piece.startswith("top") else 1
    sweep = 1 if sx * sy > 0 else 0

    def arc(rx, ry):
        return f"M {cx + sx * rx},{cy} A {rx},{ry} 0 0 {sweep} {cx},{cy + sy * ry}"

    # Keep the fill inside the outline so antialiasing can't leave a grey halo outside it.
    inset = width / 2 if outline else 0
    shapes = [f'<path d="{arc(w - inset, h - inset)} L {cx},{cy} Z" {fill_attr}/>']
    if outline:
        # A filled ring rather than a stroke: a stroke's bounds overhang the piece, and Kvantum then
        # shrinks the corner a little, which leaves notches where it meets the edges.
        iw, ih = w - width, h - width
        shapes.append(f'<path d="{arc(w, h)} L {cx},{cy + sy * ih} A {iw},{ih} 0 0 {1 - sweep} {cx + sx * iw},{cy} Z" '
                      f'fill="{outline}"/>')
    return shapes


def menu_shadow_elements():
    """Composited menus take frame and shadow from these, not from menu-normal.

    Kvantum draws them MENU_FRAME + MENU_SHADOW px wide and reads the shadow's share from the hint elements,
    so 1 SVG unit is 1 px here.
    """
    f, d, length, alpha = MENU_FRAME, MENU_SHADOW, 8, 0.08
    m = f + d
    x0 = y0 = -2600.0
    origins = {"topleft": (x0, y0), "top": (x0 + m, y0), "topright": (x0 + m + length, y0),
               "left": (x0, y0 + m), "right": (x0 + m + length, y0 + m),
               "bottomleft": (x0, y0 + m + length), "bottom": (x0 + m, y0 + m + length),
               "bottomright": (x0 + m + length, y0 + m + length)}

    def stops(start):
        return (f'<stop offset="{start}" stop-color="#000000" stop-opacity="{alpha}"/>'
                '<stop offset="1" stop-color="#000000" stop-opacity="0"/>')

    out = []
    for piece, (x, y) in origins.items():
        gid = f"menu-shadow-gradient-{piece}"
        if piece in ("top", "bottom", "left", "right"):
            w, h = (length, m) if piece in ("top", "bottom") else (m, length)

            def band(offset, thickness):
                return {"top": (x, y + offset, w, thickness), "bottom": (x, y + m - offset - thickness, w, thickness),
                        "left": (x + offset, y, thickness, h), "right": (x + m - offset - thickness, y, thickness, h)}[piece]

            sx0, sy0, sw, sh = band(0, d)
            inner, outer = {"top": ((x, y + d), (x, y)), "bottom": ((x, y + m - d), (x, y + m)),
                            "left": ((x + d, y), (x, y)), "right": ((x + m - d, y), (x + m, y))}[piece]
            body = (f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{inner[0]}" y1="{inner[1]}" '
                    f'x2="{outer[0]}" y2="{outer[1]}">{stops(0)}</linearGradient></defs>'
                    f'<rect x="{sx0}" y="{sy0}" width="{sw}" height="{sh}" fill="url(#{gid})"/>')
            for (bx, by, bw, bh), colour in ((band(d, 1), GNOME_OUTLINE), (band(d + 1, f - 1), WHITE)):
                body += f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{colour}"/>'
        else:
            cx = x + m if "left" in piece else x
            cy = y + m if piece.startswith("top") else y
            sx = -1 if "left" in piece else 1
            sy = -1 if piece.startswith("top") else 1
            sweep = 1 if sx * sy > 0 else 0

            def disc(r):
                return f"M {cx + sx * r},{cy} A {r},{r} 0 0 {sweep} {cx},{cy + sy * r} L {cx},{cy} Z"

            body = (f'<defs><radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{cx}" cy="{cy}" r="{m}">'
                    f'{stops(f / m)}</radialGradient></defs>'
                    f'<rect x="{x}" y="{y}" width="{m}" height="{m}" fill="#000000" fill-opacity="0"/>'
                    f'<path d="{disc(m)}" fill="url(#{gid})"/>'
                    f'<path d="{disc(f - 0.5)}" fill="{WHITE}"/>'
                    f'<path d="M {cx + sx * f},{cy} A {f},{f} 0 0 {sweep} {cx},{cy + sy * f} L {cx},{cy + sy * (f - 1)} '
                    f'A {f - 1},{f - 1} 0 0 {1 - sweep} {cx + sx * (f - 1)},{cy} Z" fill="{GNOME_OUTLINE}"/>')
        out.append((f"menu-shadow-{piece}", body))
    for n, side in enumerate(("top", "bottom", "left", "right")):
        w, h = (2, d) if side in ("top", "bottom") else (d, 2)
        out.append((f"menu-shadow-hint-{side}",
                    f'<rect x="{x0 + 100 + 20 * n}" y="{y0}" width="{w}" height="{h}" fill="#000000" fill-opacity="0"/>'))
    return out


def second_pass_svg(svg_path, outlined):
    svg_text = Path(svg_path).read_text()
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        sys.exit(f"the base theme's SVG can't be parsed: {svg_path}")
    for prefix, uri in re.findall(r'xmlns:?([A-Za-z0-9]*)="([^"]+)"', svg_text):
        ET.register_namespace(prefix, uri)
    root = ET.fromstring(svg_text)
    parent = {child: p for p in root.iter() for child in p}
    by_id = {e.get("id"): e for e in root.iter() if e.get("id")}

    targets = {}
    for (family, state), style in outlined.items():
        for piece in (None,) + PIECES:
            eid = f"{family}-{state}" + (f"-{piece}" if piece else "")
            if eid in by_id:
                b = renderer.boundsOnElement(eid)
                targets[eid] = (piece, round(b.x(), 3), round(b.y(), 3), round(b.width(), 3), round(b.height(), 3), style)

    fresh_ids = {f"{base}-{p}" if p else base for base in FRESH for p in (None,) + PIECES} & by_id.keys()
    glyph_bounds = {}
    for eid in GLYPHS:
        if eid in by_id:
            b = renderer.boundsOnElement(eid)
            glyph_bounds[eid] = (b.x(), b.y(), b.width(), b.height())
    shadow = menu_shadow_elements()
    replaced = set(targets) | fresh_ids | set(glyph_bounds) | ({eid for eid, _ in shadow} & by_id.keys())

    external = [e.get("id") for e in root.iter()
                if (e.get(XLINK_HREF) or e.get("href") or "").lstrip("#") in replaced and e.get("id") not in replaced]
    if external:
        sys.exit(f"elements outside the redrawn set reference redrawn ones: {external}")

    for eid in replaced:
        parent[by_id[eid]].remove(by_id[eid])
    new = []
    for eid, (piece, x, y, w, h, (fill, outline, width)) in targets.items():
        new.append((eid, "".join(piece_shapes(piece, x, y, w, h, fill, outline, width))))
    # Fresh 9-slices live off-canvas; Kvantum only cares about each element's own bounds.
    for n, (base, (f, fill, outline)) in enumerate(FRESH.items()):
        x0, y0, inner = -2000.0, -2000.0 - n * 100, 8.0
        boxes = {None: (x0 + f, y0 + f, inner, inner),
                 "top": (x0 + f, y0, inner, f), "bottom": (x0 + f, y0 + f + inner, inner, f),
                 "left": (x0, y0 + f, f, inner), "right": (x0 + f + inner, y0 + f, f, inner),
                 "topleft": (x0, y0, f, f), "topright": (x0 + f + inner, y0, f, f),
                 "bottomleft": (x0, y0 + f + inner, f, f), "bottomright": (x0 + f + inner, y0 + f + inner, f, f)}
        for piece, (x, y, w, h) in boxes.items():
            eid = f"{base}-{piece}" if piece else base
            new.append((eid, "".join(piece_shapes(piece, x, y, w, h, fill, outline, 1))))
    for eid, (x, y, w, h) in glyph_bounds.items():
        # A transparent 16x16 box keeps the original bounds so Kvantum scales the glyph the same way.
        body = f'<rect x="0" y="0" width="16" height="16" fill="#000000" fill-opacity="0"/>{GLYPHS[eid]}'
        new.append((eid, f'<g transform="translate({x},{y}) scale({w / 16},{h / 16})">{body}</g>'))
    new.extend(shadow)
    # Kvantum draws menu separators from "<indicator>-separator", which KvLibadwaita lacks.
    h = MENU_SEPARATOR_HEIGHT
    new.append(("menuitem-separator",
                f'<rect x="-2300" y="-2300" width="100" height="{h}" fill="#000000" fill-opacity="0"/>'
                f'<rect x="-2300" y="{-2300 + h // 2}" width="100" height="1" fill="{GNOME_SEPARATOR}"/>'))
    for eid, shapes in new:
        root.append(ET.fromstring(f'<g xmlns="{SVG_NS}" id="{eid}">{shapes}</g>'))
    targets = replaced | {eid for eid, _ in new}

    for e in root.iter():
        eid = e.get("id") or ""
        if eid.startswith("header-separator") or (eid.startswith("header-") and "-bottom" in eid):
            # Column header underline and separators: solid black instead of 12 % black.
            for d in e.iter():
                for attr in ("opacity", "fill-opacity"):
                    if d.get(attr):
                        d.set(attr, "1")
                if d.get("style"):
                    d.set("style", re.sub(r"(fill-opacity|opacity):[0-9.]+", r"\1:1", d.get("style")))
        if re.fullmatch(r"(checkbox|radio)-(normal|focused)", eid):
            # Unchecked indicators: black ring and pure white inside instead of light grey.
            swap = {"#bdbdbd": BLACK, "#b0b0b0": BLACK, "#f9ffff": WHITE}
            for d in e.iter():
                for attr in ("fill", "stroke"):
                    if (d.get(attr) or "").lower() in swap:
                        d.set(attr, swap[d.get(attr).lower()])
                if d.get("style"):
                    d.set("style", re.sub(r"#(bdbdbd|b0b0b0|f9ffff)", lambda m: swap["#" + m.group(1).lower()], d.get("style"), flags=re.I))
        if eid.startswith("menubar-normal"):
            # [Toolbar] also uses the menubar element, so this whitens toolbars too.
            for d in e.iter():
                if d.get("fill"):
                    d.set("fill", WHITE)
                if d.get("style"):
                    d.set("style", re.sub(r"fill:#[0-9a-fA-F]{3,6}", f"fill:{WHITE}", d.get("style")))
    return ET.tostring(root, encoding="unicode"), len(targets)


def build_kvconfig(cfg, comment):
    cfg = recolor_accent(cfg)
    out, section, seen, sections = [], None, set(), set()

    def close_section():
        trailing = []
        while out and not out[-1].strip():
            trailing.append(out.pop())
        out.extend(f"{k}={v}" for (s, k), v in FORCED.items() if s == section and (s, k) not in seen)
        out.extend(trailing)

    for line in cfg.splitlines():
        header = re.match(r"^\[(.+)\]\s*$", line)
        if header:
            close_section()
            section = header.group(1)
            sections.add(section)
            out.append(line)
            if section in BOLD_SECTIONS:
                out.append("text.bold=true")
            elif section in REGULAR_SECTIONS:
                out.append("text.bold=false")
            continue
        key = line.split("=", 1)[0].strip()
        if (section, key) in FORCED:
            seen.add((section, key))
            line = f"{key}={FORCED[(section, key)]}"
        elif section == "%General" and key == "author":
            line = f"author=eink-qt-theming, derived from KvLibadwaita ({line.split('=', 1)[1].strip()})"
        elif section == "%General" and key == "comment":
            line = f"comment={comment}"
        elif section == "GeneralColors" and key in GENERAL_COLORS:
            line = f"{key}={GENERAL_COLORS[key]}"
        elif (section in BOLD_SECTIONS or section in REGULAR_SECTIONS) and key == "text.bold":
            continue
        elif section == "PanelButtonCommand" and key == "text.margin":
            # Equal-width rows (Krusader's F-key bar) otherwise drop the longest label to non-bold.
            line = "text.margin.top=4\ntext.margin.bottom=4\ntext.margin.left=0\ntext.margin.right=0"
        elif key.startswith("text.") and key.endswith(".color"):
            line = re.sub(r"#444444|#424242|#333333", BLACK, line, flags=re.I)
        out.append(line)
    close_section()
    for missing in sorted({s for s, _ in FORCED} - sections):
        out += ["", f"[{missing}]"] + [f"{k}={v}" for (s, k), v in FORCED.items() if s == missing]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate the KvEink Kvantum theme.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("base", type=Path, nargs="?")
    parser.add_argument("--controls", choices=("gnome", "outline"), default="gnome",
                        help="gnome: libadwaita's grey fills (KvEink); outline: white with 1 px black outlines (KvEinkOutline)")
    args = parser.parse_args()
    name = NAMES[args.controls]
    out_dir = args.output_dir / name
    if args.base is None:
        args.base = next((c for c in BASE_CANDIDATES if any(c.glob("*.kvconfig"))), BASE_CANDIDATES[0])
    base_svg = next((p for p in args.base.glob("*.svg") if not p.stem.endswith("Dark")), None)
    base_cfg = next((p for p in args.base.glob("*.kvconfig") if not p.stem.endswith("Dark")), None)
    if not base_svg or not base_cfg:
        sys.exit(f"no KvLibadwaita theme found in {args.base}")
    outlined = {**OUTLINED, **GNOME_CONTROLS} if args.controls == "gnome" else OUTLINED

    app = QApplication([])  # noqa: F841 - QSvgRenderer needs a GUI application
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "stage.svg"
        stage.write_text(first_pass_svg(base_svg.read_text()))
        svg, redrawn = second_pass_svg(stage, outlined)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.svg").write_text(svg)
    comment = {"gnome": "Black and white libadwaita look for e-ink displays",
               "outline": "Black and white libadwaita look for e-ink displays, outlined controls"}[args.controls]
    (out_dir / f"{name}.kvconfig").write_text(build_kvconfig(base_cfg.read_text(), comment))
    print(f"{name}: {redrawn} elements redrawn from {args.base.name} -> {out_dir}")


if __name__ == "__main__":
    main()
