#!/usr/bin/env python3
"""Summarise a probe.csv written by mod/mx5bridge-probe.sh (BridgeProbe images).

  python3 tools/analyze_probe.py probe.csv

Prints the average/peak figures, how good the thread-based estimate of the total CPU is (est vs total) and a least-squares
fit total ~ a*evil + b*usbirq + c*ksoft + d (values per cent of one core, total per cent of all cores).
"""
import csv, sys


def rows(path):
    lines = [l for l in open(path) if not l.startswith("#")]
    out = []
    for r in csv.DictReader(lines):
        try:
            out.append({k: (float(v) / 10 if k not in ("top", "otop", "irqs") else v) for k, v in r.items() if k and v is not None})
            out[-1]["irqs"] = float(r["irqs"])
            out[-1]["top"] = r["top"]
            out[-1]["otop"] = r.get("otop", "")
        except (ValueError, TypeError):
            pass
    return out


def lstsq(X, y):
    n = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(n)] for i in range(n)]
    b = [sum(r[i] * v for r, v in zip(X, y)) for i in range(n)]
    for i in range(n):                                   # gauss
        p = max(range(i, n), key=lambda k: abs(A[k][i]))
        A[i], A[p], b[i], b[p] = A[p], A[i], b[p], b[i]
        if abs(A[i][i]) < 1e-9:
            return None
        for k in range(i + 1, n):
            f = A[k][i] / A[i][i]
            for j in range(i, n):
                A[k][j] -= f * A[i][j]
            b[k] -= f * b[i]
    x = [0] * n
    for i in reversed(range(n)):
        x[i] = (b[i] - sum(A[i][j] * x[j] for j in range(i + 1, n))) / A[i][i]
    return x


def main(path):
    r = rows(path)
    if not r:
        sys.exit("no samples")
    cores = [k for k in r[0] if k.startswith("c") and k[1:].isdigit()]
    avg = lambda k: sum(x[k] for x in r) / len(r)
    print("%d samples, %d cores" % (len(r), len(cores)))
    print("total CPU      avg %.1f %%  peak %.1f %%" % (avg("total"), max(x["total"] for x in r)))
    for c in cores:
        print("  %-4s          avg %.1f %%  peak %.1f %%" % (c, avg(c), max(x[c] for x in r)))
    print("Evil threads   avg %.1f %% of one core, other processes %.1f %%, USB irq thread %.1f %%, ksoftirqd %.1f %%" % (avg("evil"), avg("oth") if "oth" in r[0] else 0, avg("usbirq"), avg("ksoft")))
    if "hirq" in r[0]:
        print("interrupt time avg %.1f %% of all cores; sampler cost avg %.0f ms" % (avg("hirq"), avg("cost") * 10 if "cost" in r[0] else 0))
    print("USB interrupts avg %.0f /s, peak %.0f /s" % (sum(x["irqs"] for x in r) / len(r), max(x["irqs"] for x in r)))
    print("estimate (all threads)/cores: mean error %.2f points, mean |error| %.2f, worst %.2f, samples within 2 points: %d of %d" %
          (sum(x["err"] for x in r) / len(r), sum(abs(x["err"]) for x in r) / len(r), max(abs(x["err"]) for x in r),
           sum(abs(x["err"]) <= 2 for x in r), len(r)))
    X = [[x["evil"], x.get("oth", 0.0), x["usbirq"], 1.0] for x in r]
    w = lstsq(X, [x["total"] for x in r])
    if w:
        res = [x["total"] - sum(a * b for a, b in zip(X[i], w)) for i, x in enumerate(r)]
        print("fit: total = %.3f*evil + %.3f*oth + %.3f*usbirq + %.2f   (rms residual %.2f)" %
              (w[0], w[1], w[2], w[3], (sum(e * e for e in res) / len(res)) ** .5))
    busiest = max(r, key=lambda x: x["total"])
    print("busiest sample: t=%ds total %.1f %%  top threads: %s | other: %s" % (busiest["t"] * 10, busiest["total"], busiest["top"], busiest["otop"]))


if __name__ == "__main__":
    main(sys.argv[1])
