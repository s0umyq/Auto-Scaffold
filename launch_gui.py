#!/usr/bin/env python3
"""
Auto-Scaffold GUI Launcher
Simple script to launch the GUI with proper setup.
"""
import sys
import subprocess
import os
from pathlib import Path


def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    # Add src to Python path
    sys.path.insert(0, str(src_dir))
    
    # Change to project root
    os.chdir(project_root)
    
    print("=" * 50)
    print("  Auto-Scaffold GUI Launcher")
    print("=" * 50)
    print()
    print("Starting GUI server on http://127.0.0.1:8765")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Import and run the GUI
        from auto_scaffold.gui.server import run_gui
        run_gui()
    except ImportError as e:
        print(f"Error: Could not import GUI module: {e}")
        print("Make sure dependencies are installed: pip install -e .[dev]")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()