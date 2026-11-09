# How it works

## Firmware
`Update.img` is a FIT image; its `rootfs` is an xz-compressed ext4. The vendored `fitpatch.py`, `ext4.py`
and `xzblocks.py` read it, write files into it (no mounting, no root) and rebuild it. Every written file is read
back and compared before compressing.

## NAM hijack (`mx5forge/nam`)
The Anxiety OD pedal's engine object has a vtable whose `process()` slot is replaced by a 28-byte trampoline
placed in the zero gap after the code segment (the ELF program headers grow by 28 bytes, the data segment by
4 for the hook pointer). `libnam_preload.so` (LD_PRELOAD) fills the hook pointer at start-up; the hook runs the
NAM model. For 4 instances the same is done for Anxiety OD V2 (its own vtable, second trampoline, second hook slot,
`NAM_HOOK_SLOT_GONK_V2_ADDR`). The launcher script `/usr/Evil/Scripts/evil` starts Evil through `env LD_PRELOAD=...`.
`elfpatch.hijack` refuses to continue unless the vtable slot holds the original address, the segments have the
expected layout and the gap is zero (so it never patches twice or the wrong binary).

## Pedal design (`mx5forge/art`, 4 instances only)
* `qmlport.py` takes the stock `ActiveStomp.qml` from the firmware (its sha1 is checked), applies a handful of text
  substitutions (an `Image` that shows `ModuleEditors/img/<module>.png` in the chain and in the wah/volume pedal
  frame, hiding the generic body, LED, label, footswitch and A/B badge when a picture is shown), minifies it and
  fits it into **exactly** the original compressed slot (2787 bytes) with a trailing random comment tuned until the
  zlib stream has that length. The compiled QML registration of that file is renamed so Qt compiles the QML from the resources.
* `images.py` re-encodes the pedal pictures: pre-scaled to the size they are drawn at (1:1 on the device, a third of the
  memory), palette PNGs stay palette, odd-shaped pedals are cropped to their outline and fitted into the green frame
  by the QML, rack modules get your art on a 286x442 canvas. Pictures that are not pedal shaped (thin strips) are ignored
  by the QML so those modules keep the stock look.
* `manifest_mx5_2.7.json` lists, for the MX5 2.7 `Evil`, each picture's offset, slot size and sha1, and the QML blob.
  Nothing is written unless all of them match.

## MX5 Bridge (`vendor/mxedit`)
Unmodified MX-Edit 0.9.5 code (`bridgepatch.py`): USB MIDI function, `mx5bridge-*.sh`, an ARM `sqlite3`, and the
MIDI assignment QML files. It reads the NAM launcher line, so it runs after the NAM step.
