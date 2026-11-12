"""Take the nam-mod 0.1.6 hijack back out of an Evil binary and its launcher script.

Lets the build start from a firmware that already carries the mod (the community Pedalboard/MX5 "NAM mod"
updaters): the mod is removed first, then everything is applied again by the normal path, so nothing is applied
twice.  The Evil revert checks itself: hijacking the reverted binary again must give back the input byte for byte."""
import re
import struct

from . import elfpatch, launcher, targets

VADDR_BASE = elfpatch.VADDR_BASE
TRAMP = elfpatch.TRAMP_CODE_LEN


class RevertError(Exception):
    pass


def is_modded_script(text):
    return "NAM_HOOK_SLOT" in text or launcher.NAM_START in text


_EXEC = re.compile(r"systemd-inhibit --what=handle-power-key env LD_PRELOAD=/usr/Evil/libnam_preload\.so(?: NAM_[A-Z0-9_]+=\S+)* /usr/Evil/Evil")


def revert_script(text):
    """Launcher script as it was before the mod (nothing but the mod's own lines is touched)."""
    if len(_EXEC.findall(text)) != 1:
        raise RevertError("the launcher script does not look like nam-mod's (expected exactly one NAM start line)")
    text = _EXEC.sub(launcher.OLD_EXEC, text)
    s = text.find(launcher.NAM_START)
    e = text.find(launcher.NAM_END, s) if s >= 0 else -1
    if s >= 0 and e >= 0:
        end = e + len(launcher.NAM_END)
        if text[end:end + 1] == "\n":          # launcher.build() adds one blank line after the comment block
            end += 1
        text = text[:s] + text[end:]
    if "NAM_HOOK_SLOT" in text or "libnam_preload" in text:
        raise RevertError("could not remove every NAM line from the launcher script")
    return text


def _phdrs(data):
    phoff, = struct.unpack_from("<I", data, 28)
    es, n = struct.unpack_from("<HH", data, 42)
    return phoff, es, [list(struct.unpack_from("<8I", data, phoff + i * es)) for i in range(n)]


def is_modded_evil(data, target):
    """True if the V1 vtable slot no longer holds the original process() (i.e. the hijack is in)."""
    cur, = struct.unpack_from("<I", data, target["engine_vtable_vaddr"] + 8 * 4 - VADDR_BASE)
    return cur != target["orig_process_fn"]


def revert_evil(data, target):
    """Undo hijack() for the Anxiety OD (+V2, +amp if present).  Returns a new bytearray."""
    out = bytearray(data)
    phoff, es, ph = _phdrs(out)
    code = [i for i, p in enumerate(ph) if p[0] == elfpatch.PT_LOAD and p[6] == (elfpatch.PF_R | elfpatch.PF_X)]
    dat = [i for i, p in enumerate(ph) if p[0] == elfpatch.PT_LOAD and p[6] == (elfpatch.PF_R | elfpatch.PF_W)]
    if len(code) != 1 or len(dat) != 1:
        raise RevertError("unexpected LOAD segment layout")
    ci, di = code[0], dat[0]
    sites = [(target["engine_vtable_vaddr"], elfpatch.PROCESS_SLOT, target["orig_process_fn"])]
    sites.append((target["v2_engine_vtable_vaddr"], elfpatch.PROCESS_SLOT, target["v2_orig_process_fn"]))
    sites.append((target["amp_engine_vtable_vaddr"], target["amp_process_slot"], target["amp_orig_process_fn"]))
    hijacked = []
    for vt, slot, orig in sites:
        off = vt + slot * 4 - VADDR_BASE
        cur, = struct.unpack_from("<I", out, off)
        if cur != orig:
            hijacked.append((off, cur, orig))
    if not hijacked:
        raise RevertError("this Evil binary is not hijacked")
    n = len(hijacked)
    cs, ds = ph[ci], ph[di]
    code_end = cs[1] + cs[4]                      # file offset after the (extended) code segment
    first = code_end - n * TRAMP
    first_va = cs[2] + cs[4] - n * TRAMP
    for k, (off, cur, orig) in enumerate(hijacked):
        t_off = first + k * TRAMP
        want_va = first_va + k * TRAMP
        if cur != want_va:
            raise RevertError("vtable slot 0x%x points to 0x%x, not to a trampoline at 0x%x" % (off, cur, want_va))
        # the trampoline ends with the hook slot and the original function (see elfpatch.hijack)
        hook, o_fn = struct.unpack_from("<II", out, t_off + 20)
        if o_fn != orig:
            raise RevertError("trampoline %d does not lead back to the original process()" % k)
        if hook != ds[2] + ds[5] - 4 * (n - k):
            raise RevertError("trampoline %d hook slot 0x%x is not where expected" % (k, hook))
        struct.pack_into("<I", out, off, orig)
    out[first:code_end] = bytes(n * TRAMP)
    base = phoff + ci * es
    struct.pack_into("<I", out, base + 16, cs[4] - n * TRAMP)
    struct.pack_into("<I", out, base + 20, cs[5] - n * TRAMP)
    struct.pack_into("<I", out, phoff + di * es + 20, ds[5] - 4 * n)
    return out
