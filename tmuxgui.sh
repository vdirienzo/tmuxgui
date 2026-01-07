#!/bin/bash
# TmuxGUI launcher script
# Autor: Homero Thompson del Lago del Terror

export PYTHONPATH="/app/share/tmuxgui:$PYTHONPATH"
exec python3 /app/share/tmuxgui/run.py "$@"
