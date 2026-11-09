import sys

from .cli import main

if len(sys.argv) == 1:          # double click / python -m mx5forge: graphical interface
    from . import gui
    sys.exit(gui.main())
sys.exit(main())
