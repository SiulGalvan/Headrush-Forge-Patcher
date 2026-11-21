"""HeadRush MX5 Forge: build a patched HeadRush MX5 2.7 Update.img (NAM mod, MX5 Bridge, pedal design)."""
import os as _os
import sys as _sys

__version__ = "1.0.3"
HERE = _os.path.dirname(_os.path.abspath(__file__))
# MX-Edit's firmware modules (MIT) import each other as top-level modules
VENDOR = _os.path.join(HERE, "vendor", "mxedit")
if VENDOR not in _sys.path:
    _sys.path.insert(0, VENDOR)
