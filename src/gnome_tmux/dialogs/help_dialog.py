"""
help_dialog.py - Diálogos de ayuda y configuración de temas

Autor: Homero Thompson del Lago del Terror
"""

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from ..themes import ThemeManager


def show_help_dialog(parent: Adw.Window) -> None:
    """
    Muestra el diálogo de ayuda y about.

    Args:
        parent: Ventana padre
    """
    dialog = Adw.Window(transient_for=parent)
    dialog.set_title("Help - TmuxGUI")
    dialog.set_default_size(500, 600)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(True)
    toolbar_view.add_top_bar(header)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
    content.set_margin_top(24)
    content.set_margin_bottom(24)
    content.set_margin_start(24)
    content.set_margin_end(24)

    # Logo y título
    logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    logo_box.set_halign(Gtk.Align.CENTER)

    logo = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
    logo.set_pixel_size(64)
    logo_box.append(logo)

    title = Gtk.Label(label="TmuxGUI")
    title.add_css_class("title-1")
    logo_box.append(title)

    version = Gtk.Label(label="Version 0.5.0")
    version.add_css_class("dim-label")
    logo_box.append(version)

    subtitle = Gtk.Label(label="GNOME native frontend for tmux")
    subtitle.add_css_class("dim-label")
    logo_box.append(subtitle)

    content.append(logo_box)
    content.append(Gtk.Separator())

    # Features
    features_group = Adw.PreferencesGroup(title="Features")
    features = [
        ("Session Management", "Create, rename, delete tmux sessions"),
        ("Window Management", "Create, rename, close and reorder windows"),
        ("Remote Sessions", "Connect to remote hosts via SSH"),
        ("Integrated Terminal", "VTE terminal with full tmux support"),
        ("File Browser", "Navigate filesystem with CRUD operations"),
        ("Drag and Drop", "Drag files/folders to terminal, reorder sections"),
    ]

    for title_text, desc in features:
        row = Adw.ActionRow(title=title_text, subtitle=desc)
        row.set_activatable(False)
        features_group.add(row)

    content.append(features_group)

    # Shortcuts
    shortcuts_group = Adw.PreferencesGroup(title="Keyboard Shortcuts")
    shortcuts = [
        ("F9", "Toggle sessions sidebar"),
        ("F10", "Toggle file browser"),
        ("Ctrl+B d", "Detach from tmux session"),
        ("Ctrl+B c", "Create new window (in tmux)"),
        ("Ctrl+B n / p", "Next / Previous window"),
        ("Ctrl+B %", "Split pane horizontally"),
        ('Ctrl+B "', "Split pane vertically"),
    ]

    for shortcut, desc in shortcuts:
        row = Adw.ActionRow(title=shortcut, subtitle=desc)
        row.set_activatable(False)
        shortcuts_group.add(row)

    content.append(shortcuts_group)

    # Tips
    tips_group = Adw.PreferencesGroup(title="Quick Start")
    tips = [
        ("1. Create a session", "Click + button for local or remote sessions"),
        ("2. Remote hosts", "Save SSH connections for quick access"),
        ("3. Select a window", "Click on any window to attach terminal"),
        ("4. Drag to terminal", "Drag files/folders to paste their path"),
        ("5. Detach", "Press Ctrl+B d to detach from session"),
    ]

    for tip_title, tip_desc in tips:
        row = Adw.ActionRow(title=tip_title, subtitle=tip_desc)
        row.set_activatable(False)
        tips_group.add(row)

    content.append(tips_group)
    content.append(Gtk.Separator())

    # About
    about_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    about_box.set_halign(Gtk.Align.CENTER)

    author_label = Gtk.Label(label="Author")
    author_label.add_css_class("heading")
    about_box.append(author_label)

    author_name = Gtk.Label(label="Homero Thompson del Lago del Terror")
    about_box.append(author_name)

    content.append(about_box)

    # Copyright
    copyright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    copyright_box.set_halign(Gtk.Align.CENTER)
    copyright_box.set_margin_top(12)

    copyright_label = Gtk.Label(label="Copyright 2026")
    copyright_label.add_css_class("dim-label")
    copyright_box.append(copyright_label)

    license_label = Gtk.Label(label="MIT License")
    license_label.add_css_class("dim-label")
    copyright_box.append(license_label)

    github_label = Gtk.Label(label="github.com/vdirienzo/gnome-tmux")
    github_label.add_css_class("dim-label")
    copyright_box.append(github_label)

    content.append(copyright_box)

    scrolled.set_child(content)
    toolbar_view.set_content(scrolled)

    dialog.present()


def show_theme_dialog(
    parent: Adw.Window,
    theme_manager: "ThemeManager",
) -> None:
    """
    Muestra el diálogo de selección de tema.

    Args:
        parent: Ventana padre
        theme_manager: Instancia del gestor de temas
    """
    dialog = Adw.Window(transient_for=parent)
    dialog.set_title("Theme")
    dialog.set_default_size(350, 450)
    dialog.set_modal(True)

    toolbar_view = Adw.ToolbarView()
    dialog.set_content(toolbar_view)

    header = Adw.HeaderBar()
    header.set_show_end_title_buttons(True)
    toolbar_view.add_top_bar(header)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    themes_group = Adw.PreferencesGroup(title="Select Theme")

    current_theme = theme_manager.get_current_theme()
    themes = theme_manager.get_available_themes()

    first_check = None
    for theme_id, theme_data in themes.items():
        row = Adw.ActionRow(title=theme_data["name"])
        row.set_activatable(True)

        check = Gtk.CheckButton()
        check.set_active(theme_id == current_theme)
        if first_check is None:
            first_check = check
        else:
            check.set_group(first_check)

        def on_toggled(chk, tid=theme_id):
            if chk.get_active():
                theme_manager.apply_theme(tid)

        check.connect("toggled", on_toggled)
        row.add_prefix(check)
        row.set_activatable_widget(check)
        themes_group.add(row)

    content.append(themes_group)

    scrolled.set_child(content)
    toolbar_view.set_content(scrolled)

    dialog.present()
