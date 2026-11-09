"""Launcher script edit: start /usr/Evil/Evil with libnam_preload.so.

Python port of core/launcher_script.c from headrush-nam-mod (GPLv3)."""

NAM_START = "# --- NAM mod ---\n"
NAM_END = "# --- end NAM mod ---\n"
DESC = (
    "# Anxiety OD (v1) process() hijack, optionally also Anxiety OD V2's --\n"
    "# the only NAM path(s) this build applies. One of each hijacked pedal's\n"
    "# knobs (Drive/Tone/Level) now selects/scans .nam model files.\n"
    "# (The additive, own-pedal-type design in patch_namloader.py is NOT\n"
    "# applied here -- see README.md.)\n")
TAIL = (
    "# LD_PRELOAD/NAM_HOOK_SLOT_*_ADDR are scoped to the /usr/Evil/Evil exec\n"
    "# below via `env`, NOT exported here -- exporting them shell-wide would\n"
    "# also preload libnam_preload.so into systemd-inhibit (a separate,\n"
    "# dynamically-linked ELF binary launched right below). Its constructor\n"
    "# writes to a hardcoded absolute vaddr valid only inside Evil's own\n"
    "# non-PIE layout; inside systemd-inhibit's unrelated address space that\n"
    "# write hits unmapped memory and segfaults it before it ever forks Evil\n"
    "# -- an infinite crash loop, stuck on the splash screen forever.\n")
OLD_EXEC = "systemd-inhibit --what=handle-power-key /usr/Evil/Evil"


class LauncherError(Exception):
    pass


def build(stock_text, hook_slot_hex, hook_slot_v2_hex=None, hook_slot_amp_hex=None, amp_orig_hex=None):
    comment = NAM_START + DESC + TAIL + NAM_END
    s = stock_text.find(NAM_START)
    e = stock_text.find(NAM_END, s) if s >= 0 else -1
    if s >= 0 and e >= 0:
        script = stock_text[:s] + comment + stock_text[e + len(NAM_END):]
    else:
        m = stock_text.find("while [ 1 ]")
        if m < 0:
            raise LauncherError("launcher script has no 'while [ 1 ]' marker (layout changed)")
        script = stock_text[:m] + comment + "\n" + stock_text[m:]
    if script.count(OLD_EXEC) != 1:
        raise LauncherError("expected exactly 1 '%s' in the launcher script, found %d" % (OLD_EXEC, script.count(OLD_EXEC)))
    i = script.find(OLD_EXEC)
    new = ("systemd-inhibit --what=handle-power-key env LD_PRELOAD=/usr/Evil/libnam_preload.so "
           "NAM_HOOK_SLOT_GONK_ADDR=" + hook_slot_hex)
    if hook_slot_v2_hex:
        new += " NAM_HOOK_SLOT_GONK_V2_ADDR=" + hook_slot_v2_hex
    if hook_slot_amp_hex:
        # the Extended hook falls back to the Gigboard address of the original amp process() unless told otherwise
        new += " NAM_HOOK_SLOT_AMP_ADDR=" + hook_slot_amp_hex + " NAM_ORIG_AMP_PROCESS_ADDR=" + amp_orig_hex
    new += " /usr/Evil/Evil"
    return script[:i] + new + script[i + len(OLD_EXEC):]
