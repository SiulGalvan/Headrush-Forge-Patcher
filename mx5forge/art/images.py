"""Pedal images for the chain art: pre-scaled to the size they are drawn at (less memory and decoding
time on the device), palette PNGs stay palette PNGs.  Needs Pillow."""
import io
import os
import re

from PIL import Image

# Editor-only / non-pedal images that are left alone
SKIP = {"Cab.png", "IR (1024).png", "IR (1024)2.png", "IR.png", "IR2.png", "Amp.png", "Other.png", "Mix.png"}
# Pedals with a non-pedal shape: cropped to their visible outline so the QML can fit them into the green frame
ODD = ["Chord Wham", "Feedback", "Time Warp", "Ten Freq EQ", "Reso Delay", "Party Verb", "Ambi Verb",
       "Round Fuzz", "K Drive", "B Dist 7000"]
# Rack-style modules: the stock image is a thin strip.  With your own pedal-shaped art (a folder of PNGs)
# they get a pedal; without it they keep the stock look.
RACKS = {"AIR Delay": ("airdelay",), "Detune": ("detune",), "Dyn Delay": ("dyndelay",),
         "DynIII Comp": ("dyniiicomp",), "Eleven Reverb": ("elevenreverb",), "Multi Chorus": ("multichorus",),
         "Noise Filter": ("noisefilter",), "Para EQ": ("paraeq",), "Side Comp": ("sidecomp",),
         "Smart Harm": ("smartharm",), "Tape Echo": ("tapeecho", "tapedelay")}
# these were palette-quantised in the tested builds (their lossless version is much bigger)
ODD_PALETTE = {"Ambi Verb", "B Dist 7000", "Ten Freq EQ", "Reso Delay", "Party Verb"}
K = 0.5707            # 286x442 canvas -> drawn size (body 396 px tall -> 226 px, the height of the green frame)
FIT_W, FIT_H = 153, 226


def _bbox(im, thr):
    return im.getchannel("A").point(lambda v: 255 if v > thr else 0).getbbox()


def rack_canvas(path):
    """User art -> 286x442 canvas, body 396 px tall, bottom at y=409, centred horizontally."""
    im = Image.open(path).convert("RGBA")
    box = _bbox(im, 128)
    if not box:
        raise ValueError("%s has no opaque pixels" % os.path.basename(path))
    x0, y0, x1, y1 = box
    s = 396 / (y1 - y0)
    r = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    c = Image.new("RGBA", (286, 442), (0, 0, 0, 0))
    ox = round(143 - (round(x0 * s) + round(x1 * s)) / 2)
    oy = 409 - round(y1 * s)
    if ox >= 0 and oy >= 0:
        c.alpha_composite(r, (ox, oy))
    else:
        c.paste(r, (ox, oy))
    return c


def find_rack_art(folder):
    """{pedal name: path} for the PNGs in folder whose file name matches a rack module."""
    found = {}
    if not folder or not os.path.isdir(folder):
        return found
    for f in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(f)
        if ext.lower() != ".png":
            continue
        key = re.sub(r"[^a-z0-9]", "", stem.lower())
        for name, aliases in RACKS.items():
            if key in aliases:
                found[name] = os.path.join(folder, f)
    return found


def encode(im, palette):
    b = io.BytesIO()
    if palette:
        im.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG).save(b, "PNG", optimize=True)
    else:
        im.save(b, "PNG", optimize=True)
    return b.getvalue()


def prescale(name, im, palette):
    """name: 'X.png'; im: RGBA at full size.  Returns the pre-scaled PNG bytes."""
    w, h = im.size
    std = 429 < h < 461 and w < 316 and name != "Anxiety OD.png"
    s = K if std else min(FIT_W / w, FIT_H / h, 1.0)
    new = im if s >= 0.999 else im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return encode(new, palette)


def build(evil, manifest, rack_dir=None, nam_art=None, log=print):
    """Return {name.png: png bytes} for every image the chain art needs.
    nam_art: {'Anxiety OD': path, 'Anxiety OD V2': path (optional)} replaces those pedals' artwork."""
    imgs = manifest["images"]
    racks = find_rack_art(rack_dir)
    if rack_dir:
        log("Art: %d of %d rack modules have your art (%s)" % (len(racks), len(RACKS), rack_dir))
    nam_art = nam_art or {}
    out = {}
    for name in sorted(imgs):
        if name in SKIP:
            continue
        e = imgs[name]
        base = name[:-4]
        stock = Image.open(io.BytesIO(evil[e["pos"]:e["pos"] + e["slot"]]))
        if base in nam_art:
            src = Image.open(nam_art[base])
            palette = src.mode == "P"
            im = src.convert("RGBA")
        elif base in RACKS:
            if base not in racks:
                continue                      # keep the stock strip; the QML ignores strips
            im, palette = rack_canvas(racks[base]), True
        elif base in ODD:
            im = stock.convert("RGBA")
            box = _bbox(im, 16)
            im = im.crop(box)
            palette = stock.mode == "P" or base in ODD_PALETTE
        else:
            im, palette = stock.convert("RGBA"), stock.mode == "P"
        data = prescale(name, im, palette)
        if len(data) > e["slot"]:
            raise ValueError("%s: %d bytes do not fit its %d-byte slot" % (name, len(data), e["slot"]))
        out[name] = data
    return out
