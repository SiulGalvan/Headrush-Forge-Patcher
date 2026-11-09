import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mx5forge  # noqa: E402,F401
from mx5forge.nam import elfpatch, install, launcher  # noqa: E402

VT, VT2, ORIG = 0x9000, 0x9100, 0x12345


def fake_evil():
    """Minimal ARM ET_EXEC with one R+E and one R+W LOAD segment, a zero gap and a vtable slot."""
    size = 0x40000
    d = bytearray(size)
    d[:4] = b"\x7fELF"
    d[4], d[5] = 1, 1
    struct.pack_into("<HH", d, 16, 2, 40)
    struct.pack_into("<I", d, 28, 52)
    struct.pack_into("<HH", d, 42, 32, 2)
    # code: file 0..0x30000 at vaddr 0x8000 ; data: file 0x31000.. at vaddr 0x4000000
    struct.pack_into("<8I", d, 52, 1, 0, 0x8000, 0x8000, 0x30000, 0x30000, 5, 0x1000)
    struct.pack_into("<8I", d, 84, 1, 0x31000, 0x4000000, 0x4000000, 0x2000, 0x3000, 6, 0x1000)
    struct.pack_into("<I", d, VT + 32 - 0x8000, ORIG)        # slot (file offset = vaddr - 0x8000)
    return d


class ElfPatch(unittest.TestCase):
    def tramp(self):
        return install.blob("trampoline_gonk.bin")

    def test_patches_and_refuses_twice(self):
        d = fake_evil()
        slot, tv = elfpatch.hijack(d, self.tramp(), VT, ORIG)
        self.assertEqual(slot, 0x4000000 + 0x3000)
        self.assertEqual(tv, 0x8000 + 0x30000)
        self.assertEqual(struct.unpack_from("<I", d, VT + 32 - 0x8000)[0], tv)
        with self.assertRaises(elfpatch.ElfPatchError):          # slot no longer holds the original
            elfpatch.hijack(d, self.tramp(), VT, ORIG)

    def test_two_hijacks_use_separate_trampolines(self):
        d = fake_evil()
        struct.pack_into("<I", d, VT2 + 32 - 0x8000, ORIG)
        a = elfpatch.hijack(d, self.tramp(), VT, ORIG)
        b = elfpatch.hijack(d, self.tramp(), VT2, ORIG)
        self.assertEqual(b[0], a[0] + 4)
        self.assertEqual(b[1], a[1] + 28)

    def test_refuses_wrong_binary(self):
        d = fake_evil()
        struct.pack_into("<I", d, VT + 32 - 0x8000, 0x1234)
        with self.assertRaises(elfpatch.ElfPatchError):
            elfpatch.hijack(d, self.tramp(), VT, ORIG)


STOCK = ("#!/bin/sh\nfoo\nwhile [ 1 ]\ndo\n\tsystemd-inhibit --what=handle-power-key /usr/Evil/Evil\n"
         "\texitCode=$?\n\techo done\ndone\n")


class Launcher(unittest.TestCase):
    def test_single_and_double(self):
        one = launcher.build(STOCK, "0x31c3804")
        self.assertIn("NAM_HOOK_SLOT_GONK_ADDR=0x31c3804 /usr/Evil/Evil", one)
        self.assertNotIn("_V2_", one)
        two = launcher.build(STOCK, "0x31c3804", "0x31c3808")
        self.assertIn("NAM_HOOK_SLOT_GONK_V2_ADDR=0x31c3808", two)

    def test_bridge_accepts_the_result(self):
        import bridgepatch
        for v2 in (None, "0x31c3808"):
            text, nam = bridgepatch.patch_evil(launcher.build(STOCK, "0x31c3804", v2))
            self.assertTrue(nam)
            self.assertIn("mx5bridge", text)

    def test_refuses_unknown_layout(self):
        with self.assertRaises(launcher.LauncherError):
            launcher.build("nothing here\n", "0x1")


if __name__ == "__main__":
    unittest.main()


class ExtendedAndAmp(unittest.TestCase):
    def test_options(self):
        from mx5forge import pipeline
        with self.assertRaises(pipeline.Fail):
            pipeline.check_options(pipeline.Options(amp=True))                       # amp needs the extended engine
        with self.assertRaises(pipeline.Fail):
            pipeline.check_options(pipeline.Options(engine="nope"))
        pipeline.check_options(pipeline.Options(engine="extended", amp=True))
        self.assertEqual(pipeline.folder_name(pipeline.Options(4, True, True, engine="extended", amp=True)),
                         "HeadRush_MX5_2.7_NAM4_Ext_Amp_Bridge_Design_Updater")

    def test_launcher_amp(self):
        from mx5forge.nam import launcher
        stock = "x\nwhile [ 1 ]\ndo\n systemd-inhibit --what=handle-power-key /usr/Evil/Evil\ndone\n"
        s = launcher.build(stock, "0x10", "0x14", "0x18", "0x139538")
        self.assertIn("NAM_HOOK_SLOT_GONK_ADDR=0x10 NAM_HOOK_SLOT_GONK_V2_ADDR=0x14 NAM_HOOK_SLOT_AMP_ADDR=0x18 "
                      "NAM_ORIG_AMP_PROCESS_ADDR=0x139538 /usr/Evil/Evil", s)

    def test_blobs(self):
        from mx5forge.nam import install
        for e in install.ENGINES:
            for n in install.LIBS:
                self.assertGreater(len(install.blob(n, e)), 1000)
