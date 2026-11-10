# BridgeProbe: load sampler

Diagnostic build (`--probe`, Bridge only, no NAM). When USB audio starts, `mx5bridge-probe.sh` writes one CSV line every 2 s for ~2 minutes to
`/media/az01-internal/Evil/mx5bridge/probe.csv` (+ `probe_info.txt` with gadget, interrupts, IRQ affinity and the kernel log). After a **reboot** the Bridge daemon copies both
files to the `MX5Bridge` folder of the USB drive (visible from the PC in storage mode).

Columns (tenths of a percent): `total` and `c0..c3` busy of all / each core; `evil` CPU of all Evil threads (percent of one core), `usbirq` the USB interrupt
thread, `ksoft` ksoftirqd, `irqs` USB interrupts per second, `est` = (evil + usbirq + ksoft) / cores, `err` = total - est, `top` the three busiest Evil threads.

`python3 tools/analyze_probe.py probe.csv` summarises the file and fits `total = a*evil + b*usbirq + c*ksoft + d`.

## Can the total be predicted from cores and threads?
* The sum of per-thread CPU time divided by the number of cores reproduces the total when the listed threads are the whole load; `err` shows what is left
  (daemons, kernel). If `err` stays within about 2 points, the thread figures are enough to *calculate* the total without reading `/proc/stat`.
* That is an *attribution*, not a forecast. Predicting what a new block (e.g. one more NAM instance) would cost needs its own measurement; the per-thread
  figure of the Evil audio thread is the number to use for that.
* The worst core matters more than the total on this device: all USB interrupts are served by CPU0.
