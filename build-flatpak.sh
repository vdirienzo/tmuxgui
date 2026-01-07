#!/bin/bash
# Build script for TmuxGUI Flatpak
# Autor: Homero Thompson del Lago del Terror

set -e

echo "=== TmuxGUI Flatpak Builder ==="
echo ""

# Check dependencies
check_dep() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 not found. Install with:"
        echo "  sudo apt install $2"
        exit 1
    fi
}

check_dep flatpak flatpak
check_dep flatpak-builder flatpak-builder

# Add Flathub if not present
if ! flatpak remote-list | grep -q flathub; then
    echo "Adding Flathub repository..."
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
fi

# Install GNOME SDK if needed
echo "Checking GNOME Platform/SDK 48..."
flatpak install -y flathub org.gnome.Platform//49 org.gnome.Sdk//49 2>/dev/null || true

# Build
echo ""
echo "Building TmuxGUI Flatpak..."
echo ""

flatpak-builder --force-clean --user --install-deps-from=flathub build-dir org.gnome.TmuxGUI.yml

# Install locally
echo ""
echo "Installing locally..."
flatpak-builder --user --install --force-clean build-dir org.gnome.TmuxGUI.yml

echo ""
echo "=== Build complete! ==="
echo ""
echo "Run with:"
echo "  flatpak run org.gnome.TmuxGUI"
echo ""
echo "Or find it in your application menu as 'TmuxGUI'"
