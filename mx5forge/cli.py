import argparse
import sys

from . import __version__, pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mx5forge", description="Build a patched HeadRush MX5 2.7 firmware updater "
                                 "(NAM mod, MX5 Bridge, pedal design). Unofficial - use at your own risk.")
    ap.add_argument("--instances", type=int, choices=(0, 2, 4), default=2,
                    help="2 = Anxiety OD hijacked, V2 untouched; 4 = Anxiety OD and Anxiety OD V2 hijacked (default 2)")
    ap.add_argument("--engine", choices=("nam-mod", "extended", "extended-fair"), default="nam-mod",
                    help="NAM engine: nam-mod 0.1.6 (default, proven on MX5), the NAM Extended build, or extended-fair (Extended without the SCHED_IDLE/nice background priority, which slowed the MX5 in USB-audio 48 kHz mode)")
    ap.add_argument("--amp", action="store_true",
                    help="EXPERIMENTAL: also make the 82 LEAD 800 Bright amp a NAM amp (needs --engine extended)")
    ap.add_argument("--probe", action="store_true", help="DIAGNOSTIC: record load figures after USB audio starts (probe.txt on the USB drive)")
    ap.add_argument("--no-daemons", action="store_true",
                    help="DIAGNOSTIC: Bridge without its two background services (MX-Edit will not connect)")
    ap.add_argument("--model", choices=sorted(pipeline.DEVICE), default="mx5",
                    help="device to download the official firmware for (a firmware file given with --input is recognised by itself). pedalboard: experimental, never run on real hardware")
    ap.add_argument("--no-bridge", action="store_true", help="do not add the MX5 Bridge (MX-Edit support)")
    ap.add_argument("--design", action="store_true",
                    help="pedal design / chain art; Anxiety OD gets the NAM art, and with --instances 2 Anxiety OD V2 keeps its original art")
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
    o = pipeline.Options(a.instances, not a.no_bridge, a.design, a.rack_art, a.input, a.out or ".", engine=a.engine, amp=a.amp,
                         daemons=not a.no_daemons, probe=a.probe, model=a.model)
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
