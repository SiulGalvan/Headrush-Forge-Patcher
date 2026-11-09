"""Anxiety OD process() hijack of the Evil binary.

Python port of core/elf_patch.c from headrush-nam-mod (GPLv3, https://github.com/lolgab/headrush-nam-mod).
The vtable slot of the pedal's engine object is redirected to a 28-byte trampoline placed in the dead
space after the R+E segment; the trampoline jumps to a hook pointer that libnam_preload.so fills in at
startup (or to the original process() if there is none)."""
import struct

PT_LOAD, PF_X, PF_W, PF_R = 1, 1, 2, 4
PROCESS_SLOT = 8
VADDR_BASE = 0x8000
TRAMP_CODE_LEN = 28


class ElfPatchError(Exception):
    pass


def hijack(data, tramp, engine_vtable, orig_fn):
    """Patch `data` (bytearray, the Evil binary) in place. Returns (hook_slot_addr, trampoline_vaddr).
    Refuses (ElfPatchError) if anything does not look exactly like the expected stock binary."""
    if len(tramp) != 32:
        raise ElfPatchError("trampoline must be exactly 32 bytes")
    if len(data) < 52 or data[:4] != b"\x7fELF":
        raise ElfPatchError("not an ELF file")
    if data[4] != 1 or data[5] != 1:
        raise ElfPatchError("not a 32-bit little-endian ELF")
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff, = struct.unpack_from("<I", data, 28)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 42)
    if e_machine != 40:
        raise ElfPatchError("not ARM (e_machine=%d)" % e_machine)
    if e_type != 2:
        raise ElfPatchError("expected ET_EXEC (non-PIE), got e_type=%d" % e_type)
    if e_phoff + e_phentsize * e_phnum > len(data):
        raise ElfPatchError("program header table out of bounds")
    phdrs = []
    for i in range(e_phnum):
        phdrs.append(list(struct.unpack_from("<8I", data, e_phoff + i * e_phentsize)))
    # fields: type, offset, vaddr, paddr, filesz, memsz, flags, align
    slot_vaddr = engine_vtable + PROCESS_SLOT * 4
    slot_off = slot_vaddr - VADDR_BASE
    if slot_off + 4 > len(data):
        raise ElfPatchError("vtable slot file offset out of bounds")
    cur, = struct.unpack_from("<I", data, slot_off)
    if cur != orig_fn:
        raise ElfPatchError(
            "REFUSING: vtable slot @ 0x%x holds 0x%x, expected 0x%x -- wrong binary / already patched" %
            (slot_off, cur, orig_fn))
    code = [i for i, p in enumerate(phdrs) if p[0] == PT_LOAD and p[6] == (PF_R | PF_X)]
    dat = [i for i, p in enumerate(phdrs) if p[0] == PT_LOAD and p[6] == (PF_R | PF_W)]
    if len(code) != 1 or len(dat) != 1:
        raise ElfPatchError("REFUSING: unexpected LOAD segment layout (%d code, %d data)" % (len(code), len(dat)))
    ci, di = code[0], dat[0]
    cs, ds = phdrs[ci], phdrs[di]
    code_file_end = cs[1] + cs[4]
    later = [p for i, p in enumerate(phdrs) if p[0] == PT_LOAD and i != ci and p[1] >= code_file_end]
    if not later:
        raise ElfPatchError("REFUSING: no later PT_LOAD segment to bound the code cave")
    gap = min(p[1] for p in later) - code_file_end
    if gap < TRAMP_CODE_LEN:
        raise ElfPatchError("REFUSING: dead space after the code segment is too small (%d bytes)" % gap)
    if any(data[code_file_end:code_file_end + gap]):
        raise ElfPatchError("REFUSING: gap after the code segment is not zero (already patched?)")
    tramp_vaddr = cs[2] + cs[4]
    hook_slot = ds[2] + ds[5]
    t = bytearray(tramp)
    struct.pack_into("<I", t, 20, hook_slot)
    struct.pack_into("<I", t, 24, orig_fn)
    data[code_file_end:code_file_end + TRAMP_CODE_LEN] = t[:TRAMP_CODE_LEN]
    base = e_phoff + ci * e_phentsize
    struct.pack_into("<I", data, base + 16, cs[4] + TRAMP_CODE_LEN)
    struct.pack_into("<I", data, base + 20, cs[5] + TRAMP_CODE_LEN)
    struct.pack_into("<I", data, e_phoff + di * e_phentsize + 20, ds[5] + 4)
    struct.pack_into("<I", data, slot_off, tramp_vaddr)
    return hook_slot, tramp_vaddr
