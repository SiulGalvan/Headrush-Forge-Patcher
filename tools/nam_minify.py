#!/usr/bin/env python3
"""Make .nam files smaller and faster to load on the pedal (run this on your PC, not on the pedal).

A .nam file is JSON with a long "weights" list.  The pedal reads every weight as a 32-bit float, so
digits beyond what a float32 can tell apart are wasted bytes that the JSON parser still has to chew
through.  This tool rewrites each weight with the SHORTEST decimal text that still gives exactly the same
float32, drops all whitespace and leaves everything else untouched.  The model sounds bit-identical to
what the pedal already loads from the original file.

    python tools/nam_minify.py  my_models/            -> my_models/minified/*.nam
    python tools/nam_minify.py  a.nam b.nam --out out
    python tools/nam_minify.py  my_models/ --inplace  (overwrites; keeps a .bak copy of each file)

Originals are never modified unless --inplace is given.  Standard library only.
"""
import argparse
import json
import os
import shutil
import struct
import sys


def f32(x):
    """float32 value of a Python float, as the pedal sees it (double -> float cast)."""
    try:
        return struct.unpack("<f", struct.pack("<f", x))[0]
    except OverflowError:
        return x


def shortest(x):
    """Shortest decimal text for x that reads back as the same float32 (and never longer than repr(x))."""
    orig = repr(x)
    if x == 0 or x != x or x in (float("inf"), float("-inf")):
        return orig
    target = f32(x)
    lo, hi = 1, 9                      # 9 significant digits always identify a float32 uniquely
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        s = "%.*g" % (mid, x)
        if f32(float(s)) == target:
            best, hi = s, mid - 1
        else:
            lo = mid + 1
    if best is None:
        return orig
    best = best.replace("e+0", "e+").replace("e-0", "e-")
    return best if len(best) < len(orig) else orig


def minify_text(raw):
    """(new JSON text, number of weights).  Raises ValueError when the file is not a usable .nam."""
    data = json.loads(raw)
    w = data.get("weights") if isinstance(data, dict) else None
    if not isinstance(w, list) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w):
        raise ValueError("no numeric 'weights' list")
    # walk the keys once so the original key order is kept
    parts = []
    for k, v in data.items():
        key = json.dumps(k, ensure_ascii=False)
        if k == "weights":
            parts.append(key + ":[" + ",".join(shortest(float(x)) if isinstance(x, float) else str(x) for x in w) + "]")
        else:
            parts.append(key + ":" + json.dumps(v, separators=(",", ":"), ensure_ascii=False))
    return "{" + ",".join(parts) + "}", len(w)


def verify(old_raw, new_raw):
    a, b = json.loads(old_raw), json.loads(new_raw)
    if list(a) != list(b):
        return False
    for k in a:
        if k == "weights":
            if len(a[k]) != len(b[k]) or any(f32(float(x)) != f32(float(y)) for x, y in zip(a[k], b[k])):
                return False
        elif a[k] != b[k]:
            return False
    return True


def optimize_files(files, backup_dir=None, progress=None):
    """Minify .nam files IN PLACE (what the Block Manager does).

    Each file is rewritten only after the new text was verified to hold exactly the same float32 weights, via a
    temporary file + atomic replace, so a crash or a pulled USB cable cannot leave a half-written model behind.
    The first original of each file is copied to backup_dir (never overwritten by later runs).  Files that cannot be
    improved (already compact, not a .nam, unreadable) are skipped, and one bad file never stops the others.

    Returns {"changed": n, "skipped": n, "before": bytes, "after": bytes, "errors": [(name, message)]}.
    progress(i, total, name) is called before each file.
    """
    out = {"changed": 0, "skipped": 0, "before": 0, "after": 0, "errors": [], "skipped_info": []}
    total = len(files)
    for i, f in enumerate(files):
        name = os.path.basename(str(f))
        if progress:
            progress(i, total, name)
        try:
            raw = open(f, "rb").read()
            text, _n = minify_text(raw.decode("utf-8"))
            new = text.encode("utf-8")
            if len(new) >= len(raw) * 0.995:
                out["skipped"] += 1
                out["skipped_info"].append((name, "ya compacto: solo se ahorraría un %.1f %%" % (100.0 - 100.0 * len(new) / max(1, len(raw)))))
                continue
            if not verify(raw.decode("utf-8"), text):
                out["skipped"] += 1
                out["skipped_info"].append((name, "no se pudo comprobar que el sonido fuera idéntico (se deja sin tocar)"))
                continue
            if backup_dir:
                os.makedirs(backup_dir, exist_ok=True)
                dest = os.path.join(backup_dir, name)
                if not os.path.exists(dest):
                    shutil.copyfile(f, dest)
            tmp = str(f) + ".tmp-min"
            with open(tmp, "wb") as fh:
                fh.write(new)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, f)
            out["changed"] += 1
            out["before"] += len(raw)
            out["after"] += len(new)
        except Exception as e:      # keep going: one odd file must not block the rest
            out["errors"].append((name, str(e)))
            try:
                os.remove(str(f) + ".tmp-min")
            except OSError:
                pass
    if progress:
        progress(total, total, "")
    return out


def info(path):
    """Human-readable diagnostics of one .nam file (why it does or does not shrink)."""
    raw = open(path, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    w = data.get("weights", []) if isinstance(data, dict) else []
    text, n = minify_text(raw.decode("utf-8"))
    nbytes = len(w) and len(json.dumps(w, separators=(",", ":")))
    nmin = len(w) and len(",".join(shortest(float(x)) if isinstance(x, float) else str(x) for x in w)) + 2
    lines = ["file: %s" % os.path.basename(path), "size: %d bytes" % len(raw),
             "keys: %s" % ", ".join(data) if isinstance(data, dict) else "not an object",
             "weights: %d (%.1f chars each in the original, %.1f after minifying)" % (
                 n, nbytes / max(1, n), nmin / max(1, n)),
             "after minify: %d bytes (%.1f %% of the original)" % (len(text.encode("utf-8")), 100.0 * len(text.encode("utf-8")) / len(raw)),
             "first weights as stored: %s" % raw.decode("utf-8")[raw.decode("utf-8").find('"weights"'):][:160].replace("\n", " "),
             "verified identical float32: %s" % verify(raw.decode("utf-8"), text)]
    return "\n".join(lines)


def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d != "minified"]
                out += [os.path.join(root, f) for f in sorted(files)
                        if f.lower().endswith(".nam") and not f.startswith("._")]
        elif os.path.isfile(p):
            out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help=".nam files or folders")
    ap.add_argument("--out", help="output folder (default: a 'minified' folder next to each input)")
    ap.add_argument("--info", action="store_true", help="only print diagnostics of each file")
    ap.add_argument("--inplace", action="store_true", help="overwrite the files (a .bak copy is kept)")
    a = ap.parse_args(argv)
    files = collect(a.paths)
    if a.info:
        for f in files:
            print(info(f) + "\n")
        return 0
    if not files:
        print("No .nam files found.")
        return 1
    before = after = bad = 0
    for f in files:
        raw = open(f, "rb").read()
        try:
            text, n = minify_text(raw.decode("utf-8"))
            new = text.encode("utf-8")
            if not verify(raw.decode("utf-8"), text):
                raise ValueError("verification failed")
        except Exception as e:
            print("SKIP  %s: %s" % (os.path.basename(f), e))
            bad += 1
            continue
        if a.inplace:
            shutil.copyfile(f, f + ".bak")
            dest = f
        else:
            folder = a.out or os.path.join(os.path.dirname(os.path.abspath(f)), "minified")
            os.makedirs(folder, exist_ok=True)
            dest = os.path.join(folder, os.path.basename(f))
        open(dest, "wb").write(new)
        before += len(raw)
        after += len(new)
        print("OK    %-40s %9d -> %9d bytes (%4.1f%%)  %d weights" % (os.path.basename(f), len(raw), len(new),
                                                                     100.0 * len(new) / max(1, len(raw)), n))
    if before:
        print("Total: %.2f MB -> %.2f MB (%.1f%% of the original)" % (before / 1e6, after / 1e6, 100.0 * after / before))
    return 1 if bad and not before else 0


if __name__ == "__main__":
    sys.exit(main())
