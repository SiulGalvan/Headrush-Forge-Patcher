"""Picture of the NAM amp (the "82 LEAD 800 Bright" block that the Extended hook turns into a NAM amp).

The QML needs no change: it loads Pages/ModuleEditors/img/Amp/<name>.png, so the two PNGs of that amp are replaced in
place (same size 290x119, written into the original slot like the pedal pictures).  The '...2.png' variant is the one
used for the second amp of a doubled block and carries a white "2": that digit is cut out of the firmware's own picture
at build time (nothing of HeadRush is shipped) and drawn onto the NAM icon."""
import hashlib
import io
import os
import struct

from PIL import Image, ImageChops, ImageStat

from . import apply as _apply

ICON = os.path.join(_apply.ASSETS, "nam_amp.png")
PLAIN, SECOND = "82 LEAD 800 Bright.png", "82 LEAD 800 Bright2.png"


class AmpArtError(Exception):
    pass


def digit_from_stock(plain, second):
    """RGBA image of the white '2' (cut out of the stock '...2.png' by comparing it with the stock plain one)."""
    d = ImageChops.subtract(second.convert("L"), plain.convert("L"))
    mask = d.point(lambda v: min(255, v * 3) if v > 20 else 0)
    box = mask.getbbox()
    if not box:
        raise AmpArtError("could not find the '2' of the stock amp picture")
    digit = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    digit.putalpha(mask)
    return digit.crop(box)


def with_badge(icon, digit):
    out = icon.copy()
    box = icon.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0) + icon.size
    pos = (box[2] - digit.width - 14, box[1] + 12)
    # the stock digit is white (for a dark amp picture); on a light picture (silver plate) it would vanish, so draw it dark
    under = icon.convert("L").crop(pos + (pos[0] + digit.width, pos[1] + digit.height))
    if ImageStat.Stat(under).mean[0] > 100:
        dark = Image.new("RGBA", digit.size, (24, 24, 24, 255))
        dark.putalpha(digit.getchannel("A"))
        digit = dark
    out.alpha_composite(digit, pos)
    return out


def png(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def apply(evil, model="mx5", icon_path=None, log=print):
    man = _apply.load_manifest(model).get("amp")
    if not man:
        raise AmpArtError("no amp picture entries for this firmware")
    orig = bytes(evil)
    stock = {}
    for name, e in man.items():
        p = e["pos"]
        if struct.unpack(">I", orig[p - 4:p])[0] != e["slot"] or hashlib.sha1(orig[p:p + e["slot"]]).hexdigest() != e["sha1"]:
            raise AmpArtError("amp picture %s differs from the 2.7 original" % name)
        stock[name] = Image.open(io.BytesIO(orig[p:p + e["slot"]])).convert("RGBA")
    icon = Image.open(icon_path or ICON).convert("RGBA")
    if icon.size != (290, 119):
        raise AmpArtError("the amp icon must be 290x119 px (it is %dx%d)" % icon.size)
    out = {PLAIN: png(icon), SECOND: png(with_badge(icon, digit_from_stock(stock[PLAIN], stock[SECOND])))}
    for name, data in out.items():
        if len(data) > man[name]["slot"]:
            raise AmpArtError("%s: %d bytes do not fit its %d-byte slot" % (name, len(data), man[name]["slot"]))
        p = man[name]["pos"]
        evil[p:p + len(data)] = data
    log("Art: NAM amp pictures written (82 LEAD 800 Bright and its '2' variant)")
    return {"amp_images": len(out)}
