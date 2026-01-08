#!/bin/bash
# uninstall-native.sh - Desinstala TmuxGUI versión nativa
# Autor: Homero Thompson del Lago del Terror

APP_ID="io.github.vdirienzo.TmuxGUI"

echo "=== Desinstalando TmuxGUI (versión nativa) ==="

# Eliminar .desktop
rm -f ~/.local/share/applications/$APP_ID.desktop

# Eliminar iconos
rm -f ~/.local/share/icons/hicolor/48x48/apps/$APP_ID.png
rm -f ~/.local/share/icons/hicolor/64x64/apps/$APP_ID.png
rm -f ~/.local/share/icons/hicolor/128x128/apps/$APP_ID.png
rm -f ~/.local/share/icons/hicolor/512x512/apps/$APP_ID.png

# Actualizar cache
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true

echo "TmuxGUI desinstalado."
echo "Nota: El código fuente no se eliminó."
