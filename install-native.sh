#!/bin/bash
# install-native.sh - Instala TmuxGUI como aplicación nativa (sin Flatpak)
# Autor: Homero Thompson del Lago del Terror

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ID="io.github.vdirienzo.TmuxGUI"

echo "=== Instalando TmuxGUI (versión nativa) ==="

# Verificar dependencias
echo "Verificando dependencias..."
python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Vte', '3.91')" 2>/dev/null || {
    echo "ERROR: Faltan dependencias. Instalar:"
    echo "  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-vte-3.91 libadwaita-1-0 gir1.2-adw-1 tmux"
    exit 1
}

which tmux >/dev/null || {
    echo "ERROR: tmux no está instalado. Instalar con: sudo apt install tmux"
    exit 1
}

# Crear directorios
mkdir -p ~/.local/share/applications
mkdir -p ~/.local/share/icons/hicolor/48x48/apps
mkdir -p ~/.local/share/icons/hicolor/64x64/apps
mkdir -p ~/.local/share/icons/hicolor/128x128/apps
mkdir -p ~/.local/share/icons/hicolor/512x512/apps

# Copiar iconos con permisos correctos
echo "Instalando iconos..."
install -Dm644 "$SCRIPT_DIR/data/icons/hicolor/48x48/apps/$APP_ID.png" ~/.local/share/icons/hicolor/48x48/apps/$APP_ID.png
install -Dm644 "$SCRIPT_DIR/data/icons/hicolor/64x64/apps/$APP_ID.png" ~/.local/share/icons/hicolor/64x64/apps/$APP_ID.png
install -Dm644 "$SCRIPT_DIR/data/icons/hicolor/128x128/apps/$APP_ID.png" ~/.local/share/icons/hicolor/128x128/apps/$APP_ID.png
install -Dm644 "$SCRIPT_DIR/data/icons/hicolor/512x512/apps/$APP_ID.png" ~/.local/share/icons/hicolor/512x512/apps/$APP_ID.png

# Crear .desktop con path correcto
echo "Creando entrada de escritorio..."
cat > ~/.local/share/applications/$APP_ID.desktop << EOF
[Desktop Entry]
Name=TmuxGUI
Comment=GNOME frontend for tmux terminal multiplexer
Exec=python3 $SCRIPT_DIR/run.py
Icon=$APP_ID
Terminal=false
Type=Application
Categories=System;TerminalEmulator;Utility;
Keywords=terminal;tmux;session;multiplexer;
StartupNotify=true
StartupWMClass=$APP_ID
EOF

# Actualizar cache de iconos
echo "Actualizando cache de iconos..."
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true

echo ""
echo "=== Instalación completada ==="
echo ""
echo "TmuxGUI ahora aparece en el menú de aplicaciones."
echo "También podés ejecutarlo con: python3 $SCRIPT_DIR/run.py"
echo ""
echo "Para desinstalar: ./uninstall-native.sh"
