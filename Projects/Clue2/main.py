#!/usr/bin/env python3
"""
Clue Mystery Game
Entry point.
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from clue_game.app import main

if __name__ == "__main__":
    main()
