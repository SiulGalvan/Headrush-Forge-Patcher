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
y: (wah ? 257 : 255) + (std ? 19 - height : -113 - height / 2)
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


def port(stock_qml):
    m = minify(stock_qml)
    if _norm(m) != _norm(stock_qml):
        raise ArtError("minify changed the QML tokens")
    m = _sub1(m, "readonly property var outlineGlowParameters:",
              "property bool aw: sa.status === Image.Loading || "
              "sa.status === Image.Ready && sa.implicitHeight * 2 > sa.implicitWidth\n"
              "readonly property var outlineGlowParameters:")
    m = _sub1(m, "Image {\nid: stompBody\n", ART + "Image {\nid: stompBody\n")
    m = _sub1(m, BODY, PED + BODY.replace("source:", "visible: !aw\nsource:"))
    m = _sub1(m, "Colorize {\tanchors.fill: stompBody\n", "Colorize {\tanchors.fill: stompBody\nvisible: !aw\n")
    m = _sub1(m, LED, LED + "visible: !aw\n")
    m = _sub1(m, "visible: !ampOrCab() && !signalChainModule.isIR\n",
              "visible: !aw && !ampOrCab() && !signalChainModule.isIR\n")
    m = _sub1(m, "visible: isAPedalConnected || isBPedalConnected",
              "visible: !aw && (isAPedalConnected || isBPedalConnected)")
    m = _sub1(m, 'source: "../../img/stompswitch.png"',
              'source: "../../img/stompswitch.png"; opacity: aw ? 0.01 : 1')
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
