import os
import unittest
import zlib

from mx5forge.art import qmlport


class Fit(unittest.TestCase):
    """The patched QML has to fit the original slot with plain zlib (the .exe has no zopfli)."""

    def test_numeric_enums_only_for_pedalboard(self):
        stock = os.environ.get("PB_STOCK_QML")
        if not stock:
            self.skipTest("set PB_STOCK_QML to the Pedalboard ActiveStomp.qml")
        q = qmlport.port(open(stock).read(), "pedalboard")
        self.assertNotIn("Image.Ready", q)
        c = zlib.compressobj(9, zlib.DEFLATED, 15, 9)
        self.assertLessEqual(len(c.compress(q.encode()) + c.flush()), 2739)


if __name__ == "__main__":
    unittest.main()
