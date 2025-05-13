#!/usr/bin/env python3
"""
Python BitTorrent Client
A simple BitTorrent client similar to qBittorrent
"""

import sys
import os

# Add the current directory to the path to make imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run the main application
from main import main

if __name__ == "__main__":
    main() 