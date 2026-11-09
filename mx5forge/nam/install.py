"""Apply the NAM hijack to a rootfs (ext4.Ext4 object)."""
import os

from .. import fsutil

from . import elfpatch, launcher, targets

BLOBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blobs")
EVIL = "/usr/Evil/Evil"
SCRIPT = "/usr/Evil/Scripts/evil"
LIBS = ("libnam_hook.so", "libnam_preload.so")


def blob(name):
    return open(os.path.join(BLOBS, name), "rb").read()


def hijack_evil(evil, instances, log=print, target=targets.MX5):
    """Patch the Evil bytearray in place; returns (hook_slot_hex, hook_slot_v2_hex or None)."""
    tramp = blob("trampoline_gonk.bin")
    slot, tv = elfpatch.hijack(evil, tramp, target["engine_vtable_vaddr"], target["orig_process_fn"])
    log("NAM: Anxiety OD hijacked (trampoline @ 0x%x, hook slot @ 0x%x)" % (tv, slot))
    slot2 = None
    if instances == 4:
        slot2, tv2 = elfpatch.hijack(evil, tramp, target["v2_engine_vtable_vaddr"], target["v2_orig_process_fn"])
        log("NAM: Anxiety OD V2 hijacked as well (trampoline @ 0x%x, hook slot @ 0x%x)" % (tv2, slot2))
    return "0x%x" % slot, ("0x%x" % slot2 if slot2 else None)


def install(fs, evil, slot_hex, slot_v2_hex, log=print):
    """Write the patched Evil, the two libraries and the launcher script into the rootfs."""
    stock = fs.cat(SCRIPT).decode()
    if "NAM_HOOK_SLOT" in stock or fs.cat("/usr/Evil/libnam_hook.so"):
        raise launcher.LauncherError("this firmware already contains the NAM mod - start from the stock HeadRush 2.7 firmware")
    new_script = launcher.build(stock, slot_hex, slot_v2_hex)
    fsutil.overwrite(fs, EVIL, bytes(evil))
    for lib in LIBS:
        fs.write_file("/usr/Evil/" + lib, blob(lib), 0o100755)
    fs.write_file(SCRIPT, new_script.encode("ascii"), 0o100755)
    log("NAM: installed Evil, libnam_hook.so, libnam_preload.so and the launcher script")
