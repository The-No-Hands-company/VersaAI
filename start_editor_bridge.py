#!/usr/bin/env python3
"""
VersaAI Code Editor Bridge - Quick Start

Launches the WebSocket server for code editor integration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from versaai.code_editor_bridge.server import main

if __name__ == '__main__':
    main()
