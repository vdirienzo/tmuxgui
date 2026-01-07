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

# Check GNOME SDK 49
echo "Checking GNOME SDK 49..."
if ! flatpak list | grep -q "org.gnome.Sdk.*49"; then
    echo "GNOME SDK 49 not found. Installing..."
    flatpak install -y org.gnome.Sdk//49 || {
        echo "ERROR: Could not install GNOME SDK 49"
        echo "Try: flatpak install org.gnome.Sdk//49"
        exit 1
    }
fi
echo "GNOME SDK 49: OK"

# Build
echo ""
echo "Building TmuxGUI Flatpak..."
echo ""

flatpak-builder --force-clean build-dir io.github.vdirienzo.TmuxGUI.yml

# Install locally
echo ""
echo "Installing locally..."
flatpak-builder --user --install --force-clean build-dir io.github.vdirienzo.TmuxGUI.yml

echo ""
echo "=== Build complete! ==="
echo ""
echo "Run with:"
echo "  flatpak run io.github.vdirienzo.TmuxGUI"
echo ""
