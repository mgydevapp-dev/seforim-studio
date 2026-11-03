#!/bin/bash
# One-time setup for Mac / Linux
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt || python3 -m pip install --break-system-packages -r requirements.txt
echo "Done. Start with: ./run_mac_linux.sh"
