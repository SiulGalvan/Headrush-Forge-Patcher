"""Build a patched MX5 2.7 firmware updater: NAM mod (2 or 4 instances), MX5 Bridge, pedal design."""
import hashlib
import json
import lzma
import os
import shutil
import tempfile

from . import __version__
import bridgepatch   # vendored MX-Edit modules (see mx5forge/__init__.py)
import ext4
import fitpatch
import patcher
import xzblocks

from .art import apply as art_apply
from .art import qmlport
from .nam import install as nam_install

Fail = patcher.Fail
ERRORS = (patcher.Fail, bridgepatch.PatchError, ext4.Ext4Error, qmlport.ArtError, nam_install.launcher.LauncherError,
          nam_install.elfpatch.ElfPatchError, ValueError, OSError)


class Options:
    def __init__(self, instances=2, bridge=True, design=False, rack_dir=None, source=None, out_parent=None,
                 log=print, progress=None, engine="nam-mod", amp=False, audio_midi=False, daemons=True, probe=False):
        self.instances, self.bridge, self.design = instances, bridge, design
        self.rack_dir, self.source, self.out_parent = rack_dir, source, out_parent
        self.log, self.progress = log, progress
        self.engine, self.amp = engine, amp
        self.audio_midi = audio_midi
        self.daemons = daemons
        self.probe = probe


def label(o):
    if not o.instances:
        return "MX5 Bridge only (no NAM)"
    return "NAM x%d%s%s%s%s" % (o.instances, {"extended": " Extended", "extended-fair": " Extended (fair)"}.get(o.engine, ""), " + NAM amp" if o.amp else "",
                                " + MX5 Bridge" if o.bridge else "", " + pedal design" if o.design else "")


def folder_name(o):
    if not o.instances:
        return "HeadRush_MX5_2.7_BridgeOnly%s%s_Updater" % ("" if o.audio_midi else "Lite", "" if o.daemons else "NoDaemons")
    return "HeadRush_MX5_2.7_NAM%d%s%s%s%s_Updater" % (o.instances, {"extended": "_Ext", "extended-fair": "_ExtFair"}.get(o.engine, ""), "_Amp" if o.amp else "",
                                                   (("_Bridge" if o.audio_midi else "_BridgeLite") + ("" if o.daemons else "NoDaemons")) if o.bridge else "", "_Design" if o.design else "")


def config_json(o, original):
    """Config.json of the updater: the official one with new title and start button."""
    title = label(o)
    cfg = json.loads(original) if original else {"config": {}}
    c = cfg.setdefault("config", {})
    c["appName"] = "HeadRush MX5 v2.7 + %s (unofficial)" % title
    c["startButtonText"] = "Install %s" % title
    if not original:
        c.update({"deviceName": "HeadRush MX5", "notConnectedTitle": "HEADRUSH MX5 IS NOT DETECTED",
                  "allowUpdateOnBattery": True, "forceUpdate": False})
    return json.dumps(cfg, indent=4, ensure_ascii=False) + "\n"


def check_options(o):
    if o.instances not in (0, 2, 4):
        raise Fail("instances must be 0 (no NAM, diagnostic), 2 or 4")
    if o.instances == 0 and (o.design or o.amp or not o.bridge):
        raise Fail("0 NAM instances is a diagnostic build: only the MX5 Bridge can be applied")
    if o.engine not in nam_install.ENGINES:
        raise Fail("engine must be one of: " + ", ".join(nam_install.ENGINES))
    if o.amp and o.engine == "nam-mod":
        raise Fail("the NAM amp block needs the Extended engine")


def build(o):
    check_options(o)
    log = o.log
    patcher.LOG[0] = log
    if o.progress:
        patcher.PROGRESS[0] = o.progress
    model = bridgepatch.model("mx5")
    base = o.out_parent or patcher.BASE
    work = tempfile.mkdtemp(prefix="mx5forge_")
    try:
        src = o.source
        if not src:
            src = os.path.join(base, patcher.updater_name(model))
            if os.path.exists(src):
                log("Using the already downloaded %s" % os.path.basename(src))
            else:
                patcher.download(src, model)
        if not os.path.exists(src):
            raise Fail("Not found: %s" % src)
        folder = patcher.unpack(os.path.abspath(src), work)
        raw = open(os.path.join(folder, "Update.img"), "rb").read()
        if not fitpatch.verify(raw):
            raise Fail("Update.img is damaged (checksum mismatch)")
        found = patcher.model_of(raw)
        if found["key"] != "mx5":
            raise Fail("This firmware is for the HeadRush %s - this tool builds for the MX5 only." % found["device"])
        sha = hashlib.sha1(raw).hexdigest()
        if sha == found["sha1"]:
            log("Found the official HeadRush MX5 2.7 firmware.")
        else:
            log("Update.img sha1 %s is not the official 2.7 firmware - the build refuses anything that does not "
                "match exactly what it patches." % sha[:12])

        log("Unpacking the root file system ...")
        fs = ext4.Ext4(lzma.decompress(fitpatch.extract(raw, "rootfs")))
        fs.check()

        written = {}
        if o.instances:
            evil = bytearray(fs.cat(nam_install.EVIL))
            slot, slot2, slot_amp = nam_install.hijack_evil(evil, o.instances, log, amp=o.amp)
            if o.design:
                art_apply.apply(evil, o.rack_dir, nam_v2_badge=(o.instances == 4), log=log)
            nam_install.install(fs, evil, slot, slot2, log, engine=o.engine, slot_amp_hex=slot_amp)
            written[nam_install.EVIL] = bytes(evil)

        if o.bridge:
            def cat(p):
                try:
                    return fs.cat(p)
                except FileNotFoundError:
                    return b""
            info = None if not o.instances else "nam_mod_ref=%s via mx5forge %s\nnam_instanzen=%d\n" % ("Gigboard_NAM extended" if o.engine != "nam-mod" else "headrush-nam-mod 0.1.6", __version__, o.instances)
            bridgepatch.AUDIO_MIDI = o.audio_midi
            bridgepatch.DAEMONS = o.daemons
            bridgepatch.PROBE = o.probe
            files, _ = bridgepatch.plan(cat, info, log=log, device=found["device"])
            log("MX5 Bridge: writing %d files ..." % len(files))
            for target, (data, mode) in files.items():
                fs.write_file(target, data, mode)
                written[target] = data

        new_img = fs.finish()
        check = ext4.Ext4(new_img)
        check.check()
        for target, data in written.items():
            if check.cat(target) != data:
                raise Fail("Verification failed for %s" % target)
        log("All files verified. Compressing (takes a minute or two) ...")
        xz = xzblocks.compress(new_img)
        if lzma.decompress(xz) != new_img:
            raise Fail("Compression check failed")
        new = fitpatch.replace_image(raw, "rootfs", xz)
        if not fitpatch.verify(new):
            raise Fail("Final image check failed")
        for im in ("splash", "recoverysplash"):
            if fitpatch.extract(new, im) != fitpatch.extract(raw, im):
                raise Fail("Unexpected change in %s" % im)

        out = os.path.join(base, folder_name(o))
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "Update.img"), "wb").write(new)
        cfgp = os.path.join(folder, "Config.json")
        orig = open(cfgp, encoding="utf-8-sig").read() if os.path.exists(cfgp) else None
        open(os.path.join(out, "Config.json"), "w", encoding="utf-8", newline="\n").write(config_json(o, orig))
        missing = []
        for name in patcher.UPDATER_FILES:
            p = os.path.join(folder, name)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(out, name))
            else:
                missing.append(name)
        log("sha1 of the new Update.img: %s" % hashlib.sha1(new).hexdigest())
        return out, missing
    finally:
        shutil.rmtree(work, ignore_errors=True)


def hint(o, out):
    return ("To install:\n"
            "  1. Connect the MX5 to power and USB.\n"
            "  2. On the MX5: Global Settings > ... (more) > Firmware Update.\n"
            "  3. Run FirmwareUpdater.exe in %s and click \"Install %s\".\n"
            "     Do not disconnect until it has finished.\n"
            "  Recovery: hold footswitches 1 + 2 while powering on, then flash the official updater." % (out, label(o)))
