import glob
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


class PackagingFiles(unittest.TestCase):
    def test_every_art_json_is_bundled(self):
        """The .exe is built with explicit --add-data entries: a data file missing there only fails on the user's PC."""
        names = [os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "mx5forge", "art", "*.json"))]
        self.assertTrue(len(names) >= 2)
        for script in ("build_windows.bat", os.path.join(".github", "workflows", "build.yml")):
            text = open(os.path.join(ROOT, script), encoding="utf-8").read()
            for n in names:
                self.assertIn(n, text, "%s is not bundled by %s" % (n, script))


if __name__ == "__main__":
    unittest.main()
