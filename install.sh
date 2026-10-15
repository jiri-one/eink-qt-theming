#!/bin/bash
# Build and install the e-ink theming for the current user. Every file it replaces is backed up first.
# Usage: ./install.sh [KVLIBADWAITA_THEME_DIR]   (the directory holding KvLibadwaita*.svg; found automatically if omitted)
set -euo pipefail
cd "$(dirname "$0")"

CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
BACKUP="${XDG_STATE_HOME:-$HOME/.local/state}/eink-qt-theming/backup-$(date +%Y%m%d-%H%M%S)"

python3 -c 'import PyQt6.QtSvg' 2>/dev/null || python3 -c 'import PyQt5.QtSvg' 2>/dev/null ||
    { echo "Generating the theme needs PyQt6 or PyQt5 (python-pyqt6 or python-pyqt5)." >&2; exit 1; }

backup() {
    local f rel
    mkdir -p "$BACKUP"
    for f in "$@"; do
        if [ ! -e "$f" ]; then
            echo "$f" >> "$BACKUP/created-by-install.txt"
            continue
        fi
        rel="${f#"$HOME"/}"
        mkdir -p "$BACKUP/$(dirname "$rel")"
        # Copy what links point to: the writers below follow symlinks (dotfile managers), so a copied
        # link would point at the overwritten file. Fall back to the links if one dangles.
        cp -aL "$f" "$BACKUP/$rel" 2>/dev/null || { rm -rf "${BACKUP:?}/$rel"; cp -a "$f" "$BACKUP/$rel"; }
    done
}

# Like the Python writers, write through a symlinked destination instead of replacing the link.
put() {
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2" 2>/dev/null || { rm -f "$2"; cp "$1" "$2"; }
}

backup "$CONFIG/Kvantum/kvantum.kvconfig" "$CONFIG/Kvantum/KvEink" "$CONFIG/Kvantum/KvEinkOutline" \
    "$CONFIG/kdeglobals" "$CONFIG/qt5ct/qt5ct.conf" "$CONFIG/qt6ct/qt6ct.conf" \
    "$CONFIG/fontconfig/conf.d/50-eink-qt-apps.conf" "$DATA/icons/Eink" "$DATA/icons/KIconEngine" \
    "$DATA/color-schemes/Eink.colors"

python3 kvantum/build_kveink.py "$CONFIG/Kvantum" ${1:+"$1"} --controls gnome
python3 kvantum/build_kveink.py "$CONFIG/Kvantum" ${1:+"$1"} --controls outline
python3 icons/build_icons.py "$DATA/icons"
put kde/Eink.colors "$DATA/color-schemes/Eink.colors"
python3 tools/write_kdeglobals.py "$CONFIG/kdeglobals"
python3 tools/configure_qtct.py "$CONFIG"
put config/fontconfig/50-eink-qt-apps.conf "$CONFIG/fontconfig/conf.d/50-eink-qt-apps.conf"

echo
echo "Replaced files were backed up to $BACKUP; created-by-install.txt there lists the ones that are new."
cat <<'EOF'
Still manual (see README):
  - outside GNOME: export QT_WAYLAND_DECORATION=adwaita (config/niri.kdl, config/bash_profile)
  - Krusader: append config/krusader-colors.ini to ~/.config/krusaderrc while Krusader is closed
  - Kasts: set headerSize=0 in ~/.config/KDE/kasts.conf while Kasts is closed
  - GTK4 apps: add config/gtk-4.0/gtk.css to ~/.config/gtk-4.0/gtk.css for a black accent colour
Restart Qt and GTK applications to pick up the new themes.
EOF
