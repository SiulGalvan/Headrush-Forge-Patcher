"""Apply the NAM hijack to a rootfs (ext4.Ext4 object)."""
import os

from .. import fsutil

from . import elfpatch, launcher, targets

BLOBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blobs")
ENGINES = {"nam-mod": "", "extended": "extended", "extended-fair": "extended-fair"}      # engine name -> blobs sub folder
EVIL = "/usr/Evil/Evil"
SCRIPT = "/usr/Evil/Scripts/evil"
LIBS = ("libnam_hook.so", "libnam_preload.so")


def blob(name, engine="nam-mod"):
    if name == "trampoline_gonk.bin":           # identical in both engines
        engine = "nam-mod"
    return open(os.path.join(BLOBS, ENGINES[engine], name), "rb").read()


def hijack_evil(evil, instances, log=print, target=targets.MX5, amp=False):
    """Patch the Evil bytearray in place; returns (slot_hex, slot_v2_hex or None, slot_amp_hex or None)."""
    tramp = blob("trampoline_gonk.bin")
    slot, tv = elfpatch.hijack(evil, tramp, target["engine_vtable_vaddr"], target["orig_process_fn"])
    log("NAM: Anxiety OD hijacked (trampoline @ 0x%x, hook slot @ 0x%x)" % (tv, slot))
    slot2 = slot_amp = None
    if instances == 4:
        slot2, tv2 = elfpatch.hijack(evil, tramp, target["v2_engine_vtable_vaddr"], target["v2_orig_process_fn"])
        log("NAM: Anxiety OD V2 hijacked as well (trampoline @ 0x%x, hook slot @ 0x%x)" % (tv2, slot2))
    if amp:
        slot_amp, tv3 = elfpatch.hijack(evil, tramp, target["amp_engine_vtable_vaddr"], target["amp_orig_process_fn"],
                                        target["amp_process_slot"])
        log("NAM: amp block (AmpCab, 82 LEAD 800 Bright) hijacked (trampoline @ 0x%x, hook slot @ 0x%x)" % (tv3, slot_amp))
    f = lambda v: "0x%x" % v if v else None
    return f(slot), f(slot2), f(slot_amp)


def install(fs, evil, slot_hex, slot_v2_hex, log=print, engine="nam-mod", slot_amp_hex=None, target=targets.MX5, stock_text=None):
    """Write the patched Evil, the two libraries and the launcher script into the rootfs.
    stock_text: the launcher script with an earlier nam-mod already taken out (see revert.py)."""
    stock = stock_text if stock_text is not None else fs.cat(SCRIPT).decode()
    if stock_text is None and ("NAM_HOOK_SLOT" in stock or fs.exists("/usr/Evil/libnam_hook.so")):
        raise launcher.LauncherError("this firmware already contains the NAM mod - start from the stock HeadRush 2.7 firmware")
    new_script = launcher.build(stock, slot_hex, slot_v2_hex, slot_amp_hex,
                                "0x%x" % target["amp_orig_process_fn"] if slot_amp_hex else None)
    fsutil.overwrite(fs, EVIL, bytes(evil))
    for lib in LIBS:
        fs.write_file("/usr/Evil/" + lib, blob(lib, engine), 0o100755)
    fs.write_file(SCRIPT, new_script.encode("ascii"), 0o100755)
    log("NAM: installed Evil, libnam_hook.so, libnam_preload.so (%s engine) and the launcher script" % engine)
