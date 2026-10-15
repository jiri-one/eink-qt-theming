# ArchWiki draft: Uniform look for Qt and GTK applications

Proposed edits for <https://wiki.archlinux.org/title/Uniform_look_for_Qt_and_GTK_applications>, in MediaWiki
markup. Verified on Manjaro with Qt 6.11.2, KDE Frameworks 6.29, Kvantum 1.1.8 and niri 26.04. Each block says
where it goes; submit them as separate edits with short summaries.

---

## 1. Section "QGtk3Style": append after the existing paragraph

```mediawiki
The palette is derived from the active GTK 3 theme, including the built-in ''HighContrast'' theme. To adjust it, dump the mapping with {{ic|1=QT_GUI_GTK_JSON_SAVE=/path/to/file.json}} (add {{ic|1=QT_GUI_GTK_JSON_HARDCODED=true}} to save fixed colors), edit the file and load it with {{ic|1=QT_GUI_GTK_JSON=/path/to/file.json}}. Since Qt 6.10, the Fusion style draws black outlines when the platform theme reports a high-contrast preference, which {{ic|gtk3}} does when [[GNOME]]'s high contrast setting is enabled.
```

Edit summary: `QGtk3Style: palette override via QT_GUI_GTK_JSON, high contrast in Fusion`

## 2. Section "QAdwaitaDecorations": replace the sentence about the AUR packages

```mediawiki
For Qt 5 the plugin can be installed with {{AUR|qadwaitadecorations-qt5}}; for Qt 6 it is part of {{Pkg|qt6-wayland}}. Qt selects it automatically only when {{ic|XDG_CURRENT_DESKTOP}} contains {{ic|GNOME}}; on other compositors (e.g. [[niri]] or [[Sway]]) it falls back to the plain ''bradient'' decoration unless {{ic|1=QT_WAYLAND_DECORATION=adwaita}} is set. The title font is taken from the platform theme, e.g. the general font configured in {{Pkg|qt6ct}}.
```

Edit summary: `QAdwaitaDecorations: Qt 6 plugin ships with qt6-wayland; needs QT_WAYLAND_DECORATION outside GNOME`

## 3. Section "Tips and tricks": new subsection

```mediawiki
=== High contrast and e-ink displays ===

To match GNOME's high contrast mode, for example on a black-and-white e-ink monitor:

* Use [[#GTK themes ported to Kvantum|Kvantum]] with a [https://github.com/GabePoel/KvLibadwaita KvLibadwaita]-based theme recolored to high contrast and set fonts and icons in {{Pkg|qt6ct}}/{{Pkg|qt5ct}}. Do not combine Kvantum with {{ic|1=QT_QPA_PLATFORMTHEME=gtk3}}, see [[#Qt applications use a monospace font with Kvantum and the gtk3 platform theme]].
* Outside Plasma, KDE applications pick ''Breeze'' or ''Breeze Dark'' from the system's color preference, or only the platform palette when high contrast is requested, unless {{ic|ColorScheme}} is set in the {{ic|[UiSettings]}} group of {{ic|~/.config/kdeglobals}} or of the application's own configuration file, which takes precedence. Kirigami applications take their colors from this scheme, not from the Qt palette; {{ic|1=frameContrast=1.0}} in the {{ic|[KDE]}} group makes their separators black and {{ic|1=AnimationDurationFactor=0}} disables animations.
* KDE applications load icons through ''KIconLoader'', which ignores icon theme directories with {{ic|1=Context=UI}} and falls back to ''hicolor'' and ''Breeze'' when a theme has no other valid directory.
* On [[Wayland]], Qt takes antialiasing and hinting only from [[fontconfig]]. Rules can be limited to one program with {{ic|1=<nowiki><test name="prgname"></nowiki>}}.

The [https://github.com/jiri-one/eink-qt-theming eink-qt-theming] project generates a black-and-white Kvantum theme and the matching icon theme, color scheme and configuration.
```

Edit summary: `Add high contrast / e-ink tips`

## 4. Section "Troubleshooting": new subsection

```mediawiki
=== Qt applications use a monospace font with Kvantum and the gtk3 platform theme ===

With {{ic|1=QT_QPA_PLATFORMTHEME=gtk3}} and {{ic|1=QT_STYLE_OVERRIDE=kvantum}}, the application font can become the monospace font, because the GTK 3 platform theme reads the general and fixed fonts from a shared GTK style context. Use {{Pkg|qt6ct}}/{{Pkg|qt5ct}} as the platform theme with Kvantum instead.
```

Edit summary: `Troubleshooting: monospace font with Kvantum + gtk3 platform theme`

## 5. Section "Troubleshooting": new subsection (optional)

```mediawiki
=== qt6ct does not hide icons in menus ===

With Qt 6.11, the ''Show icons in menus'' option of {{Pkg|qt6ct}} ({{ic|1=menus_have_icons=false}}) has no effect: Qt sets {{ic|Qt::AA_DontShowIconsInMenus}} from the platform theme's {{ic|ShowIconsInMenus}} hint, which qt6ct does not provide. With Kvantum, set {{ic|1=iconless_menu=true}} in the {{ic|[Hacks]}} section of the theme's configuration instead.
```

Edit summary: `Troubleshooting: qt6ct menus_have_icons ineffective on Qt 6`
