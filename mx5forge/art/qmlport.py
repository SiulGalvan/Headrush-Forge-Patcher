"""Chain pedal art: patch of the stock ActiveStomp.qml (read from the user's own firmware, nothing
of HeadRush's QML is shipped here) and fitting of the result into the original resource slot."""
import random
import re
import string
import zlib


class ArtError(Exception):
    pass


def minify(s):
    """Drop blank lines, full-line // comments, indentation and the trailing '//avoid aliasing' comment."""
    out = []
    for line in s.split("\n"):
        t = line.strip()
        if not t or t.startswith("//"):
            continue
        out.append(re.sub(r"\s*//avoid aliasing of 4x12 cabs$", "", t))
    return "\n".join(out) + "\n"


def _norm(s):
    s = re.sub(r"(?m)^\s*//.*$", "", s)
    s = re.sub(r"//avoid aliasing of 4x12 cabs", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _sub1(s, old, new):
    if s.count(old) != 1:
        raise ArtError("stock ActiveStomp.qml does not look as expected (%d matches for %r)" % (s.count(old), old[:60]))
    return s.replace(old, new)


# --- the art element.  Pedals are stored pre-scaled to the size they are drawn at (std: 1:1);
# odd shapes ("not std") are fitted into the green selection outline.  Strips (racks without user
# art, aspect wider than 2:1) are ignored, so those modules keep the stock look.
ART = '''Image {
id: sa
asynchronous: true
property bool std: implicitHeight > 230
property bool wah: signalChainModule.effectType == 1
property real k: std ? 1 : Math.min((wah ? 127 : 153) / (implicitWidth || 1), 226 / (implicitHeight || 1))
width: implicitWidth * k
height: implicitHeight * k
x: 89.5 - width / 2 + (std ? 0.5 : 0)
y: (wah ? @WAHY@ : 255) + (std ? 19 - height : -113 - height / 2)
source: (activeFx.visible || activePedal.visible) && signalChainModule.type > 0 ? "../../Pages/ModuleEditors/img/" + signalChainModule.moduleTypeName.replace(" 2", "") + ".png" : ""
visible: aw && status === Image.Ready
}
'''
PED = '''Image {
x: sa.x
y: sa.y - 38
width: sa.width
height: sa.height
source: sa.source
visible: aw && sa.status === Image.Ready
}
'''
BODY = ('Image {\nx: -13\ny: -10\nanchors.horizontalCenter: parent.horizontalCenter\n'
        'source: "../../img/EXPFX_Active_1_PedalBody.png"\n}\n')
LED = ('source: signalChainModule.active ? "../../img/FXModule_Active_5_StompSwitchLED.png" '
       ': "../../img/FXModule_Bypassed_3_StompSwitchLED.png"\n')


# Pedalboard 2.7 (Evil.isMG01()): same structure, other formatting, qrc:/ paths and the expression-pedal body is
# drawn 5 px higher (y -15 instead of -10), so the wah art sits 5 px higher too (WAHY 252 instead of 257).
BODY_PB = ('Image {\nx: -13\ny: -15\nanchors.horizontalCenter: parent.horizontalCenter\n'
           'source: "qrc:/img/EXPFX_Active_1_PedalBody.png"\n}\n')


def port(stock_qml, model="mx5"):
    pb = model == "pedalboard"
    m = minify(stock_qml)
    if _norm(m) != _norm(stock_qml):
        raise ArtError("minify changed the QML tokens")
    # Pedalboard: its slot is a few bytes tighter, so the added text uses the numeric values of Image.Loading (2)
    # and Image.Ready (1) - then plain zlib is enough, without the optional zopfli.
    num = (lambda s: s.replace("Image.Loading", "2").replace("Image.Ready", "1")) if pb else (lambda s: s)
    m = _sub1(m, "readonly property var outlineGlowParameters:",
              num("property bool aw: sa.status === Image.Loading || "
                  "sa.status === Image.Ready && sa.implicitHeight * 2 > sa.implicitWidth\n") +
              "readonly property var outlineGlowParameters:")
    art = num(ART.replace("@WAHY@", "252" if pb else "257"))
    m = _sub1(m, "Image {\nid: stompBody\n", art + "Image {\nid: stompBody\n")
    body = BODY_PB if pb else BODY
    m = _sub1(m, body, num(PED) + body.replace("source:", "visible: !aw\nsource:"))
    colorize = "Colorize {\nanchors.fill: stompBody\n" if pb else "Colorize {\tanchors.fill: stompBody\n"
    m = _sub1(m, colorize, colorize + "visible: !aw\n")
    m = _sub1(m, LED, LED + "visible: !aw\n")
    m = _sub1(m, "visible: !ampOrCab() && !signalChainModule.isIR\n",
              "visible: !aw && !ampOrCab() && !signalChainModule.isIR\n")
    m = _sub1(m, "visible: isAPedalConnected || isBPedalConnected",
              "visible: !aw && (isAPedalConnected || isBPedalConnected)")
    sw = 'source: "qrc:/img/stompswitch.png"' if pb else 'source: "../../img/stompswitch.png"'
    m = _sub1(m, sw, sw + "; opacity: aw ? 0.01 : 1")
    return m


def _deflate(b):
    c = zlib.compressobj(9, zlib.DEFLATED, 15, 9)
    out = c.compress(b) + c.flush()
    try:                                  # optional: zopfli squeezes a few dozen bytes more
        import zopfli.zlib as z
        alt = z.compress(b, numiterations=15)
        if len(alt) < len(out):
            out = alt
    except ImportError:
        pass
    return out


def fit(qml, size):
    """(zlib stream of exactly `size` bytes, final QML bytes).  The slot cannot grow, so a trailing
    comment of random characters is tuned until the compressed length is exactly `size`."""
    q = qml if isinstance(qml, bytes) else qml.encode()
    base = _deflate(q)
    if len(base) > size:
        raise ArtError("patched ActiveStomp.qml compresses to %d bytes but the slot holds %d "
                       "(try: pip install zopfli)" % (len(base), size))
    if len(base) == size:
        return base, q
    for seed in range(300):
        rnd = random.Random(seed)
        pad = "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(120))
        for k in range(max(1, (size - len(base)) - 3), 4 * (size - len(base)) + 30):
            t = q + b"//" + pad[:k].encode() + b"\n"
            c = _deflate(t)
            if len(c) == size:
                return c, t
            if len(c) > size + 2:
                break
    raise ArtError("could not fit the QML into exactly %d bytes (got %d)" % (size, len(base)))
