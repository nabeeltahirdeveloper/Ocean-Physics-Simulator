#!/bin/zsh
SCRIPT_DIR="${0:A:h}"
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/ocean_wave_simulator.py"
