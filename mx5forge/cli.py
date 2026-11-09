import argparse
import sys

from . import __version__, pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mx5forge", description="Build a patched HeadRush MX5 2.7 firmware updater "
                                 "(NAM mod, MX5 Bridge, pedal design). Unofficial - use at your own risk.")
    ap.add_argument("--instances", type=int, choices=(2, 4), default=2,
                    help="2 = Anxiety OD hijacked, V2 untouched; 4 = Anxiety OD and Anxiety OD V2 hijacked (default 2)")
    ap.add_argument("--no-bridge", action="store_true", help="do not add the MX5 Bridge (MX-Edit support)")
    ap.add_argument("--design", action="store_true",
                    help="pedal design / chain art (only with --instances 4; the 2-instance build keeps the original pedals)")
    ap.add_argument("--rack-art", metavar="DIR", help="folder with your own pedal-shaped PNGs for the 11 rack modules")
    ap.add_argument("--input", metavar="FILE", help="official updater (.zip/.exe), folder or Update.img "
                                                    "(default: download it from inMusic)")
    ap.add_argument("--out", metavar="DIR", help="folder for the result (default: current folder)")
    ap.add_argument("--version", action="version", version="mx5forge " + __version__)
    ap.add_argument("--gui", action="store_true", help="open the graphical interface")
    a = ap.parse_args(argv)
    if a.gui:
        from . import gui
        return gui.main()
    o = pipeline.Options(a.instances, not a.no_bridge, a.design, a.rack_art, a.input, a.out or ".")
    print("mx5forge %s - unofficial, use at your own risk\n" % __version__)
    try:
        out, missing = pipeline.build(o)
    except pipeline.ERRORS as e:
        print("\nERROR: %s" % e)
        return 1
    print("\nDone: %s" % out)
    if missing:
        print("Copy these files from the official HeadRush updater into that folder: " + ", ".join(missing))
    print("\n" + pipeline.hint(o, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
