#!/usr/bin/env python3
"""
run.py - Script de ejecución para gnome-tmux

Autor: Homero Thompson del Lago del Terror
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gnome_tmux.main import main

if __name__ == "__main__":
    sys.exit(main())
