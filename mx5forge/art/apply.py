"""Apply the pedal design to the Evil binary (bytearray) in place."""
import hashlib
import json
import os
import re
import struct
import zlib

from . import images, qmlport

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")


def load_manifest(model="mx5"):
    return json.load(open(os.path.join(HERE, "manifest_%s_2.7.json" % model)))


def apply(evil, rack_dir=None, nam_v2_badge=True, log=print, model="mx5"):
    """Patch ActiveStomp.qml, replace the pedal PNGs and bypass the precompiled QML unit.
    Everything is checked against the manifest of the MX5 2.7 firmware first; nothing is written if the
    binary is not exactly that firmware."""
    man = load_manifest(model)
    q = man["qml"]
    orig = bytes(evil)
    qp = q["blob_off"]
    if struct.unpack(">I", orig[qp - 8:qp - 4])[0] != q["blob_len_prefix"]:
        raise qmlport.ArtError("ActiveStomp.qml blob not found - this is not the MX5 2.7 firmware")
    stock = zlib.decompress(orig[qp:qp + q["stock_clen"]])
    if hashlib.sha1(stock).hexdigest() != q["stock_sha1"]:
        raise qmlport.ArtError("ActiveStomp.qml differs from the MX5 2.7 original")
    needle = "/Groups/SignalChainModuleStomps/ActiveStomp.qml".encode("utf-16-le")
    hits = [m.start() for m in re.finditer(re.escape(needle), orig)]
    if hits != [q["register_off"]] or orig[hits[0] + 64:hits[0] + 66] != b"A\x00":
        raise qmlport.ArtError("compiled-QML registration of ActiveStomp.qml not found where expected")
    for name, e in man["images"].items():
        p = e["pos"]
        if struct.unpack(">I", orig[p - 4:p])[0] != e["slot"] or hashlib.sha1(orig[p:p + e["slot"]]).hexdigest() != e["sha1"]:
            raise qmlport.ArtError("image %s differs from the MX5 2.7 original" % name)

    nam = {"Anxiety OD": os.path.join(ASSETS, "nam_a2_v1.png")}
    if nam_v2_badge:
        nam["Anxiety OD V2"] = os.path.join(ASSETS, "nam_badge_v2.png")
    pngs = images.build(orig, man, rack_dir, nam, log)

    z, qml = qmlport.fit(qmlport.port(stock.decode(), model), q["stock_clen"])
    evil[qp - 4:qp] = struct.pack(">I", len(qml))
    evil[qp:qp + q["stock_clen"]] = z
    evil[hits[0] + 64] = ord("X")
    log("Art: chain QML patched (%d -> %d bytes, compressed slot unchanged)" % (len(stock), len(qml)))
    for name, data in pngs.items():
        p = man["images"][name]["pos"]
        evil[p:p + len(data)] = data
    log("Art: %d pedal images pre-scaled and written%s" % (len(pngs), " (NAM badge on Anxiety OD V2)" if nam_v2_badge else ""))
    return {"images": len(pngs)}
