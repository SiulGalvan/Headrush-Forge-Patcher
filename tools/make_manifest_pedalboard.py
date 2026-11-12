"""Dev tool: derive art/manifest_pedalboard_2.7.json from a Pedalboard 2.7 Evil (NAM mod taken out) plus the MX5 manifest.

The pedal pictures of the Pedalboard 2.7 Evil are byte-identical to the MX5 ones, only their positions differ; the
manifest stores positions, slot sizes and sha1 values, never any HeadRush content.
usage: make_manifest_pedalboard.py PEDALBOARD_EVIL MX5_EVIL out.json"""
import hashlib
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
pb = open(sys.argv[1], "rb").read()
mx = open(sys.argv[2], "rb").read()
man = json.load(open(os.path.join(HERE, "..", "mx5forge", "art", "manifest_mx5_2.7.json")))

out = {"firmware": "HeadRush Pedalboard 2.7 (inmusic,mg01)", "images": {}}
for name, e in man["images"].items():
    blob = mx[e["pos"]:e["pos"] + e["slot"]]
    hits = [m.start() for m in re.finditer(re.escape(blob[:64]), pb) if pb[m.start():m.start() + e["slot"]] == blob]
    mxhits = [m.start() for m in re.finditer(re.escape(blob[:64]), mx) if mx[m.start():m.start() + e["slot"]] == blob]
    if len(hits) != len(mxhits) or e["pos"] not in mxhits:
        sys.exit("%s: %d matches in the Pedalboard Evil, %d in the MX5 one" % (name, len(hits), len(mxhits)))
    p = hits[sorted(mxhits).index(e["pos"])]       # identical pictures (Anxiety OD / V2): pair the copies by order
    if struct.unpack(">I", pb[p - 4:p])[0] != e["slot"]:
        sys.exit("%s: slot length prefix differs" % name)
    d = dict(e)
    d["pos"] = p
    out["images"][name] = d

# ActiveStomp.qml: the qrc entry of the Pedalboard is a different (shorter) file
q = man["qml"]
found = []
for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", pb):
    p = m.start()
    L, U = struct.unpack(">II", pb[p - 8:p])
    if not (500 < U < 200000 and 100 < L <= U):
        continue
    try:
        o = zlib.decompressobj().decompress(pb[p:p + L], U + 10)
    except zlib.error:
        continue
    if len(o) == U and b"id: activeStomp" in o:
        found.append((p, L, U, hashlib.sha1(o).hexdigest()))
if len(found) != 1:
    sys.exit("ActiveStomp.qml: %d candidates" % len(found))
p, L, U, sha = found[0]
needle = "/Groups/SignalChainModuleStomps/ActiveStomp.qml".encode("utf-16-le")
hits = [m.start() for m in re.finditer(re.escape(needle), pb)]
if len(hits) != 1 or pb[hits[0] + 64:hits[0] + 66] != b"A\x00":
    sys.exit("compiled-QML registration not found")
out["qml"] = {"name": "ActiveStomp.qml", "blob_off": p, "blob_len_prefix": struct.unpack(">I", pb[p - 8:p - 4])[0],
              "stock_clen": L, "stock_ulen": U, "stock_sha1": sha, "register_off": hits[0], "register_byte_off": 64}
json.dump(out, open(sys.argv[3], "w"), indent=1)
print("images", len(out["images"]), "qml", out["qml"])
