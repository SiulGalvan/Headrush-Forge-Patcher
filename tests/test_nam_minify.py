import json
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import nam_minify as M  # noqa: E402


class Minify(unittest.TestCase):
    def sample(self):
        rnd = random.Random(1)
        w = [rnd.gauss(0, 0.3) for _ in range(5000)] + [0.0, 1.0, -0.5, 1e-9, -3.2e-12, 7, 123456.789012345]
        return {"version": "0.5.4", "architecture": "WaveNet", "config": {"layers": [{"channels": 16}]},
                "metadata": {"name": "tést", "loudness": -17.123456789012}, "weights": w,
                "sample_rate": 48000}

    def test_float32_identical_and_smaller(self):
        raw = json.dumps(self.sample(), indent=2)
        new, n = M.minify_text(raw)
        self.assertEqual(n, 5007)
        self.assertLess(len(new), len(raw) * 0.7)
        self.assertTrue(M.verify(raw, new))
        a, b = json.loads(raw), json.loads(new)
        self.assertEqual(list(a), list(b))                       # key order kept
        self.assertEqual(a["metadata"], b["metadata"])           # other fields untouched, bit for bit
        for x, y in zip(a["weights"], b["weights"]):
            self.assertEqual(M.f32(float(x)), M.f32(float(y)))

    def test_shortest_never_longer(self):
        for x in (0.1, 0.5, 1 / 3, 1e-30, -2.5e20, 123456.789):
            self.assertLessEqual(len(M.shortest(x)), len(repr(x)))
            self.assertEqual(M.f32(float(M.shortest(x))), M.f32(x))

    def test_cli_keeps_original(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.nam")
        open(p, "w").write(json.dumps(self.sample(), indent=1))
        before = open(p, "rb").read()
        open(os.path.join(d, "._a.nam"), "wb").write(b"\x00\x05\x16binary")
        self.assertEqual(M.main([d]), 0)
        self.assertEqual(open(p, "rb").read(), before)
        self.assertTrue(os.path.exists(os.path.join(d, "minified", "a.nam")))
        self.assertFalse(os.path.exists(os.path.join(d, "minified", "._a.nam")))

    def test_optimize_in_place_with_backup(self):
        d = tempfile.mkdtemp()
        good, bad, tiny = (os.path.join(d, n) for n in ("a.nam", "b.nam", "c.nam"))
        open(good, "w").write(json.dumps(self.sample(), indent=2))
        open(bad, "w").write("not json")
        open(tiny, "w").write(json.dumps({"weights": [0.5, 0.25]}, separators=(",", ":")))
        orig = open(good, "rb").read()
        seen = []
        r = M.optimize_files([good, bad, tiny], os.path.join(d, "bak"), lambda i, n, name: seen.append((i, n)))
        self.assertEqual((r["changed"], r["skipped"], len(r["errors"])), (1, 1, 1))
        self.assertLess(r["after"], r["before"])
        self.assertEqual(open(os.path.join(d, "bak", "a.nam"), "rb").read(), orig)       # original saved
        self.assertTrue(M.verify(orig.decode(), open(good, encoding="utf-8").read()))
        self.assertFalse([f for f in os.listdir(d) if f.endswith(".tmp-min")])           # no temp leftovers
        self.assertEqual(seen[-1], (3, 3))
        r2 = M.optimize_files([good], os.path.join(d, "bak"))                             # second run: nothing to do
        self.assertEqual(r2["changed"], 0)
        self.assertEqual(open(os.path.join(d, "bak", "a.nam"), "rb").read(), orig)       # backup keeps the FIRST original

    def test_rejects_non_nam(self):
        with self.assertRaises(ValueError):
            M.minify_text('{"a": 1}')


if __name__ == "__main__":
    unittest.main()
