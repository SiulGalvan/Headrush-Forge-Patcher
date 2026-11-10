"""PyInstaller entry point (the package's __main__.py uses relative imports)."""
import sys

from mx5forge.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:          # double click: graphical interface
        from mx5forge import gui
        sys.exit(gui.main())
    sys.exit(main())
