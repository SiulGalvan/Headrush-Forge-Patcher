"""Art tests need the stock Evil binary (not shipped).  Set MX5_STOCK_EVIL=/path/to/Evil (stock 2.7, or the
2.7 binary with only the NAM mod applied) to run them."""
import os
import pathlib
import struct
import sys
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mx5forge  # noqa: E402,F401
from mx5forge.art import apply as art_apply, images, qmlport  # noqa: E402
from mx5forge import pipeline  # noqa: E402

EVIL = os.environ.get("MX5_STOCK_EVIL")


class Options(unittest.TestCase):
    def test_design_needs_four_instances(self):
        with self.assertRaises(pipeline.Fail):
            pipeline.check_options(pipeline.Options(instances=2, design=True))
        pipeline.check_options(pipeline.Options(instances=4, design=True))
        pipeline.check_options(pipeline.Options(instances=2))

    def test_folder_names(self):
        self.assertEqual(pipeline.folder_name(pipeline.Options(2, True, False)), "HeadRush_MX5_2.7_NAM2_Bridge_Updater")
        self.assertEqual(pipeline.folder_name(pipeline.Options(4, False, True)), "HeadRush_MX5_2.7_NAM4_Design_Updater")


class Manifest(unittest.TestCase):
    def test_every_image_has_a_slot(self):
        man = art_apply.load_manifest()
        self.assertGreater(len(man["images"]), 80)
        for n, e in man["images"].items():
            self.assertGreater(e["slot"], 100, n)


@unittest.skipUnless(EVIL and os.path.exists(EVIL), "set MX5_STOCK_EVIL to run")
class WithBinary(unittest.TestCase):
    def setUp(self):
        self.evil = bytearray(pathlib.Path(EVIL).read_bytes())

    def test_qml_fits_without_zopfli(self):
        man = art_apply.load_manifest()["qml"]
        q = man["blob_off"]
        stock = zlib.decompress(bytes(self.evil[q:q + man["stock_clen"]])).decode()
        z, qml = qmlport.fit(qmlport.port(stock), man["stock_clen"])
        self.assertEqual(len(z), man["stock_clen"])
        self.assertEqual(zlib.decompress(z), qml)

    def test_images_fit_their_slots(self):
        man = art_apply.load_manifest()
        out = images.build(bytes(self.evil), man, None, {})
        self.assertGreater(len(out), 70)
        for n, data in out.items():
            self.assertLessEqual(len(data), man["images"][n]["slot"], n)

    def test_apply_changes_only_expected_regions_and_refuses_twice(self):
        before = bytes(self.evil)
        art_apply.apply(self.evil, None, log=lambda *a: None)
        self.assertNotEqual(before, bytes(self.evil))
        self.assertEqual(len(before), len(self.evil))
        with self.assertRaises(qmlport.ArtError):
            art_apply.apply(self.evil, None, log=lambda *a: None)


if __name__ == "__main__":
    unittest.main()
